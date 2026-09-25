import os
import telebot
import io
import requests
import fitz

BOT_TOKEN = os.getenv("BOT_TOKEN") or "8951863527:AAHCDAjJOCnphMu9"
bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك يا حيدر! البوت جاهز الآن لترجمة ملفات الـ PDF بدقة وإضافة الترجمة تحت كل سطر بانتظام.")

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
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            result = response.json()
            translated = "".join([item[0] for item in result[0] if item[0]])
            if translated and translated != text:
                return translated
    except Exception:
        pass
    return ""

@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    try:
        if not message.document.file_name.endswith('.pdf'):
            bot.reply_to(message, "⚠️ عذراً، يرجى إرسال ملف بصيغة PDF فقط.")
            return
            
        bot.reply_to(message, "⏳ جاري معالجة الملف وترجمة النصوص تحت كل سطر بدقة...")
        
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        doc = fitz.open(stream=downloaded_file, filetype="pdf")
        
        for page in doc:
            # استخدام blocks للحصول على مواقع النصوص بدقة وعدم تداخلها مع الصور
            blocks = page.get_text("blocks")
            for b in blocks:
                if b[6] == 0:  # التأكد أنه بلوك نصي وليس صورة
                    original_text = b[4].strip()
                    if len(original_text) > 3:
                        translated = translate_text(original_text)
                        if translated:
                            # إحداثيات موقع النص الأصلي
                            x0, y0, x1, y1 = b[0], b[1], b[2], b[3]
                            
                            # إنشاء مساحة صغيرة تحت النص الأصلي مباشرة لإدراج الترجمة
                            rect = fitz.Rect(x0, y1, x1, y1 + 15)
                            
                            page.insert_textbox(
                                rect,
                                f"ترجمة: {translated}",
                                fontsize=5.5,  # خط صغير جداً ومرتب
                                color=(0, 0, 0.7)  # لون مميز للترجمة
                            )

        output_pdf_io = io.BytesIO()
        doc.save(output_pdf_io)
        doc.close()
        output_pdf_io.seek(0)
        
        bot.send_document(
            message.chat.id, 
            output_pdf_io, 
            visible_file_name="translated_exact_layout.pdf", 
            caption="✅ تم إدراج الترجمة تحت كل فقرة بدقة ودون التأثير على الصور أو التنسيق!"
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ أثناء المعالجة: {str(e)}")

print("🤖 بوت الباتروس يعمل الآن...")
bot.infinity_polling()
