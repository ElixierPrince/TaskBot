import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import schedule
import time
import threading
import json
from datetime import datetime, timedelta

TOKEN = "7218081465:AAGvdi_ySNwfvfynVl7uOHe-8BxI8nQqZNQ"
USER_ID = 1268533347

logging.basicConfig(level=logging.INFO)

loop = asyncio.new_event_loop()
app = None


# === Start Command ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("היי! אני מוכן לעזור לך עם המשימות שלך 💪")


# === Handle Messages ===
# === Handle Messages ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import re

    message = update.message.text.strip()
    print("📩 קיבלתי הודעה:", message)
    user_id = update.message.chat_id
    now = datetime.now()
    current_hour = now.hour
    today = now.strftime('%Y-%m-%d')

    # ======= שלב משימות חדשות (אם יש פסיקים וזה בערב) ========
    if 20 <= current_hour <= 23 and "," in message and not any(word in message for word in ["סיימתי", "תעביר", "בוצע", "עשיתי", "לא הספקתי"]):
        tomorrow = (now + timedelta(days=1)).strftime('%Y-%m-%d')
        tasks = [task.strip() for task in message.split(",")]

        try:
            with open("tasks.json", "r", encoding="utf-8") as f:
                task_data = json.load(f)
        except FileNotFoundError:
            task_data = {}

        task_data[tomorrow] = tasks

        with open("tasks.json", "w", encoding="utf-8") as f:
            json.dump(task_data, f, ensure_ascii=False, indent=2)

        await update.message.reply_text("✅ שמרתי את המשימות שלך למחר!")
        return

    # טוען את המשימות הקיימות
    try:
        with open("tasks.json", "r", encoding="utf-8") as f:
            task_data = json.load(f)
    except FileNotFoundError:
        task_data = {}

    tasks_today = task_data.get(today, [])
    print("📋 משימות להיום:", tasks_today)

    # טוען סטטוס נוכחי
    try:
        with open("status.json", "r", encoding="utf-8") as f:
            status_data = json.load(f)
    except FileNotFoundError:
        status_data = {}

    if today not in status_data:
        status_data[today] = {task: "פתוח" for task in tasks_today}

    # === בדיקת בקשת סיכום סטטוס משימות ===
    summary_keywords = ["מה נשאר", "סטטוס", "מה עם", "מה יש לי", "מה הספקתי", "מה לא עשיתי"]

    if any(kw in message for kw in summary_keywords):
        done = []
        postponed = []
        open_tasks = []

        for task, status in status_data.get(today, {}).items():
            if status == "בוצע":
                done.append(task)
            elif status == "נדחה":
                postponed.append(task)
            else:
                open_tasks.append(task)

        text = f"📋 סטטוס המשימות שלך להיום:\n\n"

        if done:
            text += "✅ בוצע:\n" + "\n".join([f"- {t}" for t in done]) + "\n\n"
        if postponed:
            text += "⏭️ נדחה:\n" + "\n".join([f"- {t}" for t in postponed]) + "\n\n"
        if open_tasks:
            text += "🕓 פתוח:\n" + "\n".join([f"- {t}" for t in open_tasks]) + "\n"

        if not (done or postponed or open_tasks):
            text += "אין לך משימות פעילות להיום 🎉"

        await update.message.reply_text(text)
        return

    updated = False

    # ניתוח לפי קטעי משפט
    parts = re.split(r"[.,;|!?\n]| ו| אבל ", message)

    for part in parts:
        part = part.strip()
        for task in tasks_today:
            if task in part:
                if any(word in part for word in ["תעביר", "תדחה", "מחר", "לא הספקתי"]):
                    status_data[today][task] = "נדחה"
                    updated = True
                    print(f"↪️ '{task}' סומן כ־נדחה")
                elif any(word in part for word in ["סיימתי", "עשיתי", "בוצע"]):
                    status_data[today][task] = "בוצע"
                    updated = True
                    print(f"✅ '{task}' סומן כ־בוצע")

    if updated:
        with open("status.json", "w", encoding="utf-8") as f:
            json.dump(status_data, f, ensure_ascii=False, indent=2)
        await update.message.reply_text("📌 עדכנתי את סטטוס המשימות שלך.")
    else:
        await update.message.reply_text(f"קיבלתי: {message} (עוד מעט נתחיל לעקוב אחרי זה 😉)")


# === Ask for Tomorrow's Tasks ===
async def ask_tomorrow_tasks():
    print("⌛ שליחת הודעת מחר בפעולה...")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    try:
        await app.bot.send_message(chat_id=USER_ID, text="📅 מה אתה רוצה להספיק מחר?")
        print("✅ הודעת מחר נשלחה.")
    except Exception as e:
        print(f"❌ שגיאה בשליחת הודעת מחר: {e}")


# === Send Morning Tasks ===
async def send_morning_tasks():
    print("☀️ שליחת משימות הבוקר בפעולה...")
    today = datetime.now().strftime('%Y-%m-%d')
    try:
        with open("status.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}

    tasks = data.get(today, [])

    if tasks:
        task_list = "\n".join([f"- {task}" for task in tasks])
        text = f"בוקר טוב! הנה המשימות שלך להיום:\n{task_list}"
    else:
        text = "בוקר טוב! לא הגדרת משימות להיום. רוצה להוסיף משהו?"

    try:
        await app.bot.send_message(chat_id=USER_ID, text=text)
        print("✅ הודעת בוקר נשלחה.")
    except Exception as e:
        print(f"❌ שגיאה בשליחת הודעת הבוקר: {e}")


# === Progress Check ===
async def progress_check():
    print("🔄 שליחת תזכורת התקדמות...")
    today = datetime.now().strftime('%Y-%m-%d')
    try:
        with open("status.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}

    tasks = data.get(today, [])

    if tasks:
        text = "📌 רק מזכיר – יש לך עדיין משימות פתוחות. רוצה לעדכן משהו?"
    else:
        text = "📌 אין משימות פתוחות להיום. כל הכבוד לך, סיימת הכול!"

    try:
        await app.bot.send_message(chat_id=USER_ID, text=text)
        print("✅ תזכורת התקדמות נשלחה.")
    except Exception as e:
        print(f"❌ שגיאה בשליחת תזכורת התקדמות: {e}")


# === Scheduler Setup ===
def schedule_check():
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(1)

    # תזמונים אמיתיים
    schedule.every().day.at("09:00").do(lambda: asyncio.run_coroutine_threadsafe(send_morning_tasks(), loop))
    schedule.every().day.at("13:30").do(lambda: asyncio.run_coroutine_threadsafe(progress_check(), loop))
    schedule.every().day.at("16:30").do(lambda: asyncio.run_coroutine_threadsafe(progress_check(), loop))
    schedule.every().day.at("21:45").do(lambda: asyncio.run_coroutine_threadsafe(ask_tomorrow_tasks(), loop))

    # לצורך בדיקות מהירות (אפשר למחוק כשעוברים לייצור)
    schedule.every(1).minutes.do(lambda: asyncio.run_coroutine_threadsafe(send_morning_tasks(), loop))
    schedule.every(2).minutes.do(lambda: asyncio.run_coroutine_threadsafe(ask_tomorrow_tasks(), loop))
    schedule.every(3).minutes.do(lambda: asyncio.run_coroutine_threadsafe(progress_check(), loop))

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
