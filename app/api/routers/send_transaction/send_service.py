import httpx
import random
from typing import Dict, Optional
from fastapi import HTTPException
from app.db import get_tokens, get_db_cursor, deduct_token_balance
from datetime import datetime
from app.transactions.utils import generate_tx_hash, get_crypto_type_from_symbol

BINANCE_PAIRS = {
    "BNB": "BNBUSDT",
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "MATIC": "MATICUSDT",
    "TRX": "TRXUSDT",
    "SOL": "SOLUSDT",
    "TON": "TONUSDT",
    "TWT": "TWTBUSD"
}

# Маппинг токенов к символам для получения комиссий с Binance
TOKEN_TO_FEE_SYMBOL = {
    "usdt_erc20": "ETH",
    "usdt_trc20": "TRX",
    "usdt_bep20": "BNB",
    "matic": "MATIC",
    "tron": "TRX",
    "bnb": "BNB",
    "btc": "BTC",
    "eth": "ETH",
    "sol": "SOL",
    "ton": "TON",
    "twt": "BNB",
    "pol": "MATIC"
}


async def get_real_binance_price(symbol: str) -> Optional[float]:
    try:
        if symbol == "USDT":
            return 1.0
        pair = BINANCE_PAIRS.get(symbol)
        if not pair:
            return None
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={pair}"
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                return float(data["price"])
    except Exception as e:
        print(f"[PRICE ERROR] {symbol}: {e}")
    return None


async def get_binance_withdraw_fee(symbol: str) -> Optional[float]:
    """
    Получает комиссию на вывод с Binance для конкретного токена
    """
    try:
        # Этот эндпоинт возвращает информацию о сети и комиссиях
        url = "https://api.binance.com/sapi/v1/capital/config/getall"
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()

                # Ищем токен в ответе
                for coin_info in data:
                    if coin_info.get("coin") == symbol:
                        # Ищем сеть (если несколько сетей, берем первую)
                        network_list = coin_info.get("networkList", [])
                        if network_list:
                            # Берем комиссию из первой доступной сети
                            fee_str = network_list[0].get("withdrawFee")
                            if fee_str:
                                return float(fee_str)
    except Exception as e:
        print(f"[BINANCE FEE ERROR] {symbol}: {e}")

    return None


async def get_estimated_gas_fee(symbol: str) -> float:
    """
    Оценка комиссии газа для разных сетей
    Возвращает примерную комиссию в USD
    """
    # Базовые комиссии в нативной валюте (примерные)
    BASE_FEES = {
        "ETH": 0.002,  # ~0.002 ETH за стандартную транзакцию
        "BNB": 0.0005,  # ~0.0005 BNB
        "TRX": 10,  # ~10 TRX
        "MATIC": 0.1,  # ~0.1 MATIC
        "BTC": 0.0002,  # ~0.0002 BTC
        "SOL": 0.00001,  # ~0.00001 SOL
        "TON": 0.1,  # ~0.1 TON
    }

    fee_symbol = TOKEN_TO_FEE_SYMBOL.get(symbol, symbol.upper())

    # Пробуем получить комиссию вывода с Binance
    binance_fee = await get_binance_withdraw_fee(fee_symbol)
    if binance_fee is not None:
        # Получаем цену токена для конвертации в USD
        price = await get_real_binance_price(fee_symbol)
        if price:
            return binance_fee * price

    # Fallback: используем базовые комиссии + получаем текущую цену
    if fee_symbol in BASE_FEES:
        base_fee = BASE_FEES[fee_symbol]
        price = await get_real_binance_price(fee_symbol)
        if price:
            return base_fee * price

    # Дефолтная комиссия $1.5
    return 1.5


def find_token_in_db(symbol: str, db_symbol: str = None):
    tokens = get_tokens()
    symbol_lower = symbol.lower()

    if db_symbol:
        for token in tokens:
            if token[1].lower() == db_symbol.lower():
                return token

    if symbol_lower == "pol":
        symbol_lower = "matic"
    elif symbol_lower == "trx":
        symbol_lower = "tron"

    for token in tokens:
        if token[1].lower() == symbol_lower:
            return token
    return None


async def calculate_transaction_preview(token_symbol: str, amount: float, to_address: str,
                                        db_symbol: str = None) -> Dict:
    token = find_token_in_db(token_symbol, db_symbol)
    if not token:
        raise HTTPException(404, f"Токен {token_symbol} не найден")

    token_id, db_symbol, token_name = token[0], token[1], token[2]
    from_address = token[4] if token[4] else "0xYourWalletAddress"
    balance_usd = float(token[5]) if token[5] else 0

    # Определяем символ для цены
    price_symbol_map = {
        "matic": "MATIC",
        "tron": "TRX",
        "usdt_erc20": "ETH",
        "usdt_trc20": "TRX",
        "usdt_bep20": "BNB",
        "bnb": "BNB",
        "btc": "BTC",
        "eth": "ETH",
        "sol": "SOL",
        "ton": "TON",
        "twt": "TWT",
        "pol": "MATIC"
    }

    # Для USDT токенов
    if db_symbol.startswith("usdt_"):
        # Цена USDT всегда 1 USD
        usdt_price = 1.0

        # Нам нужна цена нативной валюты для комиссии
        native_symbol = price_symbol_map.get(db_symbol, "ETH")
        native_price = await get_real_binance_price(native_symbol)
        if native_price is None:
            raise HTTPException(503, f"Не удалось получить курс {native_symbol}")

        # Сумма в USD
        amount_usd = amount

    else:
        # Для нативных токенов
        price_symbol = price_symbol_map.get(db_symbol, db_symbol.upper())
        native_price = await get_real_binance_price(price_symbol)
        if native_price is None:
            raise HTTPException(503, f"Не удалось получить курс {price_symbol}")

        usdt_price = native_price
        amount_usd = amount * native_price

    # Получаем комиссию в USD (реальная с Binance)
    fee_usd = await get_estimated_gas_fee(db_symbol)

    # Добавляем небольшой рандом (+/- 15%)
    variation = random.uniform(0.85, 1.15)
    fee_usd = round(fee_usd * variation, 4)

    # Минимальная и максимальная комиссия
    if fee_usd < 0.1:
        fee_usd = 0.1
    elif fee_usd > 50:
        fee_usd = 50

    # Рассчитываем комиссию в нативной валюте
    if db_symbol.startswith("usdt_"):
        # Для USDT токенов: fee_native = fee_usd / цена_нативной_валюты
        fee_native = fee_usd / native_price if native_price > 0 else 0
    else:
        # Для нативных токенов: fee_native = fee_usd / цена_токена
        fee_native = fee_usd / native_price if native_price > 0 else 0

    # Определяем валюту комиссии
    fee_currency_map = {
        "usdt_erc20": "ETH",
        "usdt_bep20": "BNB",
        "usdt_trc20": "TRX",
        "matic": "POL",
        "tron": "TRX",
        "bnb": "BNB",
        "btc": "BTC",
        "eth": "ETH",
        "sol": "SOL",
        "ton": "TON",
        "twt": "TWT",
        "pol": "POL"
    }

    fee_currency = fee_currency_map.get(db_symbol, token_symbol.upper())

    # Общая сумма в USD
    total_usd = amount_usd + fee_usd

    # Рассчитываем баланс в токенах
    if db_symbol.startswith("usdt_"):
        token_balance = balance_usd  # Для USDT баланс в USD = баланс в токенах
    else:
        token_balance = balance_usd / usdt_price if usdt_price > 0 else 0

    # Определяем сеть
    network_map = {
        "bnb": "BNB Smart Chain",
        "btc": "Bitcoin",
        "eth": "Ethereum",
        "matic": "Polygon",
        "tron": "TRON",
        "twt": "BNB Smart Chain",
        "sol": "Solana",
        "ton": "TON",
        "usdt_erc20": "Ethereum (ERC20)",
        "usdt_trc20": "TRON (TRC20)",
        "usdt_bep20": "BNB Smart Chain (BEP20)",
        "pol": "Polygon"
    }

    network = network_map.get(db_symbol, db_symbol.upper())

    return {
        "success": True,
        "preview": {
            "token": {
                "id": token_id,
                "symbol": token_symbol.upper(),
                "db_symbol": db_symbol,
                "name": token_name
            },
            "amounts": {
                "token_amount": amount,
                "token_price": round(1.0 if db_symbol.startswith("usdt_") else usdt_price, 4),
                "amount_usd": round(amount_usd, 2),
                "network_fee": round(fee_native, 6),
                "network_fee_currency": fee_currency,
                "network_fee_usd": round(fee_usd, 4),
                "total_usd": round(total_usd, 2)
            },
            "addresses": {
                "from": from_address,
                "to": to_address
            },
            "network_name": network,
            "balance": {
                "token_amount": round(token_balance, 8),
                "usd_amount": round(balance_usd, 2)
            },
            "timestamp": datetime.now().isoformat()
        }
    }


def save_transaction_to_db(transaction_data: Dict) -> int:
    try:
        with get_db_cursor() as cursor:
            crypto_type = get_crypto_type_from_symbol(transaction_data["token"])
            tx_hash = generate_tx_hash(crypto_type)

            cursor.execute("""
                           INSERT INTO transactions
                           (token, type, amount, date, from_address, to_address, tx_hash, fee, explorer_link, status)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                           """, (
                               transaction_data["token"],
                               "outcome",
                               transaction_data["amount_usd"],
                               datetime.now().strftime("%Y-%m-%d %H:%M"),
                               transaction_data["from_address"],
                               transaction_data["to_address"],
                               tx_hash,
                               transaction_data["fee"],
                               f"https://etherscan.io/tx/{tx_hash}",
                               "pending"
                           ))
            return cursor.lastrowid
    except Exception as e:
        print(f"[DB ERROR] Save transaction: {e}")
        return 0