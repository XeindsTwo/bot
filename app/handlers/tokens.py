from aiogram import Router, types
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from secrets import compare_digest
from app.db import get_tokens, update_token
from app.guards import is_owner
from app.handlers.menus import tokens_menu, main_menu

router = Router()


@router.callback_query(lambda c: c.data == "tokens")
async def show_tokens(call: CallbackQuery):
    if not is_owner(call.from_user.id):
        return
    await call.message.edit_text("Управление токенами", reply_markup=tokens_menu())
    await call.answer()


@router.callback_query(lambda c: c.data == "back")
async def back_to_main(call: CallbackQuery, state: FSMContext):
    if not is_owner(call.from_user.id):
        return

    data = await state.get_data()
    if prev_msg_id := data.get("edit_msg_id"):
        try:
            await call.bot.delete_message(call.from_user.id, prev_msg_id)
        except:
            pass

    await state.clear()
    await call.message.edit_text("Админ-панель кошелька", reply_markup=main_menu())
    await call.answer()


@router.callback_query(lambda c: c.data.startswith("edit_"))
async def manage_token(call: CallbackQuery, state: FSMContext, token_key: str = None):
    if not is_owner(call.from_user.id):
        return

    data = await state.get_data()
    if prev_msg_id := data.get("edit_msg_id"):
        try:
            await call.bot.delete_message(call.from_user.id, prev_msg_id)
        except:
            pass

    await state.clear()

    if token_key is None:
        token_key = call.data.replace("edit_", "")

    tokens = get_tokens()
    current = next((t for t in tokens if compare_digest(t[0], token_key)), None)
    if not current:
        await call.answer("Токен не найден!", show_alert=True)
        return

    token, name, enabled, address, balance, locked = current

    if locked:
        await call.answer("Этот токен нельзя редактировать!", show_alert=True)
        return

    status_text = "включен" if enabled else "выключен"
    text = f"{name} | {'✅' if enabled else '❌'} {status_text} | {address or 'нет адреса'}"

    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Переключить включение", callback_data=f"toggle_{token}")],
        [types.InlineKeyboardButton(text="Изменить адрес", callback_data=f"editaddr_{token}")],
        [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="tokens")]
    ])

    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


@router.callback_query(lambda c: c.data.startswith("toggle_"))
async def toggle_token_status(call: CallbackQuery, state: FSMContext):
    if not is_owner(call.from_user.id):
        return

    token_key = call.data.replace("toggle_", "")
    tokens = get_tokens()
    current = next((t for t in tokens if compare_digest(t[0], token_key)), None)
    if not current:
        await call.answer("Токен не найден!", show_alert=True)
        return

    token, name, enabled, address, balance, locked = current

    if locked:
        await call.answer("Этот токен нельзя редактировать!", show_alert=True)
        return

    enabled = not enabled
    update_token(token, enabled=enabled)

    await manage_token(call, state, token_key=token)
    await call.answer(f"{name} теперь {'включен' if enabled else 'выключен'}")


@router.callback_query(lambda c: c.data.startswith("editaddr_"))
async def start_edit_address(call: CallbackQuery, state: FSMContext):
    if not is_owner(call.from_user.id):
        return

    token_key = call.data.replace("editaddr_", "")
    tokens = get_tokens()
    current = next((t for t in tokens if compare_digest(t[0], token_key)), None)
    if not current:
        await call.answer("Токен не найден!", show_alert=True)
        return

    token, name, enabled, address, balance, locked = current
    if locked:
        await call.answer("Этот токен нельзя редактировать!", show_alert=True)
        return

    data = await state.get_data()
    if prev_msg_id := data.get("edit_msg_id"):
        try:
            await call.bot.delete_message(call.from_user.id, prev_msg_id)
        except:
            pass

    msg = await call.message.answer(f"Отправьте новый адрес для {name}:")
    await state.update_data(edit_msg_id=msg.message_id)
    await state.set_state(f"edit_address:{token}")
    await call.answer()


@router.message()
async def save_address(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state and current_state.startswith("edit_address:"):
        token = current_state.split(":")[1]
        update_token(token, address=message.text.strip())

        tokens = get_tokens()
        current = next((t for t in tokens if compare_digest(t[0], token)), None)
        if current:
            _, name, _, _, _, _ = current
            token_name = name
        else:
            token_name = token.upper()

        data = await state.get_data()
        if prev_msg_id := data.get("edit_msg_id"):
            try:
                await message.bot.delete_message(message.from_user.id, prev_msg_id)
            except:
                pass

        await state.clear()
        await message.answer(f"Адрес для {token_name} обновлен!", reply_markup=tokens_menu())
