from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from app.db import get_tokens
from app.guards import is_owner
from app.handlers.menus import main_menu
from app.transactions.utils import generate_tx_hash, generate_fee_for_token, parse_time_input
from .states import IncomeStates
from .keyboards import tokens_keyboard, skip_cancel_keyboard, month_days_keyboard, time_cancel_keyboard
from .helpers import handle_cancel, handle_cancel_callback, finish_transaction, CANCEL_TEXT

router = Router()


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
    if await handle_cancel_callback(call, state):
        return

    token_id = int(call.data.split("_")[1])
    token = next((t for t in get_tokens() if t[0] == token_id), None)

    if not token:
        await call.answer("Токен не найден", show_alert=True)
        return

    await state.update_data(token_id=token[0], token_name=str(token[2]), token_symbol=token[1])
    await state.set_state(IncomeStates.entering_amount)

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")]
    ])

    await call.message.edit_text("Введите сумму:", reply_markup=keyboard)
    await call.answer()


@router.message(IncomeStates.entering_amount)
async def entering_amount(message: types.Message, state: FSMContext):
    if await handle_cancel(message, state):
        return

    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите корректную сумму", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")]
        ]))
        return

    await state.update_data(amount=amount)
    keyboard = [
        [types.InlineKeyboardButton(text="⏰ Сейчас", callback_data="now")],
        [types.InlineKeyboardButton(text="📅 Выбрать дату", callback_data="choose_date")],
        [types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")]
    ]

    await message.answer(f"💰 Сумма: {amount}\n\n⏰ Укажите дату транзакции:",
                         reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard))
    await state.set_state(IncomeStates.choosing_time_option)


@router.callback_query(IncomeStates.choosing_time_option)
async def choose_time_option(call: types.CallbackQuery, state: FSMContext):
    if await handle_cancel_callback(call, state):
        return

    if call.data == "now":
        tx_date = datetime.now()
        await state.update_data(tx_date=tx_date)
        await state.set_state(IncomeStates.entering_from_address)

        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")]
        ])

        await call.message.edit_text(
            f"✅ Текущая дата: {tx_date.strftime('%d.%m.%Y %H:%M')}\n\nВведите адрес отправителя:",
            reply_markup=keyboard)

    elif call.data == "choose_date":
        await state.set_state(IncomeStates.choosing_day)
        today = datetime.now()
        month_name = today.strftime("%B")
        await call.message.edit_text(f"📅 Выберите день ({month_name} {today.year}):\n\n📍 - сегодняшний день",
                                     reply_markup=month_days_keyboard())

    await call.answer()


@router.callback_query(lambda c: c.data.startswith("day_"))
async def choose_day_callback(call: types.CallbackQuery, state: FSMContext):
    if await handle_cancel_callback(call, state):
        return

    day_data = call.data.replace("day_", "")
    today = datetime.now()

    if day_data == "today":
        selected_day = today.day
        base_date = today
    elif day_data == "tomorrow":
        base_date = today + timedelta(days=1)
        selected_day = base_date.day
    elif day_data == "after_tomorrow":
        base_date = today + timedelta(days=2)
        selected_day = base_date.day
    else:
        selected_day = int(day_data)
        base_date = datetime(today.year, today.month, selected_day)

    await state.update_data(selected_day=selected_day, base_date=base_date.strftime("%Y-%m-%d"))
    await state.set_state(IncomeStates.entering_time)

    keyboard = [
        [types.InlineKeyboardButton(text="⏰ Сейчас", callback_data="now_time")],
        [types.InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")]
    ]

    await call.message.edit_text(
        f"📅 День: {selected_day}\n\n⏰ Введите время в формате **ЧЧ ММ** (например: 14 30)\nИли просто **ЧЧ** (например: 9 → будет 09:00)\nИли **ЧЧ:ММ** (например: 14:30)\n\n*Часы: 0-23, минуты: 0-59*\n\nМожете нажать **«Сейчас»** для текущего времени",
        parse_mode="Markdown",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await call.answer()


@router.callback_query(IncomeStates.entering_time)
async def handle_now_in_entering_time(call: types.CallbackQuery, state: FSMContext):
    if await handle_cancel_callback(call, state):
        return

    if call.data == "now_time":
        tx_date = datetime.now()
        await state.update_data(tx_date=tx_date)
        await state.set_state(IncomeStates.entering_from_address)

        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")]
        ])

        await call.message.edit_text(
            f"✅ Текущая дата: {tx_date.strftime('%d.%m.%Y %H:%M')}\n\nВведите адрес отправителя:",
            reply_markup=keyboard)
        await call.answer()


@router.message(IncomeStates.entering_time)
async def entering_time(message: types.Message, state: FSMContext):
    if await handle_cancel(message, state):
        return

    time_data = parse_time_input(message.text)

    if not time_data:
        await message.answer(
            "❌ Неверный формат времени.\n\nИспользуйте:\n• **14 30** (часы и минуты через пробел)\n• **9** (только часы, минуты будут 00)\n• **14:30** (через двоеточие)\n\n*Часы: 0-23, минуты: 0-59*",
            parse_mode="Markdown",
            reply_markup=time_cancel_keyboard()
        )
        return

    hour, minute = time_data
    data = await state.get_data()
    base_date_str = data.get('base_date')

    if not base_date_str:
        today = datetime.now()
        tx_date = datetime(today.year, today.month, today.day, hour, minute)
    else:
        base_date = datetime.strptime(base_date_str, "%Y-%m-%d")
        tx_date = datetime(base_date.year, base_date.month, base_date.day, hour, minute)

    await state.update_data(tx_date=tx_date)
    await state.set_state(IncomeStates.entering_from_address)

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")]
    ])

    await message.answer(f"✅ Дата установлена: {tx_date.strftime('%d.%m.%Y %H:%M')}\n\nВведите адрес отправителя:",
                         reply_markup=keyboard)


@router.callback_query(lambda c: c.data in ["skip", "cancel"])
async def handle_skip_callback(call: types.CallbackQuery, state: FSMContext):
    if await handle_cancel_callback(call, state):
        return

    current_state = await state.get_state()

    if call.data == "skip":
        if current_state == IncomeStates.entering_tx_hash:
            tx_hash = generate_tx_hash()
            await state.update_data(tx_hash=tx_hash)
            await state.set_state(IncomeStates.entering_fee)
            await call.message.edit_text(f"✅ Сгенерирован хеш: `{tx_hash[:20]}...`\n\n💰 Комиссия сети:",
                                         parse_mode="Markdown", reply_markup=skip_cancel_keyboard())
            await call.answer()

        elif current_state == IncomeStates.entering_fee:
            data = await state.get_data()
            token_symbol = data.get('token_symbol', 'eth')
            fee = generate_fee_for_token(token_symbol)
            await state.update_data(fee=fee)
            await state.set_state(IncomeStates.entering_explorer_link)
            await call.message.edit_text(f"✅ Сгенерирована комиссия: {fee}\n\n🌐 Ссылка на explorer:",
                                         parse_mode="Markdown", reply_markup=skip_cancel_keyboard())
            await call.answer()

        elif current_state == IncomeStates.entering_explorer_link:
            await finish_transaction(state=state, explorer_link=None, is_skip=True, call=call)
            await call.answer()


@router.message(IncomeStates.entering_from_address)
async def entering_from_address(message: types.Message, state: FSMContext):
    if await handle_cancel(message, state):
        return

    from_address = message.text.strip()
    if not from_address:
        await message.answer("Адрес не может быть пустым", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")]
        ]))
        return

    await state.update_data(from_address=from_address)
    await state.set_state(IncomeStates.entering_tx_hash)
    await message.answer("🔗 Хеш транзакции:\n\nВведите хеш или нажмите «Пропустить» для автоматической генерации",
                         reply_markup=skip_cancel_keyboard())


@router.message(IncomeStates.entering_tx_hash)
async def entering_tx_hash(message: types.Message, state: FSMContext):
    if await handle_cancel(message, state):
        return

    tx_hash = message.text.strip()
    if tx_hash.lower() == "пропустить":
        tx_hash = generate_tx_hash()
        await message.answer(f"✅ Сгенерирован хеш: `{tx_hash[:20]}...`", parse_mode="Markdown",
                             reply_markup=skip_cancel_keyboard())
    else:
        await message.answer("✅ Хеш принят!", reply_markup=skip_cancel_keyboard())

    await state.update_data(tx_hash=tx_hash)
    await state.set_state(IncomeStates.entering_fee)
    await message.answer("💰 Комиссия сети:\n\nВведите сумму комиссии или нажмите «Пропустить» для случайной генерации",
                         reply_markup=skip_cancel_keyboard())


@router.message(IncomeStates.entering_fee)
async def entering_fee(message: types.Message, state: FSMContext):
    if await handle_cancel(message, state):
        return

    text = message.text.strip().lower()

    if text == "пропустить":
        data = await state.get_data()
        token_symbol = data.get('token_symbol', 'eth')
        fee = generate_fee_for_token(token_symbol)
        await message.answer(f"✅ Сгенерирована комиссия: {fee}", reply_markup=skip_cancel_keyboard())
    else:
        try:
            fee = float(text)
            if fee < 0:
                raise ValueError
        except ValueError:
            await message.answer("❌ Введите корректное число", reply_markup=skip_cancel_keyboard())
            return

    await state.update_data(fee=fee)
    await state.set_state(IncomeStates.entering_explorer_link)
    await message.answer("🌐 Ссылка на explorer:\n\nВведите ссылку или нажмите «Пропустить»",
                         reply_markup=skip_cancel_keyboard())


@router.message(IncomeStates.entering_explorer_link)
async def finish_income(message: types.Message, state: FSMContext):
    if await handle_cancel(message, state):
        return

    explorer_link = None if message.text.strip().lower() == "пропустить" else message.text.strip()
    await finish_transaction(state=state, explorer_link=explorer_link, message=message)