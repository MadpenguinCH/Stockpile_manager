import copy
import math
from Recipe_prep import recipes, item_infos, nine_crate_discountable,valid_items
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt


def draw_from_inventory(ordered_items, combined_inventory):
    overview = ordered_items.merge(combined_inventory,how = 'left', left_on = 'Item', right_on = 'Item').fillna(0)
    overview['Accounted for'] = overview.loc[:,['Amount','total available']].min(axis = 1)
    overview['missing'] = overview['Amount'] - overview['Accounted for']
    return overview

# At the very start unpack all items in the order so that it doesn't matter if a vehicle was ordered crated or uncrated
#Unsure how to make distinction between liquid (crate), liquid (container), liquid (L)
# For now unpack everything even resources which can be used as inputs for recipes
def unpack_inventory(combined_inventory):
    crate_inventory = combined_inventory.loc[combined_inventory['Item'].str.contains('\\(Crate\\)')]
    #Tilde works as negation operator
    direct_inventory = combined_inventory.loc[~combined_inventory['Item'].str.contains('\\(Crate\\)')]
    crate_inventory = crate_inventory.merge(item_infos, how = 'left', left_on = 'Item', right_on = 'Item name')
    crate_inventory['Item'] = crate_inventory['Item'].str.extract(r'(.*) \(Crate\)')
    crate_inventory['total available'] = crate_inventory['total available'] * crate_inventory['Items per Crate']
    crate_inventory = crate_inventory.loc[:,['Item','total available']]
    # Join and access of total available_x and _y fails if there's two tables to merge to begin with
    if direct_inventory.shape[0] != 0:
        full_inventory = crate_inventory.merge(direct_inventory,how = 'outer', on = 'Item').fillna(0)
        full_inventory['total available'] = full_inventory['total available_x'] + full_inventory['total available_y']
        full_inventory = full_inventory.loc[:,['Item','total available']]
    else:
        full_inventory = crate_inventory.fillna(0)
    return full_inventory

# Use recipe info before splitting factory; MPF --> recipes in this exact combo have 9 crates max rest 5
def calc_recipes(ordered_items, use_MPF = False):
    try:
        craft_order = ordered_items.merge(recipes,how = 'left', on = 'Item')
        if use_MPF:
            #artificially prioritize MPF
            craft_order.loc[craft_order['Facility'] == 'MPF','Prio'] = 0
        craft_order.sort_values(by = ['Item','Prio'], ascending = [True,True], inplace=True)
        alt_recipes = craft_order[craft_order.loc[:,['Item','missing']].duplicated()]
        used_recipes = craft_order[~craft_order.loc[:,['Item','missing']].duplicated()]
        used_recipes = used_recipes.loc[~used_recipes['Facility'].isna()]
        #Later temporarily adding lists so here object instead of just int/float
        used_recipes['recipe_multiples'] = np.ceil(used_recipes['missing']/used_recipes['# Output']).astype(object)
        if not pd.isna(used_recipes['Ingredients']).all():
            # Planning to later give control over which faci for which item so there will be a scenario in which some items = MPF but general use_mpf False
            mpf_items_ordered = used_recipes.loc[used_recipes['Facility'] == 'MPF']
            #Split order into multiples of 5 or 9 mpf crate recipes and use a different recipe for the rest
            if(mpf_items_ordered.shape[0] != 0):
                mpf_items_ordered.loc[mpf_items_ordered['Item'].isin(nine_crate_discountable),'recipe_multiples'] = mpf_items_ordered.loc[mpf_items_ordered['Item'].isin(nine_crate_discountable),'recipe_multiples'].apply(lambda x: [int(x/9)*9,x%9])
                mpf_items_ordered.loc[~mpf_items_ordered['Item'].isin(nine_crate_discountable),'recipe_multiples'] = mpf_items_ordered.loc[~mpf_items_ordered['Item'].isin(nine_crate_discountable),'recipe_multiples'].apply(lambda x: [int(x/5)*5,x%5])
                mpf_items_ordered = mpf_items_ordered.explode('recipe_multiples', ignore_index = True)
                # Remove invalid 
                # If it's not even enough for a single 3-crate MPF order --> would drop ALL info about that ordered item
                # Keep the first invalid mpf order --> in that case the entire order has to be accounted by different recipes
                mpf_items_ordered = mpf_items_ordered.loc[((mpf_items_ordered['recipe_multiples'] >= 3) | (~mpf_items_ordered.drop('recipe_multiples',axis = 1).duplicated()))]
                #Group by all BUT recipe multiples
                mpf_items_ordered = mpf_items_ordered.groupby(['Item','missing','Facility','Ingredients','# Output','Prio','Signature'],as_index = False).sum()
                mpf_items_ordered['unaccounted'] = mpf_items_ordered['missing'] - (mpf_items_ordered['# Output'] * mpf_items_ordered['recipe_multiples'])
                # Fully split order --> MPF part only sees as much missing as is not handled by separate order
                # If if MPF prodcues more than needed --> keep 'missing' as is
                # If MPF part insufficient --> MPF only sees the 'clean' part of the order and order facility is the one treated as producing the excess
                mpf_items_ordered.loc[mpf_items_ordered['unaccounted'] > 0,'missing'] = (mpf_items_ordered.loc[mpf_items_ordered['unaccounted'] > 0,'# Output'] * mpf_items_ordered.loc[mpf_items_ordered['unaccounted'] > 0,'recipe_multiples']).astype(float)
                separate_craft = mpf_items_ordered.loc[mpf_items_ordered['unaccounted'] > 0,['Item','unaccounted']].rename(columns = {'unaccounted' : 'missing'})
                # the '0 multiples' ordes were used only to know how much to delegate to other facis --> need to be dropped now
                mpf_items_ordered = mpf_items_ordered.loc[mpf_items_ordered['recipe_multiples'] != 0]
                if separate_craft.shape[0] != 0:
                #Repeat breakdown but here with MPF prio = 1000 so it never gets chosen
                    separate_order = separate_craft.merge(recipes,how = 'left', on = 'Item')
                    separate_order.loc[separate_order['Facility'] == 'MPF','Prio'] = 1000
                    separate_order.sort_values(by = ['Item','Prio'], ascending = [True,True], inplace=True)
                    #For now just take first non-MPF recipe
                    # alt_recipes = separate_order[separate_order.loc[:,['Item','missing']].duplicated()]
                    separate_recipes = separate_order[~separate_order.loc[:,['Item','missing']].duplicated()]
                    separate_recipes = separate_recipes.loc[~separate_recipes['Facility'].isna()]
                    separate_recipes['recipe_multiples'] = np.ceil(separate_recipes['missing']/separate_recipes['# Output'])
                    used_recipes = pd.concat([used_recipes.loc[used_recipes['Facility'] != 'MPF'],mpf_items_ordered.drop(['unaccounted'],axis = 1),separate_recipes])
                else:
                    used_recipes = pd.concat([used_recipes.loc[used_recipes['Facility'] != 'MPF'],mpf_items_ordered.drop(['unaccounted'],axis = 1)])
              #MPF discounts
            used_recipes['recipe_multiples'] = used_recipes['recipe_multiples'].astype(int)
            mpf_discounted_prices = [0.9,0.8,0.7,0.6,0.5,0.5,0.5,0.5,0.5]
            nine_batch_discountable = (used_recipes['Facility'] == 'MPF') & (used_recipes['Item'].isin(nine_crate_discountable))
            five_batch_discountable = (used_recipes['Facility'] == 'MPF') & (~used_recipes['Item'].isin(nine_crate_discountable))
            used_recipes['discounted_factor'] = 1.00
            if sum(nine_batch_discountable) > 0:
                used_recipes.loc[nine_batch_discountable,'discounted_factor'] = used_recipes.loc[nine_batch_discountable,'recipe_multiples'].apply(lambda x: (sum([mpf_discounted_prices[crate % 9] for crate in range(x)])/x)) 
            if sum(five_batch_discountable) > 0:
                used_recipes.loc[five_batch_discountable,'discounted_factor'] = used_recipes.loc[five_batch_discountable,'recipe_multiples'].apply(lambda x: (sum([mpf_discounted_prices[crate % 5] for crate in range(x)])/x)) 
            used_recipes['Ingredients'] = used_recipes.Ingredients.str.split(';')
            used_recipes = used_recipes.explode('Ingredients', ignore_index = True)
            used_recipes.Ingredients = used_recipes.Ingredients.str.strip()
            breakdown = used_recipes.Ingredients.str.extract(r'(^[0-9]+) (.*)')
            used_recipes['Ingredient'] = breakdown.iloc[:,1]
            used_recipes['Amount'] = breakdown.iloc[:,0]
            used_recipes['Amount'] = used_recipes.Amount.astype(float) * used_recipes.recipe_multiples
            # The conditional assignment is to account for floating point inaccuracies
            used_recipes['Amount'] = (used_recipes['Amount']*used_recipes['discounted_factor']).apply(lambda x: math.ceil(x) if x-int(x) > 0.00001 else x)
            suborder = used_recipes.loc[used_recipes.Ingredient.notnull(),['Item','missing','Facility','recipe_multiples','Ingredient','Amount']]
            # Currently the 'missing column' is now kinda wrong for MPF --> it splits the order in MPF and other faci but does not reduce the 'missing'
            # So the total of missing per item is too high --> it's OK atm because the missing column isn't used
            # Might change if adding numbers to diagram arrows
            return (suborder, alt_recipes)
        else:
            return (None,None)
        
    except Exception as e:
        print(e)

# Run twice - once to determine how wide the plot actually ends up being then again to do it in correct size and drop the whitespace to the right
def draw_diagram(draws,crafts,outname,xlim = None):
    # Ugly as hell implementation --> maybe try an object based solution instead of table join based OR make sure layer 0 (the order) can be treated the same as other layers
    try:
        height = max(list(map(len,draws)))
        fig, ax = plt.subplots()
        if xlim is None:
            ax.set_xlim(0,6*len(draws))
            fig.set_size_inches(6*len(draws),height)
        else:
            ax.set_xlim(0,xlim)
            fig.set_size_inches(xlim,height)
        ax.set_ylim(0,height)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        # Basic textbox
        item_props = dict(boxstyle='round', facecolor='lightgray', alpha=1)
        faci_props = dict(boxstyle='sawtooth', facecolor='gold', alpha=1)
        layer = 0
        items={}
        facis = {}
        craft_copy = copy.deepcopy(crafts)
        xnext = 0
        while len(draws) > 0:
            items[layer] = {}
            facis[layer] = {}
            draw = draws.pop(0)
            elements = draw.shape[0]
            for row in range(elements):
                y = height/elements*(row+0.5)
                if draw['Item'].iloc[row] in valid_items:
                    itemtext = draw['Item'].iloc[row] + '\n' + str(int(draw['Accounted for'].iloc[row])) + '/' + str(int(draw['Amount'].iloc[row]))
                else:
                    itemtext = draw['Item'].iloc[row] + '\n' + str(int(draw['Amount'].iloc[row]))
                itextbox = ax.text(xnext, y, itemtext, horizontalalignment = 'left', verticalalignment = 'center', bbox = item_props)
                topright_coords = ax.transData.inverted().transform(tuple(itextbox.get_window_extent(renderer = renderer).p1))
                # print(itemtext + ':' + str(ax.transData.inverted().transform(tuple(itextbox.get_window_extent(renderer = renderer).p1))))
                # ax.plot(ax.transData.inverted().transform(tuple(itextbox.get_window_extent(renderer = renderer).p1))[0],ax.transData.inverted().transform(tuple(itextbox.get_window_extent(renderer = renderer).p1))[1],'go')
                items[layer][draw['Item'].iloc[row]] = (itextbox,topright_coords)
            xnext = max(list(map(lambda x:x[1][0],list(items[layer].values())))) + 1
            if(len(crafts) > 0):
                craft = crafts.pop(0)
                layer_facis = np.unique(craft['Facility'])
                n_facis = len(layer_facis)
                for row in range(n_facis):
                    y = height/n_facis*(row+0.5)
                    facitextbox = ax.text(xnext,y,layer_facis[row],horizontalalignment = 'left', verticalalignment = 'center', bbox = faci_props)
                    topright_coords = ax.transData.inverted().transform(tuple(facitextbox.get_window_extent(renderer = renderer).p1))
                    facis[layer][layer_facis[row]] = (facitextbox,topright_coords)
                xnext = max(list(map(lambda x:x[1][0],list(facis[layer].values())))) + 1
            layer += 1
        for layer in range(len(craft_copy)):
            craft = craft_copy[layer]
            item_faci_links = craft.loc[:,['Item','Facility']].drop_duplicates()
            for arrow in range(item_faci_links.shape[0]):
                target = items[layer][item_faci_links['Item'].iloc[arrow]]
                source = facis[layer][item_faci_links['Facility'].iloc[arrow]]
                # if(source[0]._y > target[0]._y):
                #     cstyle = 'bar,angle=90,fraction=-0.3'
                # elif (source[0]._y < target[0]._y):
                #     cstyle = 'bar,angle=-90,fraction=-0.3'
                # else:
                cstyle ='arc3,rad=0'
                ax.annotate(
                    "",
                    xy=(source[0]._x,source[0]._y), xycoords='data',
                    xytext=(target[1][0],target[0]._y),
                    arrowprops=dict(arrowstyle = '<-', connectionstyle=cstyle, alpha = 0.5)
                )
            faci_ingred_link  = craft.loc[:,['Facility','Ingredient','Amount']].groupby(['Facility','Ingredient'], as_index = False).sum()
            for arrow in range(faci_ingred_link.shape[0]):
                source = items[layer+1][faci_ingred_link['Ingredient'].iloc[arrow]]
                target = facis[layer][faci_ingred_link['Facility'].iloc[arrow]]
                text = str(int(faci_ingred_link['Amount'].iloc[arrow]))
                # if(source[0]._y > target[0]._y):
                #     cstyle = 'bar,angle=90,fraction=-0.3'
                # elif (source[0]._y < target[0]._y):
                #     cstyle = 'bar,angle=-90,fraction=-0.3'
                # else:
                cstyle ='arc3,rad=0'
                textangle = math.atan((target[0]._y-source[0]._y)/(target[1][0]-source[0]._x))/(2*math.pi)*360
                ax.annotate(
                    "",
                    xy=(source[0]._x,source[0]._y), xycoords='data',
                    xytext=(target[1][0],target[0]._y),
                    arrowprops=dict(arrowstyle = '<-', connectionstyle=cstyle, alpha = 0.5)
                )
                ax.text(
                    (target[1][0]*0.7 + source[0]._x*0.3),
                    (target[0]._y*0.7+ source[0]._y*0.3),
                    text,
                    ha='center',
                    va='center',
                    rotation = textangle
                )


                # arrow = FancyArrowPatch((source[0]._x, source[0]._y),
                #     (target[1][0], target[0]._y),
                #     patchA=source[0].get_bbox_patch(),
                #     patchB=target[0].get_bbox_patch(),
                #     arrowstyle="->",
                #     mutation_scale=15,
                #     shrinkA=20,
                #     shrinkB=20
                #     )
                # ax.add_patch(arrow)
        ax.set_axis_off()
        # fig.subplots_adjust(left=0.05, right=0.99)
        # fig.tight_layout()
        # ax.set_xlim(0,int(xnext)+1)
        
        #Plot done but now too large an x-area which is reserved before the final extent is known --> draw a second figure with different xlim
        # final_fig,final_ax = plt.subplots()
        # final_ax.set_xlim(0,math.ceil(xnext))
        # final_ax.set_ylim(0,height)
        # final_fig.set_size_inches(math.ceil(xnext),height)
        # all_children = ax.get_children()
        # for child in all_children:
        #     if isinstance(child,matplotlib.text.Text):
        #         final_ax.text(child._x,child._y,child._text,bbox = )
        if xlim is None:
            return math.ceil(xnext)
        else:
            fig.savefig(outname,bbox_inches="tight", pad_inches=0.1)
            plt.close()
    except Exception as e:
        print(e)
