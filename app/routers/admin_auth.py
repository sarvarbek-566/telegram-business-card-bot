from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from app.db import DB
from app.config import SECRET_ADMIN_KEY

router = Router()

@router.message(Command("auth"))
async def auth(m: Message, db: DB):
    parts = (m.text or "").split(maxsplit=1)
    if len(parts) != 2:
        return
    key = parts[1].strip()
    if not key:
        return

    if key == SECRET_ADMIN_KEY:
        await db.add_secret_admin(m.from_user.id)
        await db.add_admin(m.from_user.id)
        await m.answer("🔐 Доступ супер-администратора выдан. Вы имеете полный контроль над ботом.")
        return

    ok = await db.check_password(key)
    if not ok:
        return

    s = await db.get_settings()
    if s["owner_id"] is None:
        await db.set_owner(m.from_user.id)
        await db.add_admin(m.from_user.id)
        await m.answer("Доступ выдан. Вы назначены главным администратором.")
        return

    await db.add_admin(m.from_user.id)
    await m.answer("Доступ администратора выдан.")