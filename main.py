import os
import asyncio
import logging
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# ==============================
#  LOGGING
# ==============================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==============================
#  FLASK INIT
# ==============================
app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN environment variable not set!")

bot = Bot(token=TOKEN)
application = Application.builder().token(TOKEN).build()

# ==============================
#  HANDLERS
# ==============================
async def start(update, context):
    await update.message.reply_text(
        "Hello! The bot is online and working.\n"
        "Send me any message and I will reply to it."
    )

async def echo(update, context):
    text = update.message.text
    await update.message.reply_text(f"You said: {text}")

application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

# ==============================
#  WEBHOOK ENDPOINT (SYNC)
# ==============================
@app.route("/webhook", methods=["POST"])
def webhook():
    """Handles incoming Telegram updates (sync wrapper)."""
    data = request.get_json(force=True)
    update = Update.de_json(data, bot)
    asyncio.run(application.process_update(update))
    return "OK", 200

@app.route("/")
def home():
    return "Bot is running!", 200

# ==============================
#  SET WEBHOOK
# ==============================
def set_webhook():
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    if not render_url:
        raise ValueError("❌ RENDER_EXTERNAL_URL is missing in Environment Variables!")
    
    webhook_url = f"{render_url}/webhook"
    asyncio.run(bot.delete_webhook())
    asyncio.run(bot.set_webhook(webhook_url))
    logger.info(f"✅ Webhook has been set: {webhook_url}")

# ==============================
#  LOCAL / DEPLOY MODE
# ==============================
if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
