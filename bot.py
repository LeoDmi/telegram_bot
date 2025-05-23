import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
import aiosqlite
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import openai
import os

API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

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
            (message.chat.id, chat_title, message.from_user.id, display_name, message.text, datetime.utcnow())
        )
        await db.commit()

async def analyze_messages_with_gpt(user_messages):
    prompt = "Классифицируй каждое сообщение по тону: вежливое, нейтральное или грубое. Верни JSON вида: [{\"текст\": \"...\", \"тон\": \"вежливое\"}, ...]"
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
    start_time = datetime.utcnow() - timedelta(hours=24)
    async with aiosqlite.connect(db_file) as db:
        response_times = {}
        async with db.execute('SELECT chat_id, user_id, user_name, timestamp FROM messages WHERE timestamp > ? ORDER BY chat_id, timestamp', (start_time,)) as cursor:
            last_msg_by, last_msg_time = {}, {}
            for row in await cursor.fetchall():
                chat_id, user_id, user_name, timestamp = row
                timestamp = datetime.fromisoformat(timestamp)
                if chat_id not in last_msg_by:
                    last_msg_by[chat_id] = user_id
                    last_msg_time[chat_id] = timestamp
                    continue
                if last_msg_by[chat_id] != user_id:
                    if user_id not in response_times:
                        response_times[user_id] = []
                    delay = (timestamp - last_msg_time[chat_id]).total_seconds()
                    if 0 < delay < 21600:
                        response_times[user_id].append(delay)
                last_msg_by[chat_id] = user_id
                last_msg_time[chat_id] = timestamp

        hanging_chats = set()
        six_hours_ago = datetime.utcnow() - timedelta(hours=6)
        async with db.execute('''SELECT chat_id, chat_title, user_id, user_name, MAX(timestamp) FROM messages
                                 WHERE timestamp > ? GROUP BY chat_id''', (start_time,)) as cursor:
            for row in await cursor.fetchall():
                chat_id, chat_title, user_id, user_name, last_ts = row
                last_ts = datetime.fromisoformat(last_ts)
                if last_ts < six_hours_ago:
                    hanging_chats.add((chat_title, user_name))

        async with db.execute('''SELECT chat_title, user_name, user_id, COUNT(*), MIN(timestamp), MAX(timestamp)
                                 FROM messages
                                 WHERE timestamp > ?
                                 GROUP BY chat_title, user_name, user_id
                                 ORDER BY chat_title''', (start_time,)) as cursor:
            report_lines = ['📊 <b>Отчёт за последние 24 часа</b>']
            current_chat = None
            async for chat_title, user_name, user_id, count, first, last in cursor:
                duration = datetime.fromisoformat(last) - datetime.fromisoformat(first)
                avg_resp = response_times.get(user_id)
                avg_resp_str = ""
                if avg_resp:
                    avg_sec = sum(avg_resp) / len(avg_resp)
                    minutes = int(avg_sec // 60)
                    seconds = int(avg_sec % 60)
                    avg_resp_str = f" (ср. ответ: {minutes} мин {seconds} сек)"
                async with db.execute('SELECT message FROM messages WHERE user_id = ? AND timestamp > ?', (user_id, start_time)) as msg_cursor:
                    user_messages = [row[0] async for row in msg_cursor if row[0].strip() and len(row[0]) < 300]
                tone_str = ""
                if user_messages:
                    gpt_result = await analyze_messages_with_gpt(user_messages[:20])
                    if gpt_result:
                        polite, neutral, rude = gpt_result
                        tone_str = f"\nGPT-анализ: вежл — {polite}, нейтр — {neutral}, груб — {rude}"
                if current_chat != chat_title:
                    report_lines.append(f'\n<b>💬 Чат: {chat_title}</b>')
                    current_chat = chat_title
                report_lines.append(f'👤 <b>{user_name}</b> — сообщений: {count}, период: {duration}{avg_resp_str}{tone_str}')

        if hanging_chats:
            report_lines.append('\n🔕 <b>Чаты без ответа более 6 часов:</b>')
            for chat_title, user_name in hanging_chats:
                report_lines.append(f'– {chat_title} (посл. сообщение от {user_name})')
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
        print('Бот остановлен.')[содержимое последней версии кода из Canvas будет вставлено здесь вручную]
