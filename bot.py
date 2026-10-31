import os
import telebot
from deep_translator import GoogleTranslator
import PyPDF2
import io

TOKEN = '8951863527:AAHCDAjJOCnhphMu9dpMxMbiuCfA3SMkOF0'
bot = telebot.TeleBot(TOKEN)

translator = GoogleTranslator(source='en', target='ar')

@bot.message_handler(commands=['start'])
def send_welcome(bot_message):
    bot.reply_to(
        bot_message,
        "مرحباً بك يا حيدر! بوت ترجمة ملفات الـ PDF جاهز الآن لترجمة محاضراتك سطراً بسطر وبشكل مرتب."
    )

@bot.message_handler(content_types=['document'])
def handle_pdf_document(message):
    try:
        file_name = message.document.file_name.lower()
        if not file_name.endswith('.pdf'):
            bot.reply_to(message, "عذراً، يرجى إرسال ملف بصيغة PDF فقط.")
            return

        bot.reply_to(message, "جاري قراءة ملف الـ PDF وترجمته سطراً بسطر، يرجى الانتظار...")

        file_info = bot.get_file(message.document.file_info_id)
        downloaded_file = bot.download_file(file_info.file_path)

        pdf_file = io.BytesIO(downloaded_file)
        reader = PyPDF2.PdfReader(pdf_file)

        extracted_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_text += text + "\n"

        if not extracted_text.strip():
            bot.reply_to(message, "لم يتم العثور على نص داخل الملف (قد يكون مكوناً من صور مسحوبة).")
            return

        lines = extracted_text.split('\n')
        translated_lines = []

        for line in lines:
            if line.strip() == "":
                translated_lines.append("")
                continue
            try:
                res = translator.translate(line)
                translated_lines.append(f"EN: {line}")
                translated_lines.append(f"AR: {res}")
                translated_lines.append("-" * 15)
            except Exception:
                translated_lines.append(line)

        final_response = "\n".join(translated_lines)

        if len(final_response) > 4000:
            final_response = final_response[:4000] + "\n\n(تم اقتطاع جزء لأن الملف طويل جداً)"

        bot.reply_to(message, final_response)

    except Exception as e:
        bot.reply_to(message, f"حدث خطأ أثناء معالجة الملف: {str(e)}")

@bot.message_handler(func=lambda message: True)
def translate_text(message):
    text = message.text
    if not text:
        return
    try:
        res = translator.translate(text)
        bot.reply_to(message, f"EN: {text}\nAR: {res}")
    except Exception:
        bot.reply_to(message, text)

if __name__ == '__main__':
    print("Bot is running with PDF and Line-by-Line support...")
    bot.infinity_polling()