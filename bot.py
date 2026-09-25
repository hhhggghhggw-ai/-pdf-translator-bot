import os
import telebot
from deep_translator import GoogleTranslator
import PyPDF2
import io
import time

BOT_TOKEN = os.getenv("BOT_TOKEN") or "8951863527:AAHCDAjJOCnphMu9"
bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()

translator = GoogleTranslator(source='auto', target='ar')

@bot.message_handler(commands=['start'])
def send_welcome(bot_message):
    bot.reply_to(
        bot_message,
        "أهلاً بك يا حيدر! بوت ترجمة ملفات الـ PDF جاهز لاستلام ملفاتك."
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
            bot.reply_to(message, "⚠️ عذراً، لم يتم العثور على نصوص قابلة للقراءة داخل الملف.")
            return
            
        # اقتطاع جزء مناسب وآمن لتجنب حظر جوجل وتتم الترجمة بنجاح
        text_to_translate = extracted_text[:1500]
        
        translated_text = translator.translate(text_to_translate)
        
        bot.reply_to(message, f"📄 **نتيجة الترجمة (أول جزء من الملف):**\n\n{translated_text}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ أثناء الترجمة: {str(e)}")

print("🤖 البوت يعمل الآن ويستمع للرسائل...")
bot.infinity_polling()
