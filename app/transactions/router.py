from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from app.db import get_tokens
from app.guards import is_owner
from app.handlers.menus import main_menu
from .states import IncomeStates
from .keyboards import (
    tokens_keyboard, skip_cancel_keyboard, month_days_keyboard,
    time_cancel_keyboard, back_cancel_keyboard, now_cancel_keyboard
)
from .helpers import (
    handle_cancel, handle_cancel_callback, handle_back_callback,
    finish_transaction, CANCEL_TEXT
)
from .utils import (
    validate_crypto_address, generate_tx_hash, generate_fee_for_token,
    parse_time_input, get_crypto_type_from_symbol
)

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

    await state.update_data(
        token_id=token[0],
        token_name=str(token[2]),
        token_symbol=token[1]
    )
    await state.set_state(IncomeStates.entering_amount)

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")]
    ])

    await call.message.edit_text("💰 Введите сумму:", reply_markup=keyboard)
    await call.answer()


@router.message(IncomeStates.entering_amount)
async def entering_amount(message: types.Message, state: FSMContext):
    if await handle_cancel(message, state):
        return

    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0")
            return
    except ValueError:
        await message.answer("❌ Введите корректную сумму (например: 100.5)")
        return

    await state.update_data(amount=amount)

    keyboard = [
        [types.InlineKeyboardButton(text="⏰ Сейчас", callback_data="now")],
        [types.InlineKeyboardButton(text="📅 Выбрать дату", callback_data="choose_date")],
        [types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")]
    ]

    await message.answer(
        f"✅ Сумма: {amount}\n\n"
        f"⏰ Укажите дату транзакции:",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(IncomeStates.choosing_time_option)


@router.callback_query(IncomeStates.choosing_time_option)
async def choose_time_option(call: types.CallbackQuery, state: FSMContext):
    if await handle_cancel_callback(call, state):
        return

    if call.data == "now":
        tx_date = datetime.now()
        await state.update_data(tx_date=tx_date)
        await state.set_state(IncomeStates.entering_from_address)

        await call.message.edit_text(
            f"✅ Текущая дата: {tx_date.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"👤 Введите адрес отправителя:",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")]
            ])
        )

    elif call.data == "choose_date":
        await state.set_state(IncomeStates.choosing_day)
        today = datetime.now()
        month_name = today.strftime("%B")

        await call.message.edit_text(
            f"📅 Выберите день ({month_name} {today.year}):\n\n"
            f"📍 - сегодняшний день\n"
            f"🔸 - будущая дата",
            reply_markup=month_days_keyboard()
        )

    await call.answer()


@router.callback_query(lambda c: c.data.startswith("prev_month_") or c.data.startswith("next_month_"))
async def handle_month_navigation(call: types.CallbackQuery, state: FSMContext):
    if await handle_cancel_callback(call, state):
        return

    parts = call.data.split("_")
    year = int(parts[2])
    month = int(parts[3])

    month_names = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    month_name = month_names[month - 1]

    await call.message.edit_text(
        f"📅 Выберите день ({month_name} {year}):\n\n"
        f"📍 - сегодняшний день\n"
        f"🔸 - будущая дата",
        reply_markup=month_days_keyboard(year, month)
    )
    await call.answer()


@router.callback_query(lambda c: c.data.startswith("day_"))
async def handle_day_selection(call: types.CallbackQuery, state: FSMContext):
    if await handle_cancel_callback(call, state):
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
        # Формат: day_2024_12_17
        parts = day_data.split("_")
        if len(parts) == 3:
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            selected_date = datetime(year, month, day)
        else:
            # Старый формат (только день)
            selected_day = int(day_data)
            selected_date = datetime(today.year, today.month, selected_day)

    # Сохраняем дату
    await state.update_data(
        selected_date=selected_date,
        base_date=selected_date.strftime("%Y-%m-%d")
    )

    # Переходим к выбору времени
    await state.set_state(IncomeStates.entering_time)

    month_names = [
        "Января", "Февраля", "Марта", "Апреля", "Мая", "Июня",
        "Июля", "Августа", "Сентября", "Октября", "Ноября", "Декабря"
    ]

    await call.message.edit_text(
        f"📅 Выбрана дата: {selected_date.day} {month_names[selected_date.month - 1]} {selected_date.year}\n\n"
        f"⏰ Введите время:\n\n"
        f"**Форматы:**\n"
        f"• ЧЧ ММ (например: 14 30)\n"
        f"• ЧЧ:ММ (например: 14:30)\n"
        f"• ЧЧ (например: 9 → будет 09:00)\n\n"
        f"*Часы: 0-23, минуты: 0-59*\n\n"
        f"Или нажмите **«Сейчас»** для текущего времени",
        parse_mode="Markdown",
        reply_markup=now_cancel_keyboard()
    )
    await call.answer()


@router.callback_query(IncomeStates.entering_time)
async def handle_now_time(call: types.CallbackQuery, state: FSMContext):
    if await handle_cancel_callback(call, state):
        return

    if call.data == "now_time":
        tx_date = datetime.now()
        await state.update_data(tx_date=tx_date)
        await state.set_state(IncomeStates.entering_from_address)

        await call.message.edit_text(
            f"✅ Текущая дата: {tx_date.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"👤 Введите адрес отправителя:",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")]
            ])
        )
        await call.answer()


@router.message(IncomeStates.entering_time)
async def entering_time(message: types.Message, state: FSMContext):
    if await handle_cancel(message, state):
        return

    time_data = parse_time_input(message.text)

    if not time_data:
        await message.answer(
            "❌ Неверный формат времени.\n\n"
            "**Используйте:**\n"
            "• **14 30** (часы и минуты через пробел)\n"
            "• **9** (только часы, минуты будут 00)\n"
            "• **14:30** (через двоеточие)\n\n"
            "*Часы: 0-23, минуты: 0-59*",
            parse_mode="Markdown",
            reply_markup=time_cancel_keyboard()
        )
        return

    hour, minute = time_data
    data = await state.get_data()
    base_date_str = data.get('base_date')
    selected_date = data.get('selected_date')

    if selected_date:
        # Используем уже выбранную дату
        tx_date = datetime(selected_date.year, selected_date.month, selected_date.day, hour, minute)
    elif base_date_str:
        # Старый формат с base_date
        base_date = datetime.strptime(base_date_str, "%Y-%m-%d")
        tx_date = datetime(base_date.year, base_date.month, base_date.day, hour, minute)
    else:
        # Используем сегодняшнюю дату
        today = datetime.now()
        tx_date = datetime(today.year, today.month, today.day, hour, minute)

    await state.update_data(tx_date=tx_date)
    await state.set_state(IncomeStates.entering_from_address)

    await message.answer(
        f"✅ Дата установлена: {tx_date.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"👤 Введите адрес отправителя:",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")]
        ])
    )


@router.message(IncomeStates.entering_from_address)
async def entering_from_address(message: types.Message, state: FSMContext):
    if await handle_cancel(message, state):
        return

    from_address = message.text.strip()

    if not from_address:
        await message.answer(
            "❌ Адрес не может быть пустым",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")]
            ])
        )
        return

    # Получаем данные для валидации
    data = await state.get_data()
    token_symbol = data.get('token_symbol', '')

    # Определяем тип крипты
    crypto_type = get_crypto_type_from_symbol(token_symbol)

    # Валидируем адрес
    is_valid, validation_message = validate_crypto_address(from_address, crypto_type)

    if not is_valid:
        # Формируем подробное сообщение об ошибке
        error_msg = f"{validation_message}\n\n"

        # Добавляем примеры в зависимости от типа
        if crypto_type == 'tron':
            error_msg += "**Пример TRON адреса:**\n"
            error_msg += "`TYASr5UV6HEcXatwdFQh7Hr8Zc6Jqqn9fF`\n\n"
        elif crypto_type == 'btc':
            error_msg += "**Пример BTC адреса:**\n"
            error_msg += "`1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa`\n"
            error_msg += "`3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy`\n"
            error_msg += "`bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq`\n\n"
        elif crypto_type == 'eth':
            error_msg += "**Пример ETH адреса:**\n"
            error_msg += "`0x742d35Cc6634C0532925a3b844Bc9e7b8c5F4F9a`\n\n"

        error_msg += "Введите корректный адрес отправителя:"

        await message.answer(error_msg, parse_mode="Markdown",
                             reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                                 [types.InlineKeyboardButton(text=CANCEL_TEXT, callback_data="cancel")]
                             ]))
        return

    # Адрес валиден
    await state.update_data(from_address=from_address)
    await state.set_state(IncomeStates.entering_tx_hash)

    # Определяем название поля в зависимости от типа
    hash_name = "TxHash" if crypto_type in ['eth', 'bnb'] else "TXID"

    await message.answer(
        f"✅ Адрес отправителя принят!\n\n"
        f"🔗 {hash_name} транзакции:\n\n"
        f"Введите хеш транзакции или нажмите «Пропустить» для автоматической генерации.\n\n"
        f"**Примеры:**\n"
        f"• `0x4a7c5c...` (для ETH/ERC20)\n"
        f"• `64 символа hex` (для TRON/BTC)",
        parse_mode="Markdown",
        reply_markup=skip_cancel_keyboard()
    )


@router.callback_query(lambda c: c.data in ["skip", "cancel", "back"])
async def handle_special_callbacks(call: types.CallbackQuery, state: FSMContext):
    # Обработка отмены
    if await handle_cancel_callback(call, state):
        return

    # Обработка кнопки Назад
    if await handle_back_callback(call, state):
        return

    current_state = await state.get_state()
    data = await state.get_data()

    if call.data == "skip":
        if current_state == IncomeStates.entering_tx_hash:
            # Пропуск хеша - генерация
            token_symbol = data.get('token_symbol', '')
            crypto_type = get_crypto_type_from_symbol(token_symbol)
            tx_hash = generate_tx_hash(crypto_type)

            await state.update_data(tx_hash=tx_hash)
            await state.set_state(IncomeStates.entering_fee)

            short_hash = tx_hash[:20] + "..." if len(tx_hash) > 20 else tx_hash
            await call.message.edit_text(
                f"✅ Сгенерирован хеш:\n`{short_hash}`\n\n"
                f"💰 Введите комиссию сети:",
                parse_mode="Markdown",
                reply_markup=skip_cancel_keyboard()
            )

        elif current_state == IncomeStates.entering_fee:
            # Пропуск комиссии - генерация
            token_symbol = data.get('token_symbol', 'eth')
            fee = generate_fee_for_token(token_symbol)

            await state.update_data(fee=fee)
            await state.set_state(IncomeStates.entering_explorer_link)

            await call.message.edit_text(
                f"✅ Сгенерирована комиссия: {fee}\n\n"
                f"🌐 Введите ссылку на explorer:",
                reply_markup=skip_cancel_keyboard()
            )

        elif current_state == IncomeStates.entering_explorer_link:
            # Пропуск explorer ссылки - завершение
            await finish_transaction(
                state=state,
                explorer_link=None,
                is_skip=True,
                call=call
            )

    await call.answer()


@router.message(IncomeStates.entering_tx_hash)
async def entering_tx_hash(message: types.Message, state: FSMContext):
    if await handle_cancel(message, state):
        return

    tx_hash = message.text.strip()

    if not tx_hash:
        await message.answer(
            "❌ Хеш не может быть пустым",
            reply_markup=skip_cancel_keyboard()
        )
        return

    # Базовая проверка хеша
    if len(tx_hash) < 10:
        await message.answer(
            "❌ Хеш слишком короткий. Минимальная длина 10 символов.",
            reply_markup=skip_cancel_keyboard()
        )
        return

    await state.update_data(tx_hash=tx_hash)
    await state.set_state(IncomeStates.entering_fee)

    await message.answer(
        f"✅ Хеш принят: `{tx_hash[:30]}...`\n\n"
        f"💰 Введите комиссию сети:",
        parse_mode="Markdown",
        reply_markup=skip_cancel_keyboard()
    )


@router.message(IncomeStates.entering_fee)
async def entering_fee(message: types.Message, state: FSMContext):
    if await handle_cancel(message, state):
        return

    text = message.text.strip().lower()

    if text == "пропустить":
        data = await state.get_data()
        token_symbol = data.get('token_symbol', 'eth')
        fee = generate_fee_for_token(token_symbol)
        fee_text = f"✅ Сгенерирована комиссия: {fee}"
    else:
        try:
            fee = float(text.replace(",", "."))
            if fee < 0:
                await message.answer(
                    "❌ Комиссия не может быть отрицательной",
                    reply_markup=skip_cancel_keyboard()
                )
                return
            fee_text = f"✅ Комиссия установлена: {fee}"
        except ValueError:
            await message.answer(
                "❌ Введите корректное число (например: 0.001 или 1.5)",
                reply_markup=skip_cancel_keyboard()
            )
            return

    await state.update_data(fee=fee)
    await state.set_state(IncomeStates.entering_explorer_link)

    await message.answer(
        f"{fee_text}\n\n"
        f"🌐 Введите ссылку на explorer (или нажмите «Пропустить»):",
        reply_markup=skip_cancel_keyboard()
    )


@router.message(IncomeStates.entering_explorer_link)
async def finish_income(message: types.Message, state: FSMContext):
    if await handle_cancel(message, state):
        return

    explorer_link = None
    if message.text.strip().lower() != "пропустить":
        explorer_link = message.text.strip()
        # Базовая проверка ссылки
        if not (explorer_link.startswith('http://') or explorer_link.startswith('https://')):
            await message.answer(
                "❌ Ссылка должна начинаться с http:// или https://",
                reply_markup=skip_cancel_keyboard()
            )
            return

    await finish_transaction(
        state=state,
        explorer_link=explorer_link,
        message=message
    )


@router.callback_query(lambda c: c.data == "ignore")
async def handle_ignore(call: types.CallbackQuery):
    """Игнорируем нажатия на пустые кнопки"""
    await call.answer()