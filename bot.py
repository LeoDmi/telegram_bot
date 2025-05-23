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

openai.api_key = OPENAI_API_KEY

# 🤖 Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# 💬 Обработка команды /analyze
@dp.message(F.text.startswith("/analyze"))
async def handle_analyze(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("⛔ Только руководитель может запускать анализ.")
        return
    await message.reply("📊 Анализ будет доступен в webhook-версии позже")

# 🚀 Установка webhook через aiohttp.on_startup
async def aiohttp_on_startup(app: web.Application):
    await bot.set_webhook(WEBHOOK_URL)
    print("🚀 Webhook установлен")

# 🛑 Удаление webhook через aiohttp.on_cleanup
async def aiohttp_on_cleanup(app: web.Application):
    await bot.delete_webhook()
    print("🛑 Webhook удалён")

# 🌐 Основной запуск aiohttp
async def main():
    app = web.Application()

    # Добавляем aiohttp-события
    app.on_startup.append(aiohttp_on_startup)
    app.on_cleanup.append(aiohttp_on_cleanup)

    # Интеграция webhook
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    setup_application(app, dp)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=8080)
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
