import os
import telebot
import io
import requests
import fitz
import time
from deep_translator import MyMemoryTranslator

# ===== اختبار الترجمة عند بدء البوت =====
try:
    _test = MyMemoryTranslator(source='en-US', target='ar-SA').translate("Hello")
    print(f"[TEST TRANSLATE] النتيجة: {_test}")
except Exception as e:
    print(f"[TEST TRANSLATE ERROR] {e}")

BOT_TOKEN = os.getenv("BOT_TOKEN") or "8951863527:AAHCDAjJOCnphMu9"
bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك يا حيدر! الباتروس جاهز الآن لترجمة الملفات بنفس التنسيق المطلوب تماماً.")


def translate_text(text):
    """ترجمة نص واحد باستخدام MyMemory"""
    if not text.strip():
        return ""
    try:
        translator = MyMemoryTranslator(source='en-US', target='ar-SA')
        result = translator.translate(text)
        return result if result else ""
    except Exception as e:
        print(f"[TRANSLATE ERROR] {e} | النص: {text[:50]}")
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

        # ===== الخط العربي =====
        arabic_font_path = "Amiri-Regular.ttf"
        font_exists = os.path.exists(arabic_font_path)
        print(f"[FONT] الخط العربي موجود؟ {font_exists}")

        # ===== المرحلة 1: جمع كل الأسطر =====
        all_lines = []
        for page_num, page in enumerate(doc):
            text_instances = page.get_text("dict")
            for block in text_instances.get("blocks", []):
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        line_text = ""
                        x0, y0, x1, y1 = line.get("bbox", [0, 0, 0, 0])
                        for span in line.get("spans", []):
                            line_text += span.get("text", "") + " "
                        line_text = line_text.strip()
                        if len(line_text) > 2:
                            all_lines.append({
                                "page": page_num,
                                "bbox": (x0, y0, x1, y1),
                                "text": line_text
                            })

        print(f"[INFO] عدد الأسطر الكلي: {len(all_lines)}")

        if not all_lines:
            bot.reply_to(message, "⚠️ لم يتم العثور على نص في الملف.")
            return

        # ===== المرحلة 2: ترجمة كل سطر على حدة =====
        translated_count = 0
        failed_count = 0

        for idx, item in enumerate(all_lines):
            translated = translate_text(item["text"])
            if translated and translated.strip():
                page = doc[item["page"]]
                x0, y0, x1, y1 = item["bbox"]
                insert_point = fitz.Point(x0, y1 + 10)

                try:
                    if font_exists:
                        page.insert_text(
                            insert_point,
                            translated,
                            fontsize=8,
                            fontname="F0",
                            fontfile=arabic_font_path,
                            color=(0, 0, 0.6)
                        )
                    else:
                        page.insert_text(
                            insert_point,
                            translated,
                            fontsize=8,
                            color=(0, 0, 0.6)
                        )
                    translated_count += 1
                except Exception as e:
                    print(f"[INSERT ERROR] {e}")
                    failed_count += 1
            else:
                failed_count += 1

            # كل 10 أسطر اطبع تقدم
            if (idx + 1) % 10 == 0:
                print(f"[PROGRESS] {idx + 1}/{len(all_lines)} - ترجم: {translated_count}, فشل: {failed_count}")

            time.sleep(0.2)  # انتظار بسيط بين الطلبات

        print(f"[INFO] عدد الأسطر المترجمة: {translated_count}")
        print(f"[INFO] عدد الأسطر الفاشلة: {failed_count}")

        if translated_count == 0:
            bot.reply_to(message, "⚠️ لم يتم ترجمة أي سطر! تحقق من الـ Logs في Railway.")
            return

        output_pdf_io = io.BytesIO()
        doc.save(output_pdf_io)
        doc.close()
        output_pdf_io.seek(0)

        bot.send_document(
            message.chat.id,
            output_pdf_io,
            visible_file_name="translated_exact_layout.pdf",
            caption=f"✅ تمت ترجمة {translated_count} سطر بنجاح!"
        )

    except Exception as e:
        print(f"[MAIN ERROR] {e}")
        bot.reply_to(message, f"❌ حدث خطأ أثناء المعالجة: {str(e)}")


print("🤖 بوت الباتروس يعمل الآن...")
bot.infinity_polling()
