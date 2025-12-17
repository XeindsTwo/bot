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
        [types.InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip")],
        [types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)


def now_cancel_keyboard():
    keyboard = [
        [types.InlineKeyboardButton(text="⏰ Сейчас", callback_data="now")],
        [types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)


def month_days_keyboard(year=None, month=None):
    """Клавиатура с днями месяца и навигацией по месяцам"""
    today = datetime.now()

    if year is None:
        year = today.year
    if month is None:
        month = today.month

    # Определяем следующий и предыдущий месяцы
    if month == 1:
        prev_month = datetime(year - 1, 12, 1)
        next_month = datetime(year, 2, 1)
    elif month == 12:
        prev_month = datetime(year, 11, 1)
        next_month = datetime(year + 1, 1, 1)
    else:
        prev_month = datetime(year, month - 1, 1)
        next_month = datetime(year, month + 1, 1)

    # Количество дней в месяце
    days_in_month = (next_month - datetime(year, month, 1)).days

    # Названия месяцев
    month_names = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    month_name = month_names[month - 1]

    # Создаем кнопки
    buttons = []

    # Навигация по месяцам
    buttons.append([
        types.InlineKeyboardButton(text="◀️", callback_data=f"prev_month_{prev_month.year}_{prev_month.month}"),
        types.InlineKeyboardButton(text=f"{month_name} {year}", callback_data="ignore"),
        types.InlineKeyboardButton(text="▶️", callback_data=f"next_month_{next_month.year}_{next_month.month}")
    ])

    # Дни недели
    weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    weekday_buttons = [types.InlineKeyboardButton(text=day, callback_data="ignore") for day in weekdays]
    buttons.append(weekday_buttons)

    # Первый день месяца
    first_day = datetime(year, month, 1)
    start_offset = (first_day.weekday() + 1) % 7  # Пн = 0, Вс = 6

    row = []

    # Пустые кнопки для смещения
    for _ in range(start_offset):
        row.append(types.InlineKeyboardButton(text=" ", callback_data="ignore"))

    # Дни месяца
    for day in range(1, days_in_month + 1):
        current_date = datetime(year, month, day)
        is_today = (current_date.date() == today.date())
        is_future = (current_date.date() > today.date())

        if is_today:
            text = f"📍{day}"
        elif is_future:
            text = f"🔸{day}"
        else:
            text = str(day)

        row.append(types.InlineKeyboardButton(text=text, callback_data=f"day_{year}_{month}_{day}"))

        if len(row) == 7:
            buttons.append(row)
            row = []

    # Добиваем последнюю строку
    if row:
        while len(row) < 7:
            row.append(types.InlineKeyboardButton(text=" ", callback_data="ignore"))
        buttons.append(row)

    # Быстрые кнопки
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


def back_cancel_keyboard():
    keyboard = [
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data="back")],
        [types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)