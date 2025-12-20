from fastapi import APIRouter
from app.db import get_transactions

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("/")
async def api_transactions(limit: int = 100):
    transactions = get_transactions(limit=limit)
    return [
        {
            "id": tx[0],
            "token": tx[1],
            "type": tx[2],
            "amount": float(tx[3]),
            "date": tx[4],
            "from_address": tx[5],
            "to_address": tx[6],
            "tx_hash": tx[7],
            "fee": float(tx[8]) if tx[8] else 0,
            "explorer_link": tx[9],
            "status": tx[10]
        }
        for tx in transactions
    ]
