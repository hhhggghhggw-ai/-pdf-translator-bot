import os
import telebot
import io
import requests
import fitz  # مكتبة PyMuPDF للتعامل مع ملفات PDF والحفاظ على الصور والتنسيق

BOT_TOKEN = os.getenv("BOT_TOKEN") or "8951863527:AAHCDAjJOCnphMu9"
bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك يا حيدر! أرسل لي ملف PDF وسأقوم بترجمته مع الحفاظ على الصور والتنسيق الأصلي تماماً وإرجاع الملف لك.")

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
            
        bot.reply_to(message, "⏳ جاري قراءة الملف، ترجمته، والحفاظ على الصور والتنسيق... يرجى الانتظار قليلاً.")
        
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # فتح ملف الـ PDF باستخدام PyMuPDF من الذاكرة
        doc = fitz.open(stream=downloaded_file, filetype="pdf")
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            # استخراج الكتل النصية مع إحداثياتها للحفاظ على مكانها
            blocks = page.get_text("blocks")
            
            for b in blocks:
                # b يحتوي على: (x0, y0, x1, y1, text, block_no, block_type)
                # block_type == 0 يعني نص (وليست صورة)
                if b[6] == 0:
                    original_text = b[4].strip()
                    if original_text:
                        translated = translate_text(original_text)
                        # تجهيز النص المدمج (الأصلي وتحته الترجمة)
                        combined_text = f"{original_text}\n[ترجمة: {translated}]"
                        
                        # تحديد مربع النص الأصلي لمسحه أو الكتابة فوقه بشكل منظم
                        rect = fitz.Rect(b[0], b[1], b[2], b[3])
                        
                        # رسم مستطيل أبيض صغير لتغطية النص القديم بشكل نظيف (اختياري لعدم التداخل)
                        page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
                        
                        # كتابة النص الجديد (الأصلي + الترجمة) في نفس المكان
                        page.insert_textbox(rect, combined_text, fontsize=8, color=(0, 0, 0))

        # حفظ الملف الناتج في الذاكرة
        output_pdf_io = io.BytesIO()
        doc.save(output_pdf_io)
        doc.close()
        output_pdf_io.seek(0)
        
        # إرسال الملف المحدث للمستخدم
        bot.send_document(
            message.chat.id, 
            output_pdf_io, 
            visible_file_name="translated_formatted.pdf", 
            caption="✅ تم ترجمة الملف مع الحفاظ على الصور والتنسيق الأصلي بنجاح!"
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ أثناء معالجة الملف: {str(e)}")

print("🤖 بوت الباتروس يعمل الآن...")
bot.infinity_polling()
