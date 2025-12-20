from aiogram import Router, types
from aiogram.fsm.context import FSMContext
import logging

from app.guards import is_owner
from app.handlers.menus import main_menu, tokens_menu, balance_menu
from app.db import get_tokens, update_token, execute_query, get_db_cursor
from .states import TokenStates
from .keyboards import get_token_management_keyboard, get_cancel_keyboard, get_confirm_clear_keyboard
from .helpers import find_token_by_id, format_token_info, format_main_menu_balance, format_detailed_balances

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(lambda c: c.data == "back")
async def back_to_main(call: types.CallbackQuery, state: FSMContext):
    if not is_owner(call.from_user.id):
        return
    await state.clear()
    await call.message.edit_text(
        f"🏠 <b>Админ-панель крипто-кошелька</b>\n\n{format_main_menu_balance()}",
        parse_mode="HTML",
        reply_markup=main_menu()
    )
    await call.answer()

@router.callback_query(lambda c: c.data == "balance")
async def show_balance(call: types.CallbackQuery):
    if not is_owner(call.from_user.id):
        return
    text = format_detailed_balances()
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=balance_menu())
    await call.answer()

@router.callback_query(lambda c: c.data == "tokens")
async def show_tokens(call: types.CallbackQuery):
    if not is_owner(call.from_user.id):
        return
    tokens = get_tokens()
    unlocked_count = len([t for t in tokens if t[6] == 0])
    locked_count = len([t for t in tokens if t[6] == 1])
    text = (
        f"🪙 <b>Управление токенами</b>\n\n"
        f"• Всего токенов: {len(tokens)}\n"
        f"• Настраиваемые: {unlocked_count}\n"
        f"• Системные: {locked_count}\n\n"
        f"🔒 - системный (всегда включен)\n"
        f"✅ - включен | ❌ - выключен\n"
        f"💰 - есть баланс\n\n"
        f"<i>Выберите токен для управления:</i>"
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=tokens_menu())
    await call.answer()

@router.callback_query(lambda c: c.data.startswith("edit_"))
async def manage_token(call: types.CallbackQuery):
    if not is_owner(call.from_user.id):
        return
    token_id = call.data.replace("edit_", "")
    token = find_token_by_id(token_id)
    if not token:
        await call.answer("❌ Токен не найден!", show_alert=True)
        return
    token_id_int, symbol, name, enabled, address, balance, locked = token[:7]
    text = format_token_info(token, show_balance=True)
    keyboard = get_token_management_keyboard(str(token_id_int), locked=(locked == 1))
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await call.answer()

@router.callback_query(lambda c: c.data.startswith("toggle_"))
async def toggle_token_status(call: types.CallbackQuery):
    if not is_owner(call.from_user.id):
        return
    token_id = call.data.replace("toggle_", "")
    token = find_token_by_id(token_id)
    if not token:
        await call.answer("❌ Токен не найден!", show_alert=True)
        return
    token_id_int, symbol, name, enabled, address, balance, locked = token[:7]
    if locked == 1:
        await call.answer("⚠️ Это системный токен, нельзя отключать!", show_alert=True)
        return
    new_enabled = not enabled
    update_token(token_id_int, enabled=new_enabled)
    token = find_token_by_id(token_id)
    text = format_token_info(token, show_balance=True)
    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_token_management_keyboard(str(token_id_int), locked=False)
    )
    await call.answer(f"✅ {name} теперь {'включен' if new_enabled else 'выключен'}")

@router.callback_query(lambda c: c.data.startswith("editaddr_"))
async def start_edit_address(call: types.CallbackQuery, state: FSMContext):
    if not is_owner(call.from_user.id):
        return
    token_id = call.data.replace("editaddr_", "")
    token = find_token_by_id(token_id)
    if not token:
        await call.answer("❌ Токен не найден!", show_alert=True)
        return
    token_id_int, symbol, name, enabled, address, balance, locked = token[:7]
    await state.update_data(
        token_id=str(token_id_int),
        token_name=name,
        current_address=address,
        is_locked=(locked == 1)
    )
    await state.set_state(TokenStates.editing_address)
    if address:
        addr_display = address[:20] + "..." + address[-15:] if len(address) > 35 else address
        address_text = f"Текущий адрес:\n<code>{addr_display}</code>\n\n"
    else:
        address_text = "Текущий адрес: <i>не указан</i>\n\n"
    text = (
        f"✏️ <b>Изменение адреса для {name}</b>\n\n"
        f"{address_text}"
        f"<i>Введите новый адрес кошелька:</i>\n\n"
        f"💡 <b>Форматы:</b>\n"
        f"• ETH/BSC: 0x742d35Cc6634C0532925a3b844Bc9e...\n"
        f"• BTC: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa\n"
        f"• TRON: TYFm3TZ5hPKWjzVhGJuxKPo5FJzr6a9y7F\n"
        f"• TON: UQBmzW4wYlFW0tiBgj5sP1CgSlLdYs-VpjPWM7oPYPYWQBqW"
    )
    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(return_to=f"edit_{token_id_int}")
    )
    await call.answer()

@router.callback_query(lambda c: c.data.startswith("cancel_edit_"))
async def cancel_address_edit(call: types.CallbackQuery, state: FSMContext):
    if not is_owner(call.from_user.id):
        return
    return_to = call.data.replace("cancel_edit_", "")
    await state.clear()
    await call.answer("❌ Редактирование отменено")
    if return_to.startswith("edit_"):
        token_id = return_to.replace("edit_", "")
        token = find_token_by_id(token_id)
        if token:
            text = format_token_info(token, show_balance=True)
            keyboard = get_token_management_keyboard(token_id, locked=(token[6] == 1))
            await call.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    else:
        await show_tokens(call)

@router.message(TokenStates.editing_address)
async def save_new_address(message: types.Message, state: FSMContext):
    if not is_owner(message.from_user.id):
        return
    data = await state.get_data()
    token_id = data.get("token_id")
    token_name = data.get("token_name")
    current_address = data.get("current_address")
    if not token_id:
        await state.clear()
        await message.answer("❌ Ошибка: токен не найден", reply_markup=tokens_menu())
        return
    new_address = message.text.strip()
    if not new_address:
        await message.answer("❌ Адрес не может быть пустым!")
        return
    if len(new_address) < 10:
        await message.answer("❌ Слишком короткий адрес!")
        return
    if new_address == current_address:
        await message.answer("⚠️ Адрес не изменился!")
        return
    update_token(int(token_id), address=new_address)
    await state.clear()
    if len(new_address) > 30:
        display_addr = f"{new_address[:15]}...{new_address[-15:]}"
    else:
        display_addr = new_address
    await message.answer(
        f"✅ <b>Адрес обновлен!</b>\n\n"
        f"Токен: <b>{token_name}</b>\n"
        f"Новый адрес:\n<code>{display_addr}</code>\n\n"
        f"Адрес будет использоваться:\n"
        f"• При получении - как адрес получателя\n"
        f"• При отправке - как адрес отправителя",
        parse_mode="HTML",
        reply_markup=tokens_menu()
    )


@router.callback_query(lambda c: c.data == "clear_history")
async def ask_clear_history(call: types.CallbackQuery):
    if not is_owner(call.from_user.id):
        return

    # Получаем статистику
    result = execute_query("SELECT COUNT(*) as count FROM transactions")
    tx_count = result[0]["count"] if result else 0

    result = execute_query("SELECT SUM(balance) as total FROM tokens")
    # Безопасное получение total_balance
    if result and result[0]["total"] is not None:
        total_balance = float(result[0]["total"])
    else:
        total_balance = 0.0

    # Форматируем баланс
    if total_balance == 0:
        balance_text = "0"
    elif total_balance < 1:
        balance_text = f"{total_balance:.4f}"
    elif total_balance < 1000:
        balance_text = f"{total_balance:.2f}"
    else:
        balance_text = f"{total_balance:,.0f}"

    text = (
        f"⚠️ <b>ВНИМАНИЕ! Очистка истории</b>\n\n"
        f"Это действие:\n"
        f"• Удалит {tx_count} транзакций\n"
        f"• Обнулит балансы ({balance_text})\n"
        f"• Не удалит адреса кошельков\n\n"
        f"<b>Вы уверены?</b>"
    )

    await call.message.edit_text(text, parse_mode="HTML", reply_markup=get_confirm_clear_keyboard())
    await call.answer()


@router.callback_query(lambda c: c.data == "confirm_clear")
async def confirm_clear_history(call: types.CallbackQuery):
    if not is_owner(call.from_user.id):
        return

    try:
        # В ОДНОЙ ТРАНЗАКЦИИ:
        # 1. Удаляем все транзакции
        # 2. Обнуляем ВСЕ балансы
        # 3. Очищаем адреса у ВСЕХ токенов
        # 4. Выключаем unlocked токены

        with get_db_cursor() as cursor:
            cursor.execute("DELETE FROM transactions")
            cursor.execute("UPDATE tokens SET balance = 0")
            cursor.execute("UPDATE tokens SET address = ''")  # Очищаем адреса у ВСЕХ токенов
            cursor.execute("UPDATE tokens SET enabled = 0 WHERE locked = 0")
            # Locked токены (locked = 1) остаются включенными

        result = execute_query("SELECT COUNT(*) as count FROM tokens WHERE locked = 0")
        unlocked_tokens_count = result[0]["count"] if result else 0

        result = execute_query("SELECT COUNT(*) as count FROM tokens")
        total_tokens = result[0]["count"] if result else 0

        await call.message.edit_text(
            "✅ <b>История очищена!</b>\n\n"
            "• Все транзакции удалены\n"
            "• Балансы обнулены\n"
            f"• Адреса очищены у всех {total_tokens} токенов\n"
            f"• Отключено {unlocked_tokens_count} настраиваемых токенов\n"
            "• Системные токены остались включены\n\n"
            "Теперь можно начать с чистого листа",
            parse_mode="HTML",
            reply_markup=main_menu()
        )

    except Exception as e:
        logger.error(f"Ошибка очистки истории: {e}", exc_info=True)
        await call.message.edit_text(
            "❌ <b>Ошибка при очистке!</b>\n\n"
            f"Детали: {str(e)[:100]}",
            parse_mode="HTML",
            reply_markup=main_menu()
        )

    await call.answer()


@router.callback_query(lambda c: c.data == "cancel_clear")
async def cancel_clear_history(call: types.CallbackQuery):
    if not is_owner(call.from_user.id):
        return

    await call.message.edit_text(
        "❌ <b>Очистка отменена</b>\n\n"
        "Данные сохранены.",
        parse_mode="HTML",
        reply_markup=main_menu()
    )
    await call.answer()