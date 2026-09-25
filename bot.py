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
    bot.reply_to(message, "أهلاً بك يا حيدر! الباتروس جاهز الآن لترجمة الملفات بنفس التنسيق المطلوب تماماً.")

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
            if translated:
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
            
        bot.reply_to(message, "⏳ جاري معالجة الملف وترجمة النصوص تحت كل سطر بالتنسيق المطلوب...")
        
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        doc = fitz.open(stream=downloaded_file, filetype="pdf")
        
        for page in doc:
            # استخراج تفاصيل الكلمات والأسطر بدقة هندسية (get_text("words"))
            # تجميع الكلمات حسب الأسطر الحقيقية في الصفحة
            text_instances = page.get_text("dict")
            
            for block in text_instances.get("blocks", []):
                if block.get("type") == 0:  # بلوك نصي
                    for line in block.get("lines", []):
                        line_text = ""
                        x0, y0, x1, y1 = line.get("bbox", [0, 0, 0, 0])
                        
                        for span in line.get("spans", []):
                            line_text += span.get("text", "") + " "
                            
                        line_text = line_text.strip()
                        if len(line_text) > 2:
                            translated = translate_text(line_text)
                            if translated:
                                # موقع دقيق تحت السطر الأصلي مباشرة
                                insert_point = fitz.Point(x0, y1 + 10)
                                page.insert_text(
                                    insert_point,
                                    translated,
                                    fontsize=7,
                                    color=(0, 0, 0.6)  # لون أزرق هادئ للترجمة يشبه الصورة المطلوبة
                                )

        output_pdf_io = io.BytesIO()
        doc.save(output_pdf_io)
        doc.close()
        output_pdf_io.seek(0)
        
        bot.send_document(
            message.chat.id, 
            output_pdf_io, 
            visible_file_name="translated_exact_layout.pdf", 
            caption="✅ تم إتمام ترجمة الملف وإضافة الترجمة تحت السطور بدقة مطابقة للتنسيق المطلوبة!"
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ أثناء المعالجة: {str(e)}")

print("🤖 بوت الباتروس يعمل الآن...")
bot.infinity_polling()
