from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_token_management_keyboard(token_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Переключить включение", callback_data=f"toggle_{token_id}")],
        [InlineKeyboardButton(text="✏️ Изменить адрес", callback_data=f"editaddr_{token_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="tokens")]
    ])

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_edit")]
    ])