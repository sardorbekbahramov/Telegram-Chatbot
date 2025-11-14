import telebot
from google import genai
import os
from flask import Flask, request

# =========================================================================
# 1. API KEYLAR VA WEBHOOK SOZLAMALARI
# Environment Variables Render'dan olinadi, agar bo'lmasa, hardcoded qiymatlar ishlatiladi (faqat sinov uchun)

# Iltimos, keyingi deploy oldidan quyidagi zaxira kalitlarni (ikkinchi qismni) o'zgartiring!
TELEGRAM_API_KEY = os.getenv("TELEGRAM_BOT_TOKEN", "8493395845:AAGjqeWHXuQWDAFUURsEEHhseH1IU6Rbpl0") 
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyDGKKlHiooeu5o34zre5Zms7S9mFwkHA3Y") 

# Render bizga PORT va BASE_URL ni avtomatik beradi
PORT = int(os.environ.get('PORT', '8443')) 
BASE_URL = os.getenv("RENDER_EXTERNAL_URL") 

# BASE_URL ni tekshirish shart emas, chunki u Render'da doim mavjud bo'ladi
if not BASE_URL:
    # Render'da ishlamasa, mahalliy sinov uchun False URL o'rnatamiz
    WEBHOOK_URL = "http://127.0.0.1:8443/"
else:
    WEBHOOK_URL = BASE_URL + '/'

# =========================================================================
# 2. JAVOBNI BO'LAKLARGA AJRATISH FUNKSIYASI 
def split_message(text, max_length=4000):
    parts = []
    current_part = ""
    sentences = text.split('. ')
    for i, sentence in enumerate(sentences):
        sentence = sentence.strip()
        if not sentence: continue
        sentence_with_delimiter = sentence + (". " if i < len(sentences) - 1 else "")
        if len(current_part) + len(sentence_with_delimiter) > max_length:
            if current_part: parts.append(current_part.strip())
            current_part = sentence_with_delimiter
            if len(current_part) > max_length:
                # Agar bitta gap juda uzun bo'lsa, uni kesish
                parts.append(current_part[:max_length] + "...")
                current_part = ""
            
        else:
            current_part += sentence_with_delimiter
            
    if current_part: parts.append(current_part.strip())
    return parts

# =========================================================================
# 3. SYSTEM PROMPT 
MEDICAL_PROMPT = (
    "You are a highly cautious and informative medical assistant. Your primary goal is to provide general, educational health information. "
    "Keep your answers concise, clear, and focused on the main point. "
    "You MUST start every response with a clear disclaimer: '❗️Disclaimer: I am an AI and cannot provide medical advice. Always consult a healthcare professional for diagnosis or treatment.' "
    "Do not diagnose specific conditions or recommend specific treatments or dosages. "
    "When answering, be factual, cite potential sources (e.g., 'studies suggest', 'common advice'), and focus on general well-being and symptom explanation."
)

# =========================================================================
# 4. BOT, GEMINI VA FLASK OBYEKTLARINI INITSIAALLASHTIRISH
try:
    # Flask app yaratish (Web Service uchun)
    app = Flask(__name__)
    bot = telebot.TeleBot(TELEGRAM_API_KEY, parse_mode=None)
    client = genai.Client(api_key=GEMINI_API_KEY)
    
except Exception as e:
    # Agar initsializatsiya (masalan, API kaliti) xato bersa
    print(f"Xato: Initsializatsiya muammosi: {e}")
    # gunicorn'ga xato borligini bildirish uchun exit() qilib qo'yamiz.
    exit(1)


# =========================================================================
# 5. WEBHOOK HANDLER (Telegramdan kelgan xabarni ushlovchi)

@app.route('/', methods=['POST'])
def webhook():
    # Faqat Telegramdan kelgan JSON formatdagi so'rovlarni qabul qilish
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '!', 200 # Muvaffaqiyatli qabul qilinganini bildirish
    else:
        # JSON emasmi? Rad etamiz.
        return '', 403

# =========================================================================
# 6. COMMAND HANDLERS 
@bot.message_handler(commands=['start', 'help'])
def handle_commands(message):
    if message.text == '/start':
        response_text = "Hello! I am an AI assistant providing general information for medical questions. Please remember to always consult a physician for any serious medical conditions or diagnosis."
    else:
        response_text = "I support the following commands:\n/start - Start the bot\n/help - Show this help message\nYou can also send me any medical question directly."
    bot.reply_to(message, response_text)

# =========================================================================
# 7. MESSAGE HANDLER (GEMINI LOGIC) 
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_question = message.text
    # Bot 'typing' (yozmoqda) statusini ko'rsatish
    bot.send_chat_action(message.chat.id, 'typing') 
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=[user_question],
            config={"system_instruction": MEDICAL_PROMPT} 
        )
        ai_answer = response.text
        message_parts = split_message(ai_answer)
        for part in message_parts:
            bot.send_message(message.chat.id, part)

    except Exception as e:
        # API xatoliklarini foydalanuvchiga yuborish
        error_text = f"Uzr, Gemini API xatosi yuz berdi: {e}"
        if len(error_text) > 4000:
            error_text = error_text[:3990] + "..."
        bot.reply_to(message, error_text)


# =========================================================================
# 8. ASOSIY ISHGA TUSHIRISH MANTIG'I (Tuzatilgan)

def set_webhook():
    """Telegram APIga Webhook URL'ini o'rnatadi."""
    try:
        # Agar BASE_URL mavjud bo'lsa (Render'da ishlayotgan bo'lsa)
        if BASE_URL:
            bot.set_webhook(url=WEBHOOK_URL)
            print(f"Webhook muvaffaqiyatli o'rnatildi: {WEBHOOK_URL}")
        else:
            # Mahalliy sinov uchun bot.set_webhook() o'rniga Polling ishlatish mumkin
            print("Webhook o'rnatilmadi (BASE_URL yo'q). Mahalliy test uchun Polling kerak.")
            
    except Exception as e:
        print(f"Webhook o'rnatishda xato: {e}")
        
# Gunicorn bu kodni import qilganda, u set_webhook() funksiyasini chaqirishi kerak.
# Flask app.app_context() orqali buni kafolatlaymiz.
with app.app_context():
    set_webhook()
    print("Bot muvaffaqiyatli ishga tushdi va Webhook so'rovlarini kutmoqda.")