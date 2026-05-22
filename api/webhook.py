import os
import sys
from pathlib import Path

from telegram import Update
from telegram.ext import Application

# Add root directory to imports
sys.path.append(str(Path(__file__).parent.parent))

from bot import create_application

# Global app instance
app = None


async def get_application():
    global app

    if app is None:
        TOKEN = os.getenv("BOT_TOKEN")

        app = create_application()

        # Initialize application
        await app.initialize()

        # Set bot token
        app.bot.token = TOKEN

    return app


async def handler(request):
    """
    Vercel webhook handler
    """

    if request.method != "POST":
        return {
            "statusCode": 200,
            "body": "Bot is running"
        }

    try:
        data = await request.json()

        application = await get_application()

        update = Update.de_json(data, application.bot)

        await application.process_update(update)

        return {
            "statusCode": 200,
            "body": "ok"
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": str(e)
        }