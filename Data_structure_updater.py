# When i add / remove attributes to an object, live data can become invalid
# This script is for trying to resolve mismatches
import os
import json
from Stockpile_class import Stockpile
from Order_class import Order
import shutil
import datetime as dt

stockpiles = {}
orders = {}
serverconfigs = {}

new_pile_att = set(Stockpile.__static_attributes__)
currently_used_pile_att = set()
new_order_att = set(Order.__static_attributes__)
currently_used_order_att = set()
for server in [f for f in os.listdir('Server_data') if os.path.isdir(f'Server_data/{f}')]:
        # try:
        #     with open(f"Server_data/{server}/serverconfig.json", "r") as f:
        #         serverconfigs[server] = {
        #         k: v
        #         for k, v in json.load(f).items()
        #         }
        # except Exception as e:
        #     stockpiles[server] = {}
        try:
            with open(f"Server_data/{server}/stockpiles.json", "r") as f:
                for pile in json.load(f).values():
                    currently_used_pile_att = currently_used_pile_att.union(pile.keys())
        except Exception as e:
            print(e)
        try:
            with open(f"Server_data/{server}/orders.json", "r") as f:
                for order in json.load(f).values():
                     currently_used_order_att = currently_used_order_att.union(order.keys())                     
        except Exception as e:
            print(e)

dropped_pile_atts = currently_used_pile_att.difference(new_pile_att)
added_pile_atts = new_pile_att.difference(currently_used_pile_att)      
dropped_order_atts = currently_used_order_att.difference(new_order_att) 
added_order_atts =  new_order_att.difference(currently_used_order_att)
print(f"Dropped Stockpile attributes: {dropped_pile_atts}\n")
print(f"New Stockpile attributes: {added_pile_atts}\n")
print(f"Dropped Order attributes: {dropped_order_atts}\n")
print(f"New Order attributes: {added_order_atts}\n")

#Backup in case something goes wrong
backup_name = dt.datetime.strftime(dt.datetime.now(),"%m-%d-%Y_%H-%M-%S")
shutil.copytree('Server_data',f"ServerDataBackUps/{backup_name}")

for server in [f for f in os.listdir('Server_data') if os.path.isdir(f'Server_data/{f}')]:
        try:
            with open(f"Server_data/{server}/stockpiles.json", "r") as f:
                all_piles = json.load(f)
                for pile in all_piles.values():
                    for att in dropped_pile_atts:
                        if att in pile.keys():
                            del pile[att]
                    for att in added_pile_atts:
                        # Currently using None as default for basically anything
                        pile[att] = None
            with open(f"Server_data/{server}/stockpiles.json", "w") as f:   
                json.dump({k: v for k,v in all_piles.items()},f, indent=4)
        except Exception as e:
            print(e)
        try:
            with open(f"Server_data/{server}/orders.json", "r") as f:
               all_orders = json.load(f)
               for order in all_orders.values():
                for att in dropped_order_atts:
                    if att in order.keys():
                        del order[att]
                for att in added_order_atts:
                    # Currently using None as default for basically anything
                    order[att] = None
            with open(f"Server_data/{server}/orders.json", "w") as f:
                json.dump({k: v for k,v in all_orders.items()},f, indent=4)                     
        except Exception as e:
            print(e)
print('Done')
