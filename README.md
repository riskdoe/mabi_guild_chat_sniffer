# Mabinogi Chat Sniffer → Discord Bridge

A personal tool for capturing guild chat messages from **Mabinogi** and forwarding them to a Discord channel via webhook — and vice versa.


## sniffer
- Uses `pyshark` to **sniff packets** from the Mabinogi chat server
- Detects in-game messages based on known packet structure
- Extracts and decodes messages
- Forwards cleaned messages to a **Discord Webhook**

## message typer
- will take a message from a choosen discord channel, find the display name for the user
- attempt to remove any unicode emotes
- attempt to give names to any discord based emote
- split the message into chunks with out breaking apart whole words
- then type those messages out using a linux command "xdotool"


the message will be typed into any text box that is currently selected


# setup
make sure you have uv installed

install uv:
https://docs.astral.sh/uv/getting-started/installation/#__tabbed_1_1

create a venv:
`uv venv`

sync all the required packages:
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
```

run:
`uv run main.py`

###  System dependencies

- Wireshark
- xdotool
- wine

install requirements on deb based systems
`sudo apt install wireshark, xdotool`
(if your running arch im sure you know how to set this up in arch)


Make sure you have permissions for dumpcap / tshark on the user running the script

I use heroic launcher to get wine and all that set up for mabinogi, just install nexon launcher inside heroic

## extra

this will only work on linux. weird i know but my server runs linux and its easy for me


---

### Important Notes
-This is a personal project / toy tool
-Use at your own risk
-No support guaranteed

### License
MIT / FOSS — fork it, use it, break it. Have fun.
