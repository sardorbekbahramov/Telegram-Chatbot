import os
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

app = Flask(__name__)

# ===== Telegram token =====
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN environment variable not set!")

bot = Bot(token=TOKEN)
dispatcher = Dispatcher(bot, None, workers=0)  # workers=0 sync ishlatish uchun

# ===== Handlers =====
def start(update, context):
    update.message.reply_text("Hello! Bot ishlayapti ✅")

def echo(update, context):
    text = update.message.text
    update.message.reply_text(f"Siz shunday yozdingiz: {text}")

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

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
        raise ValueError("❌ RENDER_EXTERNAL_URL missing!")
    webhook_url = f"{render_url}/webhook"
    bot.delete_webhook()
    bot.set_webhook(webhook_url)
    print(f"✅ Webhook o‘rnatildi: {webhook_url}")

if __name__ == "__main__":
    set_webhook()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
