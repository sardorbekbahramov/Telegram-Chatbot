import telebot
from google import genai 
import os

# =========================================================================
# 1. API KEYLAR
TELEGRAM_API_KEY = os.getenv("TELEGRAM_BOT_TOKEN", "8493395845:AAGjqeWHXuQWDAFUURsEEHhseH1IU6Rbpl0")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyDGKKlHiooeu5o34zre5Zms7S9mFwkHA3Y") 

# =========================================================================
# 2. JAVOBNI BO'LAKLARGA AJRATISH FUNKSIYASI (Telegram cheklovi uchun)
def split_message(text, max_length=4000):
    """Matnni Telegram chekloviga mos qismlarga (4096 belgidan kichik) ajratadi."""
    parts = []
    current_part = ""
    sentences = text.split('. ')
    
    for i, sentence in enumerate(sentences):
        sentence = sentence.strip()
        if not sentence:
            continue
            
        sentence_with_delimiter = sentence + (". " if i < len(sentences) - 1 else "")
        
        if len(current_part) + len(sentence_with_delimiter) > max_length:
            if current_part:
                parts.append(current_part.strip())
            current_part = sentence_with_delimiter
        else:
            current_part += sentence_with_delimiter
            
    if current_part:
        parts.append(current_part.strip())
        
    return parts

# =========================================================================
# 3. SYSTEM PROMPT
MEDICAL_PROMPT = (
    "You are a highly cautious and informative medical assistant. "
    "Your primary goal is to provide general, educational health information. "
    "Keep your answers concise, clear, and focused on the main point. "
    "You MUST start every response with a clear disclaimer: '❗️Disclaimer: I am an AI and cannot provide medical advice. Always consult a healthcare professional for diagnosis or treatment.' "
    "Do not diagnose specific conditions or recommend specific treatments or dosages. "
    "When answering, be factual, cite potential sources (e.g., 'studies suggest', 'common advice'), and focus on general well-being and symptom explanation."
)

# =========================================================================
# 4. BOT VA GEMINI OBYEKTLARINI INITSIAALLASHTIRISH
try:
    bot = telebot.TeleBot(TELEGRAM_API_KEY)
    client = genai.Client(api_key=GEMINI_API_KEY)
    
except Exception as e:
    print(f"Error: API kalitlari bilan bog'liq muammo mavjud. Iltimos, kalitlarni tekshiring: {e}")
    exit()

# =========================================================================
# --- COMMAND HANDLERS ---
@bot.message_handler(commands=['start', 'help'])
def handle_commands(message):
    if message.text == '/start':
        response_text = "Hello! I am an AI assistant providing general information for medical questions. Please remember to always consult a physician for any serious medical conditions or diagnosis."
    else: # /help
        response_text = "I support the following commands:\n/start - Start the bot\n/help - Show this help message\nYou can also send me any medical question directly."
    bot.reply_to(message, response_text)

# =========================================================================
# --- MESSAGE HANDLER FOR ALL OTHER TEXT (GEMINI LOGIC) ---

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_question = message.text
    bot.send_chat_action(message.chat.id, 'typing')
    
    try:
        # 1. Savolni Gemini'ga yuborish (Eng sodda formatni ishlatish)
        response = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=[user_question], # <<< Eng asosiy tuzatish shu yerda. Matnni to'g'ridan-to'g'ri yuborish.
            config={"system_instruction": MEDICAL_PROMPT} 
        )
        
        # 2. AI javobini chiqarish
        ai_answer = response.text
        
        # JAVOBNI BO'LAKLARGA AJRATISH:
        message_parts = split_message(ai_answer)

        # Har bir bo'lakni alohida yuborish
        for part in message_parts:
            bot.send_message(message.chat.id, part)

    except Exception as e:
        # Xato matnini Telegram chekloviga mos ravishda qisqartirish
        error_text = f"Sorry, a Gemini API error occurred: {e}"
        if len(error_text) > 4000:
            error_text = error_text[:3990] + "..." # Cheklovdan o'tmaslik uchun juda qisqartirish
            
        bot.reply_to(message, error_text)


# =========================================================================
# --- BOTNI ISHGA TUSHIRISH ---
if __name__ == '__main__':
    print("Hey, I am up.... The bot has started and is listening for messages...")
    bot.polling()