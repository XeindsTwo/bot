from aiogram import types
from datetime import datetime, timedelta

CANCEL_TEXT = "❌ Отменить создание"


def tokens_keyboard_outcome(tokens):
    """Клавиатура для выбора токена (только с балансом > 0)"""
    keyboard = []
    row = []

    for i, token in enumerate(tokens, 1):
        row.append(types.InlineKeyboardButton(
            text=f"{token[2]} ({token[5]:.2f})",  # name + balance
            callback_data=f"outcome_token_{token[0]}"  # token_id
        ))
        if i % 2 == 0:  # По 2 токена в строке
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
    """Клавиатура с днями месяца (как в income)"""
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
            callback_data=f"outcome_day_{year}_{month}_{day}"
        ))
        if len(row) == 7:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    # Быстрые кнопки
    buttons.append([
        types.InlineKeyboardButton(text="📅 Сегодня", callback_data="outcome_day_today"),
        types.InlineKeyboardButton(text="📅 Завтра", callback_data="outcome_day_tomorrow"),
        types.InlineKeyboardButton(text="📅 Послезавтра", callback_data="outcome_day_after_tomorrow")
    ])

    # Кнопки переключения месяцев
    month_name = datetime(year, month, 1).strftime("%B %Y")
    buttons.append([
        types.InlineKeyboardButton(text="◀️", callback_data=f"outcome_month_prev_{year}_{month}"),
        types.InlineKeyboardButton(text=month_name, callback_data="outcome_month_current"),
        types.InlineKeyboardButton(text="▶️", callback_data=f"outcome_month_next_{year}_{month}")
    ])

    buttons.append([types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")])

    return types.InlineKeyboardMarkup(inline_keyboard=buttons)


def now_cancel_keyboard():
    """Клавиатура с кнопкой 'Выбрать текущую дату'"""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Выбрать текущую дату", callback_data="now_time")],
        [types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")]
    ])


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


def confirm_transaction_keyboard():
    """Клавиатура подтверждения транзакции"""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="✅ Да, подтвердить", callback_data="confirm_tx"),
            types.InlineKeyboardButton(text="❌ Нет, отменить", callback_data="cancel_tx")
        ]
    ])
