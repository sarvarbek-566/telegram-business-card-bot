from aiogram.fsm.state import State, StatesGroup

class AdminState(StatesGroup):
    waiting_text = State()
    waiting_photo = State()
    waiting_btn_text = State()
    waiting_btn_type = State()
    waiting_btn_value = State()
    waiting_new_password = State()
    waiting_remove_admin = State()