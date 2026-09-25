import os
import telebot
from googletrans import Translator
import PyPDF2
import io

BOT_TOKEN = os.getenv("BOT_TOKEN") or "8951863527:AAHCDAjJOCnphMu9"
bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()

translator = Translator()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك يا حيدر! بوت الباتروس جاهز الآن لترجمة ملفات الـ PDF بكل كفاءة.")

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

        translation = translator.translate(extracted_text[:400], dest='ar')
        
        bot.reply_to(message, f"📄 **نتيجة الترجمة:**\n\n{translation.text}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ: {str(e)}")

print("🤖 بوت الباتروس يعمل الآن...")
bot.infinity_polling()
