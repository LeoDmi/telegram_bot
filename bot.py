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

# ✅ Загружаем переменные окружения
API_TOKEN = os.getenv("API_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0").strip().lstrip("="))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()

# ✅ Настраиваем OpenAI
openai.api_key = OPENAI_API_KEY

# ✅ Настраиваем бота
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# ✅ Обработчик команды /analyze
@dp.message(F.text.startswith("/analyze"))
async def handle_analyze(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("⛔ Только руководитель может запускать анализ.")
        return
    await message.reply("📊 Анализ будет доступен в webhook-версии позже")

# ✅ Действия при запуске
async def on_startup(dispatcher: Dispatcher, bot: Bot):
    await bot.set_webhook(WEBHOOK_URL)
    print("🚀 Webhook установлен")

# ✅ Действия при завершении
async def on_shutdown(dispatcher: Dispatcher, bot: Bot):
    await bot.delete_webhook()
    print("🛑 Webhook удалён")

# ✅ Основная функция с aiohttp и webhook
async def main():
    app = web.Application()
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # 🔁 Webhook-интеграция aiogram + aiohttp
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    setup_application(app, dp)

    # 🟢 Запуск aiohttp-сервера
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("🌐 Webhook сервер запущен")

    while True:
        await asyncio.sleep(3600)

# ✅ Запуск
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен.")
