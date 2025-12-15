from aiogram import Router, types
from app.db import get_transactions
from app.guards import is_owner

router = Router()

@router.message(lambda m: is_owner(m.from_user.id))
async def view_history(message: types.Message):
    txs = get_transactions(limit=10)
    if not txs:
        await message.answer("История транзакций пуста.")
        return

    text = "Последние транзакции:\n\n"
    for tx in txs:
        text += f"{tx[1]} | {tx[3]} | {tx[4]} | {tx[5]} | {tx[8]}\n"
    await message.answer(text)