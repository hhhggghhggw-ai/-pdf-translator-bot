import os
import io
import telebot
import time
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


# ===== إعدادات قابلة للتعديل =====
ORIGINAL_FONT_SCALE = 0.85   # تصغير الأصل بنسبة 15%
TRANSLATION_FONT_SCALE = 0.80  # تصغير الترجمة بنسبة 20%
MIN_FONT_SIZE = 7             # أصغر حجم مسموح
SPACE_FONT_SIZE = 6           # حجم فراغ بين المجموعات


def translate_text(text):
    if not text.strip():
        return ""
    try:
        translator = MyMemoryTranslator(source='en-US', target='ar-SA')
        result = translator.translate(text)
        return result if result else ""
    except Exception as e:
        print(f"[TRANSLATE ERROR] {e}")
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
    """تقسيم النص إلى أسطر"""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    lines = [line.strip() for line in text.split('\n')]
    lines = [line for line in lines if line]
    if not lines:
        return [text.strip()]
    return lines


def create_text_paragraph(text_frame, text, color, size):
    """إنشاء فقرة جديدة"""
    new_para = text_frame.add_paragraph()
    new_run = new_para.add_run()
    new_run.text = text

    try:
        new_run.font.size = Pt(size)
    except:
        pass

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


def process_table(table, slide_num):
    """معالجة الجداول: ترجمة كل خلية"""
    translated = 0
    failed = 0
    for row_idx, row in enumerate(table.rows):
        for col_idx, cell in enumerate(row.cells):
            cell_text = cell.text.strip()
            if len(cell_text) > 2:
                # لا نترجم الخلايا الفارغة أو الرقمية
                if not any(c.isalpha() for c in cell_text):
                    continue

                # نترجم
                ar_text = translate_text(cell_text)
                if ar_text:
                    # نضيف الترجمة في الخلية
                    try:
                        # نضيف فقرة جديدة داخل الخلية
                        tf = cell.text_frame
                        new_p = tf.add_paragraph()
                        new_run = new_p.add_run()
                        new_run.text = ar_text
                        # نصغّر الخط
                        try:
                            new_run.font.size = Pt(9)
                        except:
                            pass
                        # RTL
                        try:
                            pPr = new_p._p.get_or_add_pPr()
                            pPr.set('rtl', '1')
                        except:
                            pass
                        translated += 1
                    except Exception as e:
                        print(f"[TABLE CELL ERROR] {e}")
                        failed += 1
                else:
                    failed += 1
                time.sleep(0.15)
    return translated, failed


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(
        message,
        "أهلاً بك يا حيدر! 🎯\n"
        "أرسل ملف PPTX وسأترجمه:\n"
        "✅ سطر سطر مع ترجمته تحته\n"
        "✅ الألوان متناسقة\n"
        "✅ حجم الخط مصغّر ليناسب الصفحة\n"
        "✅ الجداول مترجمة أيضاً"
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

        total_translated = 0
        total_failed = 0

        for slide_idx, slide in enumerate(prs.slides):
            print(f"[SLIDE {slide_idx + 1}] بدء المعالجة")

            slide_translated = 0
            slide_failed = 0

            for shape in slide.shapes:
                # === 1) الجداول ===
                if shape.has_table:
                    print(f"[TABLE] معالجة جدول في الشريحة {slide_idx + 1}")
                    t, f = process_table(shape.table, slide_idx + 1)
                    slide_translated += t
                    slide_failed += f
                    continue

                # === 2) النصوص ===
                if not shape.has_text_frame:
                    continue

                text_frame = shape.text_frame

                # نجمع كل الأسطر
                all_lines = []
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

                # نمسح كل الفقرات
                for para in list(text_frame.paragraphs):
                    p = para._p
                    p.getparent().remove(p)

                # نضيف: سطر + ترجمته + مسافة
                for line_data in all_lines:
                    original_text = line_data["text"]
                    color = line_data["color"]
                    size = line_data["size"]

                    # حجم السطر الأصلي المصغّر
                    new_size = max(MIN_FONT_SIZE, int(size * ORIGINAL_FONT_SCALE))

                    # 1) السطر الإنجليزي
                    create_text_paragraph(text_frame, original_text, color, new_size)

                    # 2) الترجمة
                    translated = translate_text(original_text)
                    if translated:
                        slide_translated += 1
                        t_size = max(MIN_FONT_SIZE, int(size * TRANSLATION_FONT_SCALE))
                        create_text_paragraph(text_frame, translated, color, t_size)
                    else:
                        slide_failed += 1

                    # 3) مسافة
                    empty_para = text_frame.add_paragraph()
                    empty_run = empty_para.add_run()
                    empty_run.text = " "
                    try:
                        empty_run.font.size = Pt(SPACE_FONT_SIZE)
                    except:
                        pass

                    time.sleep(0.15)

            print(f"[SLIDE {slide_idx + 1}] ترجم: {slide_translated}, فشل: {slide_failed}")
            total_translated += slide_translated
            total_failed += slide_failed

        print(f"[INFO] الإجمالي - مترجم: {total_translated}, فشل: {total_failed}")

        if total_translated == 0:
            bot.reply_to(message, "⚠️ لم يتم ترجمة أي نص! تحقق من الـ Logs.")
            return

        output_io = io.BytesIO()
        prs.save(output_io)
        output_io.seek(0)

        bot.send_document(
            message.chat.id,
            output_io,
            visible_file_name="translated_presentation.pptx",
            caption=f"✅ تمت ترجمة {total_translated} نص!"
        )

    except Exception as e:
        print(f"[MAIN ERROR] {e}")
        bot.reply_to(message, f"❌ حدث خطأ: {str(e)}")


print("🤖 بوت الباتروس يعمل الآن...")
bot.infinity_polling()
