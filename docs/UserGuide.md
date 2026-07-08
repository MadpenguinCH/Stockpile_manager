# Table of contents
Note: Screenshots in this manual are taken from the development version of the bot. Name of the bot & timer lengths i.a. do not match the active bot.
- [Configuring the bot before first use](#bot-setup)
- [Help! I see a stockpile expiration warning message on discord. What do i do?](#warning-messages---what-to-do)
- [Stockpile timers & codes](#stockpile-code--timer-management)
- [Inventory & order tracking](#stockpile-inventory-management--the-order-system)

# Bot setup
The bot can be added to a server using this [link](https://discord.com/oauth2/authorize?client_id=1498687391823691827&permissions=2147665984&integration_type=0&scope=bot)<br>
After the bot is added to a new server it needs to be configured in order to run properly using...<br>
**/configure_bot**<br>
Input arguments:<br>
*bot_access_role* --> Select a role from your server which is allowed to use the bot's '/'-commands. This means users with this role can retreive stockpile codes, update stockpile information etc.. Make sure you select a role assigned only to members you trust.<br>
*private_output_channel* --> Select the channel where stockpile expiry messages & notifications from the developer will be sent to. Because the warning messages contain the stockpile codes (to make it easier for people to directly resolve the problem without needing to interact with the bot), this output channel should be accessible only to users who you trust with that type of information.<br>
*role_to_ping (optional)* --> The bot sends out two warning messages before a stockpile is about to expire. One of them 8h before expiry and another 2h before.
If this optional argument is set, the second (more urgent) warning message will start with a ping to this role. 

# Warning messages - what to do?
You see this warning in a foxhole related server you're a part of and you're wondering what to do.
<img width="847" height="319" alt="Bild_2026-07-04_193316666" src="https://github.com/user-attachments/assets/6476cc50-1f02-4692-9f8e-1d4188821dec" /><br>

The 'stockpile' which is about to expire is an item storage in typically either a seaport, storage depot or aircraft depot ingame.
What you need to do to resolve the issue is the following:
1. **Locate the building in question in game, walk up to it and press 'E'**<br>
Hopefully the stockpile is named in such a way that you can identify which ingame location it corresponds to.
If not, you can try using the /show_location command on the discord where you saw the warning and select the stockpile mentioned in the warning message
(though this will only work if people also use the inventory tracking functionalities of the bot).

2. **Refresh the stockpile timer**<br>
Following step 1 should take you to the following interface.
Here you need to do two things:<br>
First, if you have never interacted with the stockpile in question before, get access to it by clicking the 'Access Reserve Stockpile' button (purple arrow).<br>
Second, click the 'Refresh Reserve Stockpile' button (red arrow).
<img width="590" height="537" alt="Stockpile_interface" src="https://github.com/user-attachments/assets/5aa8fd56-efa2-43a3-b361-d35c982e8558" /><br>

3. **Use the /refresh command on the stockpile in question**<br>
Simply go to the server where you saw the warning, type /refresh , select the stockpile in question and press enter.

--> That's it. You're done

# Stockpile code & timer management
The first step for stockpile management via this bot is to let the bot know which stockpiles your regiment has access by so it can set up its own simplified copy of the ingame stockpile. This can be achieved by using... <br>

**/add_stockpile**<br>
This command takes as inputs a name for the stockpile (should allow other players to identify type & location of the ingame stockpile in question) and an access code. Both arguments are mandatory but if you don't feel comfortable submitting your access codes to the bot you can just enter some placeholder like "Not set" or whatever.<br>
The moment you submit this command, this starts a timer of 50h corresponding to Foxholes expiry time for reserve stockpiles. If you have created the stockpile some time back and are only now entering it into the bot run the /refresh command after /add_stockpile. 

**/refresh**<br>
The only input argument is the name of the stockpile to refresh --> can be selected from a dropdown menu.
Simply resets the timer of the bot's stockpile copy to 50h. Ideally, this command should be called immediately after the stockpile has been refreshed ingame to keep both timers in-synch.

**/delete_stockpile**
The only input argument is the name of the stockpile to refresh --> can be selected from a dropdown menu.
Once you no longer need to track information about a stockpile for any reason (e.g. captured by the enemy, war ended, released to the public) you can remove it from the list of tracked stockpiles by calling this command.

**/get_stockpiles**<br>
No input argument needed.
Displays information about all stockpiles tracked on this server. Like most other commands of this bot, the results are only shown to whoever calls it, meaning that sensitive information like e.g. access codes shouldn't be visible to anyone else even if the command is accidentally called in a public text channel.

# Stockpile inventory management & the order system

## Uploading inventory data
Since the devs have implemented the option to export a stockpiles contents as a csv, it is now much easier to keep an overview of what items ARE available and compare them to what the regiment WANTS to have available (orders). To export an inventory csv from ingame, hover over the structure on the ingame map and press CTRL + A to pin its tooltip.<br>
<img width="650" height="582" alt="Stockpile_map_tooltip" src="https://github.com/user-attachments/assets/9f75eda3-979a-433d-bb76-05fd09684667" /><br>
If you have access to multiple stockpiles in a storage building (always the case if you're working with reserved stockpiles as public already counts as 1), you can select the stockpile whose contents you want to export from the dropdown (marked in red). Finally, copy the csv corresponding to this stockpile to your clipboard by pressing the button highlighted in purple.

You can now upload this information to the bot and link it to one of the existing stockpiles by using...

**/update_inventory**<br>
This command requires as inputs the name of the stockpile whose contents you want to update (select from dropdown) and the .csv file copied from within the game. Copy it directly into the commands input from your clipboard (no need to put the contents into a textfile and save it as a .csv yourself or anything like that - just CTRL + V). <br>
If anyone has previously uploaded inventory information for the stockpile in question, the bot will check whether the new metadata (stockpile location and ingame name) matches what was previously uploaded and will reject the new data if that's not the case to prevent accidentally uploading data to the wrong stockpile. If you think the currently uploaded data is incorrect you can force the new data to be accepted by setting the optional (under '+1 other') 'override_metadat' argument to True. 

Other than allowing users to now retreive information about the stockpiles inventory and location via */get_inventory* and */show_location* respectively, this inventory information can now be used as information in the order system.

## The order system
The goal of the order system is to let users specify what item they want, let them choose which stockpiles they want to draw items from (both items matching the endproducts ordered as well as intermediate products used in the crafting process) and have the bot check what is already available and what needs to be done to craft what is still missing. To make sure the order is passed to the bot in a format it understands, a template to fill can be retreived via...

**/order_excel_template**<br>
No input arguments are needed.
The bot will send you an excel file to fill out
<img width="620" height="524" alt="image" src="https://github.com/user-attachments/assets/d3596b1f-d567-42bc-97b3-9ba70e104edd" /><br>
You only need to fill out the two columns in the first sheet specifying what type of item you want and how much.
If you open the file in excel, the first column will use autocomplete to make sure you only enter valid item names. If you are using open-office
or some other similar software you might have to copy the item names directly from the second sheet (not properly tested so far).

You can now submit this order by using...

**/place_order**<br>
Input arguments: order_name to identify the order and order_file (the filled out excel from the previous step). To make use of inventory data stored via bot, you can add (currently up to 4) 'linked stockpiles' to the order by selecting stockpiles from a dropdown (accessible via optional arguments = click the '+4 other' whilst you're typing in the command). This tells the bot to check which stockpiles to look in for items to fulfill your order.

You can now generate an overview of ordered & available items plus the crafting process to make up for the difference by using...

**/order_calc**<br>
Input arguments: order_name and optionally setting 'use_mpf' (True / False, defaults to False) to configure whether you have access / plan to use the MPF for crafting items whenever available.
This will generate somewhat ugly but hopefully readable diagrams looking like the following example:
<img width="1802" height="713" alt="image" src="https://github.com/user-attachments/assets/caaf8115-0ce4-411a-8056-66cdf12b4228" /><br>
To the very left of the diagram are the items which were directly ordered. To the right of each item is the facility in which the item can be crafted and to the right of the facility in turn are the ingredients necessary for the crafting process.<br>
Under each item is also the info "{#Needed}/{#Available in linked stockpiles}".<br>
The crafting breakdown should account for MPF discounts and minimum order amounts (if use_mpf is enabled) and subtracts items used for crafting at each "layer" so e.g. in the example shown the stockpiles linked only contain 980 refined materials on the dot. This is enough to craft the base Mk. IV Silverhand's, Heralds and factory products ordered but these refined materials are then no longer considered available to craft the fourth Silverhand which serves as the basis for the Chieftain.

The items in the stockpiles are read at the time when /order_calc is called so if inventories are updated after the order is submitted this should be reflected in the order breakdown.
The command response also includes information about when each stockpile's inventory was last updated (or more specifically it's not based on the time of submission but the timestamp in the uploaded csv file - foxhole's ingame csvs seem to use a static timestamp no matter where the player is connected from. I potentially expect minor issues around summertime saving switches and stuff like that.

### Order system Limitations
1. Currently the bot will only consider facility-based crafting recipes if no other option is available. More customization is planned for future versions.
2. Recipes using liquids will show wrong numbers of items needed for crafting - I currently only convert between crates and items per crate but liquids exist as crates, uncrated containers AND liters of volume in a tank and the recipes i'm using in the background aren't formatted in a way that really accounts for that
3. It's less of a coding issue and more a fundamental problem but the bot doesn't provide a good way to check overlap between orders. E.g. if you have 3 stockpiles A,B and C with 30 bandages each and orders 1&2 requesting 50 each - assuming order 1 draws from A & B and order 2 draws from B & C both orders will see 60 bandages available and assume none need to be crafted when in reality to fulfill both orders you'd need 100 bandages but only 90 are available. But i couldn't really formulate good rules to handle when to 'reserve' items from a stockpile / how to distribute items between orders. So currently it's best to not have a ton of overlapping stockpiles between different orders.
4. The visualization is well... ugly (as you can see in the example above).
5. Recipes for colonial-only equipment are still missing. I plan to include those as well eventually but since I play Warden myself
and have tested the bot mostly with my own regiment the crafting breakdown currently is Warden-focused.

# Miscellaneous
**/timer**<br>
It isn't even really Foxhole related and an experimental feature (so not sure how reliably it works rn) whose main intended ingame-use is to keep track of user-specific timers
like refineries. Just give the the timer a name and tell it how much time until you would like to receive a warning. The bot will then send you a DM directly once the timer is up.












