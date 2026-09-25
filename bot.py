import os
import telebot
import PyPDF2
import io
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN") or "8951863527:AAHCDAjJOCnphMu9"
bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك يا حيدر! بوت الباتروس جاهز الآن لترجمة ملفات الـ PDF بكل كفاءة.")

def translate_text(text):
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "auto",
            "tl": "ar",
            "dt": "t",
            "q": text
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            result = response.json()
            translated_sentence = "".join([item[0] for item in result[0] if item[0]])
            return translated_sentence
    except Exception:
        pass
    return text

@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    try:
        if not message.document.file_name.endswith('.pdf'):
            bot.reply_to(message, "⚠️ عذراً، يرجى إرسال ملف بصيغة PDF فقط.")
            return
            
        bot.reply_to(message, "⏳ جاري استلام الملف ومعالجة النصوص...")
        
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        pdf_file = io.BytesIO(downloaded_file)
        reader = PyPDF2.PdfReader(pdf_file)
        
        if len(reader.pages) == 0:
            bot.reply_to(message, "⚠️ عذراً، الملف فارغ.")
            return
            
        extracted_text = reader.pages[0].extract_text() or ""
        
        if not extracted_text.strip():
            bot.reply_to(message, "⚠️ لم يتم العثور على نص قابل للقراءة في الصفحة الأولى.")
            return

        # ترجمة أول 400 حرف بأمان تامة
        translated_text = translate_text(extracted_text[:400])
        
        bot.reply_to(message, f"📄 **نتيجة الترجمة:**\n\n{translated_text}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ: {str(e)}")

print("🤖 بوت الباتروس يعمل الآن...")
bot.infinity_polling()
