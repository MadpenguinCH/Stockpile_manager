# Stockpile_manager
A tool for management & information sharing of stockpiles in the game Foxhole.
I have started moving this bot onto github & documentation on the 4th of June 2026 and plan to continue working on it for the forseeable future + expand said documentation.
My goal is to make logi more easily understandable and manageable for everyone in general but also specifically small groups of players (which is why the bot currently only has limited facility crafting support).

Since the source code is public (please don't make me regret it :-P) everyone can technically host their own version of the bot if they have concerns about data safety.
Otherwise you can invite a bot running this code via this [invite link](https://discord.com/oauth2/authorize?client_id=1498687391823691827&permissions=2147665984&integration_type=0&scope=bot)

# Purpose
The main purpose of this bot is to tackle 2 common logi problems in Foxhole:
1. Stockpiles expiring because no one is refreshing them because they lost track or assumed someone else probably did it.
2. Lots of manual excel sheet updating required for regis to keep track of what they have lying around in their stockpiles.

The first functionality of the bot is to keep track of the timers of reserved stockpiles by allowing users to share the information about when they refresh (by simply using /refresh on discord after they do so in game). If no one has refreshed the timer 8h before the timer is about to expire, the bot posts a warning message to a preset channel and another warning is sent 2h before expiry (optionally with ping).

<img width="841" height="331" alt="image" src="https://github.com/user-attachments/assets/fddc1eec-76d7-4532-8c67-d7c54cefda26" /><br>
Once the pile has been refreshed the warning message will be update to reflect that so users know it no longer needs to be taken care of.
(the red cross reaction will be replaced by a green checkmark, the first warning will be updated with 'Stockpile has been refreshed by {user}'
and the second 'urgent' warning message will be deleted)

The second functionality allows users to track the inventories of the ingame stockpiles using the csv exports introduced in update 64.
Users can than create orders specifying what items they want in what quantities & in which stockpiles.
The bot then creates a breakdown of which items are missing & how they can be crafted. 
The current visualization looks a bit rough bot hopefully should prove at least readable:
<img width="2190" height="713" alt="image" src="https://github.com/user-attachments/assets/3d201512-40c7-4144-8aa5-c45c26858f5d" />

For instructions regarding how to use the bot refer to
- [User manual](docs/UserGuide.md)

# Disclaimers
## Extent of AI use
Whilst I would by no means call this project 'vibe-coded', I did use the basic (free) version of ChatGPT to assist with coding.
The underlying stockpile & order logic was programmed with very little AI input but i used it a bit more heavily for programming the discord application interface side as well as for visualization of tables & diagrams (which still ended up loooking rather lackluster :-/). Though even then i still only used it in conjunction with the usual stackoverflow forum posts, youtube tutorials, discord.py's official documentation etc. and never relied on it fully. 
I also sometimes used it for debugging as in i provided it code I had written and some unexpected output and asked for potential causes.

## Data Security
Whilst I tried my best to make information entered in the bot as safe as possible, I am by no means a cyber-security expert.
Based on my own testing any stockpile information entered in the bot should only be available on the server on which it has been entered
and should only ever be displayed either in a fixed secure channel selected during initial configuration of the bot or using '/'-commands
which only show their output to the user who calls them (which requires a role on the server which is also set during initial bot configuration).
But i can't personally guarantee that no one will find a way to circumvent these checks and get access to your information.
Also, it should go without saying but any information you enter into the bot will be present on the device on which the bot is run meaning I as the developer also technically have access to it. If this is a dealbreaker for anyone, it is still entirely possible to just input placeholder access codes during stockpile creation as without this information I think there is not much for potential griefers to use.

## Technical reliability
Whilst I do test new versions of the bot on my own two testservers before deploying them, this project is a one-person passion project and currently undergoing frequent updates.
Thus, I expect some bugs to still occur occasionally. Though at least the more critical functions (sending warnings at the correct time, hide codes from players who shouldn't be able to see them) has been in active use on one regimental server for a while already and seems to work quite well.

# Get in touch
If you want to report a bug or suggest a feature which you believe could make the tool more useful to players you can contact me
on discord where my username is also just "madpenguin_ch" (or Madpenguin#5158 using old discord handle format).


