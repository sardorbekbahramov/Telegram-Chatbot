from flask import Flask, request
import os
import logging
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")

bot = Bot(TOKEN)
app_telegram = Application.builder().token(TOKEN).build()

async def start(update, context):
    await update.message.reply_text("Hello! Bot is online!")

async def echo(update, context):
    await update.message.reply_text(f"You said: {update.message.text}")

app_telegram.add_handler(CommandHandler("start", start))
app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

@app.route("/webhook", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    await app_telegram.process_update(update)
    return "OK", 200

@app.route("/")
def home():
    return "Bot is running!", 200

async def set_webhook():
    webhook_url = f"{RENDER_URL}/webhook"
    await bot.delete_webhook()
    await bot.set_webhook(webhook_url)
    logger.info(f"Webhook set: {webhook_url}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(set_webhook())
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
