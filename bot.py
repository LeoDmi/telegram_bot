import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

# 🔐 Переменные окружения
API_TOKEN = os.getenv("API_TOKEN", "").strip()
ADMIN_ID = os.getenv("ADMIN_ID", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# 🛡 Проверка
if not API_TOKEN or not ADMIN_ID:
    raise ValueError("❌ Не заданы переменные API_TOKEN или ADMIN_ID")

ADMIN_ID = int(ADMIN_ID.lstrip("="))

# 🤖 Инициализация бота
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# 💬 Обработка команды /analyze
@dp.message(F.text.startswith("/analyze"))
async def handle_analyze(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("⛔ Только руководитель может запускать анализ.")
        return
    await message.reply("📊 Анализ включится позже — бот работает через polling.")

# ▶️ Запуск polling
async def main():
    print("⚡ Running polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
