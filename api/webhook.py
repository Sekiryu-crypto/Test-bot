import sys
from pathlib import Path

# Add parent directory to path so we can import bot.py
sys.path.append(str(Path(__file__).parent.parent))

from bot import create_application
from telegram.ext import ExtBot, Application
from telegram import Update
import asyncio

# Create the application once (reused across invocations)
_app = None

def get_app() -> Application:
    global _app
    if _app is None:
        _app = create_application()
        # Initialize the bot (required for webhook)
        _app.bot = ExtBot(token="7468327119:AAFzswUn3TAcDhI_OE62YP9AeEAl5JLm05w")
        # You can also set webhook URL here (but do it once via a setup script)
    return _app

async def process_update(update_dict: dict) -> None:
    """Convert dict to Update object and feed it to the application."""
    app = get_app()
    update = Update.de_json(update_dict, app.bot)
    await app.process_update(update)

# Vercel handler
async def handler(request):
    """Main entry point for Vercel."""
    # Telegram sends POST requests to the webhook URL
    if request.method == "POST":
        body = await request.json()
        await process_update(body)
        return {"ok": True}
    return {"ok": False, "message": "Only POST allowed"} 