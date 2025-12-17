from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_token_management_keyboard(token_id: str, locked: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура управления токеном (разная для locked/unlocked)"""
    if locked:
        # Только адрес для locked токенов
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить адрес кошелька", callback_data=f"editaddr_{token_id}")],
            [InlineKeyboardButton(text="⬅️ Назад к токенам", callback_data="tokens")]
        ])
    else:
        # Полное управление для unlocked токенов
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Включить/Выключить", callback_data=f"toggle_{token_id}")],
            [InlineKeyboardButton(text="✏️ Изменить адрес кошелька", callback_data=f"editaddr_{token_id}")],
            [InlineKeyboardButton(text="⬅️ Назад к токенам", callback_data="tokens")]
        ])


def get_cancel_keyboard(return_to: str = "tokens") -> InlineKeyboardMarkup:
    """Клавиатура отмены с возможностью вернуться в разные места"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_edit_{return_to}")]
    ])


def get_confirm_clear_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения очистки истории"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, очистить", callback_data="confirm_clear"),
            InlineKeyboardButton(text="❌ Нет, отменить", callback_data="cancel_clear")
        ]
    ])