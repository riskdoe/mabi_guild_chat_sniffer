What is this


## sniffer
Grabs incoming packets from chat server and send them to worker

## worker
process guild messages and then forward them to discord using a webhook

## message typer
will take a message from a choosen discord channel, find the display name for the user
attempt to remove any unicode emotes
attempt to give names to any discord based emote
split the message into chunks with out breaking apart whole words
then type those messages out using a linux command "xdotool"


the message will be typed into any text box that is currently selected


# setup
make sure you have uv installed

`https://docs.astral.sh/uv/getting-started/installation/#__tabbed_1_1`

`uv venv`

`uv sync`

create and edit a .env file

```example
DISCORD_WEB_HOOK="hook"
BOT_NAME="botname"
IN_GAME_CHAR_NAME="ingamename"
NETWORK_INTERFACE="enp10s0"
TARGET_CHANNEL_ID="discord channel id"
GUILD_ID="discord server id"
DISCORD_TOKEN="bot token"



`uv run main.py`



## extra

this will only work on linux. weird i know but my server runs linux and its easy for me

make sure you have wireshark installed and network traffic capture dumpcap or tshark
in my case i used

```$> sudo apt install wireshark```

you will need to set perms for dumpcap and all that


# FOR PERSONAL USE, THIS IS A TOY, NO SUPPORT GIVEN

also feel free to fork or make pull requests or w/e. 
its foss do what you want
