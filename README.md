# Stockpile_manager
A tool for management & information sharing of stockpiles in the game foxhole

I have started moving this bot onto github & documentation on the 4th of June 2026 and plan to continue working on it for the forseeable future + expand said documentation

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




