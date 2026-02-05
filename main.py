import telebot
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from flask import Flask
from threading import Thread
import os
import json

# ================== SECRETS ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_CREDS = os.getenv("GOOGLE_CREDS")

if BOT_TOKEN is None:
    raise ValueError("❌ BOT_TOKEN не найден в Secrets")

if GOOGLE_CREDS is None:
    raise ValueError("❌ GOOGLE_CREDS не найден в Secrets")

ADMIN_ID = 7323147567  # твой Telegram ID
SPREADSHEET_NAME = "Заявка"
WORKSHEET_INDEX = 0
# ============================================

# ================== GOOGLE SHEETS ==================
creds_dict = json.loads(GOOGLE_CREDS)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
gc = gspread.authorize(creds)
worksheet = gc.open(SPREADSHEET_NAME).get_worksheet(WORKSHEET_INDEX)

print("✅ Google Sheets подключены")
# ==================================================

# ================== TELEGRAM BOT ==================
bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}

def safe_send(chat_id, text):
    try:
        bot.send_message(chat_id, text)
    except Exception as e:
        print(f"❌ Ошибка отправки сообщения: {e}")
# ==================================================

# ================== KEEP ALIVE ==================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive!"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    Thread(target=run).start()
# ================================================

# ================== BOT LOGIC ==================
@bot.message_handler(commands=["start"])
def start(message):
    chat_id = message.chat.id
    user_data[chat_id] = {"step": "fio"}
    safe_send(chat_id, "Привет! Напиши своё ФИО:")

@bot.message_handler(func=lambda m: True)
def form(message):
    chat_id = message.chat.id
    text = message.text

    if chat_id not in user_data:
        safe_send(chat_id, "Напиши /start для начала")
        return

    step = user_data[chat_id]["step"]

    if step == "fio":
        user_data[chat_id]["fio"] = text
        user_data[chat_id]["step"] = "phone"
        safe_send(chat_id, "Введите телефон:")

    elif step == "phone":
        user_data[chat_id]["phone"] = text
        user_data[chat_id]["step"] = "request"
        safe_send(chat_id, "Опишите заявку:")

    elif step == "request":
        user_data[chat_id]["request"] = text

        now = datetime.now()
        row = [
            now.strftime("%Y-%m-%d"),
            now.strftime("%H:%M:%S"),
            user_data[chat_id]["fio"],
            user_data[chat_id]["phone"],
            user_data[chat_id]["request"]
        ]

        try:
            worksheet.append_row(row)
            print("✅ Заявка записана")
        except Exception as e:
            print(f"❌ Ошибка записи в таблицу: {e}")

        safe_send(
            ADMIN_ID,
            f"📩 Новая заявка:\n"
            f"Дата: {row[0]}\n"
            f"Время: {row[1]}\n"
            f"ФИО: {row[2]}\n"
            f"Телефон: {row[3]}\n"
            f"Заявка: {row[4]}"
        )

        safe_send(chat_id, "✅ Ваша заявка отправлена!")
        user_data.pop(chat_id)
# ===============================================

# ================== START ==================
if __name__ == "__main__":
    keep_alive()
    print("🤖 Бот запущен")
    bot.polling(skip_pending=True)
# ==========================================
