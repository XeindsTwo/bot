from aiogram import types
from datetime import datetime, timedelta

CANCEL_TEXT = "❌ Отменить создание"


def tokens_keyboard(tokens):
    """Клавиатура для выбора токена"""
    keyboard = []
    row = []

    for i, t in enumerate(tokens, 1):
        row.append(types.InlineKeyboardButton(text=str(t[2]), callback_data=f"token_{t[0]}"))
        if i % 2 == 0:  # По 2 в строке, как в outcome
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    keyboard.append([types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")])
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)


def time_option_keyboard():
    """Клавиатура выбора опции времени"""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="⏰ Сейчас", callback_data="now")],
        [types.InlineKeyboardButton(text="📅 Выбрать дату", callback_data="choose_date")],
        [types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")]
    ])


def skip_cancel_keyboard():
    """Клавиатура с пропуском"""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Пропустить", callback_data="skip")],
        [types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")]
    ])


def month_days_keyboard(year=None, month=None):
    """Простой календарь как в outcome"""
    today = datetime.now()

    if year is None:
        year = today.year
    if month is None:
        month = today.month

    # Определяем количество дней в месяце
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)

    days_in_month = (next_month - datetime(year, month, 1)).days

    buttons = []
    row = []

    for day in range(1, days_in_month + 1):
        is_today = (day == today.day and month == today.month and year == today.year)
        text = f"📍 {day}" if is_today else str(day)
        row.append(types.InlineKeyboardButton(
            text=text,
            callback_data=f"day_{year}_{month}_{day}"
        ))
        if len(row) == 7:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    # Быстрые кнопки
    buttons.append([
        types.InlineKeyboardButton(text="📅 Сегодня", callback_data="day_today"),
        types.InlineKeyboardButton(text="📅 Завтра", callback_data="day_tomorrow"),
        types.InlineKeyboardButton(text="📅 Послезавтра", callback_data="day_after_tomorrow")
    ])

    # Кнопки переключения месяцев
    month_name = datetime(year, month, 1).strftime("%B %Y")
    buttons.append([
        types.InlineKeyboardButton(text="◀️", callback_data=f"month_prev_{year}_{month}"),
        types.InlineKeyboardButton(text=month_name, callback_data="month_current"),
        types.InlineKeyboardButton(text="▶️", callback_data=f"month_next_{year}_{month}")
    ])

    buttons.append([types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")])

    return types.InlineKeyboardMarkup(inline_keyboard=buttons)


def time_cancel_keyboard():
    """Простая клавиатура для ввода времени"""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")]
    ])


def simple_cancel_keyboard():
    """Простая клавиатура с отменой"""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")]
    ])
