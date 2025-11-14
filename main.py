from flask import Flask, request
import os
import telegram
import logging
from google.generativeai import Client # Google GenAI ni yangi import qilish usuli

# Flask ilovasini e'lon qilish
app = Flask(__name__)

# Render URL manzili uchun muhit o'zgaruvchisini olish
# Render bu o'zgaruvchini avtomatik taqdim etadi
# Agar yo'q bo'lsa, xato yuzaga keladi
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL") 

# Loglarni sozlash
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===================================================
# 1. KALITLAR VA INITSIAALIZATSIYA
# Render'da .env kerak emas, chunki kalitlar Environment Variables dan olinadi
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_TOKEN or not GEMINI_KEY:
    # Bu xato faqat lokalda yuz berishi kerak, Render'da kalitlar bo'ladi
    logger.error("❌ TELEGRAM_BOT_TOKEN yoki GEMINI_API_KEY topilmadi!")
    # O'zgaruvchilarsiz ishlamasligi uchun dasturni to'xtatish
    exit(1)

# Bot va Gemini initsializatsiyasi
bot = telegram.Bot(token=TELEGRAM_TOKEN)
gemini_client = Client(api_key=GEMINI_KEY)
# ===================================================


# ===================================================
# 2. WEBHOOK FUNKSIYALARI
# ===================================================

def setup_webhook():
    """Render'dan olingan URL manzilni Telegramga o'rnatadi."""
    if not RENDER_URL:
        logger.error("❌ RENDER_EXTERNAL_URL topilmadi. Webhook o'rnatilmadi.")
        return

    # To'liq Webhook manzilini yaratish
    webhook_url = f"{RENDER_URL}/{TELEGRAM_TOKEN}"

    try:
        # Webhookni o'rnatish
        is_set = bot.set_webhook(url=webhook_url)
        if is_set:
            logger.info(f"✅ Webhook muvaffaqiyatli o'rnatildi: {webhook_url}")
        else:
            logger.error(f"❌ Webhookni o'rnatib bo'lmadi: {webhook_url}")

    except telegram.error.TelegramError as e:
        logger.error(f"❌ Telegram xatosi: {e}")
    except Exception as e:
        logger.error(f"❌ Kutilmagan xato: {e}")


# ===================================================
# 3. FLASK YO'LLARI (ROUTES)
# ===================================================

@app.route("/")
def home():
    """Serverning ishlashini tekshirish uchun asosiy manzil."""
    # Webhookni bir marta ishga tushirish uchun
    # RENDER_URL mavjud bo'lganda, bu funksiya serverning birinchi kirishida ham ishga tushadi
    setup_webhook()
    return "Medical Assistant Bot is Running. Webhook setup initiated!", 200

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    """Telegramdan kelgan yangilanishlarni qabul qiluvchi manzil."""
    if request.method == "POST":
        try:
            # Kelgan JSON ma'lumotni Telegram Update obyektiga aylantirish
            update = telegram.Update.de_json(request.get_json(force=True), bot)
            
            chat_id = update.message.chat.id
            user_text = update.message.text
            
            # Foydalanuvchi yozuvini AI modeliga yuborish
            # Gemini-1.5-flash modelidan foydalanish
            response = gemini_client.models.generate_content(
                model='gemini-1.5-flash',
                contents=[user_text]
            )
            
            # Javobni Telegramga yuborish
            bot.sendMessage(chat_id=chat_id, text=response.text)
            
            return "OK", 200
        
        except telegram.error.TelegramError as e:
            logger.error(f"❌ Telegram Webhook xatosi: {e}")
            return "Telegram Error", 500
        except Exception as e:
            logger.error(f"❌ Webhookni qayta ishlashdagi xato: {e}")
            return "Internal Error", 500

# ===================================================
# 4. ISHGA TUSHIRISH MANTIG'I
# ===================================================

# Bu qism faqat lokal kompyuterda "python main.py" orqali ishga tushganda ishlaydi.
# Render serveri gunicorn orqali app obyektini chaqiradi.
if __name__ == "__main__":
    # Lokal testda ham webhookni o'rnatish
    setup_webhook()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))