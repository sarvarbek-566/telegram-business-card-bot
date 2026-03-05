from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

try:
    from aiogram.types import CopyTextButton
    HAS_COPY = True
except Exception:
    HAS_COPY = False
    CopyTextButton = None

def admin_menu(is_owner: bool = False) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="Предпросмотр", callback_data="ap:preview")
    b.button(text="Текст", callback_data="ap:text")
    b.button(text="Фото", callback_data="ap:photo")
    b.button(text="Кнопки", callback_data="ap:buttons")
    if is_owner:
        b.button(text="Пользователи", callback_data="ap:users")
        b.button(text="Администраторы", callback_data="ap:admins")
        b.button(text="Пароль", callback_data="ap:pass")
        b.adjust(2, 2, 1, 2)
    else:
        b.adjust(2, 2)
    return b.as_markup()

def buttons_menu() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="Добавить", callback_data="btn:add")
    b.button(text="Удалить последнюю", callback_data="btn:pop")
    b.button(text="Очистить", callback_data="btn:clear")
    b.button(text="Назад", callback_data="ap:back")
    b.adjust(2, 2)
    return b.as_markup()

def admins_menu(is_owner: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if is_owner:
        b.button(text="Удалить администратора", callback_data="adm:remove")
    b.button(text="Назад", callback_data="ap:back")
    b.adjust(1)
    return b.as_markup()

def cancel_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="❌ Отмена", callback_data="cancel")
    return b.as_markup()

def build_post_kb(buttons: list[dict]) -> InlineKeyboardMarkup | None:
    if not buttons:
        return None

    kb = InlineKeyboardBuilder()
    for item in buttons[:5]:
        text = (item.get("text") or "").strip()
        typ = (item.get("type") or "").strip()
        val = (item.get("value") or "").strip()
        bid = (item.get("id") or "").strip()
        if not text:
            continue

        if typ == "url" and val:
            kb.row(InlineKeyboardButton(text=text, url=val))
        elif typ == "copy":
            if HAS_COPY and val:
                kb.row(InlineKeyboardButton(text=text, copy_text=CopyTextButton(text=val)))
            else:
                if bid:
                    kb.row(InlineKeyboardButton(text=text, callback_data=f"copy:{bid}"))
    return kb.as_markup()