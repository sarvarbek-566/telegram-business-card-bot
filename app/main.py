import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from app.config import TOKEN, DB_PATH, ADMIN_PASSWORD
from app.db import DB
from app.routers import routers

async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    db = DB(DB_PATH)
    await db.init(ADMIN_PASSWORD)

    dp["db"] = db

    for r in routers:
        dp.include_router(r)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())