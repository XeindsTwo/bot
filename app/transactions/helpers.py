from aiogram import types
from aiogram.fsm.context import FSMContext
from app.db import get_token_by_id, create_transaction, update_balance
from app.handlers.menus import main_menu
from app.transactions.utils import generate_tx_hash, generate_fee_for_token
from .states import IncomeStates

CANCEL_TEXT = "❌ Отменить создание"


async def handle_cancel_in_message(message: types.Message, state: FSMContext) -> bool:
    """Обработка отмены через сообщение (новая функция для router.py)"""
    if message.text and message.text.strip() == CANCEL_TEXT:
        await state.clear()
        await message.answer("Создание транзакции отменено", reply_markup=main_menu())
        return True
    return False


async def handle_cancel_callback(call: types.CallbackQuery, state: FSMContext) -> bool:
    """Обработка отмены через callback (старая функция)"""
    if call.data == "cancel":
        await state.clear()
        await call.message.edit_text("Создание транзакции отменено", reply_markup=main_menu())
        await call.answer()
        return True
    return False


async def handle_skip_in_message(message: types.Message, state: FSMContext) -> bool:
    """Обработка текста 'Пропустить' в сообщениях"""
    if message.text and message.text.strip().lower() == "пропустить":
        current_state = await state.get_state()
        data = await state.get_data()

        if current_state == IncomeStates.entering_tx_hash.state:
            # Генерируем хеш
            token_symbol = data.get('token_symbol', 'eth')

            # Определяем тип
            crypto_type = 'eth'
            if 'trx' in token_symbol.lower() or 'tron' in token_symbol.lower():
                crypto_type = 'tron'
            elif 'btc' in token_symbol.lower():
                crypto_type = 'btc'

            tx_hash = generate_tx_hash(crypto_type)
            await state.update_data(tx_hash=tx_hash)
            await state.set_state(IncomeStates.entering_fee)

            from .keyboards import skip_cancel_keyboard
            await message.answer(
                f"✅ Сгенерирован хеш: <code>{tx_hash[:20]}...</code>\n\n"
                f"💰 Комиссия сети для {token_symbol.upper()}:\n\n"
                f"Введите сумму комиссии или нажмите «Пропустить» для случайной генерации",
                parse_mode="HTML",
                reply_markup=skip_cancel_keyboard()
            )
            return True

        elif current_state == IncomeStates.entering_fee.state:
            # Генерируем комиссию
            token_symbol = data.get('token_symbol', 'eth')
            fee = generate_fee_for_token(token_symbol)

            await state.update_data(fee=fee)
            await state.set_state(IncomeStates.entering_explorer_link)

            from .keyboards import skip_cancel_keyboard
            await message.answer(
                f"✅ Сгенерирована комиссия: {fee:.4f}\n\n"
                f"🌐 Введите ссылку на explorer (или нажмите «Пропустить»):",
                reply_markup=skip_cancel_keyboard()
            )
            return True

        elif current_state == IncomeStates.entering_explorer_link.state:
            # Пропускаем explorer ссылку
            await finish_transaction(state=state, explorer_link=None, message=message)
            return True

    return False


async def finish_transaction(state: FSMContext, explorer_link: str = None, is_skip: bool = False,
                             call: types.CallbackQuery = None, message: types.Message = None):
    """Завершение создания транзакции"""
    data = await state.get_data()

    # Проверка обязательных полей
    required_fields = ['token_id', 'amount', 'tx_date', 'from_address', 'tx_hash', 'fee']
    for field in required_fields:
        if field not in data:
            error_msg = f"❌ Ошибка: отсутствует поле {field}"
            if message:
                await message.answer(error_msg)
            elif call:
                await call.message.answer(error_msg)
            await state.clear()
            return False

    token = get_token_by_id(data["token_id"])
    if not token:
        error_msg = "❌ Токен не найден"
        if message:
            await message.answer(error_msg)
        elif call:
            await call.message.answer(error_msg)
        await state.clear()
        return False

    token_id, symbol, name, enabled, address, balance, locked = token

    # Создаем транзакцию
    create_transaction(
        token=symbol,
        tx_type="income",
        amount=data['amount'],
        date=data['tx_date'].strftime("%Y-%m-%d %H:%M"),
        from_addr=data['from_address'],
        to_addr="",
        tx_hash=data['tx_hash'],
        fee=data['fee'],
        explorer_link=explorer_link
    )

    # Обновляем баланс (пополнение)
    update_balance(data["token_id"], data["amount"])
    updated_token = get_token_by_id(data["token_id"])
    new_balance = updated_token[5] if updated_token else 0

    success_text = (
        f"✅ <b>Транзакция создана!</b>\n\n"
        f"<b>📊 Основные данные:</b>\n"
        f"• <b>Токен:</b> {name}\n"
        f"• <b>Сумма:</b> {data['amount']:.4f}\n"
        f"• <b>Комиссия сети:</b> {data.get('fee', 0):.4f}\n"
        f"• <b>Дата:</b> {data['tx_date'].strftime('%d.%m.%Y %H:%M')}\n"
        f"• <b>Новый баланс:</b> {new_balance:.4f}\n\n"

        f"<b>🔗 Блокчейн данные:</b>\n"
        f"• <b>Отправитель:</b>\n<code>{data['from_address']}</code>\n"
        f"• <b>Хеш транзакции:</b>\n<code>{data['tx_hash']}</code>"
    )

    if explorer_link:
        success_text += f"\n\n• <b>Explorer:</b> {explorer_link}"

    if is_skip and call:
        await call.message.edit_text(success_text, parse_mode="HTML")
        await call.message.answer("🏠 Возвращаемся в главное меню:", reply_markup=main_menu())
    elif message:
        await message.answer(success_text, parse_mode="HTML", reply_markup=main_menu())
    elif call:
        await call.message.answer(success_text, parse_mode="HTML", reply_markup=main_menu())

    await state.clear()
    return True


# Оставляем старую функцию для совместимости (если где-то используется)
async def handle_cancel(message: types.Message, state: FSMContext) -> bool:
    """Старая функция, вызывает новую для совместимости"""
    return await handle_cancel_in_message(message, state)
