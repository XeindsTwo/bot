from fastapi import APIRouter, HTTPException
from app.db import get_transactions, get_transaction_by_id
from datetime import datetime
import httpx
import asyncio

router = APIRouter(prefix="/api/transactions", tags=["transactions"])

TOKEN_CONFIG = {
    "bnb": {"pair": "BNBUSDT", "display": "BNB"},
    "btc": {"pair": "BTCUSDT", "display": "BTC"},
    "eth": {"pair": "ETHUSDT", "display": "ETH"},
    "matic": {"pair": "MATICUSDT", "display": "POL"},
    "tron": {"pair": "TRXUSDT", "display": "TRX"},
    "twt": {"pair": "TWTBUSD", "display": "TWT"},
    "sol": {"pair": "SOLUSDT", "display": "SOL"},
    "ton": {"pair": "TONUSDT", "display": "TON"},
    "usdt_erc20": {"pair": None, "display": "USDT"},
    "usdt_trc20": {"pair": None, "display": "USDT"},
    "usdt_bep20": {"pair": None, "display": "USDT"},
}


async def fetch_binance_prices():
    """Получаем цены с Binance для конвертации"""
    prices = {}
    symbols_to_fetch = {k: v for k, v in TOKEN_CONFIG.items() if v["pair"] is not None}

    async with httpx.AsyncClient(timeout=5.0) as client:
        tasks = []
        for our_symbol, config in symbols_to_fetch.items():
            task = fetch_single_price_with_fallback(client, our_symbol, config["pair"])
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        for result in results:
            if result:  # Если получили цену
                prices.update(result)

    # USDT всегда 1.0
    for usdt_key in ["usdt_erc20", "usdt_trc20", "usdt_bep20"]:
        prices[usdt_key] = {"price": 1.0}

    return prices


async def fetch_single_price_with_fallback(client, our_symbol, binance_pair):
    """Получает цену с обработкой ошибок и фоллбэком на BUSD"""
    try:
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={binance_pair}"
        resp = await client.get(url)

        if resp.status_code == 200:
            data = resp.json()
            return {
                our_symbol: {
                    "price": float(data["lastPrice"]),
                }
            }
        elif resp.status_code == 400:
            # Если пара не найдена, пробуем BUSD
            busd_pair = f"{our_symbol.upper()}BUSD"
            url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={busd_pair}"
            resp2 = await client.get(url)

            if resp2.status_code == 200:
                data = resp2.json()
                return {
                    our_symbol: {
                        "price": float(data["lastPrice"]),
                    }
                }

    except Exception as e:
        print(f"[ERROR] Price fetch for {our_symbol}: {e}")

    # Если не получили цену - возвращаем None, но не фейковые данные
    print(f"[WARN] Could not fetch price for {our_symbol}")
    return None


@router.get("/")
async def api_transactions(limit: int = 100):
    try:
        transactions = get_transactions(limit=limit)

        # Пытаемся получить текущие цены
        try:
            current_prices = await fetch_binance_prices()
        except Exception as e:
            print(f"[WARN] Could not fetch prices: {e}")
            current_prices = {}  # Если не получили - пустой словарь

        result = []
        for tx in transactions:
            if len(tx) >= 11:
                status = tx[10]
            else:
                status = "confirmed"

            token_key = tx[1]
            amount_usd = float(tx[3]) if tx[3] else 0

            token_config = TOKEN_CONFIG.get(token_key, {"pair": None, "display": token_key.upper()})
            price_data = current_prices.get(token_key)

            amount_in_token = 0.0
            if price_data and price_data.get("price", 0) > 0:
                amount_in_token = amount_usd / price_data["price"]
            else:
                # Если нет текущей цены, показываем USD значение
                amount_in_token = amount_usd

            result.append({
                "id": tx[0],
                "token": token_key,
                "display_symbol": token_config["display"],
                "type": tx[2],
                "amount": round(amount_in_token, 8),  # Округляем до 8 знаков
                "amount_usd": round(amount_usd, 2),
                "date": tx[4],
                "from_address": tx[5] if tx[5] else "",
                "to_address": tx[6] if tx[6] else "",
                "tx_hash": tx[7] if tx[7] else "",
                "fee": float(tx[8]) if tx[8] else 0,
                "explorer_link": tx[9] if tx[9] else "",
                "status": status,
                "has_price": price_data is not None  # Флаг: есть ли текущая цена
            })

        return result

    except Exception as e:
        print(f"[ERROR] api_transactions: {str(e)}")
        # Даже если ошибка - возвращаем хотя бы транзакции без конвертации
        return [{
            "error": "Failed to fetch current prices",
            "transactions": []
        }]


@router.get("/{transaction_id}/status")
async def get_transaction_status(transaction_id: int):
    try:
        transaction = get_transaction_by_id(transaction_id)

        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")

        if len(transaction) >= 11:
            current_status = transaction[10]
        else:
            current_status = "confirmed"

        return {
            "id": transaction_id,
            "status": current_status,
            "last_checked": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] get_transaction_status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{transaction_id}")
async def get_transaction_detail(transaction_id: int):
    try:
        transaction = get_transaction_by_id(transaction_id)

        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")

        token_key = transaction[1]  # db_symbol (например: "usdt_bep20", "btc", "eth")
        amount_usd = float(transaction[3]) if transaction[3] else 0
        fee_in_native = float(transaction[8]) if transaction[8] else 0

        token_config = TOKEN_CONFIG.get(token_key, {"pair": None, "display": token_key.upper()})

        fee_usd = 0
        amount_token = 0

        try:
            current_prices = await fetch_binance_prices()
            price_data = current_prices.get(token_key)

            if price_data and price_data.get("price", 0) > 0:
                current_price = price_data["price"]
                amount_token = amount_usd / current_price
                # Конвертируем fee в USD
                fee_usd = fee_in_native * current_price
        except Exception as e:
            print(f"[WARN] Could not fetch price for {token_key}: {e}")
            amount_token = amount_usd
            fee_usd = 0

        def get_network_for_frontend(db_symbol: str) -> str:
            """Точно такая же логика как в mapping_service.py"""
            # Для USDT токенов
            if db_symbol.startswith("usdt_"):
                usdt_network_map = {
                    "usdt_erc20": "eth",
                    "usdt_bep20": "bnb",
                    "usdt_trc20": "tron"
                }
                return usdt_network_map.get(db_symbol, "")

            if db_symbol == "twt":
                return "bnb"

            # Для нативных монет - ПУСТО
            native_coins = ["btc", "eth", "bnb", "matic", "tron", "sol", "ton"]
            if db_symbol in native_coins:
                return ""

            return ""

        network = get_network_for_frontend(token_key)

        def get_display_symbol(db_symbol: str) -> str:
            """Символ для отображения"""
            if db_symbol == "matic":
                return "POL"
            elif db_symbol == "tron":
                return "TRX"
            elif db_symbol.startswith("usdt_"):
                return "USDT"
            return db_symbol.upper()

        display_symbol = get_display_symbol(token_key)

        total_usd = amount_usd + fee_usd

        return {
            "id": transaction[0],
            "token": {
                "symbol": display_symbol,
                "db_symbol": token_key,  # Добавляем оригинальный символ
                "network": network  # "" для нативных, "eth"/"bnb"/"tron" для токенов
            },
            "type": transaction[2],  # "income" или "outcome"
            "title": f"{'Receive' if transaction[2] == 'income' else 'Send'} {display_symbol}",
            "amount_token": round(amount_token, 6),
            "amount_usd": round(amount_usd, 2),
            "date": transaction[4],
            "datetime": transaction[4],
            "from_address": transaction[5] if transaction[5] else "",
            "to_address": transaction[6] if transaction[6] else "",
            "tx_hash": transaction[7] if transaction[7] else "",
            "fee": fee_in_native,
            "fee_usd": round(fee_usd, 2),
            "fee_currency": display_symbol,
            "explorer_link": transaction[9] if transaction[9] else "",
            "status": transaction[10] if len(transaction) > 10 and transaction[10] else "confirmed",
            "total_usd": round(total_usd, 2),
            "network": network  # Дублируем в корне для удобства
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] get_transaction_detail: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")