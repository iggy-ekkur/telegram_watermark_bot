from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_settings_menu():
    buttons = [
        [InlineKeyboardButton(text="📡 Установить канал", callback_data="set_channel")],
        [InlineKeyboardButton(text="✍️ Установить вотермарк", callback_data="setmark_text")],
        [InlineKeyboardButton(text="ℹ️ Инфо", callback_data="info")],
        [InlineKeyboardButton(text="❌ Закрыть меню", callback_data="hide_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
