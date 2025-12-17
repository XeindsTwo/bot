from aiogram import types
from aiogram.fsm.context import FSMContext
from app.db import get_token_by_id, create_transaction, update_balance
from app.handlers.menus import main_menu

CANCEL_TEXT = "❌ Отменить создание"


async def handle_cancel_outcome(message: types.Message, state: FSMContext) -> bool:
    if message.text.strip() == CANCEL_TEXT:
        await state.clear()
        await message.answer("Создание отправки отменено", reply_markup=main_menu())
        return True
    return False


async def handle_cancel_callback_outcome(call: types.CallbackQuery, state: FSMContext) -> bool:
    if call.data == "cancel":
        await state.clear()
        await call.message.edit_text("Создание отправки отменено", reply_markup=main_menu())
        await call.answer()
        return True
    return False


async def finish_outcome_transaction(state: FSMContext, call: types.CallbackQuery = None,
                                     message: types.Message = None):
    """Завершение создания исходящей транзакции"""
    data = await state.get_data()

    # Проверка обязательных полей
    required_fields = ['token_id', 'amount', 'tx_date', 'to_address', 'tx_hash', 'fee']
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
    total_debit = data['amount'] + data['fee']

    if total_debit > balance:
        error_msg = f"❌ Недостаточно средств! Нужно: {total_debit:.4f}, есть: {balance:.4f}"
        if message:
            await message.answer(error_msg)
        elif call:
            await call.message.answer(error_msg)
        await state.clear()
        return False

    create_transaction(
        token=symbol,
        tx_type="outcome",
        amount=data['amount'],
        date=data['tx_date'].strftime("%Y-%m-%d %H:%M"),
        from_addr=address,
        to_addr=data['to_address'],
        tx_hash=data['tx_hash'],
        fee=data['fee'],
        explorer_link=data.get('explorer_link', '')
    )

    update_balance(token_id, -total_debit)
    updated_token = get_token_by_id(token_id)
    new_balance = updated_token[5] if updated_token else 0

    success_text = (
        f"✅ <b>Отправка создана!</b>\n\n"
        f"<b>📊 Основные данные:</b>\n"
        f"• <b>Токен:</b> {name}\n"
        f"• <b>Сумма отправки:</b> {data['amount']:.4f}\n"
        f"• <b>Комиссия сети:</b> {data['fee']:.4f}\n"
        f"• <b>Итого списано:</b> {total_debit:.4f}\n"
        f"• <b>Дата:</b> {data['tx_date'].strftime('%d.%m.%Y %H:%M')}\n"
        f"• <b>Новый баланс:</b> {new_balance:.4f}\n\n"

        f"<b>🔗 Блокчейн данные:</b>\n"
        f"• <b>Отправитель (наш адрес):</b>\n<code>{address}</code>\n"
        f"• <b>Получатель:</b>\n<code>{data['to_address']}</code>\n"
        f"• <b>Хеш транзакции:</b>\n<code>{data['tx_hash']}</code>"
    )

    if data.get('explorer_link'):
        success_text += f"\n\n• <b>Explorer:</b> {data['explorer_link']}"

    if call:
        await call.message.edit_text(success_text, parse_mode="HTML")
        await call.message.answer("🏠 Возвращаемся в главное меню:", reply_markup=main_menu())
    elif message:
        await message.answer(success_text, parse_mode="HTML", reply_markup=main_menu())

    await state.clear()
    return True