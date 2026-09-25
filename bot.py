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
    bot.reply_to(message, "أهلاً بك يا حيدر! بوت الباتروس جاهز الآن لترجمة ملفات الـ PDF بدقة تامة وضبط أحجام الخطوط.")

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
    return f"[تعذر الترجمة]"

@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    try:
        if not message.document.file_name.endswith('.pdf'):
            bot.reply_to(message, "⚠️ عذراً، يرجى إرسال ملف بصيغة PDF فقط.")
            return
            
        bot.reply_to(message, "⏳ جاري قراءة الملف، تصغير الخط، وترجمة النصوص بدقة...")
        
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        doc = fitz.open(stream=downloaded_file, filetype="pdf")
        
        for page in doc:
            text = page.get_text()
            if text.strip():
                # استخراج الأسطر المفيدة وتجنب الفراغات
                lines = [line.strip() for line in text.split('\n') if len(line.strip()) > 2]
                
                # إضافة المساحة والترجمة في أسفل الصفحة بخط صغير جداً ومرتب (حجم 6) ليتناسب تماماً
                y_offset = 30
                max_height = page.rect.height - 40
                
                for line in lines[:20]: # ترجمة أول 20 سطراً أساسياً بكل عناية
                    translated = translate_text(line)
                    if translated:
                        # كتابة النص الأصلي والترجمة بخط صغير متناسق
                        content_to_insert = f"EN: {line} | AR: {translated}"
                        
                        page.insert_text(
                            fitz.Point(30, max_height - y_offset), 
                            content_to_insert, 
                            fontsize=6,  # حجم خط صغير جداً ومناسب للصفحة
                            color=(0, 0, 0.8)
                        )
                        y_offset += 12 # مسافة صغيرة ومرتبة بين السطور
                        
                        if y_offset > max_height - 50:
                            break

        output_pdf_io = io.BytesIO()
        doc.save(output_pdf_io)
        doc.close()
        output_pdf_io.seek(0)
        
        bot.send_document(
            message.chat.id, 
            output_pdf_io, 
            visible_file_name="translated_perfect.pdf", 
            caption="✅ تم ترجمة الملف بنجاح مع تصغير الخط وضبط التنسيق تماماً!"
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ أثناء المعالجة: {str(e)}")

print("🤖 بوت الباتروس يعمل الآن...")
bot.infinity_polling()
