from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.db import get_tokens


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Балансы", callback_data="balance")],
        [InlineKeyboardButton(text="🪙 Управление токенами", callback_data="tokens")],
        [InlineKeyboardButton(text="➕ Создать транзакцию", callback_data="income")],
        [InlineKeyboardButton(text="➖ Создать отправку", callback_data="outcome")],
        [InlineKeyboardButton(text="🧹 Очистить историю", callback_data="clear_history")],
        [InlineKeyboardButton(text="📜 История транзакций", callback_data="history")]
    ])


def tokens_menu() -> InlineKeyboardMarkup:
    tokens = get_tokens()
    buttons = []

    sorted_tokens = sorted(tokens, key=lambda t: (t[6], t[2].lower()))

    locked_tokens = [t for t in sorted_tokens if t[6] == 1]
    unlocked_tokens = [t for t in sorted_tokens if t[6] == 0]

    for token in locked_tokens:
        token_id, symbol, name, enabled, address, balance, locked = token
        buttons.append([InlineKeyboardButton(
            text=f"🔒 {name}",
            callback_data=f"edit_{token_id}"
        )])

    if locked_tokens and unlocked_tokens:
        buttons.append([])

    for token in unlocked_tokens:
        token_id, symbol, name, enabled, address, balance, locked = token
        emoji = "✅" if enabled else "❌"
        status = " (вкл)" if enabled else " (выкл)"
        buttons.append([InlineKeyboardButton(
            text=f"{emoji} {name}{status}",
            callback_data=f"edit_{token_id}"
        )])

    buttons.append([InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def balance_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_balance")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
    ])
