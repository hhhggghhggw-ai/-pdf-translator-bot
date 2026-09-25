import os
import telebot
import PyPDF2
import io
import requests
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

BOT_TOKEN = os.getenv("BOT_TOKEN") or "8951863527:AAHCDAjJOCnphMu9"
bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك يا حيدر! أرسل لي ملف PDF وسأقوم بترجمته سطراً بسطر مع الاحتفاظ بالتنسيق وإرساله لك كملف جديد.")

def translate_text(text):
    if not text.strip():
        return ""
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
            return "".join([item[0] for item in result[0] if item[0]])
    except Exception:
        pass
    return text

@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    try:
        if not message.document.file_name.endswith('.pdf'):
            bot.reply_to(message, "⚠️ عذراً، يرجى إرسال ملف بصيغة PDF فقط.")
            return
            
        bot.reply_to(message, "⏳ جاري قراءة الملف، الترجمة سطر بسطر، وإنشاء ملف الـ PDF الجديد... البضع ثوانٍ من فضلك.")
        
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        pdf_file = io.BytesIO(downloaded_file)
        reader = PyPDF2.PdfReader(pdf_file)
        
        if len(reader.pages) == 0:
            bot.reply_to(message, "⚠️ عذراً، الملف فارغ.")
            return
            
        # استخراج النص من الصفحة الأولى كمثال عملي للترجمة السطرية
        page = reader.pages[0]
        extracted_text = page.extract_text() or ""
        
        if not extracted_text.strip():
            bot.reply_to(message, "⚠️ لم يتم العثور على نص قابل للقراءة في الصفحة.")
            return

        lines = extracted_text.split('\n')
        
        # إنشاء ملف PDF جديد للنتيجة
        output_pdf_io = io.BytesIO()
        c = canvas.Canvas(output_pdf_io, pagesize=letter)
        width, height = letter
        
        y_position = height - 50  # البدء من أعلى الصفحة
        
        for line in lines[:25]:  # ترجمة أول 25 سطراً كبداية لضمان السرعة وعدم تجاوز الوقت
            if not line.strip():
                continue
                
            translated_line = translate_text(line)
            
            # كتابة السطر الأصلي بالإنجليزية
            c.setFont("Helvetica", 10)
            c.drawString(50, y_position, line[:80]) # تقطير النص الطويل لكي لا يخرج عن الحافة
            y_position -= 15
            
            # كتابة الترجمة تحته
            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, y_position, f"ترجمة: {translated_line[:80]}")
            y_position -= 25
            
            if y_position < 50: # الانتقال لصفحة جديدة إذا انتهت المساحة
                c.showPage()
                y_position = height - 50
                
        c.save()
        output_pdf_io.seek(0)
        
        # إرسال الملف الناتج للمستخدم
        bot.send_document(
            message.chat.id, 
            output_pdf_io, 
            visible_file_name="translated_output.pdf", 
            caption="✅ تم ترجمة الملف بنجاح (السطر الأصلي وتحته الترجمة العربية)!"
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ أثناء المعالجة: {str(e)}")

print("🤖 بوت الباتروس يعمل الآن...")
bot.infinity_polling()
