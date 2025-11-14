import os
import telebot
from flask import Flask, request
from google.genai import Client   # Correct Gemini import

# ==============================================================
# 1. API KEYS
TELEGRAM_API_KEY = os.getenv("TELEGRAM_BOT_TOKEN", "8493395845:AAGjqeWHXuQWDAFUURsEEHhseH1IU6Rbpl0")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyDGKKlHiooeu5o34zre5Zms7S9mFwkHA3Y")

if not TELEGRAM_API_KEY:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN environment variable is missing!")

if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY environment variable is missing!")

# ==============================================================
# 2. WEBHOOK SETTINGS
BASE_URL = os.getenv("RENDER_EXTERNAL_URL")
PORT = int(os.getenv("PORT", 8443))

if BASE_URL:
    WEBHOOK_URL = BASE_URL.rstrip("/") + "/"   # Prevent double slashes
else:
    WEBHOOK_URL = None

# ==============================================================
# 3. SYSTEM PROMPT
MEDICAL_PROMPT = (
    "❗️Disclaimer: I am an AI language model and cannot provide medical advice. "
    "Always consult a licensed healthcare provider for diagnosis or treatment.\n\n"
    "You are a cautious, safe medical assistant. Provide general educational "
    "health information only. Do NOT diagnose diseases, do NOT recommend "
    "specific medications, treatments, or dosages. Keep answers simple, accurate, "
    "and focused on general well-being."
)

# ==============================================================
# 4. INITIALIZE FLASK, TELEGRAM BOT, GEMINI CLIENT
app = Flask(__name__)
bot = telebot.TeleBot(TELEGRAM_API_KEY, parse_mode="HTML")  # HTML safe
client = Client(api_key=GEMINI_API_KEY)

# ==============================================================
# 5. SPLIT LONG MESSAGES (Telegram's 4096 char limit)
def split_message(text, max_length=4000):
    parts = []
    while len(text) > max_length:
        split_at = text.rfind(". ", 0, max_length)
        if split_at == -1:
            split_at = max_length
        parts.append(text[:split_at])
        text = text[split_at:].lstrip()
    parts.append(text)
    return parts

# ==============================================================
# 6. WEBHOOK ENDPOINT (Telegram → POST)
@app.route("/", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return "Bot is running!", 200

    if request.headers.get("content-type") == "application/json":
        data = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(data)
        bot.process_new_updates([update])
        return "OK", 200

    return "Forbidden", 403

# ==============================================================
# 7. COMMAND HANDLERS
@bot.message_handler(commands=["start", "help"])
def handle_commands(message):
    bot.reply_to(
        message,
        "👋 Hello!\n"
        "I am an AI assistant that provides *general* health information.\n\n"
        "❗️For real medical problems or symptoms, always consult a doctor."
    )

# ==============================================================
# 8. MAIN MESSAGE HANDLER (Gemini response)
@bot.message_handler(func=lambda msg: True)
def handle_user_message(message):
    user_text = message.text
    bot.send_chat_action(message.chat.id, "typing")

    try:
        # Correct Gemini 2.5 API format
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            system_instruction=MEDICAL_PROMPT,
            contents=[
                {
                    "role": "user",
                    "parts": [{"text": user_text}]
                }
            ]
        )

        answer = response.text
        chunks = split_message(answer)

        for chunk in chunks:
            bot.send_message(message.chat.id, chunk)

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Gemini API error:\n{e}")

# ==============================================================
# 9. SETUP WEBHOOK
def setup_webhook():
    bot.remove_webhook()
    if WEBHOOK_URL:
        bot.set_webhook(url=WEBHOOK_URL)
        print("Webhook set to:", WEBHOOK_URL)
    else:
        print("No webhook URL detected. Use polling for local testing.")

with app.app_context():
    setup_webhook()

      