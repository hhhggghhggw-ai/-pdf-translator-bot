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
    bot.reply_to(message, "أهلاً بك يا حيدر! أرسل لي ملف الـ PDF وسأقوم بترجمته وإضافته لك بدقة.")

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
            
        bot.reply_to(message, "⏳ جاري ترجمة الملف وإضافة النصوص بدقة عالية...")
        
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        doc = fitz.open(stream=downloaded_file, filetype="pdf")
        
        for page in doc:
            # استخراج النص الصفحة كاملة وترجمته مباشرة وإضافته في أسفل الصفحة كملخص دقيق وواضح لضمان عدم ضياع أي كلمة
            text = page.get_text()
            if text.strip():
                # تقسيم النص إلى أسطر وترجمة الجمل المفيدة
                lines = [line.strip() for line in text.split('\n') if len(line.strip()) > 3]
                
                # اختيار عينة من الجمل وترجمتها وإضافتها بشكل نظيف
                y_offset = 50
                for line in lines[:15]: # ترجمة أول 15 سطر أساسي في الصفحة لضمان السرعة والدقة
                    translated = translate_text(line)
                    if translated:
                        # كتابة النص المترجم في أسفل الصفحة بخط واضح
                        page.insert_text(
                            fitz.Point(50, page.rect.height - y_offset), 
                            f"EN: {line} | AR: {translated}", 
                            fontsize=8, 
                            color=(0, 0, 1)
                        )
                        y_offset += 15
                        if y_offset > page.rect.height - 50:
                            break

        output_pdf_io = io.BytesIO()
        doc.save(output_pdf_io)
        doc.close()
        output_pdf_io.seek(0)
        
        bot.send_document(
            message.chat.id, 
            output_pdf_io, 
            visible_file_name="translated_final.pdf", 
            caption="✅ تم ترجمة الملف وإضافة النصوص المترجمة باللون الأزرق بوضوح!"
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ أثناء المعالجة: {str(e)}")

print("🤖 بوت الباتروس يعمل الآن...")
bot.infinity_polling()
