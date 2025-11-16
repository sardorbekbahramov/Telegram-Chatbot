import os
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, filters

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN environment variable not set!")

bot = Bot(token=TOKEN)
dispatcher = Dispatcher(bot, None, workers=0)  # sync mode

# ===== Handlers =====
def start(update, context):
    update.message.reply_text("Hello! The bot is online and working.")

def echo(update, context):
    text = update.message.text
    update.message.reply_text(f"You said: {text}")

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

# ===== Webhook =====
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot)
    dispatcher.process_update(update)
    return "OK", 200

@app.route("/")
def home():
    return "Bot is running!", 200

# ===== Set webhook automatically =====
def set_webhook():
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    if not render_url:
        raise ValueError("❌ RENDER_EXTERNAL_URL missing in environment variables!")
    webhook_url = f"{render_url}/webhook"
    bot.set_webhook(webhook_url)
    print(f"✅ Webhook has been set: {webhook_url}")

if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
