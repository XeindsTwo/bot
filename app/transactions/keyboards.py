from aiogram import types
from .helpers import CANCEL_TEXT

def tokens_keyboard(tokens):
    keyboard = []
    row = []

    for i, t in enumerate(tokens, 1):
        row.append(types.InlineKeyboardButton(
            text=str(t[2]), # отображаемое имя
            callback_data=f"token_{t[0]}"  # ID, обязательно число
        ))
        if i % 4 == 0:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    keyboard.append([types.InlineKeyboardButton(
        text=CANCEL_TEXT,
        callback_data="cancel"
    )])

    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)


def skip_cancel_keyboard():
    keyboard = [
        [types.InlineKeyboardButton(text="Пропустить", callback_data="skip")],
        [types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)


def now_cancel_keyboard():
    keyboard = [
        [types.InlineKeyboardButton(text="Сейчас", callback_data="now")],
        [types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)