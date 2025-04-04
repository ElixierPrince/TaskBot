import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import schedule
import time
import threading
import json
from datetime import datetime, timedelta
import re

TOKEN = "7218081465:AAGvdi_ySNwfvfynVl7uOHe-8BxI8nQqZNQ"
USER_ID = 1268533347

logging.basicConfig(level=logging.INFO)

loop = asyncio.new_event_loop()
app = None

# === Start Command ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("היי! אני מוכן לעזור לך עם המשימות שלך 💪")

# === Handle Messages ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text.strip()
    print("📩 קיבלתי הודעה:", message)
    user_id = update.message.chat_id
    now = datetime.now()
    current_hour = now.hour
    today = now.strftime('%Y-%m-%d')

    # === בדיקת משימה לתאריך מסוים ===
    date_match = re.search(r"(?:ב־|ל־|ב|ל)?(\d{1,2})[./](\d{1,2})", message)
    if date_match and not any(word in message for word in ["סיימתי", "תעביר", "בוצע", "עשיתי", "לא הספקתי", "מה"]):
        day, month = map(int, date_match.groups())
        year = datetime.now().year
        try:
            task_date = datetime(year, month, day).strftime('%Y-%m-%d')
        except ValueError:
            await update.message.reply_text("📅 נראה שהתאריך לא תקין. נסה שוב.")
            return

        task_text = re.sub(r"(?:ב־|ל־|ב|ל)?\d{1,2}[./]\d{1,2}", "", message).strip()
        if not task_text:
            await update.message.reply_text("❗ לא מצאתי תוכן למשימה. נסה לנסח מחדש.")
            return

        try:
            with open("tasks.json", "r", encoding="utf-8") as f:
                task_data = json.load(f)
        except FileNotFoundError:
            task_data = {}

        if task_date in task_data:
            task_data[task_date].append(task_text)
        else:
            task_data[task_date] = [task_text]

        with open("tasks.json", "w", encoding="utf-8") as f:
            json.dump(task_data, f, ensure_ascii=False, indent=2)

        await update.message.reply_text(f"📅 שמרתי את המשימה לתאריך {day}.{month}: \"{task_text}\" ✅")
        return

    # === שאר הטיפול הרגיל (למשימות היום, סטטוסים, ניתוחים וכו') ===
    # כאן תוכל להוסיף את הקוד הרגיל שלך, כולל שמירת משימות לערב, בדיקת סטטוס, וכו'.

# === Ask for Tomorrow's Tasks ===
async def ask_tomorrow_tasks():
    print("⌛ שליחת הודעת מחר בפעולה...")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    try:
        with open("tasks.json", "r", encoding="utf-8") as f:
            task_data = json.load(f)
    except FileNotFoundError:
        task_data = {}

    if task_data.get(tomorrow):
        print("ℹ️ כבר קיימות משימות למחר – לא נשלח שוב.")
        return

    try:
        await app.bot.send_message(chat_id=USER_ID, text="📅 מה אתה רוצה להספיק מחר?")
        print("✅ הודעת מחר נשלחה.")
    except Exception as e:
        print(f"❌ שגיאה בשליחת הודעת מחר: {e}")

# === Scheduler Setup ===
def schedule_check():
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(1)

    schedule.every().day.at("09:00").do(lambda: asyncio.run_coroutine_threadsafe(send_morning_tasks(), loop))
    schedule.every().day.at("13:30").do(lambda: asyncio.run_coroutine_threadsafe(progress_check(), loop))
    schedule.every().day.at("16:30").do(lambda: asyncio.run_coroutine_threadsafe(progress_check(), loop))
    schedule.every().day.at("21:45").do(lambda: asyncio.run_coroutine_threadsafe(ask_tomorrow_tasks(), loop))

    threading.Thread(target=run_scheduler, daemon=True).start()

# === Main Function ===
def main():
    global app, loop
    asyncio.set_event_loop(loop)
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    schedule_check()

    app.run_polling()

if __name__ == '__main__':
    main()
