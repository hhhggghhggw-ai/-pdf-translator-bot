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
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك يا حيدر! بوت (الباتروس) لترجمة الـ PDF جاهز للعمل واستلام ملفاتك.")

@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    try:
        if not message.document.file_name.endswith('.pdf'):
            bot.reply_to(message, "⚠️ عذراً، يرجى إرسال ملف بصيغة PDF فقط.")
            return
            
        bot.reply_to(message, "⏳ جاري استلام الملف وترجمته (سطراً بسطر) لتجنب حظر جوجل... الرجاء الانتظار.")
        
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        pdf_file = io.BytesIO(downloaded_file)
        reader = PyPDF2.PdfReader(pdf_file)
        
        if len(reader.pages) == 0:
            bot.reply_to(message, "⚠️ عذراً، الملف لا يحتوي على صفحات.")
            return
            
        # استخراج نص الصفحة الأولى فقط للتجربة
        extracted_text = reader.pages[0].extract_text() or ""
        
        if not extracted_text.strip():
            bot.reply_to(message, "⚠️ الصفحة الأولى لا تحتوي على نصوص قابلة للقراءة (قد تكون صوراً).")
            return

        # تقسيم النص إلى أسطر لترجمتها سطراً بسطر
        lines = extracted_text.split('\n')
        translated_text = ""
        
        # ترجمة أول 10 أسطر ببطء لتجنب الحظر نهائياً
        for line in lines[:10]:
            if line.strip():
                translated = translator.translate(line.strip())
                translated_text += translated + "\n"
                time.sleep(1.5)  # ⏱️ تأخير لمدة ثانية ونصف بين كل سطر لتجنب الخطأ
        
        bot.reply_to(message, f"📄 **نتيجة الترجمة (الأسطر الأولى):**\n\n{translated_text}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ أثناء الترجمة: {str(e)}")

print("🤖 بوت الباتروس يعمل الآن ويستمع للرسائل...")
bot.infinity_polling()
