import os
import telebot
import io
import requests
import fitz  # PyMuPDF

BOT_TOKEN = os.getenv("BOT_TOKEN") or "8951863527:AAHCDAjJOCnphMu9"
bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك يا حيدر! أرسل لي ملف PDF وسأقوم بإضافة الترجمة تحته مع الحفاظ على الصور والتنسيق.")

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
            
        bot.reply_to(message, "⏳ جاري معالجة الملف وإضافة الترجمة بدقة...")
        
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        doc = fitz.open(stream=downloaded_file, filetype="pdf")
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("blocks")
            
            for b in blocks:
                if b[6] == 0:  # إذا كان بلوك نصي
                    original_text = b[4].strip()
                    if original_text:
                        translated = translate_text(original_text)
                        
                        # إنشاء إحداثيات أسفل النص الأصلي مباشره لإدراج الترجمة
                        rect = fitz.Rect(b[0], b[3] - 5, b[2], b[3] + 25)
                        
                        # إدراج الترجمة تحته بخط صغير وواضح
                        page.insert_textbox(
                            rect, 
                            f"ترجمة: {translated}", 
                            fontsize=7, 
                            color=(0, 0, 1)  # لون أزرق للترجمة لتمييزها عن الأصلي
                        )

        output_pdf_io = io.BytesIO()
        doc.save(output_pdf_io)
        doc.close()
        output_pdf_io.seek(0)
        
        bot.send_document(
            message.chat.id, 
            output_pdf_io, 
            visible_file_name="translated_with_original.pdf", 
            caption="✅ تم إدراج الترجمة تحت النصوص مع الحفاظ على الصور والتنسيق تماماً!"
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ أثناء المعالجة: {str(e)}")

print("🤖 بوت الباتروس يعمل الآن...")
bot.infinity_polling()
