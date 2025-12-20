import httpx
import random
import asyncio
from fastapi import APIRouter, HTTPException
from app.db import get_tokens

router = APIRouter(prefix="/api/tokens", tags=["tokens"])

# Маппинг наших символов на Binance пары
BINANCE_SYMBOLS = {
    "bnb": "BNBUSDT",
    "btc": "BTCUSDT",
    "eth": "ETHUSDT",
    "matic": "MATICUSDT",
    "tron": "TRXUSDT",
    "twt": "TWTUSDT",
    "sol": "SOLUSDT",
    "ton": "TONUSDT",
}


async def fetch_binance_prices():
    """Получаем цены с Binance Public API"""
    prices = {}

    async with httpx.AsyncClient(timeout=3.0) as client:  # Короткий таймаут
        tasks = []
        for our_symbol, binance_symbol in BINANCE_SYMBOLS.items():
            task = fetch_single_price(client, our_symbol, binance_symbol)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Собираем только успешные результаты
        for result in results:
            if isinstance(result, dict):
                prices.update(result)

    return prices


async def fetch_single_price(client, our_symbol, binance_symbol):
    """Получает цену для одного токена"""
    try:
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={binance_symbol}"
        resp = await client.get(url)

        if resp.status_code == 200:
            data = resp.json()
            return {
                our_symbol: {
                    "price": float(data["lastPrice"]),
                    "change_24h": float(data["priceChangePercent"])
                }
            }
        else:
            # Если Binance вернул ошибку - просто не добавляем этот токен
            print(f"[INFO] Binance {binance_symbol}: {resp.status_code}")
            return {}

    except Exception as e:
        print(f"[INFO] Binance timeout для {binance_symbol}: {e}")
        return {}  # Пустой результат, пропускаем этот токен


@router.post("/refresh-balances")
async def refresh_balances():
    try:
        # 1. Получаем токены из БД
        db_tokens = get_tokens()
        active_tokens = [t for t in db_tokens if t[6] == 1 or (t[6] == 0 and t[3] == 1)]

        # 2. Получаем актуальные цены с Binance
        binance_prices = await fetch_binance_prices()

        # 3. Проверяем какие токены получили цены
        tokens_without_prices = []
        for token in active_tokens:
            db_symbol = token[1]
            if not db_symbol.startswith("usdt_") and db_symbol not in binance_prices:
                tokens_without_prices.append(db_symbol)

        # 4. Если для важных токенов (BNB, BTC, ETH) нет цен - ошибка
        important_tokens = ["bnb", "btc", "eth"]
        missing_important = [t for t in important_tokens if t in tokens_without_prices]

        if missing_important:
            raise HTTPException(
                status_code=503,
                detail=f"Binance API не вернул цены для: {', '.join(missing_important)}"
            )

        total_balance_usd = 0
        updated_tokens = []

        # 5. Обрабатываем каждый токен
        for token in active_tokens:
            token_id = token[0]
            db_symbol = token[1]
            balance_usd = float(token[5]) if token[5] else 0

            # USDT
            if db_symbol.startswith("usdt_"):
                current_price = round(0.99 + (random.random() * 0.02), 2)
                price_change_24h = round(random.uniform(-0.1, 0.1), 2)
            else:
                # Проверяем есть ли цена
                price_data = binance_prices.get(db_symbol)
                if not price_data:
                    print(f"[WARN] Пропускаем {db_symbol} - нет цены от Binance")
                    continue

                current_price = price_data["price"]
                price_change_24h = price_data["change_24h"]

            # Расчёт value
            if current_price > 0 and balance_usd > 0:
                value = round(balance_usd / current_price, 8)
            else:
                value = balance_usd

            # Форматирование символа
            display_symbol = db_symbol.upper()
            if db_symbol == "matic":
                display_symbol = "POL"
            elif db_symbol == "tron":
                display_symbol = "TRX"
            elif db_symbol.startswith("usdt_"):
                display_symbol = "USDT"

            # Сеть для USDT
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

        # 6. Если вообще нет токенов после фильтрации
        if not updated_tokens:
            raise HTTPException(
                status_code=503,
                detail="Не удалось получить цены ни для одного токена"
            )

        # 7. Сортировка
        updated_tokens.sort(key=lambda x: (-x["locked"], -x["balance_usd"]))

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