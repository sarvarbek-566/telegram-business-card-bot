from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from app.keyboards import build_post_kb
from app.db import DB

router = Router()

@router.message(F.text == "/start")
async def start(m: Message, db: DB):
    await db.add_user(
        user_id=m.from_user.id,
        username=m.from_user.username,
        first_name=m.from_user.first_name,
        last_name=m.from_user.last_name
    )
    
    s = await db.get_settings()
    kb = build_post_kb(s["buttons"])

    text = (s["text"] or "").strip()
    entities = s["entities"]
    photo = s["photo"]

    if photo:
        await m.answer_photo(
            photo=photo,
            caption=text if text else None,
            caption_entities=entities if text else None,
            reply_markup=kb
        )
        return

    if text:
        await m.answer(text=text, entities=entities, reply_markup=kb)
        return

    await m.answer("Пост ещё не настроен. Обратитесь к администратору.")

@router.callback_query(F.data.startswith("copy:"))
async def copy_fallback(c: CallbackQuery, db: DB):
    s = await db.get_settings()
    bid = c.data.split(":", 1)[1]
    value = None
    for item in s["buttons"]:
        if (item.get("id") or "") == bid and (item.get("type") or "") == "copy":
            value = item.get("value")
            break
    await c.answer()
    if value:
        await c.message.answer(value)