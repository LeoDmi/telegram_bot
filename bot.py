import asyncio
import os
import openai
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

# 🔐 Переменные окружения
API_TOKEN = os.getenv("API_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0").strip().lstrip("="))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

openai.api_key = OPENAI_API_KEY

# 🤖 Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# 💬 Команда /analyze
@dp.message(F.text.startswith("/analyze"))
async def handle_analyze(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("⛔ Только руководитель может запускать анализ.")
        return
    await message.reply("📊 Анализ будет доступен в следующей версии polling-бота")

# ▶️ Запуск через polling
async def main():
    print("🤖 Бот стартовал через polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен.")
