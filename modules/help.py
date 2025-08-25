#Copyright @ISmartCoder
#Updates Channel t.me/TheSmartDev
from telethon import TelegramClient, events, Button
from utils import LOGGER
from config import COMMAND_PREFIX, UPDATE_CHANNEL_URL
import asyncio
import html

def setup_help_handler(app: TelegramClient):
    pattern = '|'.join(rf'\{prefix}(help|cmds)$' for prefix in COMMAND_PREFIX)
    @app.on(events.NewMessage(pattern=pattern, incoming=True))
    async def help_message(event):
        try:
            chat_id = event.chat_id
            animation_message = await event.respond("<b>Starting Smart OTP Cmds ⚙️...</b>", parse_mode='html')
            await asyncio.sleep(0.3)
            await app.edit_message(chat_id, animation_message, "<b>Generating Session Keys Please Wait...</b>", parse_mode='html')
            await asyncio.sleep(0.3)
            await app.delete_messages(chat_id, animation_message)
            
            full_name = "User"
            if event.sender:
                first_name = getattr(event.sender, 'first_name', '') or ""
                last_name = getattr(event.sender, 'last_name', '') or ""
                full_name = f"{first_name} {last_name}".strip() or "User"
            
            if event.is_private:
                response_text = (
                    f"**Hi {html.escape(full_name)} 🇧🇩! Welcome To This Bot**\n"
                    "**━━━━━━━━━━━━━━━━━━━━━━**\n"
                    "**Smart OTP** The ultimate toolkit on Telegram, offering various countries otp to you instantly after sending. Enjoy earning ,oney with our bot.\n"
                    "**━━━━━━━━━━━━━━━━━━━━━━**\n"
                    f"**Don't forget to [ Join Here]({UPDATE_CHANNEL_URL}) for updates!**"
                )
            else:
                chat_entity = await event.get_chat()
                group_name = getattr(chat_entity, 'title', 'this group')
                response_text = (
                    f"**Hi! Welcome {html.escape(group_name)} To This Bot**\n"
                    "**━━━━━━━━━━━━━━━━━━━━━━**\n"
                    "**Smart OTP** The ultimate toolkit on Telegram, offering various countries otp to you instantly after sending. Enjoy earning ,oney with our bot.\n"
                    "**━━━━━━━━━━━━━━━━━━━━━━**\n"
                    f"**Don't forget to [ Join Here]({UPDATE_CHANNEL_URL}) for updates!**"
                )
            
            await event.respond(
                response_text,
                parse_mode='md',
                buttons=[[Button.url("Updates Channel", UPDATE_CHANNEL_URL)]],
                link_preview=False
            )
            LOGGER.info(f"Sent /help or /cmds message to {full_name} (ID: {event.sender_id}) in chat {chat_id}")
        except events.FloodWaitError as e:
            LOGGER.warning(f"Flood wait error: Waiting {e.seconds} seconds")
            await asyncio.sleep(e.seconds + 1)
            await event.respond(response_text, parse_mode='md', buttons=[[Button.url("Updates Channel", UPDATE_CHANNEL_URL)]], link_preview=False)
        except events.PeerIdInvalidError:
            LOGGER.error(f"Invalid peer ID for /help or /cmds command in chat {chat_id}")
        except Exception as e:
            LOGGER.error(f"Error in /help or /cmds handler: {e}")