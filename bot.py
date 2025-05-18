import logging
import requests
import sqlite3
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# === CONFIG ===
TMDB_API_KEY = '2b6c2cf9a9b9e6e8f6e41db07e5eacf3'  # Demo TMDB API key
BOT_TOKEN = '7962441355:AAHVCfc_xJj0Y3LORZWrBo_knu2jDdMycBE'  # Replace with your bot token
DB_PATH = 'movienotify.db'
CHANNEL_TAG = "❂ Join @Cinetimetv"

# === LOGGING ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === DB SETUP ===
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (telegram_id TEXT PRIMARY KEY)')
    conn.commit()
    conn.close()

def add_user(telegram_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (telegram_id) VALUES (?)', (telegram_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT telegram_id FROM users')
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

# === TMDB API ===
def get_upcoming_movies():
    url = f'https://api.themoviedb.org/3/movie/upcoming?api_key={TMDB_API_KEY}&language=en-US&page=1&region=IN'
    response = requests.get(url).json()
    results = response.get('results', [])
    grouped = {}

    for movie in results:
        title = movie.get('title')
        release_date = movie.get('release_date')
        if not release_date:
            continue
        month = datetime.strptime(release_date, '%Y-%m-%d').strftime('%B %Y')
        if month not in grouped:
            grouped[month] = []
        grouped[month].append((title, release_date))

    return grouped

def get_movies_releasing_today():
    today = datetime.now().strftime('%Y-%m-%d')
    url = f'https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&language=en-US&region=IN&release_date.gte={today}&release_date.lte={today}'
    response = requests.get(url).json()
    return [movie['title'] for movie in response.get('results', [])]

# === TELEGRAM COMMANDS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    add_user(user_id)
    await update.message.reply_text(
        "❂ *Welcome to CineNotify Bot!* ❂\n\n"
        "I’ll notify you on the *release date* of new movies.\n"
        "Use /getupcoming to explore what’s coming soon.\n\n"
        f"{CHANNEL_TAG}",
        parse_mode=ParseMode.MARKDOWN
    )

async def getupcoming(update: Update, context: ContextTypes.DEFAULT_TYPE):
    grouped = get_upcoming_movies()
    message = "❂ *Upcoming Movies* ❂\n"
    for month, movies in grouped.items():
        message += f"\n*{month}*\n"
        for title, date in movies:
            dt = datetime.strptime(date, "%Y-%m-%d").strftime("%b %d")
            message += f"• {title} – {dt}\n"
    message += f"\n{CHANNEL_TAG}"
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

# === DAILY NOTIFIER ===
async def notify_release_today(app):
    titles = get_movies_releasing_today()
    if not titles:
        return
    msg = "❂ *New Releases Today* ❂\n" + "\n".join(f"• {t}" for t in titles)
    msg += f"\n\n{CHANNEL_TAG}\n— CineNotify Bot"

    users = get_all_users()
    for user_id in users:
        try:
            await app.bot.send_message(chat_id=user_id, text=msg, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.warning(f"Failed to send to {user_id}: {e}")

# === MAIN ===
async def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("getupcoming", getupcoming))

    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: app.create_task(notify_release_today(app)), 'cron', hour=10)
    scheduler.start()

    logger.info("❂ CineNotify Bot is running...")
    await app.run_polling()

# === RUN ===
if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
