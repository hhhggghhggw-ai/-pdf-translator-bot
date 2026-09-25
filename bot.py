import os
import telebot
from deep_translator import GoogleTranslator
import PyPDF2
import io

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
        # أخذ أول صفحة فقط لتجنب الضغط والخطأ
        if len(reader.pages) > 0:
            extracted_text = reader.pages[0].extract_text() or ""
                
        if not extracted_text.strip():
            bot.reply_to(message, "⚠️ عذراً، لم يتم العثور على نصوص قابلة للقراءة في الصفحة الأولى من الملف.")
            return
            
        # تقليل عدد الحروف المترجمة لضمان عدم حدوث حظر
        short_text = extracted_text[:400]
        translated_text = translator.translate(short_text)
        
        bot.reply_to(message, f"📄 **نتيجة ترجمة الصفحة الأولى:**\n\n{translated_text}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ أثناء الترجمة: {str(e)}")

print("🤖 البوت يعمل الآن ويستمع للرسائل...")
bot.infinity_polling()
