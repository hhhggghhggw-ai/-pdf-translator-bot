import os
import telebot
import io
import requests
import fitz
import time
import re
import arabic_reshaper
from bidi.algorithm import get_display
from deep_translator import MyMemoryTranslator

# ===== اختبار الترجمة عند بدء البوت =====
try:
    _test = MyMemoryTranslator(source='en-US', target='ar-SA').translate("Hello")
    print(f"[TEST TRANSLATE] النتيجة: {_test}")
except Exception as e:
    print(f"[TEST TRANSLATE ERROR] {e}")

BOT_TOKEN = os.getenv("BOT_TOKEN") or "8951863527:AAHCDAjJOCnhphMu9dpMxMbiuCfA3SMkOF0"
bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()


def fix_arabic(text):
    """تصحيح النص العربي ليعرض بشكل صحيح في PyMuPDF"""
    if not text:
        return ""
    try:
        reshaped = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped)
        return bidi_text
    except Exception as e:
        print(f"[ARABIC FIX ERROR] {e}")
        return text


def translate_text(text):
    """ترجمة نص واحد"""
    if not text.strip():
        return ""
    try:
        translator = MyMemoryTranslator(source='en-US', target='ar-SA')
        result = translator.translate(text)
        return result if result else ""
    except Exception as e:
        print(f"[TRANSLATE ERROR] {e} | النص: {text[:50]}")
        return ""


def is_sentence_end(text):
    """هل النص ينتهي بنقطة/؟/!؟"""
    return bool(re.search(r'[.!?]\s*$', text.strip()))


def get_line_color(line):
    """
    استخراج اللون السائد في السطر
    يُرجع tuple: (r, g, b)
    """
    color_counts = {}
    for span in line.get("spans", []):
        color_int = span.get("color", 0)
        # تحويل اللون من int إلى RGB
        r = (color_int >> 16) & 255
        g = (color_int >> 8) & 255
        b = color_int & 255
        # تجميع حسب اللون
        color_key = (r // 50, g // 50, b // 50)  # تجميع تقريبي
        color_counts[color_key] = color_counts.get(color_key, 0) + len(span.get("text", ""))
    
    if not color_counts:
        return (0, 0, 0)  # أسود افتراضي
    
    # اللون الأكثر تكراراً
    dominant = max(color_counts, key=color_counts.get)
    # إرجاعه بألوان فعلية (نأخذ من أول span لهذا اللون)
    for span in line.get("spans", []):
        color_int = span.get("color", 0)
        r = (color_int >> 16) & 255
        g = (color_int >> 8) & 255
        b = color_int & 255
        if (r // 50, g // 50, b // 50) == dominant:
            return (r / 255, g / 255, b / 255)
    
    return (0, 0, 0)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك يا حيدر! الباتروس جاهز الآن لترجمة الملفات جملة جملة مع الحفاظ على الألوان.")


@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    try:
        if not message.document.file_name.endswith('.pdf'):
            bot.reply_to(message, "⚠️ عذراً، يرجى إرسال ملف بصيغة PDF فقط.")
            return

        bot.reply_to(message, "⏳ جاري معالجة الملف وترجمة الجمل مع الألوان...")

        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        doc = fitz.open(stream=downloaded_file, filetype="pdf")

        # ===== الخط العربي =====
        arabic_font_path = "Amiri-Regular.ttf"
        font_exists = os.path.exists(arabic_font_path)
        print(f"[FONT] الخط العربي موجود؟ {font_exists}")

        translated_count = 0
        failed_count = 0

        for page_num, page in enumerate(doc):
            print(f"[PAGE] معالجة الصفحة {page_num + 1}")

            text_instances = page.get_text("dict")

            # ===== المرحلة 1: جمع الأسطر مع ألوانها =====
            page_lines = []
            for block in text_instances.get("blocks", []):
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        line_text = ""
                        x0, y0, x1, y1 = line.get("bbox", [0, 0, 0, 0])
                        for span in line.get("spans", []):
                            line_text += span.get("text", "") + " "
                        line_text = line_text.strip()
                        if line_text:
                            # استخراج لون السطر
                            color = get_line_color(line)
                            page_lines.append({
                                "bbox": (x0, y0, x1, y1),
                                "text": line_text,
                                "color": color
                            })

            # ===== المرحلة 2: تجميع الأسطر في جمل =====
            sentences = []
            current_sentence = {"text": "", "lines": [], "color": (0, 0, 0)}

            for line in page_lines:
                # إذا كانت الجملة فارغة → نأخذ لون أول سطر
                if not current_sentence["lines"]:
                    current_sentence["color"] = line["color"]
                current_sentence["text"] += " " + line["text"]
                current_sentence["lines"].append(line)

                if is_sentence_end(line["text"]):
                    current_sentence["text"] = current_sentence["text"].strip()
                    sentences.append(current_sentence)
                    current_sentence = {"text": "", "lines": [], "color": (0, 0, 0)}

            if current_sentence["text"].strip():
                current_sentence["text"] = current_sentence["text"].strip()
                sentences.append(current_sentence)

            print(f"[INFO] عدد الجمل في الصفحة: {len(sentences)}")

            # ===== المرحلة 3: ترجمة كل جملة =====
            for sentence in sentences:
                if len(sentence["text"]) < 3:
                    continue

                translated = translate_text(sentence["text"])

                if translated and translated.strip():
                    last_line = sentence["lines"][-1]
                    x0, y0, x1, y1 = last_line["bbox"]
                    color = sentence["color"]

                    arabic_fixed = fix_arabic(translated)

                    # تقسيم الترجمة الطويلة إلى أسطر
                    max_chars = 85
                    words = arabic_fixed.split()
                    lines_to_write = []
                    current_line = ""
                    for word in words:
                        if len(current_line) + len(word) + 1 <= max_chars:
                            current_line += " " + word if current_line else word
                        else:
                            lines_to_write.append(current_line)
                            current_line = word
                    if current_line:
                        lines_to_write.append(current_line)

                    # كتابة كل سطر تحت السابق
                    for i, line_text in enumerate(lines_to_write):
                        insert_point = fitz.Point(x0, y1 + 13 + (i * 11))
                        try:
                            if font_exists:
                                page.insert_text(
                                    insert_point,
                                    line_text,
                                    fontsize=9,
                                    fontname="F0",
                                    fontfile=arabic_font_path,
                                    color=color
                                )
                            else:
                                page.insert_text(
                                    insert_point,
                                    line_text,
                                    fontsize=9,
                                    color=color
                                )
                        except Exception as e:
                            print(f"[INSERT ERROR] {e}")

                    translated_count += 1
                else:
                    failed_count += 1

                time.sleep(0.2)

        print(f"[INFO] عدد الجمل المترجمة: {translated_count}")
        print(f"[INFO] عدد الجمل الفاشلة: {failed_count}")

        if translated_count == 0:
            bot.reply_to(message, "⚠️ لم يتم ترجمة أي جملة! تحقق من الـ Logs.")
            return

        output_pdf_io = io.BytesIO()
        doc.save(output_pdf_io)
        doc.close()
        output_pdf_io.seek(0)

        bot.send_document(
            message.chat.id,
            output_pdf_io,
            visible_file_name="translated_colored.pdf",
            caption=f"✅ تمت ترجمة {translated_count} جملة مع الحفاظ على الألوان!"
        )

    except Exception as e:
        print(f"[MAIN ERROR] {e}")
        bot.reply_to(message, f"❌ حدث خطأ: {str(e)}")


print("🤖 بوت الباتروس يعمل الآن...")
bot.infinity_polling()
