import json
import aiosqlite
from typing import Optional
from aiogram.types import MessageEntity

def _loads(s: str, default):
    try:
        return json.loads(s) if s else default
    except Exception:
        return default

def _dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)

def entities_to_json(entities: list[MessageEntity] | None) -> str:
    if not entities:
        return "[]"
    return _dumps([e.model_dump() for e in entities])

def entities_from_json(s: str) -> list[MessageEntity]:
    data = _loads(s, [])
    if not isinstance(data, list):
        return []
    out = []
    for item in data:
        try:
            out.append(MessageEntity.model_validate(item))
        except Exception:
            pass
    return out

class DB:
    def __init__(self, path: str):
        self.path = path

    async def init(self, initial_password: str):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""
            CREATE TABLE IF NOT EXISTS settings(
                id INTEGER PRIMARY KEY CHECK(id=1),
                owner_id INTEGER,
                password TEXT,
                post_text TEXT,
                post_entities TEXT,
                photo_id TEXT,
                buttons_json TEXT
            )
            """)
            await db.execute("""
            CREATE TABLE IF NOT EXISTS admins(
                user_id INTEGER PRIMARY KEY
            )
            """)
            await db.execute("""
            CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                joined_at INTEGER
            )
            """)
            await db.execute("""
            CREATE TABLE IF NOT EXISTS secret_admins(
                user_id INTEGER PRIMARY KEY
            )
            """)
            cur = await db.execute("SELECT 1 FROM settings WHERE id=1")
            if await cur.fetchone() is None:
                await db.execute(
                    "INSERT INTO settings(id, owner_id, password, post_text, post_entities, photo_id, buttons_json) VALUES(1, NULL, ?, '', '[]', NULL, '[]')",
                    (initial_password,)
                )
            await db.commit()

    async def get_settings(self) -> dict:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("""
                SELECT owner_id, password, post_text, post_entities, photo_id, buttons_json
                FROM settings WHERE id=1
            """)
            owner_id, password, text, ent_json, photo_id, btn_json = await cur.fetchone()
            buttons = _loads(btn_json, [])
            if not isinstance(buttons, list):
                buttons = []
            return {
                "owner_id": owner_id,
                "password": password or "",
                "text": text or "",
                "entities": entities_from_json(ent_json or "[]"),
                "photo": photo_id,
                "buttons": buttons
            }

    async def set_owner(self, owner_id: int | None):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE settings SET owner_id=? WHERE id=1", (owner_id,))
            await db.commit()

    async def check_password(self, key: str) -> bool:
        s = await self.get_settings()
        return key == s["password"]

    async def set_password(self, new_password: str):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE settings SET password=? WHERE id=1", (new_password,))
            await db.commit()

    async def is_admin(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,))
            return (await cur.fetchone()) is not None

    async def add_admin(self, user_id: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT OR IGNORE INTO admins(user_id) VALUES(?)", (user_id,))
            await db.commit()

    async def remove_admin(self, user_id: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
            await db.commit()

    async def list_admins(self) -> list[int]:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT user_id FROM admins ORDER BY user_id")
            rows = await cur.fetchall()
            return [r[0] for r in rows]

    async def set_post_text_and_entities(self, text: str, entities: list[MessageEntity] | None):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE settings SET post_text=?, post_entities=? WHERE id=1",
                (text or "", entities_to_json(entities))
            )
            await db.commit()

    async def set_photo(self, file_id: Optional[str]):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE settings SET photo_id=? WHERE id=1", (file_id,))
            await db.commit()

    async def set_buttons(self, buttons: list[dict]):
        buttons = buttons[:5]
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE settings SET buttons_json=? WHERE id=1", (_dumps(buttons),))
            await db.commit()

    async def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        import time
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO users(user_id, username, first_name, last_name, joined_at)
                VALUES(?, ?, ?, ?, ?)
            """, (user_id, username, first_name, last_name, int(time.time())))
            await db.commit()

    async def list_users(self) -> list[dict]:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT user_id, username, first_name, last_name, joined_at FROM users ORDER BY joined_at DESC")
            rows = await cur.fetchall()
            return [
                {
                    "user_id": r[0],
                    "username": r[1],
                    "first_name": r[2],
                    "last_name": r[3],
                    "joined_at": r[4]
                }
                for r in rows
            ]

    async def is_secret_admin(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT 1 FROM secret_admins WHERE user_id=?", (user_id,))
            return (await cur.fetchone()) is not None

    async def add_secret_admin(self, user_id: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT OR IGNORE INTO secret_admins(user_id) VALUES(?)", (user_id,))
            await db.commit()

    async def remove_secret_admin(self, user_id: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM secret_admins WHERE user_id=?", (user_id,))
            await db.commit()