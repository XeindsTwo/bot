from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from app.db import get_tokens, get_transactions

# для асинхронного запуска вместе с ботом
@asynccontextmanager
async def lifespan(app: FastAPI):
    # запуск при старте (если нужно)
    yield
    # очистка при остановке

app = FastAPI(lifespan=lifespan)

# разрешаем запросы из браузера/расширения
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/tokens")
async def api_tokens():
    """
    Возвращает:
    1. Все системные токены (locked = True) - ВСЕГДА показываем
    2. Пользовательские токены (locked = False) только если enabled = True
    """
    tokens = get_tokens()

    filtered_tokens = [
        t for t in tokens
        if t[6] == 1 or (t[6] == 0 and t[3] == 1)
    ]

    filtered_tokens.sort(key=lambda t: (-t[5], -t[6]))

    return [
        {
            "id": t[0],
            "symbol": t[1],
            "name": t[2],
            "enabled": bool(t[3]),
            "address": t[4],
            "balance_usd": float(t[5]),
            "locked": bool(t[6])
        }
        for t in filtered_tokens
    ]

@app.get("/api/transactions")
async def api_transactions(limit: int = 100):
    """Все транзакции"""
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

# для запуска API отдельно
def run_api():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")