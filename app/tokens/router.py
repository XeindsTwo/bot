from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from app.guards import is_owner
from app.handlers.menus import tokens_menu, main_menu
from app.db import update_token
from .states import TokenStates
from .keyboards import get_token_management_keyboard, get_cancel_keyboard
from .helpers import find_token_by_id

router = Router()


@router.callback_query(lambda c: c.data == "tokens")
async def show_tokens(call: types.CallbackQuery):
    if not is_owner(call.from_user.id):
        return
    await call.message.edit_text("Управление токенами", reply_markup=tokens_menu())
    await call.answer()


@router.callback_query(lambda c: c.data == "back")
async def back_to_main(call: types.CallbackQuery, state: FSMContext):
    if not is_owner(call.from_user.id):
        return
    await state.clear()
    await call.message.edit_text("Админ-панель кошелька", reply_markup=main_menu())
    await call.answer()


@router.callback_query(lambda c: c.data.startswith("edit_"))
async def manage_token(call: types.CallbackQuery):
    if not is_owner(call.from_user.id):
        return

    token_id = call.data.replace("edit_", "")
    token = find_token_by_id(token_id)

    if not token:
        await call.answer("Токен не найден!", show_alert=True)
        return

    token_id, symbol, name, enabled, address, balance, locked = token

    if locked:
        await call.answer("Этот токен нельзя редактировать!", show_alert=True)
        return

    status = "🟢 Включен" if enabled else "🔴 Выключен"
    text = (
        f"<b>Токен: {name}</b>\n\n"
        f"• Статус: {status}\n"
        f"• Баланс: {balance:.2f}\n"
        f"• Адрес: {f'<code>{address}</code>' if address else '❌ Не указан'}\n\n"
        f"<i>Выберите действие:</i>"
    )

    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_token_management_keyboard(str(token_id))
    )
    await call.answer()


@router.callback_query(lambda c: c.data.startswith("toggle_"))
async def toggle_token_status(call: types.CallbackQuery):
    if not is_owner(call.from_user.id):
        return

    token_id = call.data.replace("toggle_", "")
    token = find_token_by_id(token_id)

    if not token:
        await call.answer("Токен не найден!", show_alert=True)
        return

    token_id, symbol, name, enabled, address, balance, locked = token

    if locked:
        await call.answer("Этот токен нельзя редактировать!", show_alert=True)
        return

    new_enabled = not enabled
    update_token(token_id, enabled=new_enabled)

    await call.answer(f"{name} теперь {'включен' if new_enabled else 'выключен'}")

    status = "🟢 Включен" if new_enabled else "🔴 Выключен"
    text = (
        f"<b>Токен: {name}</b>\n\n"
        f"• Статус: {status}\n"
        f"• Баланс: {balance:.2f}\n"
        f"• Адрес: {f'<code>{address}</code>' if address else '❌ Не указан'}\n\n"
        f"<i>Выберите действие:</i>"
    )

    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_token_management_keyboard(str(token_id))
    )


@router.callback_query(lambda c: c.data.startswith("editaddr_"))
async def start_edit_address(call: types.CallbackQuery, state: FSMContext):
    if not is_owner(call.from_user.id):
        return

    token_id = call.data.replace("editaddr_", "")
    token = find_token_by_id(token_id)

    if not token:
        await call.answer("Токен не найден!", show_alert=True)
        return

    token_id, symbol, name, enabled, address, balance, locked = token

    if locked:
        await call.answer("Этот токен нельзя редактировать!", show_alert=True)
        return

    await state.update_data(
        token_id=str(token_id),
        token_name=name
    )
    await state.set_state(TokenStates.editing_address)

    text = (
        f"✏️ Изменение адреса для <b>{name}</b>\n\n"
        f"Текущий адрес: {f'<code>{address}</code>' if address else '❌ Не указан'}\n\n"
        f"<i>Введите новый адрес:</i>"
    )

    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await call.answer()


@router.callback_query(lambda c: c.data == "cancel_edit")
async def cancel_address_edit(call: types.CallbackQuery, state: FSMContext):
    if not is_owner(call.from_user.id):
        return

    data = await state.get_data()
    token_id = data.get("token_id")

    await state.clear()
    await call.answer("Редактирование отменено")

    if token_id:
        token = find_token_by_id(token_id)
        if token:
            token_id, symbol, name, enabled, address, balance, locked = token
            status = "🟢 Включен" if enabled else "🔴 Выключен"
            text = (
                f"<b>Токен: {name}</b>\n\n"
                f"• Статус: {status}\n"
                f"• Баланс: {balance:.2f}\n"
                f"• Адрес: {f'<code>{address}</code>' if address else '❌ Не указан'}\n\n"
                f"<i>Выберите действие:</i>"
            )

            await call.message.edit_text(
                text,
                parse_mode="HTML",
                reply_markup=get_token_management_keyboard(str(token_id))
            )
    else:
        await show_tokens(call)


@router.message(TokenStates.editing_address)
async def save_new_address(message: types.Message, state: FSMContext):
    if not is_owner(message.from_user.id):
        return

    data = await state.get_data()
    token_id = data.get("token_id")
    token_name = data.get("token_name")

    if not token_id:
        await state.clear()
        await message.answer("Ошибка: токен не найден", reply_markup=tokens_menu())
        return

    new_address = message.text.strip()
    update_token(int(token_id), address=new_address)
    await state.clear()

    await message.answer(
        f"✅ Адрес для <b>{token_name}</b> обновлен!\n\n"
        f"Новый адрес: <code>{new_address}</code>",
        parse_mode="HTML",
        reply_markup=tokens_menu()
    )
