import httpx
import random
from typing import Dict, Optional
from fastapi import HTTPException
from app.db import get_tokens, get_db_cursor
from datetime import datetime

from app.transactions.utils import (
    generate_fee_for_token,
    generate_tx_hash,
    get_crypto_type_from_symbol
)

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


async def get_real_binance_price(symbol: str) -> Optional[float]:
    """Получаем реальную цену с Binance"""
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


def find_token_in_db(symbol: str, db_symbol: str = None):
    """Ищем токен в БД с указанием конкретного db_symbol"""
    tokens = get_tokens()
    symbol_lower = symbol.lower()

    # Если передали db_symbol - ищем по нему
    if db_symbol:
        for token in tokens:
            if token[1].lower() == db_symbol.lower():
                return token

    # Старая логика для совместимости
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
    """Основная функция расчета preview"""
    # 1. Ищем токен в БД с указанием db_symbol
    token = find_token_in_db(token_symbol, db_symbol)
    if not token:
        raise HTTPException(404, f"Токен {token_symbol} не найден")

    token_id, db_symbol, token_name = token[0], token[1], token[2]
    from_address = token[4] if token[4] else "0xYourWalletAddress"
    balance_usd = float(token[5]) if token[5] else 0

    # 2. Определяем символ для цены (ИСПРАВЛЕНО!)
    price_symbol_map = {
        "matic": "MATIC",
        "tron": "TRX",
        "usdt_erc20": "ETH",
        "usdt_trc20": "TRX",
        "usdt_bep20": "BNB"  # ← ВОТ ОНО! BEP20 = BNB цена
    }

    price_req_symbol = price_symbol_map.get(db_symbol, db_symbol.upper())

    # 3. Получаем РЕАЛЬНУЮ цену с Binance
    real_price = await get_real_binance_price(price_req_symbol)

    # 4. ДЛЯ USDT ТОКЕНОВ ЦЕНА = 1.0!
    if db_symbol.startswith("usdt_"):
        real_price = 1.0  # USDT всегда 1:1 к доллару
        print(f"[DEBUG] USDT token: {db_symbol}, price forced to 1.0")

    if real_price is None:
        raise HTTPException(503, "Не удалось получить курс")

    # 5. Определяем сеть
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
        "usdt_bep20": "BNB Smart Chain (BEP20)"
    }

    network = network_map.get(db_symbol, db_symbol.upper())

    # 6. РАСЧЕТ КОМИССИИ
    fee_usd = generate_fee_for_token(db_symbol)

    # Для USDT токенов конвертируем правильно!
    if db_symbol.startswith("usdt_"):
        # Для USDT комиссия в нативной валюте сети
        fee_native = fee_usd / real_price if real_price > 0 else fee_usd
    else:
        fee_native = fee_usd / real_price if real_price > 0 else 0

    # Определяем валюту комиссии
    fee_currency_map = {
        "usdt_erc20": "ETH",
        "usdt_bep20": "BNB",  # ← BEP20 комиссия в BNB
        "usdt_trc20": "TRX",
        "matic": "POL",
        "tron": "TRX"
    }

    fee_currency = fee_currency_map.get(db_symbol, token_symbol.upper())

    # 7. РАСЧЕТ TOTAL USD (ИСПРАВЛЕНО!)
    # Для USDT: amount_usd = amount * 1.0
    # Для других: amount_usd = amount * real_price

    if db_symbol.startswith("usdt_"):
        amount_usd = amount  # USDT 1:1
    else:
        amount_usd = amount * real_price

    total_usd = amount_usd + fee_usd  # fee_usd уже в USD

    # 8. Баланс в токенах
    if db_symbol.startswith("usdt_"):
        token_balance = balance_usd  # USDT 1:1
    else:
        token_balance = balance_usd / real_price if real_price > 0 else 0

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
                "token_price": round(real_price, 4),
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
            "network": network,
            "balance": {
                "token_amount": round(token_balance, 8),
                "usd_amount": round(balance_usd, 2)
            },
            "timestamp": datetime.now().isoformat()
        }
    }


def save_transaction_to_db(transaction_data: Dict) -> int:
    """Сохраняем транзакцию в БД с реалистичным хэшем"""
    try:
        with get_db_cursor() as cursor:
            # Генерируем реалистичный хэш
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
                               tx_hash,  # ← реалистичный хэш
                               transaction_data["fee"],
                               f"https://etherscan.io/tx/{tx_hash}",  # ссылка на explorer
                               "pending"
                           ))
            return cursor.lastrowid
    except Exception as e:
        print(f"[DB ERROR] Save transaction: {e}")
        return 0
