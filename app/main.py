import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from .config import BOT_TOKEN
from .handlers.admin import router as admin_router
from .api.main import run_api
import threading
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

async def run_bot():
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(admin_router)
    logger.info("Бот запущен...")
    await dp.start_polling(bot)

def run_fastapi():
    logger.info("FastAPI запущен на http://localhost:8000")
    run_api()

async def main():
    api_thread = threading.Thread(target=run_fastapi, daemon=True)
    api_thread.start()
    await run_bot()

if __name__ == "__main__":
    asyncio.run(main())