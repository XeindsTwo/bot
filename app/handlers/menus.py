from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.db import get_tokens


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🪙 Управление токенами", callback_data="tokens")],
        [InlineKeyboardButton(text="➕ Создать транзакцию", callback_data="income")],
        [InlineKeyboardButton(text="➖ Создать отправку", callback_data="outcome")],
        [InlineKeyboardButton(text="🧹 Очистить историю", callback_data="clear")],
        [InlineKeyboardButton(text="📜 История транзакций", callback_data="history")]
    ])


def tokens_menu() -> InlineKeyboardMarkup:
    tokens = get_tokens()
    buttons = []

    editable_tokens = [t for t in tokens if t[5] == 0]

    for i in range(0, len(editable_tokens), 2):
        row = []
        for j in range(2):
            if i + j < len(editable_tokens):
                token, name, enabled, address, balance, _ = editable_tokens[i + j]
                status_text = "включен" if enabled else "выключен"
                text = f"{name}\n{'✅' if enabled else '❌'} {status_text}"
                row.append(InlineKeyboardButton(text=text, callback_data=f"edit_{token}"))
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)