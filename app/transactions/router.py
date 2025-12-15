from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from datetime import datetime
from app.db import get_tokens
from app.guards import is_owner
from app.handlers.menus import main_menu
from app.transactions.utils import generate_tx_hash, generate_fee, parse_date_input
from .states import IncomeStates
from .keyboards import tokens_keyboard, skip_cancel_keyboard, now_cancel_keyboard
from .helpers import handle_cancel, handle_cancel_callback, finish_transaction

router = Router()


# ========== КОЛБЭКИ ДЛЯ FSM ==========

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

    # Сохраняем ВСЕ данные токена
    await state.update_data(
        token_id=token[0],
        token_name=str(token[2]),
        token_symbol=token[1]  # <-- ДОБАВЛЯЕМ СИМВОЛ ТОКЕНА
    )
    await state.set_state(IncomeStates.entering_amount)

    await call.message.edit_text("Введите сумму:")
    await call.answer()


# ========== FSM ОБРАБОТЧИКИ СООБЩЕНИЙ ==========

@router.message(IncomeStates.entering_amount)
async def entering_amount(message: types.Message, state: FSMContext):
    if await handle_cancel(message, state):
        return

    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите корректную сумму (число больше нуля)")
        return

    await state.update_data(amount=amount)
    await state.set_state(IncomeStates.entering_date)
    await message.answer(
        "📅 Дата транзакции:\n\nНапишите дату в формате `ГГГГ-ММ-ДД ЧЧ:ММ` (например, 2025-12-15 14:30) или нажмите кнопку «Сейчас»",
        reply_markup=now_cancel_keyboard())


@router.callback_query(lambda c: c.data in ["now", "skip", "cancel"])
async def handle_date_callback(call: types.CallbackQuery, state: FSMContext):
    if await handle_cancel_callback(call, state):
        return

    current_state = await state.get_state()

    if call.data == "now":
        tx_date = datetime.now()
        await state.update_data(tx_date=tx_date)
        await state.set_state(IncomeStates.entering_from_address)
        await call.message.edit_text("Введите адрес отправителя:")
        await call.answer()



    elif call.data == "skip":

        if current_state == IncomeStates.entering_fee:
            # Получаем данные чтобы узнать токен

            data = await state.get_data()

            token_symbol = data.get('token_symbol', 'eth')

            # Генерируем правильную комиссию

            from app.transactions.utils import generate_fee_for_token

            fee = generate_fee_for_token(token_symbol)

            await state.update_data(fee=fee)

            await state.set_state(IncomeStates.entering_explorer_link)

            await call.message.edit_text(

                f"✅ Сгенерирована комиссия: {fee}\n\n🌐 Ссылка на explorer:",

                parse_mode="Markdown"

            )

            await call.answer()


@router.message(IncomeStates.entering_date)
async def entering_date(message: types.Message, state: FSMContext):
    if await handle_cancel(message, state):
        return

    tx_date = parse_date_input(message.text)
    if not tx_date:
        await message.answer("❌ Неверный формат даты.\nИспользуйте: `ГГГГ-ММ-ДД ЧЧ:ММ` (например, 2025-12-15 14:30)")
        return

    await state.update_data(tx_date=tx_date)
    await state.set_state(IncomeStates.entering_from_address)
    await message.answer("Введите адрес отправителя:")


@router.message(IncomeStates.entering_from_address)
async def entering_from_address(message: types.Message, state: FSMContext):
    if await handle_cancel(message, state):
        return

    from_address = message.text.strip()
    if not from_address:
        await message.answer("Адрес не может быть пустым")
        return

    await state.update_data(from_address=from_address)
    await state.set_state(IncomeStates.entering_tx_hash)
    await message.answer("🔗 Хеш транзакции:\n\nВведите хеш или напишите «пропустить» для автоматической генерации",
                         reply_markup=skip_cancel_keyboard())


@router.message(IncomeStates.entering_tx_hash)
async def entering_tx_hash(message: types.Message, state: FSMContext):
    if await handle_cancel(message, state):
        return

    tx_hash = message.text.strip()
    if tx_hash.lower() == "пропустить":
        tx_hash = generate_tx_hash()
        await message.answer(f"✅ Сгенерирован хеш: `{tx_hash[:20]}...`", parse_mode="Markdown")

    await state.update_data(tx_hash=tx_hash)
    await state.set_state(IncomeStates.entering_fee)
    await message.answer("💰 Комиссия сети:\n\nВведите сумму комиссии или «пропустить» для случайной генерации",
                         reply_markup=skip_cancel_keyboard())


@router.message(IncomeStates.entering_fee)
async def entering_fee(message: types.Message, state: FSMContext):
    if await handle_cancel(message, state):
        return

    text = message.text.strip().lower()

    if text == "пропустить":
        # символ токена из состояния
        data = await state.get_data()
        token_symbol = data.get('token_symbol', 'eth')  # по дефолту ETH

        # реалистичная комиссия для этого токена
        from app.transactions.utils import generate_fee_for_token
        fee = generate_fee_for_token(token_symbol)

        await message.answer(f"✅ Сгенерирована комиссия: {fee}")
    else:
        try:
            fee = float(text)
            if fee < 0:
                raise ValueError
        except ValueError:
            await message.answer("❌ Введите корректное число (больше или равно 0)")
            return

    await state.update_data(fee=fee)
    await state.set_state(IncomeStates.entering_explorer_link)
    await message.answer("🌐 Ссылка на explorer (например, etherscan.io):\n\nВведите ссылку или «пропустить»",
                         reply_markup=skip_cancel_keyboard())


@router.message(IncomeStates.entering_explorer_link)
async def finish_income(message: types.Message, state: FSMContext):
    if await handle_cancel(message, state):
        return

    explorer_link = None if message.text.strip().lower() == "пропустить" else message.text.strip()

    await finish_transaction(
        state=state,
        explorer_link=explorer_link,
        message=message
    )
