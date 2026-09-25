import os
import io
import telebot
import time
import copy
from deep_translator import MyMemoryTranslator
from pptx import Presentation
from pptx.util import Pt, Emu, Inches
from pptx.dml.color import RGBColor

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
    """استخراج اللون من run"""
    try:
        if run.font.color and run.font.color.rgb:
            rgb = run.font.color.rgb
            return RGBColor(rgb[0], rgb[1], rgb[2])
    except:
        pass
    return RGBColor(0, 0, 0)  # أسود افتراضي


def get_run_size(run, default=12):
    """استخراج حجم الخط"""
    try:
        if run.font.size:
            return run.font.size.pt
    except:
        pass
    return default


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

        if not file_name.endswith('.pptx'):
            bot.reply_to(message, "⚠️ عذراً، يرجى إرسال ملف PowerPoint بصيغة PPTX فقط.")
            return

        bot.reply_to(message, "⏳ جاري معالجة الملف وترجمة المحتوى... قد يأخذ دقائق.")

        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        prs = Presentation(io.BytesIO(downloaded_file))
        print(f"[INFO] عدد الشرائح: {len(prs.slides)}")

        translated_count = 0
        failed_count = 0

        # ===== المرور على كل شريحة =====
        for slide_idx, slide in enumerate(prs.slides):
            print(f"[SLIDE] معالجة الشريحة {slide_idx + 1}")

            # نجمع كل مربعات النص في الشريحة
            shapes_to_process = []
            for shape in slide.shapes:
                if shape.has_text_frame and shape.text.strip():
                    shapes_to_process.append(shape)

            # ===== معالجة كل مربع نص =====
            for shape in shapes_to_process:
                text_frame = shape.text_frame

                # نجمع النصوص والفقرات
                original_paragraphs = []  # [(text, color, size, paragraph)]
                for paragraph in text_frame.paragraphs:
                    full_text = ""
                    color = RGBColor(0, 0, 0)
                    size = 12

                    for run in paragraph.runs:
                        if run.text:
                            full_text += run.text
                            color = get_run_color(run)
                            size = get_run_size(run)

                    full_text = full_text.strip()
                    if len(full_text) > 2:
                        original_paragraphs.append({
                            "text": full_text,
                            "color": color,
                            "size": size,
                            "paragraph": paragraph
                        })

                # ===== نضيف الترجمة بعد كل فقرة =====
                for p_data in original_paragraphs:
                    translated = translate_text(p_data["text"])

                    if translated:
                        translated_count += 1
                        try:
                            # نضيف فقرة جديدة في نفس text_frame
                            new_para = text_frame.add_paragraph()
                            new_run = new_para.add_run()
                            new_run.text = translated  # ✅ بدون arabic_reshaper!

                            # حجم خط الترجمة (أصغر قليلاً)
                            try:
                                new_size = max(9, int(p_data["size"]) - 1)
                                new_run.font.size = Pt(new_size)
                            except:
                                new_run.font.size = Pt(11)

                            # نفس لون النص الأصلي
                            new_run.font.color.rgb = p_data["color"]

                            # ضبط اتجاه النص للعربية (RTL)
                            try:
                                from pptx.oxml.ns import qn
                                pPr = new_para._p.get_or_add_pPr()
                                pPr.set('rtl', '1')
                            except Exception as e:
                                print(f"[RTL ERROR] {e}")

                            print(f"[TRANSLATED] {p_data['text'][:40]} → {translated[:40]}")
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
            caption=f"✅ تمت ترجمة {translated_count} نص!"
        )

    except Exception as e:
        print(f"[MAIN ERROR] {e}")
        bot.reply_to(message, f"❌ حدث خطأ: {str(e)}")


print("🤖 بوت الباتروس يعمل الآن...")
bot.infinity_polling()
