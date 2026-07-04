import pandas as pd
from Stockpile_class import *

#Visualization of order
#Returns the function color_from_meta with the right meta as part of the single-argument function so one can just call df.style.apply(make_color_from_meta(meta))
def make_color_from_meta(meta):

    def color_from_meta(df):
        styles = pd.DataFrame("", index=df.index, columns=df.columns)

        for col in meta.columns:
            for idx in meta.index:
                value = meta.loc[idx, col]

                if value == 1:
                    color = "white"
                elif value == 2:
                    color = "yellow"
                elif value > 2:
                    color = "red"
                else:
                    color = "white"

                styles.loc[idx, col] = f"background-color: {color}"

        return styles

    return color_from_meta

class Order:
    #Pandas Data frame with contents
    order_contents = None
    #linked_stockpiles here only stores the names
    #When working with the actual contents, will need to be passed from outside
    linked_stockpiles = None

    def __init__(self, order_contents = None, linked_stockpiles = None):
        self.order_contents = order_contents
        self.linked_stockpiles = linked_stockpiles

    def get_linked_piles(self):
        return self.linked_stockpiles

    def get_status(self,linked_stockpiles):
        # linked_inventories = [pile.get_stockpile_contents() for pile in linked_stockpiles if linked_stockpiles.inventory is not None else None]
        known_inventories = []
        for pile in linked_stockpiles:
            if pile.inventory is not None:
                known_inventories.append(pile.get_stockpile_contents())
        order_overview = self.order_contents
        #Check if empty inventories are stored as none or just skipped
        for inventory in range(len(known_inventories)):
            order_overview = order_overview.merge(known_inventories[inventory],how = 'left',left_on = 'Item', right_on = 'Item').fillna(0)
        #Due to introduction of NA's, some cols are converted to float --> cast back  to int
        #First col is name so skipped
        for col in order_overview.columns[1:]:
            order_overview[col] = pd.to_numeric(order_overview[col],downcast = 'integer')
        color_flags = order_overview.loc[:,order_overview.columns.str.match('num_orders_requesting')]
        order_overview = order_overview.loc[:,[not i for i in (order_overview.columns.str.match('num_orders_requesting'))]]
        order_overview.columns = pd.Index(['Item','Ordered']+[pile.name for pile in linked_stockpiles])
        color_flags.columns = pd.Index([pile.name for pile in linked_stockpiles])
        #Add up all stockpiles
        order_overview['total available'] = order_overview.iloc[:,2:].sum(axis = 1)
        order_overview['needed'] = order_overview['Ordered'] - order_overview['total available']
        order_overview['needed'] = order_overview['needed'].clip(lower = 0)
        # Apply coloring for visualization
        # order_overview = order_overview.style.background_gradient(
        # cmap="RdYlGn",
        # subset=color_flags.columns,
        # gmap=color_flags,
        # axis = None
        # )
        return order_overview.style.apply(make_color_from_meta(color_flags), axis = None)

    def to_dict(self):
        return {
            "order_contents": self.order_contents.to_dict() if self.order_contents is not None else None,
            "linked_stockpiles":[pile for pile in self.linked_stockpiles]
        }
    
     #Using cls as input arg not really necessary here?
    #Classmethod decorator passes class as the first argument
    @classmethod
    def from_dict(cls, logfile):
        return cls(
            order_contents=pd.DataFrame(logfile["order_contents"]) if not logfile["order_contents"] is None else None,
            linked_stockpiles = logfile["linked_stockpiles"]
            )

        
