from flask import Flask, request
import os
import telegram
import logging
from google.generativeai import Client # Google GenAI ni yangi import qilish usuli

# Flask ilovasini e'lon qilish
app = Flask(__name__)

# Render URL manzili uchun muhit o'zgaruvchisini olish
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL") 

# Loglarni sozlash
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===================================================
# 1. KALITLAR VA INITSIAALIZATSIYA
# ===================================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_TOKEN or not GEMINI_KEY:
    logger.error("❌ TELEGRAM_BOT_TOKEN yoki GEMINI_API_KEY topilmadi!")
    exit(1)

# Bot va Gemini initsializatsiyasi
bot = telegram.Bot(token=TELEGRAM_TOKEN)
gemini_client = Client(api_key=GEMINI_KEY)


# ===================================================
# 2. SYSTEM PROMPT (Gemini uchun rol)
# ===================================================
MEDICAL_PROMPT = (
    "You are a highly cautious and informative medical assistant. Your primary goal is to provide general, educational health information. "
    "Keep your answers concise, clear, and focused on the main point. "
    "You MUST start every response with a clear disclaimer: '❗️Disclaimer: I am an AI and cannot provide medical advice. Always consult a healthcare professional for diagnosis or treatment.' "
    "Do not diagnose specific conditions or recommend specific treatments or dosages. "
    "When answering, be factual, cite potential sources (e.g., 'studies suggest', 'common advice'), and focus on general well-being and symptom explanation."
)


# ===================================================
# 3. WEBHOOK FUNKSIYALARI
# ===================================================

def setup_webhook():
    """Render'dan olingan URL manzilni Telegramga o'rnatadi."""
    if not RENDER_URL:
        logger.error("❌ RENDER_EXTERNAL_URL topilmadi. Webhook o'rnatilmadi.")
        return

    webhook_url = f"{RENDER_URL}/{TELEGRAM_TOKEN}"

    try:
        is_set = bot.set_webhook(url=webhook_url)
        if is_set:
            logger.info(f"✅ Webhook muvaffaqiyatli o'rnatildi: {webhook_url}")
        else:
            # Agar oldingi Webhook bo'lsa, uni avval o'chirib keyin qayta o'rnatish yaxshi
            bot.delete_webhook()
            is_set = bot.set_webhook(url=webhook_url)
            if is_set:
                 logger.info(f"✅ Webhook qayta o'rnatildi: {webhook_url}")

    except telegram.error.TelegramError as e:
        logger.error(f"❌ Telegram xatosi: {e}")
    except Exception as e:
        logger.error(f"❌ Kutilmagan xato: {e}")


# ===================================================
# 4. FLASK YO'LLARI (ROUTES)
# ===================================================

@app.route("/")
def home():
    """Serverning ishlashini tekshirish uchun asosiy manzil va Webhookni o'rnatish."""
    setup_webhook()
    return "Medical Assistant Bot is Running. Webhook setup initiated!", 200

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    """Telegramdan kelgan yangilanishlarni qabul qiluvchi manzil."""
    if request.method == "POST":
        try:
            # Kelgan JSON ma'lumotni Telegram Update obyektiga aylantirish
            update = telegram.Update.de_json(request.get_json(force=True), bot)
            
            # Faqat xabar (message) turi mavjudligini tekshirish
            if not update.message:
                return "No message", 200

            chat_id = update.message.chat.id
            user_text = update.message.text
            
            
            # --- COMMAND HANDLER MANTIG'I (Siz so'ragan qism) ---
            if user_text in ["/start", "/help"]:
                if user_text == '/start':
                    reply = (
                        "👋 Hello! I am an AI assistant providing general information for medical questions. "
                        "I use the Gemini model to answer your queries.\n\n"
                        "❗️ Please remember to always consult a physician for any serious medical conditions or diagnosis."
                    )
                else:
                    reply = (
                        "ℹ️ I support the following commands:\n"
                        "/start - Start the bot\n"
                        "/help - Show this help message\n\n"
                        "You can also send me any health-related question directly."
                    )
                bot.sendMessage(chat_id=chat_id, text=reply)
                return "Command handled", 200

            # --- MAIN MESSAGE HANDLER MANTIG'I ---
            # Foydalanuvchi yozuvini AI modeliga yuborish
            response = gemini_client.models.generate_content(
                model='gemini-1.5-flash',
                system_instruction=MEDICAL_PROMPT, # System Prompt qo'shildi!
                contents=[user_text]
            )
            
            # Javobni Telegramga yuborish
            bot.sendMessage(chat_id=chat_id, text=response.text)
            
            return "OK", 200
        
        except telegram.error.TelegramError as e:
            logger.error(f"❌ Telegram Webhook xatosi: {e}")
            return "Telegram Error", 500
        except Exception as e:
            logger.error(f"❌ Webhookni qayta ishlashdagi kutilmagan xato: {e}")
            return "Internal Error", 500

# ===================================================
# 5. LOKAL ISHGA TUSHIRISH (RENDER UCHUN KERAK EMAS)
# ===================================================
if __name__ == "__main__":
    # Lokal test uchun
    # setup_webhook() ni izohga olib qo'ying, agar lokalda ishga tushirsangiz
    # Uning o'rniga polling ishlatish tavsiya qilinadi
    logger.warning("Lokalda ishga tushirish uchun Webhook sozlamalarini tekshiring!")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))