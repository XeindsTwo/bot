from fastapi import FastAPI, Query, Response
from app.db import update_token_balance
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import httpx
from app.config import CMC_API_KEY

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


def format_large_number(value: float) -> str:
    if value >= 1_000_000_000:
        return f"${value/1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"${value/1_000_000:.2f}M"
    elif value >= 1_000:
        return f"${value:,.0f}"
    else:
        return f"${value:.2f}"

@app.get("/api/token-image")
async def token_image(url: str = Query(...)):
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10.0)
            if resp.status_code == 200:
                return Response(
                    content=resp.content,
                    media_type=resp.headers.get("content-type", "image/png")
                )
        except Exception:
            pass
    return Response(status_code=404)


@app.get("/api/alpha-tokens")
async def alpha_tokens():
    url = "https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        data = resp.json()

    tokens = []
    for t in data.get("data", [])[:6]:
        image_url = t.get("iconUrl") or t.get("chainIconUrl") or ""

        # Если есть URL, формируем ссылку через прокси
        proxied_image = ""
        if image_url:
            proxied_image = f"http://localhost:8000/api/token-image?url={image_url}"

        market_cap = float(t.get("marketCap", 0))

        tokens.append({
            "network": t.get("chainName", ""),
            "name": t.get("name", ""),
            "symbol": t.get("symbol", ""),
            "image": proxied_image,  # Проксированная ссылка
            "price": round(float(t.get("price", 0)), 2),
            "change24h": float(t.get("percentChange24h", 0)),
            "market_cap_formatted": format_large_number(market_cap),
        })

    return tokens


@app.post("/api/refresh-balances")
async def refresh_balances():
    """
    "Обновление" балансов - просто пересчитываем сумму
    """
    try:
        tokens = get_tokens()
        total_balance = sum(float(token[5]) if token[5] else 0 for token in tokens)

        return {
            "success": True,
            "message": "Балансы получены",
            "total_balance": total_balance
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# для запуска API отдельно
def run_api():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
