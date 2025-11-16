# main.py
import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import telegram
from google.genai import Client

# Load .env for local development
load_dotenv()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")  # Render provides this in their env (optional)
PORT = int(os.getenv("PORT", 5000))

# Validate keys
if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN is missing. Set it in .env or Render environment variables.")
    raise SystemExit(1)

if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY is missing. Set it in .env or Render environment variables.")
    raise SystemExit(1)

# Initialize clients
bot = telegram.Bot(token=TELEGRAM_TOKEN)
gemini = Client(api_key=GEMINI_API_KEY)

# System prompt for Gemini (medical assistant)
MEDICAL_PROMPT = (
    "❗️Disclaimer: I am an AI and cannot provide medical advice. Always consult a healthcare professional for diagnosis or treatment.\n\n"
    "You are a highly cautious and informative medical assistant. Provide general, educational health information only. "
    "Do NOT provide specific diagnoses, dosages, or prescribe medications. Keep answers concise and factual."
)

app = Flask(__name__)

def split_message(text, max_length=4000):
    """Split long text into chunks not exceeding max_length. Prefer splitting at sentence boundaries."""
    parts = []
    while len(text) > max_length:
        split_at = text.rfind(". ", 0, max_length)
        if split_at == -1:
            split_at = max_length
        parts.append(text[:split_at].strip())
        text = text[split_at:].lstrip()
    parts.append(text.strip())
    return parts

def set_telegram_webhook():
    """
    Set Telegram webhook to RENDER_EXTERNAL_URL + /<token>.
    This function is safe to call multiple times; errors are logged.
    """
    if not RENDER_URL:
        logger.info("RENDER_EXTERNAL_URL not set - skipping automatic webhook setup.")
        return

    webhook_url = f"{RENDER_URL.rstrip('/')}/{TELEGRAM_TOKEN}"
    try:
        # Remove existing webhook then set (safe approach)
        bot.delete_webhook()
        success = bot.set_webhook(url=webhook_url)
        if success:
            logger.info("Webhook set to: %s", webhook_url)
        else:
            logger.error("Failed to set webhook to: %s", webhook_url)
    except telegram.error.TelegramError as te:
        logger.error("Telegram error when setting webhook: %s", te)
    except Exception as e:
        logger.error("Unexpected error when setting webhook: %s", e)

@app.route("/", methods=["GET"])
def index():
    """Health check — also attempts to set webhook (only if RENDER_URL available)."""
    # Try to set webhook once (har safar chaqirilsa ham yaxshi)
    try:
        set_telegram_webhook()
    except Exception as e:
        logger.warning("Webhook setup attempt failed: %s", e)
    return jsonify({"status": "ok", "message": "Medical Assistant Bot running"}), 200

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def telegram_webhook():
    """
    Telegram will POST updates to this endpoint.
    Endpoint path includes the bot token for basic obscurity: /<TOKEN>
    """
    try:
        update_json = request.get_json(force=True)
        update = telegram.Update.de_json(update_json, bot)

        # Only process messages with text
        if not update.message or not update.message.text:
            return "ok", 200

        chat_id = update.message.chat.id
        user_text = update.message.text.strip()
        logger.info("Received message from %s: %s", chat_id, user_text[:200])

        # Handle commands
        if user_text.lower() in ("/start", "/help"):
            if user_text.lower() == "/start":
                reply = (
                    "👋 Hello! I am an AI assistant providing general information for medical questions.\n\n"
                    "❗️Disclaimer: I am an AI and cannot provide medical advice. Always consult a healthcare professional."
                )
            else:
                reply = (
                    "ℹ️ Commands:\n"
                    "/start - Start the bot\n"
                    "/help - Show this help message\n\n"
                    "Or just send your medical-related question."
                )
            bot.send_message(chat_id=chat_id, text=reply)
            return "ok", 200

        # --- Send to Gemini model ---
        try:
            response = gemini.models.generate_content(
                model="gemini-2.5-flash",
                system_instruction=MEDICAL_PROMPT,
                contents=[
                    {"role": "user", "parts": [{"text": user_text}]}
                ]
            )
            ai_text = getattr(response, "text", None) or getattr(response, "output", None) or str(response)
            if not ai_text:
                ai_text = "Sorry, I couldn't generate an answer. Please try again later."

        except Exception as gen_e:
            logger.exception("Gemini API error: %s", gen_e)
            ai_text = "❌ Sorry, AI service is temporarily unavailable. Please try again later."

        # Split long replies and send
        for chunk in split_message(ai_text):
            bot.send_message(chat_id=chat_id, text=chunk)

        return "ok", 200

    except telegram.error.TelegramError as te:
        logger.exception("Telegram error while handling update: %s", te)
        return "telegram error", 500
    except Exception as e:
        logger.exception("Unexpected error while handling update: %s", e)
        return "internal error", 500

if __name__ == "__main__":
    # Local development only
    logger.info("Starting Flask development server on 0.0.0.0:%s", PORT)
    # Do NOT call set_telegram_webhook() automatically in multi-worker production (gunicorn) - Render will call index endpoint once on health-check.
    app.run(host="0.0.0.0", port=PORT, debug=False)
