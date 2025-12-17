from aiogram import Router, types
from aiogram.filters import Command
from app.handlers.menus import main_menu
from app.guards import is_owner

from app.transactions.router import router as income_router
from app.tokens.router import router as tokens_router
from app.handlers.history.router import router as history_router
from app.outcome.router import router as outcome_router

router = Router()

router.include_router(outcome_router)
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