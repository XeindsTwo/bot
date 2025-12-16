from aiogram import types
from aiogram.fsm.context import FSMContext
from app.db import get_token_by_id, create_transaction, update_balance
from app.handlers.menus import main_menu

CANCEL_TEXT = "❌ Отменить создание"


async def handle_cancel(message: types.Message, state: FSMContext) -> bool:
    if message.text.strip() == CANCEL_TEXT:
        await state.clear()
        await message.answer("Создание транзакции отменено", reply_markup=main_menu())
        return True
    return False


async def handle_cancel_callback(call: types.CallbackQuery, state: FSMContext) -> bool:
    if call.data == "cancel":
        await state.clear()
        await call.message.edit_text("Создание транзакции отменено", reply_markup=main_menu())
        await call.answer()
        return True
    return False


async def finish_transaction(state: FSMContext, explorer_link: str = None, is_skip: bool = False,
                             call: types.CallbackQuery = None, message: types.Message = None):
    data = await state.get_data()
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

    create_transaction(
        token=data["token_id"],
        tx_type="income",
        amount=data["amount"],
        date=data["tx_date"].strftime("%Y-%m-%d %H:%M"),
        from_addr=data["from_address"],
        to_addr="",
        tx_hash=data["tx_hash"],
        fee=data["fee"],
        explorer_link=explorer_link
    )

    update_balance(data["token_id"], data["amount"])
    updated_token = get_token_by_id(data["token_id"])
    new_balance = updated_token[5] if updated_token else 0

    success_text = (
        f"✅ Транзакция создана!\n\n"
        f"• Токен: {data.get('token_name', 'Unknown')}\n"
        f"• Сумма: {data['amount']}\n"
        f"• Комиссия: {data.get('fee', 0)}\n"
        f"• Дата: {data['tx_date'].strftime('%d.%m.%Y %H:%M')}\n"
        f"• Отправитель:\n`{data['from_address']}`\n"
        f"• Хеш:\n`{data['tx_hash']}`\n"
        f"• Новый баланс: {new_balance:.2f}"
    )

    if explorer_link:
        success_text += f"\n• Explorer: {explorer_link[:30]}..."

    if is_skip and call:
        await call.message.edit_text(success_text, parse_mode="Markdown")
        await call.message.answer("🏠 Возвращаемся в главное меню:", reply_markup=main_menu())
    elif message:
        await message.answer(success_text, parse_mode="Markdown", reply_markup=main_menu())
    elif call:
        await call.message.answer(success_text, parse_mode="Markdown", reply_markup=main_menu())

    await state.clear()
    return True