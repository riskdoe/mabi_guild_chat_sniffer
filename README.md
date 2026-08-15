# Mabinogi Guild Chat Sniffer

Bidirectional bridge between Mabinogi guild chat and Discord. Captures in-game guild messages via packet sniffing and forwards them to a Discord webhook. Reads messages from a Discord channel and types them into the game via xdotool.


# AI disclosure
I've been using this project to learn about and how to use tools like opencode.
there is *some* AI genned code. I'll attempt to mark it as such as it comes up.

## Architecture

**In-game → Discord (Sniffer)**
- Uses `pyshark` to capture TCP packets on a network interface
- Filters for Mabinogi chat server traffic (default BPF: `src host 54.214.176.167`)
- Parses guild chat packets using custom Mabinogi packet parser
- Extracts sender name and message content
- Cleans message (removes @everyone/@here, replaces configured mentions)
- Sends to Discord via webhook with username set to character name
- Adds custom embed images for specific emotes (`:foxspinn:`, `:foxspin:`)

**Discord → In-game (Typer)**
- Discord bot listens to a target channel (ignores bots, webhooks, commands)
- Normalizes messages: replaces custom emotes with `:name:`, strips Unicode emojis, removes mentions/markdown
- Splits into chunks (default 80 chars) without breaking words
- Types each chunk into the active Mabinogi window via `xdotool`

## Requirements

- Linux (tested on Debian-based)
- Python 3.13+
- Wireshark (provides `dumpcap`/`tshark` for packet capture)
- `xdotool` for typing into game window
- Wine + Heroic Launcher (for running Mabinogi on Linux)
- `uv` for Python package management

## Installation

```bash
# Install system dependencies (Debian/Ubuntu)
sudo apt install wireshark xdotool

# Install uv if not present
# https://docs.astral.sh/uv/getting-started/installation/

# Create venv and sync dependencies
uv venv
uv sync
```

## Configuration

Copy `.env.example` to `.env` and fill in:

```env
DISCORD_TOKEN=your_bot_token
DISCORD_GUILD_ID=your_guild_id          # Optional: for faster command sync
TARGET_CHANNEL_ID=channel_id_to_read_from
DISCORD_WEB_HOOK=webhook_url_for_sending
IN_GAME_CHAR_NAME=YourCharacterName     # Used to filter own messages
NETWORK_INTERFACE=Ethernet              # Interface to sniff (e.g., eth0, enp3s0)
BOT_NAME=BotDisplayName                 # Optional, default: DefaultBot
BPF_FILTER="src host 54.214.176.167"    # Optional, default shown
```

Additional options (set in `.env` or code):
- `GUILD_ID` — Discord guild ID for slash command sync (optional)
- `delay_seconds` — Typing delay between keystrokes (default: 0.02)

**Permissions**: The user running the script needs `dumpcap`/`tshark` capture permissions:
```bash
sudo setcap cap_net_raw,cap_net_admin+eip $(which dumpcap)
# or run with sudo (not recommended)
```

## Running

```bash
# TUI mode (default when run in terminal with curses)
uv run main.py

# Console mode (when not in TTY or curses unavailable)
uv run main.py
```

The TUI shows uptime, packet/message counters, errors, and recent logs. Press `q` to quit.

## Mention Configuration

Create `mentions_config.json` (see `mentions_config.example.json`) to map `@keyword` to Discord role/user mentions:

```json
{
  "role_mentions": { "keyword": "role_id" },
  "user_mentions": { "keyword": "user_id" }
}
```

## License

MIT — fork, use, break, fix. No warranty.
