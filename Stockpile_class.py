import datetime
import matplotlib.pyplot as plt
import cv2
import numpy as np
import re
from Hex_mapping import hex_images
import pandas as pd
import io
from Recipe_prep import valid_items
class Stockpile:
    # Set inside init
    # expiration_time = datetime.datetime.now()
    # name = ''
    # # When bot sends out a warning message for a stockpile, message id stored here
    # # Used to update warning when stockpile is refreshed i.a.
    # warning_message_1 = None
    # warning_message_2 = None
    # warning_time_seconds = 0
    # second_warning_time_seconds = 0
    # timer_length_minutes = 0
    # access_code = "Not set"
    # location_image_path = None
    # inventory = None
    # region = None
    # piletype = None

    def __init__(self, name, ingame_name = None, warning_message_1 = None , warning_message_2 = None,
                  warning_time_seconds = 60*60*8, timer_length_minutes = 50*60, second_warning_time_seconds = 60*60*2 ,
                    existing_timer = None, access_code = "Not_set", inventory = None, region = None, piletype = None,
                    x = None, y = None, last_inventory_update = None):
        #When stockpile is not created from scratch but reloaded from json, do not start new timer
        if not (existing_timer):
            self.expiration_time = datetime.datetime.now() + datetime.timedelta(minutes=timer_length_minutes)
        else:
            self.expiration_time = existing_timer
        self.name = name
        self.ingame_name = ingame_name
        self.warning_message_1 = warning_message_1
        self.warning_message_2 = warning_message_2
        self.warning_time_seconds = warning_time_seconds
        self.timer_length_minutes = timer_length_minutes
        self.second_warning_time_seconds = second_warning_time_seconds
        self.access_code = access_code
        #Pandas Dataframe
        self.inventory = inventory
        self.region = region
        self.piletype = piletype
        self.x = x
        self.y = y
        self.last_inventory_update = last_inventory_update

    def refresh(self):
        self.expiration_time = datetime.datetime.now() + datetime.timedelta(minutes=self.timer_length_minutes)
        previous_warning_1 = self.warning_message_1
        previous_warning_2 = self.warning_message_2
        self.warning_message_1 = None
        self.warning_message_2 = None
        return previous_warning_1,previous_warning_2

    def time_to_expiration(self):
        return(self.expiration_time - datetime.datetime.now())


    def check_warning_necessary(self,second_warning_check=False):
        if(self.time_to_expiration().total_seconds() < self.warning_time_seconds and self.time_to_expiration().total_seconds() > 0 and not self.warning_message_1):
            return True
        else:
            return False

    def followup_warning_necessary(self):
        if(self.time_to_expiration().total_seconds() < self.second_warning_time_seconds and 
           self.time_to_expiration().total_seconds() > 0 and 
           self.warning_message_1 and
           not self.warning_message_2):
            return True
        else:
            return False 


    # When bot sends a warning message, store message ID via this function
    def set_warning_message_1(self,message_id):
        self.warning_message_1 = message_id
    
    def set_warning_message_2(self,message_id):
        self.warning_message_2 = message_id

    def get_expiration_time(self):
        py_dt = self.expiration_time.replace(second=0,microsecond=0)  # Whatever your current datetime is
        epoch = round(py_dt.timestamp())  # Timestamp returns a float so round it
        disc_dt = f"<t:{epoch}:F>"
        return disc_dt

    def time_since_last_update(self):
        if not (self.last_inventory_update is None):
        # Foxhole timestamp seems static --> 2h between timezone of device where this bot is run on
            updatetime = datetime.datetime.strptime(self.last_inventory_update,'%Y.%m.%d-%H.%M.%S')+ datetime.timedelta(hours = 2)
            timedelta = datetime.datetime.now()-updatetime
            td_string = ''
            # // = division result as integer
            days,hours,minutes = (timedelta.days, timedelta.seconds//3600, (timedelta.seconds//60)%60)
            return f"{str(days) + " days, "  if days > 0 else ""}{str(hours) + " hours, " if hours > 0 else ""}{str(minutes)+" minutes ago"}"
        else:
            return "Never"

    def info_string(self):
        outstring = "Name: " + self.name + '\t' + \
        "Expiration time: " + self.get_expiration_time() + '\n' + \
        "Access code: " + str(self.access_code) + '\n'
        # "Expiration time: " + str(self.expiration_time.replace(second=0,microsecond=0)) + '\n'

        return outstring
    
    def set_stockpile_info(self, header, full_file, override_loc = False):
        try:
            pattern = '^([^-]+) - ([^-]+) - ([^-]+) - ([^-]+) - X: ([^ ]+) Y: ([^ ]+),([0-9]{4}\\.[0-9]{2}\\.[0-9]{2}-[0-9]{2}\\.[0-9]{2}\\.[0-9]{2})$'
            found = re.search(pattern,header)
            #Header format example:
            #Morgen's Crossing - Allsight - Storage Depot - Public - X: 0.610119 Y: 0.1288359,2026.05.29-13.40.49
            region = found[1]
            pile = found[3]
            ingame_name = found[4]
            x = found[5]
            y = found[6]
            timestamp = found[7]
            global valid_items
            file_inventory = pd.read_csv(io.BytesIO(full_file),index_col=0, skiprows=1)
            valid = set.intersection(set(file_inventory.index),valid_items)
            invalid = set.difference(set(file_inventory.index),valid_items)
            new_inventory = file_inventory.loc[list(valid),:].reset_index()
            new_inventory.columns = pd.Index(["Item","Amount"])
            #Inventory is simply overriden but amount of orders is kept
            if self.inventory is None:
                new_inventory['num_orders_requesting'] = 0
            else:
                new_inventory = new_inventory.merge(self.inventory.loc[:,['Item','num_orders_requesting']],left_on = 'Item',right_on = 'Item')
            self.inventory = new_inventory
            #If header info has not been stored before, do now (mostly setting location info)
            # Seems to be GMT no matter the timezone of the user
            self.last_inventory_update = timestamp
            if ((not self.x) or override_loc):
                # and region in hex_images.keys()
                self.region = region
                self.piletype = pile
                self.x = x
                self.y = y
                self.ingame_name = ingame_name
                # heximage_path = hex_images[region]
                # image_path = 'Hex_images/'+heximage_path
                # heximage = cv2.imread(image_path)
                # height, width = heximage.shape[:2]
                # xshow = int(float(x) * width)
                # yshow = int(float(y) * height)
                # cv2.circle(heximage, (xshow, yshow), radius=5, color=(0, 0, 255), thickness=-1)
                # self.location_image_path = 'Stockpile_locations/'+self.name+'_loc.jpg'
                # self.region = region
                # self.piletype = pile
                # cv2.imwrite(self.location_image_path,heximage)
            # for warning message if some items were not recognized
            return invalid
        except Exception as e:
            print(e)
            return None


    # No clean way to implement a reservation system --> maxflow/ FIFO greedy order allocation/ most exclusive stockpiles first/ keep reserves?
    # None of those would be useful criteria --> instead just show for each stockpile in an order if an item is also requested by a different order
    # def reserve_item(self,item,amount):
    #     if(item in self.inventory.keys()):
    #         total,reserved = self.inventory[item][:2]
    #         self.inventory[item] = total,reserved+amount,total-(reserved+amount)

    #returns pandas table of inventory
    def get_stockpile_contents(self):
        if self.inventory is None:
            return None
        else:
            return self.inventory[(self.inventory.Amount >0) | (self.inventory.num_orders_requesting > 0)]
    
    # Store info about how many orders are requesting a given item from this stockpile
    # Increasing = mark item as reserved by an order, if false --> one less order requesting this item
    def mark_ordered_items(self, order, increasing = True):  
        # ordered_items = list(set(order.order_contents["Item"]).intersection(set(self.inventory["Item"])))
        ordered_items = order.order_contents["Item"]
        #If no inventory info has been set yet but receiving order --> initiate a table just to store the reservation
        if self.inventory is None:
            global valid_items
            self.inventory = pd.DataFrame(columns=pd.Index(["Amount"]),index = pd.Index(valid_items)).reset_index(names = 'Item')
            self.inventory['num_orders_requesting'] = 0
        if increasing:
            self.inventory.loc[self.inventory['Item'].isin(ordered_items),'num_orders_requesting']+=1
        else:
            self.inventory.loc[self.inventory['Item'].isin(ordered_items),'num_orders_requesting']-=1

    # Check that info is available in the bot calling the function
    def get_location_image(self):
        if self.region in hex_images.keys():
            heximage_path = hex_images[self.region]
            image_path = 'Hex_images/'+heximage_path
            heximage = cv2.imread(image_path)
            height, width = heximage.shape[:2]
            xshow = int(float(self.x) * width)
            yshow = int(float(self.y) * height)
            cv2.circle(heximage, (xshow, yshow), radius=5, color=(0, 0, 255), thickness=-1)
            # cv2.imwrite(self.location_image_path,heximage)
        return (heximage,self.region,self.piletype)

    # Functions to make stockpile data convertable to json for saving
    def to_dict(self):
            return {
                "expiration_time": datetime_serial(self.expiration_time),
                "name": self.name,
                "ingame_name": self.ingame_name,
                "warning_message_1": self.warning_message_1,
                "warning_message_2": self.warning_message_2,
                "timer_length_minutes":self.timer_length_minutes,
                "warning_time_seconds":self.warning_time_seconds,
                "second_warning_time_seconds":self.second_warning_time_seconds,
                "access_code":self.access_code,
                "inventory": self.inventory.to_dict() if self.inventory is not None else None,
                "region":self.region,
                "piletype":self.piletype,
                "x":self.x,
                "y":self.y,
                "last_inventory_update": self.last_inventory_update
            }

    
    #Using cls as input arg not really necessary here?
    #Classmethod decorator passes class as the first argument
    @classmethod
    def from_dict(cls, logfile):
        return cls(
            name=logfile["name"],
            ingame_name = logfile["ingame_name"],
            warning_message_1=logfile["warning_message_1"],
            warning_message_2=logfile["warning_message_2"],
            warning_time_seconds=logfile["warning_time_seconds"],
            timer_length_minutes=logfile["timer_length_minutes"],
            existing_timer=datetime.datetime.strptime(logfile["expiration_time"],'%Y-%m-%dT%H:%M:%S.%f'),
            second_warning_time_seconds=logfile["second_warning_time_seconds"],
            access_code=logfile["access_code"],
            inventory=pd.DataFrame(logfile["inventory"]) if not logfile["inventory"] is None else None,
            region=logfile["region"],
            piletype=logfile["piletype"],
            x = logfile["x"],
            y = logfile["y"],
            last_inventory_update= logfile["last_inventory_update"]
            )


#Datetime also needs its own json serialization helper function
#Convert to string on save then create from string on load
def datetime_serial(obj):
    """JSON serializer for datetimes not serializable by default json code"""
    if isinstance(obj, (datetime.datetime)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))

