import json
from Stockpile_class import Stockpile
from Order_class import Order
import datetime as dt
import os
# Save and load functions so the bot doesn't lose track of stockpiles if it temporarily stops/crashes
# Stockpiles and orders are saved together since they are inherently linked
# Indent 4 means each new key gets its own line and different layers of nesting depth are separated by 4 whitespaces
# Folders to be created when config is called
def save_data(server,piles,orders):
    with open(f"Server_data/{server}/stockpiles.json", "w") as f:
        json.dump({k: v.to_dict() for k, v in piles.items()}, f, indent=4)
    with open(f"Server_data/{server}/orders.json", "w") as f:
        json.dump({k: v.to_dict() for k, v in orders.items()}, f, indent=4)

# Stockpiles and orders somewhat linked but custom timers independent
def save_timers(timers):
    # Accessing dateitme by list index a bit ugly but keeping things as simple as possible
    with open('timers.json','w') as f:
        json.dump(list(map(lambda x: x[:2] + [x[2].strftime('%Y-%m-%d %H:%M:%S')], timers)),f)

def save_config(server,config):
    with open(f"Server_data/{server}/serverconfig.json", "w") as f:
        json.dump({k: v for k,v in config.items()},f, indent=4)

# Server configs loaded first to establish which 

def load_data():
    stockpiles = {}
    orders = {}
    serverconfigs = {}
    for server in [f for f in os.listdir('Server_data') if os.path.isdir(f'Server_data/{f}')]:
        try:
            with open(f"Server_data/{server}/serverconfig.json", "r") as f:
                serverconfigs[server] = {
                k: v
                for k, v in json.load(f).items()
                }
        except Exception as e:
            serverconfigs[server] = {}
        try:
            with open(f"Server_data/{server}/stockpiles.json", "r") as f:
                stockpiles[server] = {
                k: Stockpile.from_dict(v)
                for k, v in json.load(f).items()
                }
        except Exception as e:
            stockpiles[server] = {}
        try:
            with open(f"Server_data/{server}/orders.json", "r") as f:
                orders[server] = {
                k: Order.from_dict(v)
                for k, v in json.load(f).items()
                }
        except Exception as e:
            orders[server] = {}
    
    #Timers are not per server but by user
    try:
        with open('timers.json', 'r') as f:
            timers = json.load(f)
        timers = list(map(lambda x: x[:2] + [dt.datetime.strptime(x[2],'%Y-%m-%d %H:%M:%S')], timers))
    except FileNotFoundError:
        timers = []
    return (stockpiles,orders,serverconfigs,timers)
    

# def load_timers():
#     global timers
#     try:
#         with open("timers.json", "r") as f:
#            timers = json.load(f)
#     except FileNotFoundError:
#         timers = []