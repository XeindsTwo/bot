from aiogram import types
from datetime import datetime
from .helpers import CANCEL_TEXT

def tokens_keyboard(tokens):
    keyboard = []
    row = []

    for i, t in enumerate(tokens, 1):
        row.append(types.InlineKeyboardButton(text=str(t[2]), callback_data=f"token_{t[0]}"))
        if i % 4 == 0:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    keyboard.append([types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")])
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

def month_days_keyboard():
    today = datetime.now()
    year, month = today.year, today.month

    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)

    days_in_month = (next_month - datetime(year, month, 1)).days
    buttons = []
    row = []

    for day in range(1, days_in_month + 1):
        is_today = (day == today.day)
        text = f"📍 {day}" if is_today else str(day)
        row.append(types.InlineKeyboardButton(text=text, callback_data=f"day_{day}"))
        if len(row) == 7:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([
        types.InlineKeyboardButton(text="📅 Сегодня", callback_data="day_today"),
        types.InlineKeyboardButton(text="📅 Завтра", callback_data="day_tomorrow"),
        types.InlineKeyboardButton(text="📅 Послезавтра", callback_data="day_after_tomorrow")
    ])
    buttons.append([types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")])

    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def time_cancel_keyboard():
    keyboard = [
        [types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)