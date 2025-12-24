from aiogram import types
from aiogram.fsm.context import FSMContext
from app.db import get_token_by_id, create_transaction, update_balance
from app.handlers.menus import main_menu
from app.transactions.utils import generate_tx_hash, generate_fee_for_token
from .states import IncomeStates

CANCEL_TEXT = "❌ Отменить создание"


async def handle_cancel_in_message(message: types.Message, state: FSMContext) -> bool:
    """Обработка отмены через сообщение"""
    if message.text and message.text.strip() == CANCEL_TEXT:
        await state.clear()
        await message.answer("Создание транзакции отменено", reply_markup=main_menu())
        return True
    return False


async def handle_cancel_callback(call: types.CallbackQuery, state: FSMContext) -> bool:
    """Обработка отмены через callback"""
    if call.data == "cancel":
        await state.clear()
        await call.message.edit_text("Создание транзакции отменено", reply_markup=main_menu())
        await call.answer()
        return True
    return False


async def handle_skip_in_message(message: types.Message, state: FSMContext) -> bool:
    """Обработка текста 'Пропустить'"""
    if message.text and message.text.strip().lower() == "пропустить":
        current_state = await state.get_state()
        data = await state.get_data()

        if current_state == IncomeStates.entering_tx_hash.state:
            token_symbol = data.get('token_symbol', 'eth')
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
                f"💰 Комиссия сети (в USD):\n\n"
                f"Введите сумму комиссии или нажмите «Пропустить»",
                parse_mode="HTML",
                reply_markup=skip_cancel_keyboard()
            )
            return True

        elif current_state == IncomeStates.entering_fee.state:
            token_symbol = data.get('token_symbol', 'eth')
            fee_usd = generate_fee_for_token(token_symbol)  # Генерируем USD

            await state.update_data(fee_usd=fee_usd)  # Сохраняем как USD
            await state.set_state(IncomeStates.entering_explorer_link)

            from .keyboards import skip_cancel_keyboard
            await message.answer(
                f"✅ Сгенерирована комиссия: ${fee_usd:.2f} USD\n\n"
                f"🌐 Введите ссылку на explorer (или нажмите «Пропустить»):",
                reply_markup=skip_cancel_keyboard()
            )
            return True

        elif current_state == IncomeStates.entering_explorer_link.state:
            await finish_transaction(state=state, explorer_link=None, message=message)
            return True

    return False


async def finish_transaction(state: FSMContext, explorer_link: str = None, is_skip: bool = False,
                             call: types.CallbackQuery = None, message: types.Message = None):
    """Завершение создания транзакции - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    data = await state.get_data()

    # Проверка обязательных полей
    required_fields = ['token_id', 'amount', 'tx_date', 'from_address', 'tx_hash']
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

    token_id, symbol, name, enabled, address, balance, locked = token[:7]

    # Цены токенов для конвертации USD → токен
    token_prices = {
        'btc': 87000,
        'eth': 3500,
        'bnb': 600,
        'matic': 0.8,
        'tron': 0.12,
        'sol': 150,
        'ton': 5,
        'twt': 1.5,
        'usdt_erc20': 1,
        'usdt_bep20': 1,
        'usdt_trc20': 1,
        'pol': 0.8
    }

    token_price = token_prices.get(symbol.lower(), 1.0)

    # Получаем данные
    amount_usd = data['amount']  # USD сумма (пользователь вводил в USD)
    fee_usd = data.get('fee_usd', 0)  # USD комиссия (теперь отдельное поле)

    # Конвертируем fee USD в токены для хранения в БД
    if token_price > 0 and fee_usd > 0:
        fee_in_token = fee_usd / token_price
    else:
        fee_in_token = fee_usd

    # Создаем транзакцию
    create_transaction(
        token=symbol,
        tx_type="income",
        amount=amount_usd,  # USD сумма
        date=data['tx_date'].strftime("%Y-%m-%d %H:%M"),
        from_addr=data['from_address'],
        to_addr=address,  # Наш адрес
        tx_hash=data['tx_hash'],
        fee=fee_in_token,  # Теперь в валюте токена! (например 0.000086 BTC)
        explorer_link=explorer_link
    )

    # Обновляем баланс (пополнение) - amount_usd в USD
    update_balance(token_id, amount_usd)
    updated_token = get_token_by_id(token_id)
    new_balance = updated_token[5] if updated_token else 0

    # Форматируем fee для отображения
    if fee_in_token > 0:
        if token_price > 0:
            fee_display = f"{fee_in_token:.8f} {symbol.upper()} (${fee_usd:.2f})"
        else:
            fee_display = f"{fee_in_token:.4f} {symbol.upper()}"
    else:
        fee_display = "0"

    success_text = (
        f"✅ <b>Транзакция создана!</b>\n\n"
        f"<b>📊 Основные данные:</b>\n"
        f"• <b>Токен:</b> {name}\n"
        f"• <b>Сумма:</b> ${amount_usd:,.2f}\n"
        f"• <b>Комиссия сети:</b> {fee_display}\n"
        f"• <b>Дата:</b> {data['tx_date'].strftime('%d.%m.%Y %H:%M')}\n"
        f"• <b>Новый баланс:</b> ${new_balance:,.2f}\n\n"

        f"<b>🔗 Блокчейн данные:</b>\n"
        f"• <b>Отправитель:</b>\n<code>{data['from_address']}</code>\n"
        f"• <b>Получатель (Ваш кошелек):</b>\n<code>{address or 'Не указан'}</code>\n"
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