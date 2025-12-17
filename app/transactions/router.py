from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from app.db import get_tokens, get_token_by_id
from app.guards import is_owner
from app.handlers.menus import main_menu
from app.transactions.utils import parse_time_input, validate_crypto_address
from .states import IncomeStates
from .keyboards import (
    tokens_keyboard, time_option_keyboard, skip_cancel_keyboard,
    month_days_keyboard, time_cancel_keyboard, simple_cancel_keyboard
)
# Импортируем функции из helpers.py
from .helpers import (
    handle_cancel_in_message,
    handle_skip_in_message,
    finish_transaction,
    handle_cancel_callback,  # если нужен
    CANCEL_TEXT
)

router = Router()
# УДАЛИ ЭТУ СТРОКУ, так как CANCEL_TEXT уже импортирован из helpers.py
# CANCEL_TEXT = "❌ Отменить создание"


# ========== ОСНОВНЫЕ ОБРАБОТЧИКИ ==========
@router.callback_query(lambda c: is_owner(c.from_user.id) and c.data == "income")
async def start_income(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    tokens = [t for t in get_tokens() if t[3] == 1]

    if not tokens:
        await call.message.answer("Нет доступных токенов", reply_markup=main_menu())
        await call.answer()
        return

    await state.set_state(IncomeStates.choosing_token)
    await call.message.answer("Выберите токен:", reply_markup=tokens_keyboard(tokens))
    await call.answer()


@router.callback_query(lambda c: c.data.startswith("token_"))
async def choose_token_callback(call: types.CallbackQuery, state: FSMContext):
    token_id = int(call.data.split("_")[1])
    token = next((t for t in get_tokens() if t[0] == token_id), None)

    if not token:
        await call.answer("❌ Токен не найден", show_alert=True)
        return

    await state.update_data(
        token_id=token[0],
        token_name=str(token[2]),
        token_symbol=token[1]
    )
    await state.set_state(IncomeStates.entering_amount)

    await call.message.edit_text("💰 Введите сумму:", reply_markup=simple_cancel_keyboard())
    await call.answer()


@router.message(IncomeStates.entering_amount)
async def entering_amount(message: types.Message, state: FSMContext):
    if await handle_cancel_in_message(message, state):
        return

    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректную сумму", reply_markup=simple_cancel_keyboard())
        return

    await state.update_data(amount=amount)

    await message.answer(
        f"✅ Сумма: {amount}\n\n⏰ Укажите дату транзакции:",
        reply_markup=time_option_keyboard()
    )
    await state.set_state(IncomeStates.choosing_time_option)


@router.callback_query(IncomeStates.choosing_time_option)
async def choose_time_option(call: types.CallbackQuery, state: FSMContext):
    if call.data == "cancel":
        await state.clear()
        await call.message.edit_text("❌ Создание отменено", reply_markup=main_menu())
        await call.answer()
        return

    if call.data == "now":
        tx_date = datetime.now()
        await state.update_data(tx_date=tx_date)
        await state.set_state(IncomeStates.entering_from_address)

        await call.message.edit_text(
            f"✅ Текущая дата: {tx_date.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"👤 Введите адрес отправителя:",
            reply_markup=simple_cancel_keyboard()
        )

    elif call.data == "choose_date":
        await state.set_state(IncomeStates.choosing_day)
        today = datetime.now()
        month_name = today.strftime("%B")

        await call.message.edit_text(
            f"📅 Выберите день ({month_name} {today.year}):\n\n📍 - сегодняшний день",
            reply_markup=month_days_keyboard()
        )

    await call.answer()


@router.callback_query(lambda c: c.data.startswith("month_"))
async def switch_month_callback(call: types.CallbackQuery, state: FSMContext):
    if call.data == "cancel":
        await state.clear()
        await call.message.edit_text("❌ Создание отменено", reply_markup=main_menu())
        await call.answer()
        return

    data = call.data.replace("month_", "")

    if data == "current":
        today = datetime.now()
        await call.message.edit_text(
            f"📅 Выберите день ({today.strftime('%B %Y')}):\n\n📍 - сегодняшний день",
            reply_markup=month_days_keyboard()
        )
    elif data.startswith("prev_") or data.startswith("next_"):
        try:
            parts = data.split("_")
            direction = parts[0]
            year = int(parts[1])
            month = int(parts[2])

            if direction == "prev":
                if month == 1:
                    month = 12
                    year -= 1
                else:
                    month -= 1
            else:
                if month == 12:
                    month = 1
                    year += 1
                else:
                    month += 1

            await call.message.edit_text(
                f"📅 Выберите день ({datetime(year, month, 1).strftime('%B %Y')}):",
                reply_markup=month_days_keyboard(year, month)
            )
        except:
            await call.answer("❌ Ошибка", show_alert=True)

    await call.answer()


@router.callback_query(lambda c: c.data.startswith("day_"))
async def choose_day_callback(call: types.CallbackQuery, state: FSMContext):
    if call.data == "cancel":
        await state.clear()
        await call.message.edit_text("❌ Создание отменено", reply_markup=main_menu())
        await call.answer()
        return

    day_data = call.data.replace("day_", "")
    today = datetime.now()

    if day_data == "today":
        selected_date = today
    elif day_data == "tomorrow":
        selected_date = today + timedelta(days=1)
    elif day_data == "after_tomorrow":
        selected_date = today + timedelta(days=2)
    else:
        try:
            year_str, month_str, day_str = day_data.split("_")
            year = int(year_str)
            month = int(month_str)
            day = int(day_str)
            selected_date = datetime(year, month, day)
        except:
            await call.answer("❌ Ошибка", show_alert=True)
            return

    await state.update_data(
        selected_date=selected_date,
        base_date=selected_date.strftime("%Y-%m-%d")
    )
    await state.set_state(IncomeStates.entering_time)

    month_names = ["Января", "Февраля", "Марта", "Апреля", "Мая", "Июня",
                   "Июля", "Августа", "Сентября", "Октября", "Ноября", "Декабря"]

    await call.message.edit_text(
        f"📅 Выбрана дата: {selected_date.day} {month_names[selected_date.month - 1]} {selected_date.year}\n\n"
        f"⏰ Введите время (ЧЧ ММ или ЧЧ:ММ):\n\n"
        f"Часы: 0-23, минуты: 0-59",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="⏰ Сейчас", callback_data="now_time")],
            [types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")]
        ])
    )
    await call.answer()


@router.callback_query(IncomeStates.entering_time)
async def handle_now_time(call: types.CallbackQuery, state: FSMContext):
    if call.data == "cancel":
        await state.clear()
        await call.message.edit_text("❌ Создание отменено", reply_markup=main_menu())
        await call.answer()
        return

    if call.data == "now_time":
        tx_date = datetime.now()
        await state.update_data(tx_date=tx_date)
        await state.set_state(IncomeStates.entering_from_address)

        await call.message.edit_text(
            f"✅ Текущая дата: {tx_date.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"👤 Введите адрес отправителя:",
            reply_markup=simple_cancel_keyboard()
        )
        await call.answer()


@router.message(IncomeStates.entering_time)
async def entering_time(message: types.Message, state: FSMContext):
    if await handle_cancel_in_message(message, state):
        return

    time_data = parse_time_input(message.text)

    if not time_data:
        await message.answer(
            "❌ Неверный формат времени.\nИспользуйте: 14 30, 9, 14:30",
            reply_markup=time_cancel_keyboard()
        )
        return

    hour, minute = time_data
    data = await state.get_data()
    selected_date = data.get('selected_date')

    if selected_date:
        tx_date = datetime(selected_date.year, selected_date.month, selected_date.day, hour, minute)
    else:
        today = datetime.now()
        tx_date = datetime(today.year, today.month, today.day, hour, minute)

    await state.update_data(tx_date=tx_date)
    await state.set_state(IncomeStates.entering_from_address)

    await message.answer(
        f"✅ Дата установлена: {tx_date.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"👤 Введите адрес отправителя:",
        reply_markup=simple_cancel_keyboard()
    )


@router.message(IncomeStates.entering_from_address)
async def entering_from_address(message: types.Message, state: FSMContext):
    if await handle_cancel_in_message(message, state):
        return

    from_address = message.text.strip()

    if not from_address:
        await message.answer("❌ Адрес не может быть пустым", reply_markup=simple_cancel_keyboard())
        return

    is_valid, error_message = validate_crypto_address(from_address)

    if not is_valid:
        await message.answer(f"❌ {error_message}", reply_markup=simple_cancel_keyboard())
        return

    await state.update_data(from_address=from_address)
    await state.set_state(IncomeStates.entering_tx_hash)

    await message.answer(
        "✅ Адрес принят!\n\n"
        "🔗 Хеш транзакции:\n\n"
        "Введите хеш транзакции или нажмите «Пропустить» для автоматической генерации",
        reply_markup=skip_cancel_keyboard()
    )


@router.message(IncomeStates.entering_tx_hash)
async def entering_tx_hash(message: types.Message, state: FSMContext):
    """Ввод хеша транзакции"""
    if await handle_cancel_in_message(message, state):
        return

    if await handle_skip_in_message(message, state):
        return

    tx_hash = message.text.strip()

    if not tx_hash:
        await message.answer("❌ Хеш не может быть пустым", reply_markup=skip_cancel_keyboard())
        return

    await state.update_data(tx_hash=tx_hash)
    await state.set_state(IncomeStates.entering_fee)

    data = await state.get_data()
    token_symbol = data.get('token_symbol', 'eth')

    await message.answer(
        f"✅ Хеш принят!\n\n"
        f"💰 Комиссия сети для {token_symbol.upper()}:\n\n"
        f"Введите сумму комиссии или нажмите «Пропустить» для случайной генерации",
        reply_markup=skip_cancel_keyboard()
    )


@router.message(IncomeStates.entering_fee)
async def entering_fee(message: types.Message, state: FSMContext):
    """Ввод комиссии"""
    if await handle_cancel_in_message(message, state):
        return

    if await handle_skip_in_message(message, state):
        return

    text = message.text.strip().lower()

    try:
        fee = float(text.replace(",", "."))
        if fee < 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Введите корректное число",
            reply_markup=skip_cancel_keyboard()
        )
        return

    await state.update_data(fee=fee)
    await state.set_state(IncomeStates.entering_explorer_link)

    await message.answer(
        f"✅ Комиссия установлена: {fee:.4f}\n\n"
        f"🌐 Введите ссылку на explorer (или нажмите «Пропустить»):",
        reply_markup=skip_cancel_keyboard()
    )


@router.message(IncomeStates.entering_explorer_link)
async def finish_income(message: types.Message, state: FSMContext):
    """Завершение ввода ссылки на explorer"""
    if await handle_cancel_in_message(message, state):
        return

    if await handle_skip_in_message(message, state):
        return

    explorer_link = None
    if message.text.strip().lower() != "пропустить":
        explorer_link = message.text.strip()
        if not (explorer_link.startswith('http://') or explorer_link.startswith('https://')):
            await message.answer(
                "❌ Ссылка должна начинаться с http:// или https://",
                reply_markup=skip_cancel_keyboard()
            )
            return

    await finish_transaction(state, explorer_link, message=message)


# ========== ОБРАБОТЧИКИ КНОПОК ==========
@router.callback_query(lambda c: c.data == "skip")
async def handle_skip_button(call: types.CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Пропустить'"""
    current_state = await state.get_state()

    if current_state == IncomeStates.entering_tx_hash.state:
        # Пропуск хеша
        from app.transactions.utils import generate_tx_hash
        data = await state.get_data()
        token_symbol = data.get('token_symbol', 'eth')

        crypto_type = 'eth'
        if 'trx' in token_symbol.lower() or 'tron' in token_symbol.lower():
            crypto_type = 'tron'
        elif 'btc' in token_symbol.lower():
            crypto_type = 'btc'

        tx_hash = generate_tx_hash(crypto_type)
        await state.update_data(tx_hash=tx_hash)
        await state.set_state(IncomeStates.entering_fee)

        await call.message.edit_text(
            f"✅ Сгенерирован хеш: <code>{tx_hash[:20]}...</code>\n\n"
            f"💰 Комиссия сети для {token_symbol.upper()}:\n\n"
            f"Введите сумму комиссии или нажмите «Пропустить» для случайной генерации",
            parse_mode="HTML",
            reply_markup=skip_cancel_keyboard()
        )

    elif current_state == IncomeStates.entering_fee.state:
        # Пропуск комиссии
        from app.transactions.utils import generate_fee_for_token
        data = await state.get_data()
        token_symbol = data.get('token_symbol', 'eth')
        fee = generate_fee_for_token(token_symbol)

        await state.update_data(fee=fee)
        await state.set_state(IncomeStates.entering_explorer_link)

        await call.message.edit_text(
            f"✅ Сгенерирована комиссия: {fee:.4f}\n\n"
            f"🌐 Введите ссылку на explorer:",
            reply_markup=skip_cancel_keyboard()
        )

    elif current_state == IncomeStates.entering_explorer_link.state:
        # Пропуск explorer ссылки
        await finish_transaction(state, None, is_skip=True, call=call)

    await call.answer()


@router.callback_query(lambda c: c.data == "cancel")
async def handle_cancel_button(call: types.CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Отменить'"""
    await state.clear()
    await call.message.edit_text("❌ Создание транзакции отменено", reply_markup=main_menu())
    await call.answer()


@router.callback_query(lambda c: c.data == "now_time")
async def handle_now_time_button(call: types.CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Сейчас'"""
    tx_date = datetime.now()
    await state.update_data(tx_date=tx_date)
    await state.set_state(IncomeStates.entering_from_address)

    await call.message.edit_text(
        f"✅ Текущая дата: {tx_date.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"👤 Введите адрес отправителя:",
        reply_markup=simple_cancel_keyboard()
    )
    await call.answer()