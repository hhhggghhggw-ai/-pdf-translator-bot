import os
import io
import telebot
import time
import copy
from deep_translator import MyMemoryTranslator
from pptx import Presentation
from pptx.util import Pt
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn

# ===== اختبار الترجمة =====
try:
    _test = MyMemoryTranslator(source='en-US', target='ar-SA').translate("Hello")
    print(f"[TEST TRANSLATE] النتيجة: {_test}")
except Exception as e:
    print(f"[TEST TRANSLATE ERROR] {e}")

BOT_TOKEN = os.getenv("BOT_TOKEN") or ""
bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()


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


def get_run_color(run):
    try:
        if run.font.color and run.font.color.rgb:
            rgb = run.font.color.rgb
            return RGBColor(rgb[0], rgb[1], rgb[2])
    except:
        pass
    return RGBColor(0, 0, 0)


def get_run_size(run, default=12):
    try:
        if run.font.size:
            return run.font.size.pt
    except:
        pass
    return default


def split_into_lines(text):
    """
    تقسيم النص إلى أسطر منفصلة
    - بناءً على \n
    - أو إذا طويل جداً، نقسمه
    """
    # نستبدل \r\n بـ \n
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # نقسم على \n أولاً
    lines = [line.strip() for line in text.split('\n')]

    # نحذف الأسطر الفارغة
    lines = [line for line in lines if line]

    # إذا ما فيه \n، السطر كامل جملة واحدة
    if not lines:
        return [text.strip()]

    return lines


def create_text_paragraph(text_frame, text, color, size, space_before=0):
    """
    إنشاء فقرة جديدة في text_frame بالنص واللون والحجم المحدد
    """
    new_para = text_frame.add_paragraph()
    new_run = new_para.add_run()
    new_run.text = text

    # الحجم
    try:
        new_run.font.size = Pt(size)
    except:
        pass

    # اللون
    try:
        new_run.font.color.rgb = color
    except:
        pass

    # RTL
    try:
        pPr = new_para._p.get_or_add_pPr()
        pPr.set('rtl', '1')
    except:
        pass

    return new_para


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(
        message,
        "أهلاً بك يا حيدر! 🎯\n"
        "أرسل لي ملف PowerPoint (PPTX) وسأترجمه:\n"
        "✅ سطر سطر\n"
        "✅ ترجمة تحت كل سطر\n"
        "✅ مسافة بين المجموعات"
    )


@bot.message_handler(content_types=['document'])
def handle_pptx(message):
    try:
        file_name = message.document.file_name.lower()

        if not file_name.endswith('.pptx'):
            bot.reply_to(message, "⚠️ عذراً، يرجى إرسال ملف PowerPoint بصيغة PPTX فقط.")
            return

        bot.reply_to(message, "⏳ جاري معالجة الملف...")

        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        prs = Presentation(io.BytesIO(downloaded_file))
        print(f"[INFO] عدد الشرائح: {len(prs.slides)}")

        translated_count = 0
        failed_count = 0

        for slide_idx, slide in enumerate(prs.slides):
            print(f"[SLIDE] معالجة الشريحة {slide_idx + 1}")

            for shape in slide.shapes:
                if not shape.has_text_frame:
                    continue

                text_frame = shape.text_frame

                # نجمع كل الأسطر من كل الفقرات
                all_lines = []  # [{text, color, size}]

                for para in text_frame.paragraphs:
                    para_text = ""
                    para_color = RGBColor(0, 0, 0)
                    para_size = 12

                    for run in para.runs:
                        if run.text:
                            para_text += run.text
                            para_color = get_run_color(run)
                            para_size = get_run_size(run)

                    para_text = para_text.strip()
                    if len(para_text) > 2:
                        # نقسم الفقرة إلى أسطر
                        lines = split_into_lines(para_text)
                        for line in lines:
                            if len(line) > 2:
                                all_lines.append({
                                    "text": line,
                                    "color": para_color,
                                    "size": para_size
                                })

                if not all_lines:
                    continue

                # ===== نمسح محتوى المربع الأصلي =====
                # نحذف كل الفقرات الحالية
                for para in list(text_frame.paragraphs):
                    p = para._p
                    p.getparent().remove(p)

                # ===== نضيف: سطر أصلي + ترجمته + مسافة =====
                for line_data in all_lines:
                    original_text = line_data["text"]
                    color = line_data["color"]
                    size = line_data["size"]

                    # 1) السطر الإنجليزي
                    create_text_paragraph(text_frame, original_text, color, size)

                    # 2) الترجمة
                    translated = translate_text(original_text)
                    if translated:
                        translated_count += 1
                        # حجم الترجمة أصغر بنقطة
                        t_size = max(9, int(size) - 1)
                        create_text_paragraph(text_frame, translated, color, t_size)
                    else:
                        failed_count += 1

                    # 3) مسافة فارغة
                    empty_para = text_frame.add_paragraph()
                    empty_run = empty_para.add_run()
                    empty_run.text = " "
                    try:
                        empty_run.font.size = Pt(8)
                    except:
                        pass

                    time.sleep(0.15)

        print(f"[INFO] عدد الأسطر المترجمة: {translated_count}")
        print(f"[INFO] عدد الأسطر الفاشلة: {failed_count}")

        if translated_count == 0:
            bot.reply_to(message, "⚠️ لم يتم ترجمة أي نص! تحقق من الـ Logs.")
            return

        output_io = io.BytesIO()
        prs.save(output_io)
        output_io.seek(0)

        bot.send_document(
            message.chat.id,
            output_io,
            visible_file_name="translated_presentation.pptx",
            caption=f"✅ تمت ترجمة {translated_count} سطر!"
        )

    except Exception as e:
        print(f"[MAIN ERROR] {e}")
        bot.reply_to(message, f"❌ حدث خطأ: {str(e)}")


print("🤖 بوت الباتروس يعمل الآن...")
bot.infinity_polling()
