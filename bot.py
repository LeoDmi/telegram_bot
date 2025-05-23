import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
import aiosqlite
from datetime import datetime, timedelta, UTC
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import openai
import os

print("🚀 Бот стартует...")

API_TOKEN = os.getenv("API_TOKEN", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
openai.api_key = OPENAI_API_KEY

try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0").strip().lstrip("="))
except ValueError:
    print("❌ ADMIN_ID задан некорректно. Установлен в 0.")
    ADMIN_ID = 0

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
db_file = 'messages.db'

async def setup_database():
    async with aiosqlite.connect(db_file) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            chat_title TEXT,
            user_id INTEGER,
            user_name TEXT,
            message TEXT,
            timestamp DATETIME
        )
        """)
        await db.commit()

@dp.message(F.text)
async def log_message(message: Message):
    full_name = message.from_user.full_name
    username = message.from_user.username
    display_name = f"{full_name} (@{username})" if username else full_name
    chat_title = message.chat.title if message.chat.title else f"Private chat {message.chat.id}"
    async with aiosqlite.connect(db_file) as db:
        await db.execute(
            'INSERT INTO messages (chat_id, chat_title, user_id, user_name, message, timestamp) VALUES (?, ?, ?, ?, ?, ?)',
            (message.chat.id, chat_title, message.from_user.id, display_name, message.text, datetime.now(UTC))
        )
        await db.commit()

async def analyze_messages_with_gpt(user_messages):
    prompt = "Классифицируй каждое сообщение по тону: вежливое, нейтральное или грубое."
    joined = "\n".join(user_messages)
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": joined}
            ],
            temperature=0.2
        )
        text = response.choices[0].message.content
        polite = text.lower().count("вежливое")
        neutral = text.lower().count("нейтральное")
        rude = text.lower().count("грубое")
        return polite, neutral, rude
    except Exception:
        return None

@dp.message(F.text.startswith("/analyze"))
async def handle_manual_analysis(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("⛔ Только руководитель может запускать анализ.")
        return
    await message.reply("⏳ Формирую отчёт...")
    report = await build_report()
    await message.reply(report)

async def send_daily_report():
    report = await build_report()
    await bot.send_message(chat_id=ADMIN_ID, text=report)

async def build_report():
    start_time = datetime.now(UTC) - timedelta(hours=24)
    async with aiosqlite.connect(db_file) as db:
        async with db.execute('''SELECT chat_title, user_name, COUNT(*), MIN(timestamp), MAX(timestamp)
                                 FROM messages
                                 WHERE timestamp > ?
                                 GROUP BY chat_title, user_name
                                 ORDER BY chat_title''', (start_time,)) as cursor:
            report_lines = ['📊 <b>Отчёт за последние 24 часа</b>']
            async for row in cursor:
                chat_title, user_name, count, first, last = row
                duration = datetime.fromisoformat(last) - datetime.fromisoformat(first)
                report_lines.append(f'👤 <b>{user_name}</b> в чате <b>{chat_title}</b> — сообщений: {count}, период: {duration}')
    return '\n'.join(report_lines)

scheduler = AsyncIOScheduler()
scheduler.add_job(send_daily_report, CronTrigger(hour=15, minute=0))

async def main():
    await setup_database()
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print('Бот остановлен.')
