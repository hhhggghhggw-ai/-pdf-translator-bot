import os
import telebot
from deep_translator import GoogleTranslator
import PyPDF2
import io

# جلب توكن البوت من متغيرات البيئة بأمان (أو وضعه مباشرة)
BOT_TOKEN = os.getenv("BOT_TOKEN") or "8951863527:AAHCDAjJOCnphMu9"

bot = telebot.TeleBot(BOT_TOKEN)

# حذف أي ويبهوك قديم معلق لحل مشكلة التعارض (Conflict Error)
bot.remove_webhook()

translator = GoogleTranslator(source='auto', target='ar')

@bot.message_handler(commands=['start'])
def send_welcome(bot_message):
    bot.reply_to(
        bot_message,
        "أهلاً بك يا حيدر! بوت ترجمة ملفات الـ PDF يعمل الآن بكفاءة وجاهز لاستلام ملفاتك."
    )

@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    try:
        file_info = bot.get_file(message.document.file_id)
        if not message.document.file_name.endswith('.pdf'):
            bot.reply_to(message, "⚠️ عذراً، يرجى إرسال ملف بصيغة PDF فقط.")
            return
            
        bot.reply_to(message, "⏳ جاري استلام وتحميل ملف الـ PDF وترجمته...")
        
        downloaded_file = bot.download_file(file_info.file_path)
        pdf_file = io.BytesIO(downloaded_file)
        reader = PyPDF2.PdfReader(pdf_file)
        
        extracted_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_text += text + "\n"
                
        if not extracted_text.strip():
            bot.reply_to(message, "⚠️ عذراً، لم يتم العثور على نصوص قابلة للقرائة داخل ملف الـ PDF.")
            return
            
        # ترجمة النصوص (أخذ أول جزء لتجنب تجاوز الحد الأقصى)
        translated_text = translator.translate(extracted_text[:4000])
        
        bot.reply_to(message, f"📄 **نتيجة الترجمة:**\n\n{translated_text}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ أثناء معالجة الملف: {str(e)}")

print("🤖 البوت يعمل الآن ويستمع للرسائل...")
bot.infinity_polling()
