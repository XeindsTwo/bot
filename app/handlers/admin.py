from aiogram import Router, types
from aiogram.filters import Command
from app.handlers.menus import main_menu
from app.guards import is_owner

from app.transactions.router import router as income_router
from app.tokens.router import router as tokens_router
from app.transactions.history import router as history_router

router = Router()

# ВАЖНО: income_router ПЕРВЫМ - его обработчики с FSM должны регистрироваться раньше
router.include_router(income_router)
router.include_router(tokens_router)
router.include_router(history_router)


@router.message(Command("start"))
async def start(message: types.Message):
    if not is_owner(message.from_user.id):
        return

    await message.answer(
        "👋 Привет!\n\nЭто админ-панель кошелька",
        reply_markup=main_menu()
    )


@router.callback_query(lambda c: c.data == "history")
async def history_callback(call: types.CallbackQuery):
    if not is_owner(call.from_user.id):
        return

    await call.message.answer("📜 История транзакций")
    await call.answer()