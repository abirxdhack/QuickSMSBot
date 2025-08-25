#Copyright @ISmartCoder
#Updates Channel t.me/TheSmartDev
from utils import LOGGER
from core.start import setup_start_handler
from modules.help import setup_help_handler
from modules.scraper import setup_otp_handler
from app import app
import asyncio

async def main():
    await app.start()
    LOGGER.info("Bot Successfully Started! 💥")
    setup_start_handler(app)
    setup_help_handler(app)
    setup_otp_handler(app)
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
        app.run_until_disconnected()
    except KeyboardInterrupt:
        LOGGER.info("Bot Stopped Successfully!")
        try:
            loop.run_until_complete(app.disconnect())
        except Exception as e:
            LOGGER.error(f"Failed to stop client: {e}")
        finally:
            if not loop.is_closed():
                loop.close()