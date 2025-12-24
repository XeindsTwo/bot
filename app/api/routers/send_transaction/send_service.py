import httpx
import random
from typing import Dict, Optional
from fastapi import HTTPException
from app.db import get_tokens, get_db_cursor
from datetime import datetime

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

# Нативные монеты (платят комиссию собой)
NATIVE_COINS = ["btc", "eth", "bnb", "matic", "tron", "sol", "ton", "pol"]

# Оптимизированные комиссии (конец 2025)
BASE_FEES = {
    "ETH": 0.0005,  # ~$2-3
    "BNB": 0.00025,  # ~$0.15
    "TRX": 5,  # ~$0.5
    "MATIC": 0.05,  # ~$0.04
    "BTC": 0.00002,  # ~$2
    "SOL": 0.000005,  # ~$0.1
    "TON": 0.05,  # ~$0.3
    "POL": 0.05,  # ~$0.04
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


async def get_estimated_gas_fee(symbol: str) -> float:
    """
    Оценка комиссии газа для разных сетей
    Возвращает примерную комиссию в USD
    """
    # Определяем символ для комиссии
    fee_symbol_map = {
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

    fee_symbol = fee_symbol_map.get(symbol, symbol.upper())

    # Используем оптимизированные базовые комиссии
    if fee_symbol in BASE_FEES:
        base_fee_native = BASE_FEES[fee_symbol]
        price = await get_real_binance_price(fee_symbol)
        if price:
            base_fee_usd = base_fee_native * price
        else:
            base_fee_usd = 1.5
    else:
        base_fee_usd = 1.5

    # Небольшая рандомизация
    variation = random.uniform(0.9, 1.1)
    fee_usd = round(base_fee_usd * variation, 4)

    # Лимиты комиссий
    if fee_usd < 0.05:
        fee_usd = 0.05
    elif fee_usd > 25:
        fee_usd = 25

    return fee_usd


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

    # Определяем, нативная ли это монета
    is_native = db_symbol in NATIVE_COINS

    # Получаем цены
    if db_symbol.startswith("usdt_"):
        # Для USDT токенов
        token_price = 1.0
        # Для комиссии нужна нативная валюта сети
        if db_symbol == "usdt_erc20":
            native_price = await get_real_binance_price("ETH")
        elif db_symbol == "usdt_bep20":
            native_price = await get_real_binance_price("BNB")
        elif db_symbol == "usdt_trc20":
            native_price = await get_real_binance_price("TRX")
        else:
            native_price = 1.0
        amount_usd = amount * token_price
    else:
        # Для нативных токенов
        price_symbol = db_symbol.upper()
        token_price = await get_real_binance_price(price_symbol)
        if token_price is None:
            raise HTTPException(503, f"Не удалось получить курс {price_symbol}")
        native_price = token_price
        amount_usd = amount * token_price

    # Получаем комиссию в USD
    fee_usd = await get_estimated_gas_fee(db_symbol)

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

    # Рассчитываем комиссию в нативной валюте
    fee_native = fee_usd / native_price if native_price > 0 else 0

    # Для нативных монет корректируем сумму отправки
    if is_native:
        # Баланс в токенах
        token_balance = balance_usd / token_price if token_price > 0 else 0

        # Проверяем, не превышает ли сумма + комиссия баланс
        if amount + fee_native > token_balance:
            # Автоматически корректируем
            final_send_amount = max(0.00000001, token_balance - fee_native)  # Минимум 1 сатоши
            was_adjusted = True
            # Пересчитываем amount_usd для скорректированной суммы
            amount_usd = final_send_amount * token_price
        else:
            final_send_amount = amount
            was_adjusted = False

        # Общая USD сумма (amount_usd + fee_usd)
        total_usd = amount_usd + fee_usd

    else:
        # Для токенов сумма не корректируется
        final_send_amount = amount
        was_adjusted = False
        total_usd = amount_usd  # Комиссия оплачивается отдельно

    # ОКРУГЛЕНИЕ ВСЕХ ЗНАЧЕНИЙ
    # Функция для правильного округления
    def smart_round(value: float, is_token_amount: bool = False) -> float:
        """Умное округление с учетом типа значения"""
        if value == 0:
            return 0.0

        if is_token_amount:
            # Для сумм токенов: максимум 8 знаков
            return round(value, 8)
        elif value < 0.001:
            # Для очень маленьких значений: 8 знаков
            return round(value, 8)
        elif value < 1:
            # Для значений < 1: 6 знаков
            return round(value, 6)
        else:
            # Для больших значений: 2 знака
            return round(value, 2)

    # Округляем значения
    token_amount_display = smart_round(amount, True)  # Что показываем пользователю
    final_send_amount = smart_round(final_send_amount, True)  # Что будем отправлять
    fee_native = smart_round(fee_native, True)
    fee_usd = round(fee_usd, 4)
    amount_usd = round(amount_usd, 2)
    total_usd = round(total_usd, 2)
    token_price = round(token_price, 4)

    # Баланс для отображения
    if db_symbol.startswith("usdt_"):
        token_balance_display = balance_usd
    else:
        token_balance_display = balance_usd / token_price if token_price > 0 else 0
    token_balance_display = smart_round(token_balance_display, True)

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
                "token_amount": token_amount_display,  # Что показываем пользователю
                "token_price": token_price,
                "amount_usd": amount_usd,
                "network_fee": fee_native,
                "network_fee_currency": fee_currency,
                "network_fee_usd": fee_usd,
                "total_usd": total_usd,
                "is_native": is_native,
                "was_adjusted": was_adjusted,
                "final_send_amount": final_send_amount  # Что фактически отправится
            },
            "addresses": {
                "from": from_address,
                "to": to_address
            },
            "network_name": network,
            "balance": {
                "token_amount": token_balance_display,
                "usd_amount": round(balance_usd, 2)
            },
            "timestamp": datetime.now().isoformat()
        }
    }


def save_transaction_to_db(transaction_data: Dict) -> int:
    try:
        with get_db_cursor() as cursor:
            from app.transactions.utils import generate_tx_hash, get_crypto_type_from_symbol
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