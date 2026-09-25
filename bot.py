import os
import io
import telebot
import time
import arabic_reshaper
from bidi.algorithm import get_display
from deep_translator import MyMemoryTranslator
from pptx import Presentation
from pptx.util import Pt, Emu
from pptx.dml.color import RGBColor
from PIL import Image

# ===== اختبار الترجمة =====
try:
    _test = MyMemoryTranslator(source='en-US', target='ar-SA').translate("Hello")
    print(f"[TEST TRANSLATE] النتيجة: {_test}")
except Exception as e:
    print(f"[TEST TRANSLATE ERROR] {e}")

BOT_TOKEN = os.getenv("BOT_TOKEN") or ""
bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()


def fix_arabic(text):
    """تصحيح النص العربي للعرض الصحيح"""
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


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(
        message,
        "أهلاً بك يا حيدر! 🎯\n"
        "أرسل لي ملف PowerPoint (PPTX) وسأترجمه:\n"
        "✅ النص الأصلي كما هو\n"
        "✅ الترجمة العربية تحت كل نص\n"
        "✅ الألوان متناسقة\n"
        "✅ الصور والجداول محفوظة"
    )


@bot.message_handler(content_types=['document'])
def handle_pptx(message):
    try:
        file_name = message.document.file_name.lower()

        # التحقق من النوع
        if not (file_name.endswith('.pptx') or file_name.endswith('.ppt')):
            bot.reply_to(message, "⚠️ عذراً، يرجى إرسال ملف PowerPoint (PPTX) فقط.")
            return

        if file_name.endswith('.ppt') and not file_name.endswith('.pptx'):
            bot.reply_to(message, "⚠️ الرجاء حفظ الملف بصيغة PPTX (وليس PPT القديم).")
            return

        bot.reply_to(message, "⏳ جاري معالجة الملف وترجمة المحتوى... قد يأخذ دقائق.")

        # تحميل الملف
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # فتح العرض
        prs = Presentation(io.BytesIO(downloaded_file))
        print(f"[INFO] عدد الشرائح: {len(prs.slides)}")

        translated_count = 0
        failed_count = 0

        # ===== المرور على كل شريحة =====
        for slide_idx, slide in enumerate(prs.slides):
            print(f"[SLIDE] معالجة الشريحة {slide_idx + 1}")

            # نجمع كل النصوص في الشريحة
            text_shapes = []  # [{shape, original_text, color, font_size}]

            for shape in slide.shapes:
                # === 1) النصوص ===
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        full_text = ""
                        color = (0, 0, 0)  # أسود افتراضي
                        font_size = 12

                        for run in paragraph.runs:
                            if run.text:
                                full_text += run.text

                                # استخراج اللون
                                try:
                                    if run.font.color and run.font.color.rgb:
                                        rgb = run.font.color.rgb
                                        color = (rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)
                                except:
                                    pass

                                # استخراج حجم الخط
                                try:
                                    if run.font.size:
                                        font_size = run.font.size.pt
                                except:
                                    pass

                        full_text = full_text.strip()
                        if len(full_text) > 2:
                            text_shapes.append({
                                "shape": shape,
                                "text": full_text,
                                "color": color,
                                "font_size": font_size,
                                "paragraph": paragraph
                            })

                # === 2) الصور ===
                if shape.shape_type == 13:  # PICTURE
                    # نصغر الصورة بنسبة 70% (اختياري)
                    try:
                        new_width = int(shape.width * 0.7)
                        new_height = int(shape.height * 0.7)
                        shape.width = new_width
                        shape.height = new_height
                        print(f"[IMAGE] تم تصغير الصورة في الشريحة {slide_idx + 1}")
                    except Exception as e:
                        print(f"[IMAGE RESIZE ERROR] {e}")

                # === 3) الجداول ===
                if shape.has_table:
                    try:
                        table = shape.table
                        # نصغر الجدول بنسبة 70%
                        new_width = int(shape.width * 0.7)
                        new_height = int(shape.height * 0.7)
                        shape.width = new_width
                        shape.height = new_height
                        print(f"[TABLE] تم تصغير الجدول في الشريحة {slide_idx + 1}")

                        # نترجم محتوى الجدول
                        for row in table.rows:
                            for cell in row.cells:
                                cell_text = cell.text.strip()
                                if len(cell_text) > 2:
                                    cell_translated = translate_text(cell_text)
                                    if cell_translated:
                                        translated_count += 1
                                        # نضيف الترجمة في نفس الخلية تحت النص
                                        arabic_fixed = fix_arabic(cell_translated)
                                        cell.text = cell_text + "\n" + arabic_fixed
                                    else:
                                        failed_count += 1
                    except Exception as e:
                        print(f"[TABLE ERROR] {e}")

            # ===== ترجمة النصوص وإضافة الترجمة تحتها =====
            for text_data in text_shapes:
                shape = text_data["shape"]
                original_text = text_data["text"]
                color = text_data["color"]
                font_size = text_data["font_size"]

                translated = translate_text(original_text)

                if translated:
                    translated_count += 1
                    arabic_fixed = fix_arabic(translated)

                    try:
                        # نضيف فقرة جديدة في نفس مربع النص
                        new_paragraph = shape.text_frame.add_paragraph()
                        new_run = new_paragraph.add_run()
                        new_run.text = arabic_fixed

                        # حجم خط الترجمة (أصغر قليلاً)
                        new_run.font.size = Pt(max(9, font_size - 1))

                        # نفس اللون
                        new_run.font.color.rgb = RGBColor(
                            int(color[0] * 255),
                            int(color[1] * 255),
                            int(color[2] * 255)
                        )

                        print(f"[TRANSLATED] {original_text[:40]} → {arabic_fixed[:40]}")
                    except Exception as e:
                        print(f"[INSERT ERROR] {e}")
                        failed_count += 1
                else:
                    failed_count += 1

                time.sleep(0.15)

        print(f"[INFO] عدد النصوص المترجمة: {translated_count}")
        print(f"[INFO] عدد النصوص الفاشلة: {failed_count}")

        if translated_count == 0:
            bot.reply_to(message, "⚠️ لم يتم ترجمة أي نص! تحقق من الـ Logs.")
            return

        # ===== حفظ الملف =====
        output_io = io.BytesIO()
        prs.save(output_io)
        output_io.seek(0)

        bot.send_document(
            message.chat.id,
            output_io,
            visible_file_name="translated_presentation.pptx",
            caption=f"✅ تمت ترجمة {translated_count} نص!\n📄 الملف جاهز بصيغة PPTX"
        )

    except Exception as e:
        print(f"[MAIN ERROR] {e}")
        bot.reply_to(message, f"❌ حدث خطأ: {str(e)}")


print("🤖 بوت الباتروس يعمل الآن...")
bot.infinity_polling()
