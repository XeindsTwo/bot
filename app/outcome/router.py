from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from app.db import get_tokens, get_token_by_id
from app.guards import is_owner
from app.handlers.menus import main_menu
from app.transactions.utils import generate_tx_hash, generate_fee_for_token, parse_time_input
from .states import OutcomeStates
from .keyboards import (
    tokens_keyboard_outcome, time_option_keyboard, skip_cancel_keyboard,
    month_days_keyboard, now_cancel_keyboard, time_cancel_keyboard,
    simple_cancel_keyboard, confirm_transaction_keyboard
)
from .helpers import (
    handle_cancel_outcome, handle_cancel_callback_outcome,
    finish_outcome_transaction, CANCEL_TEXT
)

router = Router()


@router.callback_query(lambda c: is_owner(c.from_user.id) and c.data == "outcome")
async def start_outcome(call: types.CallbackQuery, state: FSMContext):
    """Начало создания исходящей транзакции"""
    await state.clear()

    # Только токены с балансом > 0
    tokens = [t for t in get_tokens() if t[5] > 0 and t[3] == 1]

    if not tokens:
        await call.message.answer(
            "❌ Нет доступных токенов для отправки.\n"
            "Убедитесь, что:\n"
            "1. Токен включен (enabled)\n"
            "2. Баланс больше 0",
            reply_markup=main_menu()
        )
        await call.answer()
        return

    await state.set_state(OutcomeStates.choosing_token)
    await call.message.answer(
        "➖ Выберите токен для отправки:\n"
        "(показаны только токены с балансом > 0)",
        reply_markup=tokens_keyboard_outcome(tokens)
    )
    await call.answer()


@router.callback_query(OutcomeStates.choosing_token)
async def choose_token_callback(call: types.CallbackQuery, state: FSMContext):
    """Обработка выбора токена"""
    if await handle_cancel_callback_outcome(call, state):
        return

    if not call.data.startswith("outcome_token_"):
        return

    token_id = int(call.data.replace("outcome_token_", ""))
    token = get_token_by_id(token_id)

    if not token:
        await call.answer("❌ Токен не найден", show_alert=True)
        return

    token_id, symbol, name, enabled, address, balance, locked = token

    if balance <= 0:
        await call.answer("❌ Баланс токена равен 0", show_alert=True)
        return

    await state.update_data(
        token_id=token_id,
        token_name=name,
        token_symbol=symbol,
        wallet_address=address
    )
    await state.set_state(OutcomeStates.entering_amount)

    await call.message.edit_text(
        f"💰 <b>{name}</b>\n"
        f"Текущий баланс: <code>{balance:.4f}</code>\n\n"
        f"Введите сумму для отправки:",
        parse_mode="HTML",
        reply_markup=simple_cancel_keyboard()
    )
    await call.answer()


@router.message(OutcomeStates.entering_amount)
async def entering_amount(message: types.Message, state: FSMContext):
    """Ввод суммы отправки с проверкой баланса"""
    if await handle_cancel_outcome(message, state):
        return

    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Введите корректную положительную сумму",
            reply_markup=simple_cancel_keyboard()
        )
        return

    data = await state.get_data()
    token = get_token_by_id(data['token_id'])

    if not token:
        await state.clear()
        await message.answer("❌ Токен не найден", reply_markup=main_menu())
        return

    token_id, symbol, name, enabled, address, balance, locked = token

    if amount > balance:
        await message.answer(
            f"❌ Недостаточно средств!\n"
            f"Максимально можно отправить: {balance:.4f}",
            reply_markup=simple_cancel_keyboard()
        )
        return

    await state.update_data(amount=amount)
    await state.set_state(OutcomeStates.choosing_time_option)

    await message.answer(
        f"💰 Сумма: {amount:.4f}\n\n⏰ Укажите дату отправки:",
        reply_markup=time_option_keyboard()
    )


@router.callback_query(OutcomeStates.choosing_time_option)
async def choose_time_option(call: types.CallbackQuery, state: FSMContext):
    """Выбор опции времени (Сейчас или Выбрать дату)"""
    if await handle_cancel_callback_outcome(call, state):
        return

    if call.data == "now":
        tx_date = datetime.now()
        await state.update_data(tx_date=tx_date)
        await state.set_state(OutcomeStates.entering_to_address)

        await call.message.edit_text(
            f"✅ Текущая дата: {tx_date.strftime('%d.%m.%Y %H:%M')}\n\nВведите адрес получателя:",
            reply_markup=simple_cancel_keyboard()
        )

    elif call.data == "choose_date":
        await state.set_state(OutcomeStates.choosing_day)
        today = datetime.now()
        month_name = today.strftime("%B")
        await call.message.edit_text(
            f"📅 Выберите день ({month_name} {today.year}):\n\n📍 - сегодняшний день",
            reply_markup=month_days_keyboard()
        )

    await call.answer()


@router.callback_query(lambda c: c.data.startswith("outcome_day_"))
async def choose_day_callback(call: types.CallbackQuery, state: FSMContext):
    """Обработка выбора дня (из календаря или быстрых кнопок)"""
    if await handle_cancel_callback_outcome(call, state):
        return

    day_data = call.data.replace("outcome_day_", "")
    today = datetime.now()

    if day_data == "today":
        selected_day = today.day
        base_date = today
        year, month = today.year, today.month
    elif day_data == "tomorrow":
        base_date = today + timedelta(days=1)
        selected_day = base_date.day
        year, month = base_date.year, base_date.month
    elif day_data == "after_tomorrow":
        base_date = today + timedelta(days=2)
        selected_day = base_date.day
        year, month = base_date.year, base_date.month
    else:
        # Формат: year_month_day
        try:
            year_str, month_str, day_str = day_data.split("_")
            year = int(year_str)
            month = int(month_str)
            selected_day = int(day_str)
            base_date = datetime(year, month, selected_day)
        except:
            await call.answer("❌ Ошибка формата даты", show_alert=True)
            return

    await state.update_data(
        selected_day=selected_day,
        base_date=base_date.strftime("%Y-%m-%d"),
        selected_year=year,
        selected_month=month
    )
    await state.set_state(OutcomeStates.entering_time)

    await call.message.edit_text(
        f"📅 День: {selected_day}.{month}.{year}\n\n"
        f"⏰ Введите время в формате ЧЧ ММ (например: 14 30)\n"
        f"Или просто ЧЧ (например: 9 → будет 09:00)\n"
        f"Или ЧЧ:ММ (например: 14:30)\n\n"
        f"Часы: 0-23, минуты: 0-59\n\n"
        f"Можете нажать «Выбрать текущую дату» для выбора сегодняшней даты",
        reply_markup=now_cancel_keyboard()
    )
    await call.answer()


@router.callback_query(lambda c: c.data.startswith("outcome_month_"))
async def switch_month_callback(call: types.CallbackQuery, state: FSMContext):
    """Переключение месяцев в календаре"""
    if await handle_cancel_callback_outcome(call, state):
        return

    data = call.data.replace("outcome_month_", "")

    if data == "current":
        today = datetime.now()
        await call.message.edit_text(
            f"📅 Выберите день ({today.strftime('%B %Y')}):\n\n📍 - сегодняшний день",
            reply_markup=month_days_keyboard()
        )
    elif data.startswith("prev_") or data.startswith("next_"):
        try:
            # ИСПРАВЛЕННЫЙ ПАРСИНГ
            parts = data.split("_")
            direction = parts[0]  # "prev" или "next"
            year_str = parts[1]  # "2024"
            month_str = parts[2]  # "12"

            year = int(year_str)
            month = int(month_str)

            if direction == "prev":
                if month == 1:
                    month = 12
                    year -= 1
                else:
                    month -= 1
            else:  # "next"
                if month == 12:
                    month = 1
                    year += 1
                else:
                    month += 1

            await call.message.edit_text(
                f"📅 Выберите день ({datetime(year, month, 1).strftime('%B %Y')}):",
                reply_markup=month_days_keyboard(year, month)
            )
        except Exception as e:
            print(f"❌ Ошибка переключения месяца: {e}, data: {data}")
            await call.answer("❌ Ошибка переключения месяца", show_alert=True)

    await call.answer()


@router.callback_query(OutcomeStates.entering_time)
async def handle_now_in_entering_time(call: types.CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Сейчас' при вводе времени"""
    if await handle_cancel_callback_outcome(call, state):
        return

    if call.data == "now_time":
        tx_date = datetime.now()
        await state.update_data(tx_date=tx_date)
        await state.set_state(OutcomeStates.entering_to_address)

        await call.message.edit_text(
            f"✅ Текущая дата: {tx_date.strftime('%d.%m.%Y %H:%M')}\n\nВведите адрес получателя:",
            reply_markup=simple_cancel_keyboard()
        )
        await call.answer()


@router.message(OutcomeStates.entering_time)
async def entering_time(message: types.Message, state: FSMContext):
    """Ввод времени"""
    if await handle_cancel_outcome(message, state):
        return

    time_data = parse_time_input(message.text)

    if not time_data:
        await message.answer(
            "❌ Неверный формат времени.\n\nИспользуйте:\n"
            "• 14 30 (часы и минуты через пробел)\n"
            "• 9 (только часы, минуты будут 00)\n"
            "• 14:30 (через двоеточие)\n\n"
            "Часы: 0-23, минуты: 0-59",
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
    await state.set_state(OutcomeStates.entering_to_address)

    await message.answer(
        f"✅ Дата установлена: {tx_date.strftime('%d.%m.%Y %H:%M')}\n\nВведите адрес получателя:",
        reply_markup=simple_cancel_keyboard()
    )


@router.message(OutcomeStates.entering_to_address)
async def entering_to_address(message: types.Message, state: FSMContext):
    """Ввод адреса получателя с валидацией"""
    if await handle_cancel_outcome(message, state):
        return

    to_address = message.text.strip()

    if not to_address:
        await message.answer(
            "❌ Адрес не может быть пустым",
            reply_markup=simple_cancel_keyboard()
        )
        return

    from .utils import validate_crypto_address
    is_valid, error_message = validate_crypto_address(to_address)

    if not is_valid:
        error_text = f"❌ Неверный формат адреса!\n\n{error_message}\n\n"

        # Добавляем подсказку в зависимости от типа адреса
        if to_address.startswith('0x') and len(to_address) < 42:
            error_text += f"💡 Ethereum/BSC адрес должен быть 42 символа.\nПример: 0x742d35Cc6634C0532925a3b844Bc9e..."
        elif to_address.startswith('0x') and len(to_address) > 42:
            error_text += f"💡 Ethereum/BSC адрес должен быть ровно 42 символа."
        elif 'l' in to_address.lower() or 'o' in to_address.lower() or 'i' in to_address.lower():
            error_text += "💡 В крипто-адресах используются только цифры 0-9 и буквы a-f (A-F).\nБуквы i, I, l, L, o, O не используются."

        error_text += "\n\nВведите корректный адрес получателя:"

        await message.answer(
            error_text,
            reply_markup=simple_cancel_keyboard()
        )
        return

    # Проверка, что не отправляем на свой адрес
    data = await state.get_data()
    wallet_address = data.get('wallet_address', '')

    if to_address.lower() == wallet_address.lower():
        await message.answer(
            "❌ Нельзя отправлять на собственный адрес кошелька!\n"
            "Введите адрес получателя:",
            reply_markup=simple_cancel_keyboard()
        )
        return

    await state.update_data(to_address=to_address)
    await state.set_state(OutcomeStates.entering_tx_hash)

    await message.answer(
        "✅ Адрес принят!\n\n"
        "🔗 Хеш транзакции:\n\n"
        "Введите хеш транзакции или нажмите «Пропустить» для автоматической генерации",
        reply_markup=skip_cancel_keyboard()
    )


@router.message(OutcomeStates.entering_tx_hash)
async def entering_tx_hash(message: types.Message, state: FSMContext):
    """Ввод хеша транзакции"""
    if await handle_cancel_outcome(message, state):
        return

    tx_hash = message.text.strip()

    if tx_hash.lower() == "пропустить":
        tx_hash = generate_tx_hash()
        # ИСПРАВЛЕНО: Используем HTML вместо Markdown
        await message.answer(
            f"✅ Сгенерирован хеш: <code>{tx_hash[:20]}...</code>",
            parse_mode="HTML",  # ← ИСПРАВЛЕНО НА HTML
            reply_markup=skip_cancel_keyboard()
        )
    else:
        await message.answer(
            "✅ Хеш принят!",
            reply_markup=skip_cancel_keyboard()
        )

    await state.update_data(tx_hash=tx_hash)
    await state.set_state(OutcomeStates.entering_fee)

    data = await state.get_data()
    token_symbol = data.get('token_symbol', 'eth')

    await message.answer(
        f"💰 Комиссия сети для {token_symbol.upper()}:\n\n"
        f"Введите сумму комиссии или нажмите «Пропустить» для случайной генерации",
        reply_markup=skip_cancel_keyboard()
    )


@router.message(OutcomeStates.entering_fee)
async def entering_fee(message: types.Message, state: FSMContext):
    """Ввод комиссии и переход к подтверждению"""
    if await handle_cancel_outcome(message, state):
        return

    data = await state.get_data()
    token = get_token_by_id(data['token_id'])

    if not token:
        await state.clear()
        await message.answer("❌ Токен не найден", reply_markup=main_menu())
        return

    token_id, symbol, name, enabled, address, balance, locked = token

    text = message.text.strip().lower()

    if text == "пропустить":
        token_symbol = data.get('token_symbol', 'eth')
        fee = generate_fee_for_token(token_symbol)
        await message.answer(
            f"✅ Сгенерирована комиссия: {fee:.4f}",
            reply_markup=skip_cancel_keyboard()
        )
    else:
        try:
            fee = float(text.replace(",", "."))
            if fee < 0:
                raise ValueError
        except ValueError:
            await message.answer(
                "❌ Введите корректное положительное число",
                reply_markup=skip_cancel_keyboard()
            )
            return

    amount = data['amount']
    total_required = amount + fee

    # Проверяем, хватает ли средств
    if total_required > balance:
        # ПРЕДЛАГАЕМ АЛЬТЕРНАТИВУ
        max_amount = balance - fee

        if max_amount <= 0:
            await message.answer(
                f"❌ Недостаточно средств даже для комиссии!\n"
                f"Баланс: {balance:.4f}\n"
                f"Комиссия: {fee:.4f}\n"
                f"Максимально можно отправить: 0",
                reply_markup=skip_cancel_keyboard()
            )
            return

        await state.update_data(fee=fee, max_amount=max_amount)
        await state.set_state(OutcomeStates.confirming_transaction)

        # Формируем предложение
        confirmation_text = (
            f"⚠️ <b>Недостаточно средств для отправки {amount:.4f}</b>\n\n"
            f"• Текущий баланс: <code>{balance:.4f}</code>\n"
            f"• Комиссия сети: <code>{fee:.4f}</code>\n"
            f"• Нужно всего: <code>{total_required:.4f}</code>\n\n"
            f"💡 <b>Можно отправить максимум: <code>{max_amount:.4f}</code></b>\n"
            f"(баланс {balance:.4f} - комиссия {fee:.4f})\n\n"
            f"📝 <b>Детали отправки:</b>\n"
            f"• Сумма отправки: <code>{max_amount:.4f}</code>\n"
            f"• Комиссия: <code>{fee:.4f}</code>\n"
            f"• Итого списано: <code>{balance:.4f}</code>\n"
            f"• Остаток: <code>0</code>\n\n"
            f"Подтвердить создание транзакции?"
        )

        await message.answer(
            confirmation_text,
            parse_mode="HTML",
            reply_markup=confirm_transaction_keyboard()
        )
        return

    # Если средств хватает — показываем подтверждение
    await state.update_data(fee=fee)
    await state.set_state(OutcomeStates.confirming_transaction)

    confirmation_text = (
        f"✅ <b>Средств достаточно!</b>\n\n"
        f"📊 <b>Детали транзакции:</b>\n"
        f"• Токен: {name}\n"
        f"• Сумма отправки: <code>{amount:.4f}</code>\n"
        f"• Комиссия сети: <code>{fee:.4f}</code>\n"
        f"• Итого списано: <code>{total_required:.4f}</code>\n"
        f"• Баланс до: <code>{balance:.4f}</code>\n"
        f"• Баланс после: <code>{balance - total_required:.4f}</code>\n"
        f"• Получатель: <code>{data.get('to_address', '')[:20]}...</code>\n"
        f"• Дата: {data.get('tx_date', datetime.now()).strftime('%d.%m.%Y %H:%M')}\n\n"
        f"<b>Подтвердить создание транзакции?</b>"
    )

    await message.answer(
        confirmation_text,
        parse_mode="HTML",
        reply_markup=confirm_transaction_keyboard()
    )


@router.callback_query(OutcomeStates.confirming_transaction)
async def handle_confirmation(call: types.CallbackQuery, state: FSMContext):
    """Обработка подтверждения транзакции"""
    if call.data == "cancel_tx":
        await state.clear()
        await call.message.edit_text(
            "❌ Создание транзакции отменено",
            reply_markup=main_menu()
        )
        await call.answer()
        return

    elif call.data == "confirm_tx":
        data = await state.get_data()

        # Если пользователь выбрал отправку максимума
        if 'max_amount' in data and data['max_amount'] < data['amount']:
            # Обновляем сумму на максимально возможную
            await state.update_data(amount=data['max_amount'])

        # Завершаем транзакцию
        await finish_outcome_transaction(state=state, call=call)
        await call.answer()


@router.callback_query(lambda c: c.data == "skip_outcome")
async def handle_skip_outcome(call: types.CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Пропустить'"""
    current_state = await state.get_state()

    if current_state == OutcomeStates.entering_tx_hash.state:
        tx_hash = generate_tx_hash()
        await state.update_data(tx_hash=tx_hash)
        await state.set_state(OutcomeStates.entering_fee)

        data = await state.get_data()
        token_symbol = data.get('token_symbol', 'eth')

        # ИСПРАВЛЕНО: Убрал Markdown, используем HTML
        await call.message.edit_text(
            f"✅ Сгенерирован хеш: <code>{tx_hash[:20]}...</code>\n\n"
            f"💰 Комиссия сети для {token_symbol.upper()}:",
            parse_mode="HTML",  # ← ИСПРАВЛЕНО НА HTML
            reply_markup=skip_cancel_keyboard()
        )
        await call.answer()

    elif current_state == OutcomeStates.entering_fee.state:
        data = await state.get_data()
        token_symbol = data.get('token_symbol', 'eth')
        fee = generate_fee_for_token(token_symbol)

        await state.update_data(fee=fee)
        token = get_token_by_id(data['token_id'])

        if token:
            token_id, symbol, name, enabled, address, balance, locked = token
            amount = data['amount']
            total_required = amount + fee

            if total_required > balance:
                max_amount = balance - fee

                if max_amount <= 0:
                    await call.message.edit_text(
                        f"❌ Недостаточно средств даже для комиссии!\n"
                        f"Баланс: {balance:.4f}\nКомиссия: {fee:.4f}",
                        reply_markup=skip_cancel_keyboard()
                    )
                    return

                await state.update_data(max_amount=max_amount)
                await state.set_state(OutcomeStates.confirming_transaction)

                confirmation_text = (
                    f"⚠️ <b>Недостаточно средств для отправки {amount:.4f}</b>\n\n"
                    f"• Текущий баланс: <code>{balance:.4f}</code>\n"
                    f"• Комиссия сети: <code>{fee:.4f}</code>\n"
                    f"• Нужно всего: <code>{total_required:.4f}</code>\n\n"
                    f"💡 <b>Можно отправить максимум: <code>{max_amount:.4f}</code></b>\n\n"
                    f"Подтвердить отправку {max_amount:.4f}?"
                )

                await call.message.edit_text(
                    confirmation_text,
                    parse_mode="HTML",
                    reply_markup=confirm_transaction_keyboard()
                )
            else:
                await state.set_state(OutcomeStates.confirming_transaction)

                confirmation_text = (
                    f"✅ <b>Детали транзакции:</b>\n\n"
                    f"• Сумма: <code>{amount:.4f}</code>\n"
                    f"• Комиссия: <code>{fee:.4f}</code>\n"
                    f"• Итого: <code>{total_required:.4f}</code>\n"
                    f"• Баланс после: <code>{balance - total_required:.4f}</code>\n\n"
                    f"<b>Подтвердить?</b>"
                )

                await call.message.edit_text(
                    confirmation_text,
                    parse_mode="HTML",
                    reply_markup=confirm_transaction_keyboard()
                )

        await call.answer()
