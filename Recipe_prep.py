import pandas as pd
import copy
import numpy as np
recipes = pd.read_excel('Ordersheet_input.xlsx',sheet_name='Recipes')
item_infos = pd.read_excel('Ordersheet_input.xlsx',sheet_name='Items')
# These recipes can be crafted in batches of 9 at MPF, rest only 5
nine_crate_discountable = pd.unique((recipes.loc[recipes['Facility'] == 'Factory; MPF','Item']).str.removesuffix('(Crate)').str.strip())
recipe_copy = copy.deepcopy(recipes) 
recipe_copy['Ingredients'] = recipe_copy.Ingredients.str.split(';')
recipe_copy = recipe_copy.explode('Ingredients', ignore_index = True)
recipe_copy.Ingredients = recipe_copy.Ingredients.str.strip()
breakdown = recipe_copy.Ingredients.str.extract(r'(^[0-9]+) (.*)')
used_as_mats = pd.unique(breakdown[1])
# A small handful of items get used in recipes as crates but ONLY ever as crates (specifically weapon or uniform upgrades)
# For crafting breakdown i need to know how ingredients are crafted which usually means i need ingredients per unpacked item but for
# these few exceptions i need the recipe both as crate or non crate
crate_recipes = recipes.loc[recipes['Item'].str.contains('\\(Crate\\)')]
# Here again including the crate recipes which need to be known as crate recipes
direct_recipes = recipes.loc[~(recipes['Item'].str.contains('\\(Crate\\)')) | recipes['Item'].isin(used_as_mats)]
crate_recipes = crate_recipes.merge(item_infos,how = 'left', left_on = 'Item', right_on = 'Item name')
crate_recipes['# Output'] = crate_recipes['# Output'] * crate_recipes['Items per Crate']
crate_recipes['Item'] = crate_recipes['Item'].str.removesuffix('(Crate)').str.strip()
crate_recipes['output crated'] = True
direct_recipes['output crated'] = False
recipes = pd.concat([crate_recipes.loc[:,['Item','Facility','Ingredients','# Output','output crated']], direct_recipes])
recipes['Facility'] = recipes.Facility.str.split(';')
recipes = recipes.explode('Facility', ignore_index = True)
recipes['Facility'] = recipes.Facility.str.strip()
# Can't be stored in stockpile so it makes no sense to show 0/available
raw_resources = item_infos['Item name'].loc[item_infos['Category'] == 'Raw resources'].to_list()
# recipes = recipes.loc[~recipes['Item'].isin(raw_resources)]
default_order = ['Infantry Kit Factory', 'Ammunition Factory', 'Materials Factory', 'MPF', 'Shipyard', 'Factory', 'Refinery']
alt_order = [                                                     
'Offshore Platform',
'Refinery',
'Factory',
'Shipyard',
'Garage',
'Base',
'Construction Yard',
'Aircraft Hangar',
'Coal Refinery',
'Ammunition Factory',
'Infantry Kit Factory',
'Metalworks Factory'
'Materials Factory',
'Small Assembly Station',
'Concrete Mixer',
'Oil Refinery',
'Infantry Kit Factory\n(Small Arms Workshop)',
'Infantry Kit Factory\n(Heavy Munitions Foundry)',
'Ammunition Factory\n(Large Shell Factory)',
'Materials Factory\n(Forge)',
'Metalworks Factory\n(Blast Furnace)',
'Metalworks Factory\n(Engineering Station)',
'Infantry Kit Factory\n(Special-Issue Firearms Assembly)',
'Small Assembly Station\n(Field Station)',
'Small Assembly Station\n(Weapons Platform)',
'Materials Factory\n(Assembly Bay)',
'Coal Refinery\n(Coke Furnace)',
'Coal Refinery\n(Advanced Coal Liquifier)',
'Small Assembly Station\n(Advanced Structure Manufactory)',
'Ammunition Factory\n(Tripod Factory)',
'Small Assembly Station\n(Tank Factory)',
'Small Assembly Station\n(Motor Pool)',
'Oil Refinery\n(Cracking Unit)',
'Small Assembly Station\n(Battery Line)',
'Large Assembly Station\n(Aircraft Assembly)',
'Oil Refinery\n(Reformer)',
'Metalworks Factory\n(Recycler)',
'MPF'
]
sort_order = pd.DataFrame({
"Facility": alt_order,
"Prio": [i for i in range(len(alt_order))]
}
)
recipes = recipes.merge(sort_order, how = 'left', on = 'Facility')
recipes['Signature'] = recipes['Item'] + '@' + recipes['Facility']
ambiguous = recipes['Item'].isin(pd.unique(recipes['Item'].loc[recipes['Signature'].duplicated()]))
recipes.loc[ambiguous,'Signature'] = recipes.loc[ambiguous,'Signature'] + recipes.loc[ambiguous,'Ingredients'].str.replace(' ','')
valid_items = pd.read_excel('Ordersheet_input.xlsx',sheet_name='Items')
valid_items = np.unique(pd.concat([valid_items['Item name'].str.extract(r'(.*) \(Crate\)')[0].dropna(),valid_items['Item name']]))

# item_infos['Item name'] = item_infos['Item name'].str.removesuffix('(Crate)').str.strip()
# item_infos = item_infos.sort_values(['Item name','Items per Crate'])
# #Keep entry without crate info only when the one with crate info is not available
# item_infos = item_infos.loc[-item_infos['Item name'].duplicated()]
# item_infos['Items per Crate'] = item_infos['Items per Crate'].fillna(0)

# #Save processed excel for easier typescript version port
# item_infos.to_csv('Item_infos.csv',index = False)
# recipes.to_csv('Item_recipes.csv',index = False)