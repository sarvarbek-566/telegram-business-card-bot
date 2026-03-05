import uuid
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from app.db import DB
from app.states import AdminState
from app.keyboards import admin_menu, buttons_menu, admins_menu, build_post_kb, cancel_keyboard

router = Router()

async def is_admin(uid: int, db: DB) -> bool:
    return await db.is_admin(uid)

async def is_owner(uid: int, db: DB) -> bool:
    s = await db.get_settings()
    return s["owner_id"] == uid

async def is_secret_admin(uid: int, db: DB) -> bool:
    return await db.is_secret_admin(uid)

async def is_super_user(uid: int, db: DB) -> bool:
    return await is_owner(uid, db) or await is_secret_admin(uid, db)

@router.message(Command("ap"))
async def ap(m: Message, db: DB):
    if not await is_admin(m.from_user.id, db):
        return
    super_user = await is_super_user(m.from_user.id, db)
    await m.answer("Панель администратора", reply_markup=admin_menu(super_user))

@router.callback_query(F.data == "ap:back")
async def back(c: CallbackQuery, db: DB):
    if not await is_admin(c.from_user.id, db):
        await c.answer()
        return
    super_user = await is_super_user(c.from_user.id, db)
    await c.message.edit_text("Панель администратора", reply_markup=admin_menu(super_user))
    await c.answer()

@router.callback_query(F.data == "cancel")
async def cancel_action(c: CallbackQuery, state: FSMContext, db: DB):
    if not await is_admin(c.from_user.id, db):
        await c.answer()
        return
    current_state = await state.get_state()
    await state.clear()
    
    if current_state and "btn" in current_state:
        s = await db.get_settings()
        await c.message.edit_text(f"❌ Отменено.\n\nКнопки: {len(s['buttons'])}/5", reply_markup=buttons_menu())
    else:
        super_user = await is_super_user(c.from_user.id, db)
        await c.message.edit_text("❌ Отменено.\n\nПанель администратора", reply_markup=admin_menu(super_user))
    await c.answer()

@router.callback_query(F.data == "ap:preview")
async def preview(c: CallbackQuery, db: DB):
    if not await is_admin(c.from_user.id, db):
        await c.answer()
        return

    s = await db.get_settings()
    kb = build_post_kb(s["buttons"])

    text = (s["text"] or "").strip()
    entities = s["entities"]
    photo = s["photo"]

    if photo:
        await c.message.answer_photo(
            photo=photo,
            caption=text if text else None,
            caption_entities=entities if text else None,
            reply_markup=kb
        )
    elif text:
        await c.message.answer(text=text, entities=entities, reply_markup=kb)
    else:
        await c.message.answer("Пост ещё не настроен.")
    await c.answer()

@router.callback_query(F.data == "ap:text")
async def text_prompt(c: CallbackQuery, state: FSMContext, db: DB):
    if not await is_admin(c.from_user.id, db):
        await c.answer()
        return
    await state.set_state(AdminState.waiting_text)
    await c.message.edit_text("Отправьте новый текст поста. Эмодзи и форматирование будут сохранены.", reply_markup=cancel_keyboard())
    await c.answer()

@router.message(AdminState.waiting_text)
async def text_set(m: Message, state: FSMContext, db: DB):
    if not await is_admin(m.from_user.id, db):
        return
    text = m.text or ""
    entities = m.entities or []
    await db.set_post_text_and_entities(text=text, entities=entities)
    await state.clear()
    super_user = await is_super_user(m.from_user.id, db)
    await m.answer("Сохранено.", reply_markup=admin_menu(super_user))

@router.callback_query(F.data == "ap:photo")
async def photo_prompt(c: CallbackQuery, state: FSMContext, db: DB):
    if not await is_admin(c.from_user.id, db):
        await c.answer()
        return
    await state.set_state(AdminState.waiting_photo)
    await c.message.edit_text("Отправьте одно фото. Чтобы удалить фото, отправьте: skip", reply_markup=cancel_keyboard())
    await c.answer()

@router.message(AdminState.waiting_photo)
async def photo_set(m: Message, state: FSMContext, db: DB):
    if not await is_admin(m.from_user.id, db):
        return

    super_user = await is_super_user(m.from_user.id, db)

    if (m.text or "").strip().lower() == "skip":
        await db.set_photo(None)
        await state.clear()
        await m.answer("Фото удалено.", reply_markup=admin_menu(super_user))
        return

    if not m.photo:
        return

    await db.set_photo(m.photo[-1].file_id)
    await state.clear()
    await m.answer("Фото сохранено.", reply_markup=admin_menu(super_user))

@router.callback_query(F.data == "ap:buttons")
async def buttons_root(c: CallbackQuery, db: DB):
    if not await is_admin(c.from_user.id, db):
        await c.answer()
        return
    s = await db.get_settings()
    await c.message.edit_text(f"Кнопки: {len(s['buttons'])}/5", reply_markup=buttons_menu())
    await c.answer()

@router.callback_query(F.data == "btn:clear")
async def btn_clear(c: CallbackQuery, db: DB):
    if not await is_admin(c.from_user.id, db):
        await c.answer()
        return
    await db.set_buttons([])
    await c.message.edit_text("Кнопки очищены.", reply_markup=buttons_menu())
    await c.answer()

@router.callback_query(F.data == "btn:pop")
async def btn_pop(c: CallbackQuery, db: DB):
    if not await is_admin(c.from_user.id, db):
        await c.answer()
        return
    s = await db.get_settings()
    btns = s["buttons"]
    if btns:
        btns.pop()
        await db.set_buttons(btns)
    await c.message.edit_text(f"Кнопки: {len(btns)}/5", reply_markup=buttons_menu())
    await c.answer()

@router.callback_query(F.data == "btn:add")
async def btn_add(c: CallbackQuery, state: FSMContext, db: DB):
    if not await is_admin(c.from_user.id, db):
        await c.answer()
        return
    s = await db.get_settings()
    if len(s["buttons"]) >= 5:
        await c.answer("Достигнут лимит: 5 кнопок.", show_alert=True)
        return
    await state.set_state(AdminState.waiting_btn_text)
    await c.message.edit_text("Отправьте текст кнопки.", reply_markup=cancel_keyboard())
    await c.answer()

@router.message(AdminState.waiting_btn_text)
async def btn_text(m: Message, state: FSMContext, db: DB):
    if not await is_admin(m.from_user.id, db):
        return
    t = (m.text or "").strip()
    if not t:
        await m.answer("Текст кнопки не может быть пустым. Попробуйте снова.", reply_markup=cancel_keyboard())
        return
    if len(t) > 64:
        await m.answer("Текст кнопки слишком длинный (максимум 64 символа). Попробуйте снова.", reply_markup=cancel_keyboard())
        return
    await state.update_data(btn_text=t)
    await state.set_state(AdminState.waiting_btn_type)
    await m.answer("Отправьте тип кнопки: url или copy", reply_markup=cancel_keyboard())

@router.message(AdminState.waiting_btn_type)
async def btn_type(m: Message, state: FSMContext, db: DB):
    if not await is_admin(m.from_user.id, db):
        return
    typ = (m.text or "").strip().lower()
    if typ not in ("url", "copy"):
        await m.answer("Неверный тип. Отправьте: url или copy", reply_markup=cancel_keyboard())
        return
    await state.update_data(btn_type=typ)
    await state.set_state(AdminState.waiting_btn_value)
    if typ == "url":
        await m.answer("Отправьте ссылку (https://... или http://...)", reply_markup=cancel_keyboard())
    else:
        await m.answer("Отправьте текст для копирования.", reply_markup=cancel_keyboard())

@router.message(AdminState.waiting_btn_value)
async def btn_value(m: Message, state: FSMContext, db: DB):
    if not await is_admin(m.from_user.id, db):
        return
    val = (m.text or "").strip()
    if not val:
        await m.answer("Значение не может быть пустым. Попробуйте снова.", reply_markup=cancel_keyboard())
        return
    
    data = await state.get_data()
    btn_type = data.get("btn_type")
    
    if btn_type == "url":
        if not (val.startswith("http://") or val.startswith("https://")):
            await m.answer("❌ Ссылка должна начинаться с http:// или https://\n\nПопробуйте снова:", reply_markup=cancel_keyboard())
            return
        if len(val) > 2048:
            await m.answer("❌ Ссылка слишком длинная (максимум 2048 символов).\n\nПопробуйте снова:", reply_markup=cancel_keyboard())
            return
        if " " in val:
            await m.answer("❌ Ссылка не должна содержать пробелы.\n\nПопробуйте снова:", reply_markup=cancel_keyboard())
            return
    
    if btn_type == "copy" and len(val) > 4096:
        await m.answer("❌ Текст для копирования слишком длинный (максимум 4096 символов).\n\nПопробуйте снова:", reply_markup=cancel_keyboard())
        return
    
    s = await db.get_settings()
    btns = s["buttons"]

    btns.append({
        "id": uuid.uuid4().hex[:12],
        "text": data["btn_text"],
        "type": btn_type,
        "value": val
    })

    await db.set_buttons(btns)
    await state.clear()
    await m.answer(f"✅ Кнопка добавлена.\n\nКнопки: {len(btns)}/5", reply_markup=buttons_menu())

@router.callback_query(F.data == "ap:users")
async def users_list(c: CallbackQuery, db: DB):
    if not await is_admin(c.from_user.id, db):
        await c.answer()
        return
    
    if not await is_super_user(c.from_user.id, db):
        await c.answer("❌ Недостаточно прав. Только главный администратор может просматривать пользователей.", show_alert=True)
        return
    
    users = await db.list_users()
    
    if not users:
        await c.message.edit_text("Пользователей пока нет.", reply_markup=admins_menu(True))
        await c.answer()
        return
    
    lines = [f"👥 Пользователи ({len(users)}):"]
    lines.append("")
    
    for user in users[:50]:
        uid = user["user_id"]
        username = f"@{user['username']}" if user.get("username") else ""
        first_name = user.get("first_name") or ""
        last_name = user.get("last_name") or ""
        
        name_parts = []
        if first_name:
            name_parts.append(first_name)
        if last_name:
            name_parts.append(last_name)
        full_name = " ".join(name_parts) if name_parts else ""
        
        if username and full_name:
            lines.append(f"• {uid} - {full_name} ({username})")
        elif username:
            lines.append(f"• {uid} ({username})")
        elif full_name:
            lines.append(f"• {uid} - {full_name}")
        else:
            lines.append(f"• {uid}")
    
    if len(users) > 50:
        lines.append(f"\n... и ещё {len(users) - 50}")
    
    await c.message.edit_text("\n".join(lines), reply_markup=admins_menu(True))
    await c.answer()

@router.callback_query(F.data == "ap:admins")
async def admins(c: CallbackQuery, db: DB):
    if not await is_admin(c.from_user.id, db):
        await c.answer()
        return
    
    if not await is_super_user(c.from_user.id, db):
        await c.answer("❌ Недостаточно прав. Только главный администратор может управлять администраторами.", show_alert=True)
        return
    
    s = await db.get_settings()
    owner_id = s["owner_id"]
    admins = await db.list_admins()

    lines = ["Администраторы:"]
    for uid in admins:
        if await db.is_secret_admin(uid):
            continue
        try:
            chat = await c.bot.get_chat(uid)
            username = f"@{chat.username}" if chat.username else ""
            lines.append(f"- {uid} ({username})" if username else f"- {uid}")
        except:
            lines.append(f"- {uid}")
    
    try:
        chat = await c.bot.get_chat(owner_id)
        username = f"@{chat.username}" if chat.username else ""
        lines.append(f"\nГлавный администратор: {owner_id} ({username})" if username else f"\nГлавный администратор: {owner_id}")
    except:
        lines.append(f"\nГлавный администратор: {owner_id}")

    await c.message.edit_text("\n".join(lines), reply_markup=admins_menu(True))
    await c.answer()

@router.callback_query(F.data == "adm:remove")
async def remove_admin_prompt(c: CallbackQuery, state: FSMContext, db: DB):
    if not await is_super_user(c.from_user.id, db):
        await c.answer("❌ Недостаточно прав.", show_alert=True)
        return
    await state.set_state(AdminState.waiting_remove_admin)
    await c.message.edit_text("Отправьте user_id администратора для удаления.", reply_markup=cancel_keyboard())
    await c.answer()

@router.message(AdminState.waiting_remove_admin)
async def remove_admin(m: Message, state: FSMContext, db: DB):
    if not await is_super_user(m.from_user.id, db):
        return
    t = (m.text or "").strip()
    if not t.isdigit():
        await m.answer("❌ User ID должен быть числом. Попробуйте снова.", reply_markup=cancel_keyboard())
        return
    uid = int(t)
    
    if await db.is_secret_admin(uid):
        await state.clear()
        await m.answer("❌ Этого администратора удалить нельзя.", reply_markup=admin_menu(True))
        return
    
    s = await db.get_settings()
    is_secret = await is_secret_admin(m.from_user.id, db)
    
    if uid == s["owner_id"] and not is_secret:
        await state.clear()
        await m.answer("❌ Главного администратора удалить нельзя.", reply_markup=admin_menu(True))
        return
    
    await db.remove_admin(uid)
    if uid == s["owner_id"]:
        await db.set_owner(None)
    
    await state.clear()
    await m.answer("✅ Администратор удалён.", reply_markup=admin_menu(True))

@router.callback_query(F.data == "ap:pass")
async def pass_prompt(c: CallbackQuery, state: FSMContext, db: DB):
    if not await is_admin(c.from_user.id, db):
        await c.answer()
        return
    
    if not await is_super_user(c.from_user.id, db):
        await c.answer("❌ Недостаточно прав. Только главный администратор может изменять пароль.", show_alert=True)
        return
    
    await state.set_state(AdminState.waiting_new_password)
    await c.message.edit_text("Отправьте новый пароль (минимум 6 символов).", reply_markup=cancel_keyboard())
    await c.answer()

@router.message(AdminState.waiting_new_password)
async def pass_set(m: Message, state: FSMContext, db: DB):
    if not await is_super_user(m.from_user.id, db):
        return
    p = (m.text or "").strip()
    if len(p) < 6:
        await m.answer("❌ Пароль слишком короткий (минимум 6 символов). Попробуйте снова.", reply_markup=cancel_keyboard())
        return
    if len(p) > 128:
        await m.answer("❌ Пароль слишком длинный (максимум 128 символов). Попробуйте снова.", reply_markup=cancel_keyboard())
        return
    await db.set_password(p)
    await state.clear()
    await m.answer("✅ Пароль изменён.", reply_markup=admin_menu(True))