from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime
from .send_service import calculate_transaction_preview, save_transaction_to_db, find_token_in_db, NATIVE_COINS
from app.db import deduct_token_balance, get_transaction_by_id, get_transaction_by_hash
from app.transactions.processor import start_transaction_processor

router = APIRouter(prefix="/api/send", tags=["send"])

transaction_processor = None


@router.on_event("startup")
async def startup_event():
    global transaction_processor
    transaction_processor = start_transaction_processor()


class PreviewRequest(BaseModel):
    token: str
    amount: float
    to: str


class SendRequest(BaseModel):
    token: str
    amount: float  # Фактическая сумма отправки (уже скорректированная из preview)
    to: str
    network_fee: float
    total_usd: float
    is_native: bool = False
    original_amount: float = None  # Оригинальная сумма с фронта


@router.post("/preview")
async def preview_transaction(request: PreviewRequest):
    try:
        if request.amount <= 0:
            raise HTTPException(400, "Amount должен быть > 0")
        if len(request.to) < 10:
            raise HTTPException(400, "Некорректный адрес")

        token = find_token_in_db(request.token)
        if not token:
            raise HTTPException(404, "Токен не найден")

        db_symbol = token[1]

        return await calculate_transaction_preview(
            token_symbol=request.token,
            amount=request.amount,
            to_address=request.to,
            db_symbol=db_symbol
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Ошибка расчета: {str(e)}")


@router.post("/confirm")
async def confirm_transaction(request: SendRequest, background_tasks: BackgroundTasks):
    try:
        token = find_token_in_db(request.token)
        if not token:
            raise HTTPException(404, "Токен не найден")

        db_symbol = token[1]
        from_address = token[4] if token[4] else "0xYourWalletAddress"

        # Списываем общую сумму (total_usd уже включает комиссию для нативных)
        if not deduct_token_balance(token[0], request.total_usd):
            raise HTTPException(400, "Недостаточно средств")

        # Для нативных монет amount уже пришел скорректированный (final_send_amount)
        # Для токенов amount пришел оригинальный
        transaction_data = {
            "token": db_symbol,
            "amount_usd": request.amount,  # Уже правильная сумма из фронта
            "from_address": from_address,
            "to_address": request.to,
            "fee": request.network_fee
        }

        tx_id = save_transaction_to_db(transaction_data)

        if tx_id == 0:
            from app.db import update_token_balance
            update_token_balance(token[0], float(token[5]) + request.total_usd)
            raise HTTPException(500, "Ошибка сохранения транзакции")

        saved_tx = get_transaction_by_id(tx_id)
        if not saved_tx:
            raise HTTPException(500, "Транзакция не найдена после сохранения")

        tx_hash = saved_tx[7] if len(saved_tx) > 7 else ""

        # Запускаем фоновую задачу для подтверждения транзакции
        background_tasks.add_task(confirm_transaction_background, tx_id)

        return {
            "success": True,
            "message": "Транзакция отправлена",
            "transaction": {
                "id": tx_id,
                "type": "outcome",
                "token": request.token.upper(),
                "amount_token": request.amount,  # Фактическая сумма отправки
                "amount_usd": request.total_usd,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "from_address": from_address,
                "to_address": request.to,
                "tx_hash": tx_hash,
                "fee": request.network_fee,
                "explorer_link": saved_tx[9] if len(saved_tx) > 9 else "",
                "status": "pending",
                "is_native": request.is_native
            },
            "next_step": "/history"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Ошибка отправки: {str(e)}")


async def confirm_transaction_background(tx_id: int):
    """Фоновая задача для подтверждения транзакции"""
    import asyncio
    import random

    delay = random.uniform(5, 10)
    await asyncio.sleep(delay)

    from app.db import update_transaction_status
    update_transaction_status(tx_id, "confirmed")


@router.get("/status/{tx_hash}")
async def get_transaction_status(tx_hash: str):
    transaction = get_transaction_by_hash(tx_hash)

    if not transaction:
        raise HTTPException(404, "Транзакция не найдена")

    status = transaction[10] if len(transaction) > 10 else "pending"

    return {
        "success": True,
        "tx_hash": tx_hash,
        "status": status,
        "confirmations": 15 if status == "confirmed" else 0,
        "timestamp": datetime.now().isoformat()
    }