import asyncio
import os
import openai
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# 🔐 Переменные окружения
API_TOKEN = os.getenv("API_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0").strip().lstrip("="))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()

# 🔧 Настройка OpenAI
openai.api_key = OPENAI_API_KEY

# 🤖 Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# 🧠 Обработчик команды /analyze
@dp.message(F.text.startswith("/analyze"))
async def handle_analyze(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("⛔ Только руководитель может запускать анализ.")
        return
    await message.reply("📊 Анализ будет доступен в webhook-версии позже")

# 🚀 Webhook при запуске
async def on_startup(*, bot: Bot, **kwargs):
    await bot.set_webhook(WEBHOOK_URL)
    print("🚀 Webhook установлен")

# 🛑 Webhook при остановке
async def on_shutdown(*, bot: Bot, **kwargs):
    await bot.delete_webhook()
    print("🛑 Webhook удалён")

# 🌐 Основной запуск aiohttp
async def main():
    app = web.Application()

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Webhook обработчик
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    setup_application(app, dp)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("🌐 Webhook сервер запущен")

    while True:
        await asyncio.sleep(3600)

# ▶️ Запуск
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен.")
