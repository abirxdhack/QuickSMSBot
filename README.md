# QuickSMSBot

An Asynchronous Telegram Bot For Scrapping OTP From ivas.com Using Aiohttp & Pure Python3 MtProto API Telethon Library.With Advanced
Features & Cool UI / UX 

## Features
- Scrapes OTPs from ivasms.com using aiohttp for non-blocking requests
- Extracts numeric OTPs (e.g., `702434` from `G-702434 is your Google verification code`)
- Sends startup alerts to group chat and owner with developer and channel buttons
- Sends OTP messages only to group chat with a "Copy OTP Code" button
- Supports multiple command prefixes (`,`, `.`, `/`, `!`, `#`) for `/start`, `/help`, `/cmds`
- Handles rate-limiting (429 errors) with exponential backoff
- Uses asyncio.Lock for safe file operations
- Logs activities to `botlog.txt` and console

## Setup Tutorial

1. **Clone the Repository**
   ```bash
   git clone https://github.com/abirxdhack/QuickSMSBot.git
   cd QuickSMSBot
   ```

2. **Install Dependencies**
   Ensure Python 3.9 Or Above  is installed, then install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the Bot**
   - Open `config.py` and verify the following:
     - `API_ID`: YOUR_API_ID
     - `API_HASH`: "YOUR_API_HASH"
     - `BOT_TOKEN`: "YOUR_BOT_TOKEN"
     - `COMMAND_PREFIX`: [",", ".", "/", "!", "#"]
     - `UPDATE_CHANNEL_URL`: https://t.me/TheSmartDev
     - `EMAIL`: "IVAS_ACCOUNT_MAIL"
     - `PASSWORD`: "IVAS_ACCOUNT_PASSWORD"
     - `CHAT_IDS`: [OTP_GROUP_CHAT_ID]
     - `OWNER_ID`: YOUR_OWNER_ID
   - Replace `OWNER_ID` with your Telegram user ID if different.

4. **Run the Bot**
   ```bash
   python3 main.py
   ```

5. **Interact with the Bot**
   - Use `/start`, `/help`, or `/cmds` (with any prefix, e.g., `.start`, `!help`) in the group chat (-1002796548432) or private chat.
   - Startup alerts are sent to the group chat and owner (7666341631).
   - OTP messages are sent only to the group chat with a "Copy OTP Code 🗒" button.

## Repository
[github.com/abirxdhack/QuickSMSBot](https://github.com/abirxdhack/QuickSMSBot)

## Updates
Join [TheSmartDev](https://t.me/TheSmartDev) for updates and support.


