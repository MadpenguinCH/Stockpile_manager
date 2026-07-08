from discord.ext import commands, tasks
import discord
from discord import app_commands
# Timer and inventory tracking
from Stockpile_class import *
import json
import os
# The images for each ingame hex in Foxhole
from Hex_mapping import pile_icons
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
import io
# Framework for ordering items
from Order_class import *
# from Table_manip import *
import dataframe_image as dfi
import datetime as dt
# Item recipes from foxhole
from Recipe_prep import valid_items
import numpy as np
# Breakdown of how to craft ordered items using what is available in linked stockpiles or raw resources
from Order_breakdown_functions import *
import logging
# import traceback
from logging.handlers import RotatingFileHandler
# Saving and loading bot data to and from json files so it is conserved between crashes/restarts
from Bot_data_save_and_load import *
import re
import secrets
from pathlib import Path
import uuid
import copy

handler = RotatingFileHandler(
    "error.log",
    maxBytes=5_000_000,
    backupCount=20
)
logging.basicConfig(
    handlers=[handler],
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

#Set up bot
intents = discord.Intents.default()
intents.message_content = True

#Read token from separate file 
with open("./Bot_token.txt") as readfile:
    token = readfile.read()

with open("config.json","r") as config:
    loaded=json.load(config)
    warning_timer_seconds = loaded["Warning_timer_seconds"]
    timer_length_minutes = loaded["Timer_length_minutes"]
    second_warning_time_seconds = loaded["second_warning_time_seconds"]
    dev_mode = loaded['Env'] == 'Dev'

# role_mention = "<@&"+str(ping_role_id)+">"

# This is just my personal discord id - anyone can see it anyways so it can be in the code
StockBot = commands.Bot( command_prefix= '!',intents = intents, owner_id=174264687993552896)
#Whenever the bot is restarted, generate a random number and store it to a textfile
#For the update notification messages, this token needs to be entered
#Extra layer of security --> if someone somehow hacks my discord account but not the device on which i run the bot
#They can't check the token and thus not use my account to spam messages to all servers on which bot is installed
random_token = secrets.token_hex(32)
path = Path("admin_token.txt")
path.write_text(random_token)
os.chmod(path, 0o600)

class PasswordModal(discord.ui.Modal, title = "Password verification"):
    pw = discord.ui.Label(text='Password', component=discord.ui.TextInput(style=discord.TextStyle.paragraph))
    msg = discord.ui.Label(text='Message', component=discord.ui.TextInput(style=discord.TextStyle.paragraph))

    def __init__(self):
        super().__init__(title="Password verification",timeout=180)
        self.value = None


    async def on_submit(self, interaction):
        self.value = self.pw.component.value
        self.message = self.msg.component.value
        await interaction.response.defer()
        self.stop()




# GUILD_ID = discord.Object(id=serverid)

#For errors in slash commands
@StockBot.tree.error
async def on_app_command_error(interaction, error):
    if isinstance(error,discord.app_commands.errors.CheckFailure):
        await interaction.response.send_message('You lack the permissions to use this command or the bot has not yet been configured for this server.', ephemeral = True)
    else:
        logging.exception(
            f"Error in command {interaction.command.name}",
            exc_info=error
        )
        await interaction.response.send_message('Something went wrong.', ephemeral = True)

#For errors in other events (mainly the loop which checks the timers)
@StockBot.event
async def on_error(event, *args, **kwargs):
    logging.exception(f"Unhandled exception in event {event}")

stockpiles = {}
orders = {}
serverconfigs = {}
# I need them ordered
timers = []

stockpiles,orders,serverconfigs,timers = load_data()

def has_inventory_permission():
    async def predicate(interaction: discord.Interaction):
        if interaction.guild is None or (not str(interaction.guild.id) in serverconfigs.keys()):
            return False
        allowed_role = serverconfigs[str(interaction.guild.id)]['access_perm_role']
        user_roles = [role.id for role in interaction.user.roles]
        #Does the user have any of the roles which are allowed to use the bot on this server
        # return len(set(allowed_roles).intersection(set(user_roles))) > 0
        return allowed_role in user_roles
    return app_commands.check(predicate)

def is_owner():
    async def predicate(interaction: discord.Interaction):
        return await interaction.client.is_owner(interaction.user)
    return app_commands.check(predicate)


# Provide existing stockpiles as selection for modifying commands like refresh & delete
async def stockpile_autocomplete(
    interaction: discord.Interaction,
    current: str
):  
    if str(interaction.guild.id) in stockpiles.keys():
        return [
            app_commands.Choice(name=name, value=name)
            for name in stockpiles[str(interaction.guild.id)].keys()
            if current.lower() in name.lower()
        ][:10]  # Discord limit
    else:
        return []

async def orders_autocomplete(
    interaction: discord.Interaction,
    current: str
):  
    if str(interaction.guild.id) in orders.keys():
        return [
            app_commands.Choice(name=name, value=name)
            for name in orders[str(interaction.guild.id)].keys()
            if current.lower() in name.lower()
        ][:10]  # Discord limit
    else:
        return []


@StockBot.event
async def setup_hook():
    if dev_mode:
        # These are my development servers --> they got no special privileges it's just where i make sure the bot works how it is intended
        guild = discord.Object(id=1498687058661871838)
        StockBot.tree.copy_global_to(guild=guild)
        await StockBot.tree.sync(guild=guild)
        guild = discord.Object(id=1513649125055398040)
        StockBot.tree.copy_global_to(guild=guild)
        await StockBot.tree.sync(guild=guild)
    else:
        await StockBot.tree.sync()


@StockBot.event
async def on_ready():
    # Bot dev server --> only I myself really need to know slash command synching errors
    # channel = StockBot.get_channel()
    # await channel.send("Bot is ready")
    #Dev server should be immediately synched other servers regular schedule
    # guild = discord.Object(id=1498687058661871838)
    # try:
    #     synced = await StockBot.tree.sync(guild=guild)
    # except Exception as e:
    #     print(f"Error syncing slash commands: {e}")
    stockpile_expiration_check.start()

    
@StockBot.tree.command(name = 'configure_bot', description= 'Define server-specific settings for the bot to run properly')
@app_commands.checks.has_permissions(manage_channels=True)
async def configure_bot(interaction: discord.Interaction, bot_access_role : discord.Role, private_output_channel : discord.TextChannel, role_to_ping : discord.Role = None):
    serverconfigs[str(interaction.guild.id)] = {'access_perm_role': bot_access_role.id, 'warn_channel': private_output_channel.id, 'ping_role': role_to_ping.id if not role_to_ping is None else None}
    if not os.path.isdir(f"Server_data/{interaction.guild.id}"):
        os.mkdir(f"Server_data/{interaction.guild.id}")
    save_config(interaction.guild.id,serverconfigs[str(interaction.guild.id)])
    if not str(interaction.guild.id) in stockpiles.keys():
        stockpiles[str(interaction.guild.id)] = {}
    if not str(interaction.guild.id) in orders.keys():
        orders[str(interaction.guild.id)] = {}
    await interaction.response.send_message('Bot configured and (hopefully) ready to use', ephemeral=True)


@StockBot.tree.command(name = "add_stockpile", description = "Creates new stockpile and starts its timer")
# @app_commands.guilds(GUILD_ID)
# @app_commands.checks.has_role(commands_permission_role)
@has_inventory_permission()
async def add_stockpile(interaction: discord.Interaction, stockpile_name: str, access_code: str):
    stockpiles[str(interaction.guild.id)][stockpile_name] = Stockpile(stockpile_name,
                                            warning_time_seconds= warning_timer_seconds,
                                            timer_length_minutes= timer_length_minutes,
                                            second_warning_time_seconds= second_warning_time_seconds,
                                            access_code= access_code
                                            )
    save_data(interaction.guild.id,stockpiles[str(interaction.guild.id)],orders[str(interaction.guild.id)])
    await interaction.response.send_message(f"added stockpile: {stockpile_name}", ephemeral=True)

@StockBot.tree.command(name = "delete_stockpile", description = "Deletes the specified stockpile from the list")
@app_commands.autocomplete(stockpile_name=stockpile_autocomplete)
# @app_commands.guilds(GUILD_ID)
@has_inventory_permission()
# @app_commands.checks.has_role(commands_permission_role)
async def delete_stockpile(interaction: discord.Interaction, stockpile_name: str):
    del stockpiles[str(interaction.guild.id)][stockpile_name]
    for order in orders[str(interaction.guild.id)].values():
        if stockpile_name in order.linked_stockpiles:
            order.linked_stockpiles.remove(stockpile_name)
    save_data(interaction.guild.id,stockpiles[str(interaction.guild.id)],orders[str(interaction.guild.id)])
    await interaction.response.send_message(f"Deleted stockpile: {stockpile_name}", ephemeral=True)

@StockBot.tree.command(name = "delete_order", description = "Deletes the specified order")
@app_commands.autocomplete(order_name=orders_autocomplete)
# @app_commands.guilds(GUILD_ID)
@has_inventory_permission()
# @app_commands.checks.has_role(commands_permission_role)
async def delete_order(interaction: discord.Interaction, order_name: str):
    for pile in orders[str(interaction.guild.id)][order_name].linked_stockpiles:
        if pile in stockpiles[str(interaction.guild.id)].keys():
            stockpiles[str(interaction.guild.id)][pile].mark_ordered_items(orders[str(interaction.guild.id)][order_name],increasing= False)
    del orders[str(interaction.guild.id)][order_name]
    save_data(interaction.guild.id,stockpiles[str(interaction.guild.id)],orders[str(interaction.guild.id)])
    await interaction.response.send_message(f"Deleted order: {order_name}", ephemeral=True)


@StockBot.tree.command(name = "get_stockpiles", description = "Lists all stockpiles and their expiration times")
# @app_commands.guilds(GUILD_ID)
@has_inventory_permission()
# @app_commands.checks.has_role(commands_permission_role)
async def get_stockpiles(interaction: discord.Interaction):
    message = 'Currently active stockpiles: ' + '\n'
    if(str(interaction.guild.id) in stockpiles.keys() and len(stockpiles[str(interaction.guild.id)]) > 0):
        for stockpile in stockpiles[str(interaction.guild.id)].values():
            message += stockpile.info_string()
    await interaction.response.send_message(message, ephemeral=True)

@StockBot.tree.command(name = "refresh", description = "Refreshes the timer on the specified stockpile")
@app_commands.autocomplete(stockpile_name=stockpile_autocomplete)
# @app_commands.guilds(GUILD_ID)
@has_inventory_permission()
# @app_commands.checks.has_role(commands_permission_role)
async def refresh(interaction: discord.Interaction, stockpile_name: str):
    channel = StockBot.get_channel(serverconfigs[str(interaction.guild.id)]['warn_channel'])
    if channel is None:
        channel = await StockBot.fetch_channel(serverconfigs[str(interaction.guild.id)]['warn_channel'])
    # channel = await StockBot.fetch_channel(serverconfigs[str(interaction.guild.id)]['warn_channel'])
    if(stockpile_name in stockpiles[str(interaction.guild.id)].keys()):
        #If a warning has been sent out for this stockpile, refresh returns said warning so it can be updated
        warning_message_1, warning_message_2 = stockpiles[str(interaction.guild.id)][stockpile_name].refresh()
        save_data(interaction.guild.id,stockpiles[str(interaction.guild.id)],orders[str(interaction.guild.id)])
        await interaction.response.send_message(stockpile_name + ' refreshed' + "\n" + \
                    "New expiration time: " + stockpiles[str(interaction.guild.id)][stockpile_name].get_expiration_time()
                    , ephemeral=True
                    )
        if(warning_message_1):
            message_object = await channel.fetch_message(warning_message_1)
            old_content = message_object.content
            new_content = old_content +'\n' + \
            'Update: Stockpile has been refreshed by ' + interaction.user.global_name
            await message_object.edit(content = new_content)
            await message_object.remove_reaction('❌',StockBot.user)
            await message_object.add_reaction('✅')

        if(warning_message_2):
            message_object = await channel.fetch_message(warning_message_2)
            await message_object.delete()
        
    else:
        await interaction.response.send_message("Stockpile " + stockpile_name + " not found",ephemeral=True)


@StockBot.tree.command(name = "update_inventory", description = "Read the contents from the game-generated stockpile content file")
@app_commands.autocomplete(stockpile_name=stockpile_autocomplete)
# @app_commands.guilds(GUILD_ID)
@has_inventory_permission()
# @app_commands.checks.has_role(commands_permission_role)
async def update_inventory(interaction: discord.Interaction, stockpile_name: str ,file: discord.Attachment, override_metadat: bool = False):
    if file.content_type != "text/plain; charset=utf-8" or file.size > 50000:
        await interaction.response.send_message("Input not recognized", ephemeral=True)
    else:
        content = await file.read()
        content_text = content.decode("utf-8")
        header = content_text.splitlines()[0]
        pattern = '^([^-]+) - ([^-]+) - ([^-]+) - ([^-]+) - X: ([^ ]+) Y: ([^ ]+),([0-9]{4}\\.[0-9]{2}\\.[0-9]{2}-[0-9]{2}\\.[0-9]{2}\\.[0-9]{2})$'
        found = re.search(pattern,header)
        #Header format example:
        #Morgen's Crossing - Allsight - Storage Depot - Public - X: 0.610119 Y: 0.1288359,2026.05.29-13.40.49
        region = found[1]
        piletype = found[3]
        ingame_name = found[4]
        x = float(found[5])
        y = float(found[6])
        #set info and get list of items which weren't recognized
        pile = stockpiles[str(interaction.guild.id)][stockpile_name]
        if (not(pile.last_inventory_update is None)\
            and not override_metadat)\
            and (((region,piletype,ingame_name) != (pile.region,pile.piletype,pile.ingame_name)) \
            or abs(x-float(pile.x)) > 0.001 or abs(y-float(pile.y)) > 0.001):
            msg = f"Stored stockpile metadata doesn't match new input header - cancelling update.\n\
            Set optional argument override_metadat to true if you want to force the update\n\
            Metadata (Stored | Input):\n\
                Region: {pile.region} | {region}\n\
                Piletype: {pile.piletype} | {piletype}\n\
                Ingame name: {pile.ingame_name} | {ingame_name}\n\
                x,y: ({pile.x},{pile.y}) | ({x},{y})"
            await interaction.response.send_message(msg,ephemeral=True)
        else:
            invalid_items = stockpiles[str(interaction.guild.id)][stockpile_name].set_stockpile_info(header,content, override_loc = override_metadat)
            invalid_string = ('\nUnrecognized items: \n' + str([i for i in invalid_items])) if invalid_items else ''
            save_data(interaction.guild.id,stockpiles[str(interaction.guild.id)],orders[str(interaction.guild.id)])
            await interaction.response.send_message('Stockpile contents updated'+invalid_string,ephemeral=True)

@StockBot.tree.command(name = "get_inventory", description = "Print the last known contents of the stockpile")
@app_commands.autocomplete(stockpile_name=stockpile_autocomplete)
# @app_commands.guilds(GUILD_ID)
@has_inventory_permission()
# @app_commands.checks.has_role(commands_permission_role)
async def get_inventory(interaction: discord.Interaction, stockpile_name: str):
    try:
        pile = stockpiles[str(interaction.guild.id)][stockpile_name]
        inv_table = pile.get_stockpile_contents()
        if inv_table is None:
            await interaction.response.send_message(content='No inventory info has been uploaded for this stockpile',ephemeral=True)
        #Embeds have higher character limits than simple interaction responses so using embed for displaying tables
        else:
            # inv_table = inv_table.reset_index()
            # inv_table = inv_table.rename(columns={"index": "Item", "0": "Amount"})
            figname = stockpile_name+"_inventory.png"
            dfi.export(inv_table.style.hide(),figname,table_conversion="matplotlib")
            file = discord.File(figname)
            await interaction.response.send_message(f"Last updated {pile.time_since_last_update()}\n\
                                                    ",file=file,ephemeral = True)
            file.close()
            os.remove(figname)
    except Exception as e:
        print(e)


@StockBot.tree.command(name = "show_location", description = "Show an image with the location of the stockpile highlighted on the hexmap")
@app_commands.autocomplete(stockpile_name=stockpile_autocomplete)
# @app_commands.guilds(GUILD_ID)
@has_inventory_permission()
# @app_commands.checks.has_role(commands_permission_role)
async def show_location(interaction: discord.Interaction, stockpile_name: str):
    if stockpile_name in stockpiles[str(interaction.guild.id)].keys():
        pile = stockpiles[str(interaction.guild.id)][stockpile_name]
        if not(pile.last_inventory_update is None):
            image,region,piletype = stockpiles[str(interaction.guild.id)][stockpile_name].get_location_image()
            tmpfile_path = f"{str(interaction.guild_id)}_{stockpile_name}_loc.jpg"
            cv2.imwrite(tmpfile_path,image)
            myfile = discord.File(tmpfile_path,filename='Location.png')
            loc_message = discord.Embed(title="Hex name: " + region, colour=discord.Colour(0x7d25b9), description="Showing location of the " + stockpile_name + " stockpile" +'\n'
                                        + "If you can't find the hex in question, use the ingame Map's (M) search function in the top right corner")
            loc_message.set_image(url="attachment://Location.png")
            files = [myfile]
            if piletype in pile_icons.keys():
                iconpath = 'Icons/'+pile_icons[piletype]
                thumbfile = discord.File(iconpath,filename='icon.png')
                loc_message.set_thumbnail(url = "attachment://icon.png")
                files.append(thumbfile)
            else:
                thumbfile = None
            await interaction.response.send_message(files=files,embed=loc_message, ephemeral=True)
            myfile.close()
            os.remove(tmpfile_path)
        else:
            await interaction.response.send_message("No csv was ever uploaded for this stockpile - location info not available", ephemeral=True)
    else:
        await interaction.response.send_message("No stockpile with this name found for this server", ephemeral=True)

@StockBot.tree.command(name = "order_excel_template", description = "Returns an excel to fill in & submit with /place_order")
# @app_commands.guilds(GUILD_ID)
@has_inventory_permission()
# @app_commands.checks.has_role(commands_permission_role)
async def order_excel_template(interaction: discord.Interaction):
    order_excel = discord.File('Ordersheet_input.xlsx')
    await interaction.response.send_message('Fill in the items to order and the ordered amount in the first sheet then submit with /place_order', file=order_excel, ephemeral=True)
    order_excel.close()



@StockBot.tree.command(name = "place_order", description = "Place an item order by uploading an excel and specifying which stockpiles to draw from")
@app_commands.autocomplete(linked_stockpile_1=stockpile_autocomplete,
                           linked_stockpile_2=stockpile_autocomplete,
                           linked_stockpile_3=stockpile_autocomplete,
                           linked_stockpile_4=stockpile_autocomplete)
# @app_commands.guilds(GUILD_ID)
@has_inventory_permission()
# @app_commands.checks.has_role(commands_permission_role)
async def place_order(interaction: discord.Interaction,
                      order_name: str,
                      order_file: discord.Attachment,
                      linked_stockpile_1: str | None = None, 
                      linked_stockpile_2:str | None = None,
                      linked_stockpile_3:str | None = None,
                      linked_stockpile_4:str | None = None):
    try:
        selected = [
            s for s in (linked_stockpile_1, linked_stockpile_2, linked_stockpile_3, linked_stockpile_4)
            if s is not None
        ]
        # Download the attachment bytes
        data = await order_file.read()
        order_content = pd.read_excel(io.BytesIO(data),index_col=0,sheet_name='Order')
        invalid_items = set.difference(set(order_content.index),valid_items)
        valid = set.intersection(set(order_content.index),valid_items)
        response_message = "Order has been placed\n"
        if(invalid_items):
            response_message += "Unrecognized items from the order excel:"
            response_message += str([item for item in invalid_items])
        order_content = order_content.loc[list(valid),:]
        order_content = order_content.reset_index()
        order_content.columns = pd.Index(['Item','Amount'])
        someorder = Order(order_content,[stockpiles[str(interaction.guild.id)][pile].name for pile in selected])
        for pile in selected:
            stockpiles[str(interaction.guild.id)][pile].mark_ordered_items(someorder)
        orders[str(interaction.guild.id)][order_name] = someorder
        save_data(interaction.guild.id,stockpiles[str(interaction.guild.id)],orders[str(interaction.guild.id)])
        await interaction.response.send_message(response_message,ephemeral=True)
    except Exception as e:
        print(e)

# Mostly replaced by order calc
# @StockBot.tree.command(name = "check_order", description = "Check the status of an order")
# @app_commands.autocomplete(order_name = orders_autocomplete)
# # @app_commands.guilds(GUILD_ID)
# @has_inventory_permission()
# # @app_commands.checks.has_role(commands_permission_role)
# async def check_orders(interaction: discord.Interaction, order_name: str):
#     order = orders[str(interaction.guild.id)][order_name]
#     overview = order.get_status([stockpiles[str(interaction.guild.id)][pile] for pile in order.get_linked_piles()])
#     # overview = overview.reset_index().style.hide(axis = "index")
#     figname = 'order_overview.png'
#     dfi.export(overview.hide(),figname,table_conversion='matplotlib')
#     file = discord.File(figname)
#     await interaction.response.send_message("Cells highlighted if the same item is requested by one (yellow) or more (red) different orders linked to the same stockpile",file=file, ephemeral = True)
#     file.close()
#     os.remove(figname)

#WIP
# @StockBot.tree.command(name = "inventory_csv_dump", description = "Submit multiple stockpile inventories at once")
# @app_commands.guilds(GUILD_ID)
# @app_commands.checks.has_role(commands_permission_role)
# async def inventory_csv_dump(interaction: discord.Interaction,
#                       csv1: discord.Attachment, 
#                       csv2:discord.Attachment | None = None,
#                       csv3:discord.Attachment | None = None,
#                       csv4:discord.Attachment | None = None,
#                       csv5:discord.Attachment | None = None,
#                       csv6:discord.Attachment | None = None,
#                       csv7:discord.Attachment | None = None,
#                       csv8:discord.Attachment | None = None,
#                       csv9:discord.Attachment | None = None,
#                       csv10:discord.Attachment | None = None,
#                       csv11:discord.Attachment | None = None,
#                       csv12:discord.Attachment | None = None,
#                       csv13:discord.Attachment | None = None,
#                       csv14:discord.Attachment | None = None,
#                       csv15:discord.Attachment | None = None,
#                       csv16:discord.Attachment | None = None
#                       ):
#     for file in [csv1, csv2, csv3, csv4, csv5, csv6, csv7, csv8, csv9, csv10, csv11, csv12, csv13, csv14, csv15, csv16]:
#         if not file is None:
#             if file.content_type != "text/plain; charset=utf-8" or file.size > 50000:
#                 continue
#             else:
#                 content = await file.read()
#                 content_text = content.decode("utf-8")
#                 header = content_text.splitlines()[0]
#                 print(header)

@StockBot.tree.command(name = "order_calc", description = "Check the status of an order")
@app_commands.autocomplete(order_name = orders_autocomplete)
# @app_commands.guilds(GUILD_ID)
@has_inventory_permission()
# @app_commands.checks.has_role(commands_permission_role)
async def order_calc(interaction: discord.Interaction, order_name: str, use_mpf: bool = False):
    order = orders[str(interaction.guild.id)][order_name]
    ordered_items = order.order_contents
    known_inventories = []
    for pile in order.linked_stockpiles:
        if stockpiles[str(interaction.guild.id)][pile].inventory is not None:
            known_inventories.append(stockpiles[str(interaction.guild.id)][pile].get_stockpile_contents().loc[:,['Item','Amount']].rename(columns={"Amount": pile}))
    #Check if empty inventories are stored as none or just skipped
    if len(known_inventories) >= 1:
        combined_inventory = known_inventories[0]
        for extra in range(1,len(known_inventories)):
            combined_inventory = combined_inventory.merge(known_inventories[extra],how = 'outer', left_on = 'Item', right_on = 'Item').fillna(0)
    elif len(known_inventories) == 0:
        combined_inventory = pd.DataFrame(columns=['Item','Amount','num_orders_requesting'])
    for col in combined_inventory.columns[1:]:
        combined_inventory[col] = pd.to_numeric(combined_inventory[col],downcast = 'integer')
    recipe_choices = pd.DataFrame(columns = ['Item','Facility'])
    draws = []
    crafts = []
    combined_inventory['total available'] = combined_inventory.iloc[:,1:].sum(axis = 1)
    # Vehicles can be present directly or as crate --> break down order into number of ordered items total
    ordered_items = unpack_inventory(ordered_items.rename(columns = {'Amount':'total available'})).rename(columns = {'total available': 'Amount'})
    combined_inventory = unpack_inventory(combined_inventory.loc[:,['Item','total available']])
    starting_point = ordered_items.merge(combined_inventory, how = 'left', on = 'Item').fillna(0)
    starting_point['accounted_for'] = starting_point.to_numpy()[:,1:].min(axis = 1)
    starting_point['missing'] = starting_point['Amount'] - starting_point['accounted_for']
    
    included_items = []
        
    craftView = discord.ui.View(timeout=180)
    #name for temporary file
    fname = f"{uuid.uuid4()}.png"

    for row in range(starting_point.shape[0]):
        Iname = starting_point.loc[row,'Item']
        needed = starting_point.loc[row,'Amount']
        available = starting_point.loc[row,'accounted_for']

        ibutton = discord.ui.Button(
            label=f"{Iname}: {str(int(available))}/{str(int(needed))}",
            style = discord.ButtonStyle.success if needed == available else discord.ButtonStyle.gray,
            # is np.False_ or np.True_ --> convert to JUST bool
            disabled= bool(needed == available)
        )

        async def buttonpress(interaction,item = Iname, button = ibutton):
            if item not in included_items:
                included_items.append(item)
                button.style = discord.ButtonStyle.blurple
            else:
                included_items.remove(item)
                button.style = discord.ButtonStyle.gray
            ordered_items[ordered_items['Item'].isin(included_items)]

            fname = f"{uuid.uuid4()}.png"
            if len(included_items) > 0:
                order_calc_static(ordered_items[ordered_items['Item'].isin(included_items)], copy.deepcopy(combined_inventory),fname, use_mpf)
                breakdown_image = discord.File(fname)
                imfile = [breakdown_image]
            else:
                imfile = []

            await interaction.response.edit_message(
                content= "Click on items to include/exclude them in visual crafting breakdown",
                view = craftView,
                attachments = imfile
            )


            if len(imfile) != 0:
                breakdown_image.close()
                os.remove(fname)

        ibutton.callback = buttonpress
        craftView.add_item(ibutton)
    await interaction.response.send_message('Click on items to include/exclude them in visual crafting breakdown',view = craftView,ephemeral=True)
    
        
def order_calc_static(ordered_items, combined_inventory,filename,use_mpf):
    recipe_choices = pd.DataFrame(columns = ['Item','Facility'])
    draws = []
    crafts = []

    while True:
        drawable = draw_from_inventory(ordered_items,combined_inventory)
        draws.append(drawable)
        if(all(drawable['missing']==0)):
            break

        combined_inventory['total available'] = combined_inventory['total available'].to_numpy() - combined_inventory.merge(drawable.loc[:,['Item','Accounted for']], how = 'left', left_on = 'Item', right_on = 'Item').fillna(0)['Accounted for'].to_numpy()
        craft_order = drawable.loc[:,['Item','missing']].loc[drawable['missing'] != 0]
        new_order,alt_recipes = calc_recipes(craft_order, use_MPF=use_mpf)
        if(new_order is None):
            break
        crafts.append(new_order)
        recipe_choices = pd.concat([recipe_choices,alt_recipes])
        ordered_items = new_order.loc[:,['Ingredient','Amount']].rename(columns = {'Ingredient': 'Item'}).groupby('Item').sum()
    plot_extent = draw_diagram(copy.deepcopy(draws),copy.deepcopy(crafts),filename)
    draw_diagram(draws,crafts,filename,plot_extent)


@StockBot.tree.command(name = "send_notification", description = "Send info about e.g. updates / downtimes & new features to all servers")
@is_owner()
async def send_notification(interaction: discord.Interaction):
    global random_token
    pwcheck = PasswordModal()
    await interaction.response.send_modal(pwcheck)
    #awaits until pwcheck is either submitted or times out
    timed_out = await pwcheck.wait()
    if timed_out:
        return
    
    if not secrets.compare_digest(pwcheck.value, random_token):
        await interaction.followup.send("Wrong password", ephemeral= True)
        return
    
    if secrets.compare_digest(pwcheck.value, random_token):
        random_token = secrets.token_hex(32)
        path = Path("admin_token.txt")
        path.write_text(random_token)
        os.chmod(path, 0o600)
        for guild in serverconfigs.keys():
            channel = StockBot.get_channel(serverconfigs[guild]['warn_channel'])
            if channel is None:
                channel = await StockBot.fetch_channel(serverconfigs[guild]['warn_channel'])
            await channel.send(pwcheck.message)
            #If it fails for one server just try the other ones anyways but log the error
        await interaction.followup.send("Sent server notifications",ephemeral=True)


# Help message
# Commands generated using https://leovoel.github.io/embed-visualizer/
help_message = discord.Embed(title="Stockpile bot", colour=discord.Colour(0x7d25b9))
# help_message.set_footer(text="All responses sent by this bot as well as the /message used to call the bot are only visible to the user who uses the respective command. The only publicly visible messages are the two warnings sent before a stockpile is about to expire (1st message without a ping 8h before expiry and a 2nd message with ping 2h before expiry)")
help_message.add_field(name="General documentation", value="A general overview over what this bot does + code can be found on [Github](https://github.com/MadpenguinCH/Stockpile_manager)",inline=False)
help_message.add_field(name="Quickstart manual", value="An overview of the bots commands can be found [here](https://github.com/MadpenguinCH/Stockpile_manager/blob/main/docs/UserGuide.md)",inline=False)


@StockBot.tree.command(name = "help", description = "Get an overview of this bot's commands")
# @app_commands.guilds(GUILD_ID)
async def help(interaction: discord.Interaction):
    await interaction.response.send_message(embed = help_message,ephemeral=True)

@StockBot.tree.command(name = "timer", description = "Set a custom timer with no other info attached")
# @app_commands.guilds(GUILD_ID)
async def help(interaction: discord.Interaction, name:str, hours: int, minutes: int):
    reminder_time = datetime.datetime.now() + datetime.timedelta(hours=hours, minutes=minutes)
    timers.append([interaction.user.id, name, reminder_time])
    # Sort by time to expiry --> to save looping over the entire list each periodic check, only loop until first timer which is still pending
    timers.sort(key = lambda x: x[2])
    save_timers()
    await interaction.response.send_message('Timer set: '+ str(hours) + 'h ' + str(minutes) + 'min', ephemeral= True)
    

@tasks.loop(minutes=1)
async def stockpile_expiration_check():
    for guild in serverconfigs.keys():
        try:
            channel = StockBot.get_channel(serverconfigs[guild]['warn_channel'])
            if channel is None:
                channel = await StockBot.fetch_channel(serverconfigs[guild]['warn_channel'])
            ping_role_id = serverconfigs[guild]['ping_role']
            if(len(stockpiles[guild]) != 0):
                for stockpile in stockpiles[guild].values():
                    # with open('loop_debug_print.txt','a') as f:
                    #     f.write(stockpile.name)
                    if(stockpile.check_warning_necessary()):
                        # with open('loop_debug_print.txt','a') as f:
                        #     f.write(f"{stockpile.name} sending warning in {channel.name}"   )
                        message = await channel.send('Stockpile expiring soon:' + '\n' + stockpile.info_string() + \
                        '\nPlease refresh the stockpile in game then use the /refresh command to update the timer'+\
                        "\nSee /help for an overview of this bot's commands\n"+\
                            "\n If a stockpile inventory has been uploaded at any point you can display the stockpile location with /show_location")
                        stockpile.set_warning_message_1(message.id)
                        await message.add_reaction('❌')
                        save_data(guild,stockpiles[guild],orders[guild])
                    if(stockpile.followup_warning_necessary()):
                        role_mention = f"<@&{ping_role_id}> " if not ping_role_id is None else ""
                        message = await channel.send(role_mention+'Reminder: Stockpile expiring soon:' + '\n' + stockpile.info_string())
                        stockpile.set_warning_message_2(message.id)
                        save_data(guild,stockpiles[guild],orders[guild])
        #If it fails for one server just try the other ones anyways but log the error
        except Exception as error:
            logging.exception(
            f"Error in stockpile timer check loop",
            exc_info=error
            )
            continue
            
    for timer in timers:
        if timer[2] <= dt.datetime.now():
            user = await StockBot.fetch_user(timer[0])
            await user.send('Timer is up: '+ timer[1])
            timers.remove(timer)
            save_timers(timers)
        # Sorted by datetime so all timers after first to not send a warning should also still be pending
        else:
            break

# Run bot continuously
StockBot.run(token)
