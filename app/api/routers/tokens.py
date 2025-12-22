import httpx
import asyncio
from fastapi import APIRouter, HTTPException
from app.db import get_tokens

router = APIRouter(prefix="/api/tokens", tags=["tokens"])

BINANCE_SYMBOLS = {
    "bnb": "BNBUSDT",
    "btc": "BTCUSDT",
    "eth": "ETHUSDT",
    "matic": "MATICUSDT",
    "tron": "TRXUSDT",
    "twt": "TWTBUSD",  # USDT не работает, используем BUSD
    "sol": "SOLUSDT",
    "ton": "TONUSDT",
}


async def fetch_binance_prices():
    """Получаем цены ТОЛЬКО с Binance"""
    prices = {}

    async with httpx.AsyncClient(timeout=5.0) as client:
        tasks = []
        for our_symbol, binance_symbol in BINANCE_SYMBOLS.items():
            task = fetch_single_price(client, our_symbol, binance_symbol)
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        for idx, (our_symbol, binance_symbol) in enumerate(BINANCE_SYMBOLS.items()):
            result = results[idx]

            if result:
                # Успешный ответ от Binance
                prices.update(result)
            else:
                # Если не получили с Binance - ОШИБКА
                print(f"[ERROR] Не удалось получить цену для {our_symbol} с Binance")
                # НЕ возвращаем фейковые данные, просто пропускаем

    return prices


async def fetch_single_price(client, our_symbol, binance_symbol):
    """Получает цену для одного токена с Binance"""
    try:
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={binance_symbol}"
        resp = await client.get(url, timeout=3.0)

        if resp.status_code == 200:
            data = resp.json()
            return {
                our_symbol: {
                    "price": float(data["lastPrice"]),
                    "change_24h": float(data["priceChangePercent"])
                }
            }
        elif resp.status_code == 400:
            # Если пара не найдена, пробуем BUSD
            busd_symbol = f"{our_symbol.upper()}BUSD"
            url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={busd_symbol}"
            resp2 = await client.get(url, timeout=3.0)

            if resp2.status_code == 200:
                data = resp2.json()
                return {
                    our_symbol: {
                        "price": float(data["lastPrice"]),
                        "change_24h": float(data["priceChangePercent"])
                    }
                }

    except Exception as e:
        print(f"[ERROR] Binance error для {binance_symbol}: {e}")

    return None  # Если ошибка - возвращаем None


@router.post("/refresh-balances")
async def refresh_balances():
    try:
        db_tokens = get_tokens()

        active_tokens = [t for t in db_tokens if t[6] == 1 or (t[6] == 0 and t[3] == 1)]

        binance_prices = await fetch_binance_prices()

        if not binance_prices:
            raise HTTPException(
                status_code=503,
                detail="Не удалось получить цены с Binance"
            )

        total_balance_usd = 0
        updated_tokens = []

        for token in active_tokens:
            token_id = token[0]
            db_symbol = token[1]
            balance_usd = float(token[5]) if token[5] else 0

            if db_symbol.startswith("usdt_"):
                current_price = 1.0
                price_change_24h = 0.0
            else:
                price_data = binance_prices.get(db_symbol)

                if not price_data:
                    print(f"[WARN] Нет цены для токена {db_symbol}, пропускаем")
                    continue

                current_price = price_data["price"]
                price_change_24h = price_data["change_24h"]

            if current_price > 0 and balance_usd > 0:
                value = round(balance_usd / current_price, 8)
            else:
                value = balance_usd

            display_symbol = db_symbol.upper()
            if db_symbol == "matic":
                display_symbol = "POL"
            elif db_symbol == "tron":
                display_symbol = "TRX"
            elif db_symbol.startswith("usdt_"):
                if db_symbol == "usdt_erc20":
                    display_symbol = "USDT_ERC20"
                elif db_symbol == "usdt_trc20":
                    display_symbol = "USDT_TRC20"
                elif db_symbol == "usdt_bep20":
                    display_symbol = "USDT_BEP20"

            network = token[8] if len(token) > 8 and token[8] else ""
            if db_symbol == "usdt_erc20":
                network = "eth"
            elif db_symbol == "usdt_trc20":
                network = "tron"
            elif db_symbol == "usdt_bep20":
                network = "bnb"

            token_obj = {
                "id": token_id,
                "symbol": display_symbol,
                "name": token[2],
                "enabled": bool(token[3]),
                "address": token[4],
                "value": value,
                "balance_usd": round(balance_usd, 2),
                "locked": bool(token[6]),
                "full_name": token[7] if len(token) > 7 and token[7] else token[2],
                "network": network,
                "current_price": round(current_price, 2),
                "price_change_24h": round(price_change_24h, 2)
            }

            updated_tokens.append(token_obj)
            total_balance_usd += balance_usd

        if not updated_tokens:
            raise HTTPException(
                status_code=503,
                detail="Не удалось получить данные ни для одного токена"
            )

        # ВОТ ОНА - ЧИСТАЯ СОРТИРОВКА ПО УБЫВАНИЮ БАЛАНСА!
        # ТОЛЬКО balance_usd, больше НИЧЕГО не влияет!
        updated_tokens.sort(key=lambda x: -x["balance_usd"])

        return {
            "success": True,
            "message": "Балансы обновлены",
            "total_balance": round(total_balance_usd, 2),
            "tokens": updated_tokens
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] refresh_balances: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка сервера: {str(e)}"
        )