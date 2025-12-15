from aiogram import types
from aiogram.fsm.context import FSMContext
from datetime import datetime
from app.db import get_token_by_id, create_transaction, update_balance
from app.handlers.menus import main_menu

CANCEL_TEXT = "❌ Отменить создание"


async def handle_cancel(message: types.Message, state: FSMContext) -> bool:
    if message.text.strip() == CANCEL_TEXT:
        await state.clear()
        try:
            await message.delete()
        except Exception:
            pass
        await message.answer("Создание транзакции отменено", reply_markup=main_menu())
        return True
    return False


async def handle_cancel_callback(call: types.CallbackQuery, state: FSMContext) -> bool:
    if call.data == "cancel":
        await state.clear()
        try:
            await call.message.delete()
        except Exception:
            pass
        await call.message.answer("Создание транзакции отменено", reply_markup=main_menu())
        await call.answer()
        return True
    return False


async def finish_transaction(
        state: FSMContext,
        explorer_link: str = None,
        is_skip: bool = False,
        call: types.CallbackQuery = None,
        message: types.Message = None
):
    """Завершает создание транзакции (общая логика для пропуска и обычного завершения)"""

    # Получаем данные ИЗ СОСТОЯНИЯ
    data = await state.get_data()

    # Проверяем обязательные поля
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

    # Сохраняем транзакцию
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

    # Обновляем баланс
    update_balance(data["token_id"], data["amount"])

    # Получаем новый баланс для отображения
    updated_token = get_token_by_id(data["token_id"])
    new_balance = updated_token[5] if updated_token else 0

    # Формируем сообщение об успехе
    success_text = (
        f"✅ Транзакция создана!\n\n"
        f"• Токен: {data.get('token_name', 'Unknown')}\n"
        f"• Сумма: {data['amount']}\n"
        f"• Новый баланс: {new_balance:.2f}\n"
        f"• Хеш: `{data['tx_hash'][:20]}...`"
    )

    # Отправляем сообщение в зависимости от контекста
    if is_skip and call:
        await call.message.edit_text(success_text, parse_mode="Markdown")
        await call.message.answer("🏠 Возвращаемся в главное меню:", reply_markup=main_menu())
    elif message:
        # Если обычное завершение через сообщение
        await message.answer(success_text, parse_mode="Markdown", reply_markup=main_menu())
    elif call:
        # Если коллбэк без пропуска
        await call.message.answer(success_text, parse_mode="Markdown", reply_markup=main_menu())

    await state.clear()
    return True
