import random
import string
from datetime import datetime, timedelta
import hashlib


def validate_crypto_address(address):
    """Простая валидация - только длина и префикс"""
    address = address.strip()

    if not address:
        return False, "Адрес не может быть пустым"

    # TRON
    if address.startswith('T'):
        if len(address) < 26:
            return False, f"TRON адрес слишком короткий ({len(address)} символов). Минимум 26"
        return True, "TRON адрес принят"

    # ETH/BSC
    elif address.startswith('0x'):
        if len(address) != 42:
            return False, f"ETH/BSC адрес должен быть 42 символа (получено {len(address)})"
        return True, "ETH/BSC адрес принят"

    # BTC
    elif address.startswith(('1', '3', 'bc1')):
        if len(address) < 26 or len(address) > 90:
            return False, f"BTC адрес неверной длины ({len(address)} символов)"
        return True, "BTC адрес принят"

    return False, "Неизвестный формат адреса"

def generate_tx_hash(crypto_type=None):
    """Генерация хеша транзакции для разных сетей"""
    random_data = f"{random.random()}{datetime.now().timestamp()}"
    hash_object = hashlib.sha256(random_data.encode())
    hex_digest = hash_object.hexdigest()

    # Форматируем в зависимости от типа сети
    if crypto_type == 'eth' or crypto_type == 'bnb':
        return f"0x{hex_digest[:64]}"
    elif crypto_type == 'tron':
        # TRON хеши обычно 64 символа без 0x
        return hex_digest[:64]
    elif crypto_type == 'btc':
        # BTC транзакции тоже 64 символа hex
        return hex_digest[:64]
    else:
        # По умолчанию как ETH
        return f"0x{hex_digest[:64]}"


def generate_fee_for_token(token_symbol):
    fee_ranges_usd = {
        'eth': (0.3, 4),
        'bnb': (0.015, 0.1),
        'matic': (0.0008, 0.015),
        'usdt_erc20': (4, 12),
        'usdt_bep20': (0.4, 1.5),
        'usdt_trc20': (0.08, 0.7),
        'btc': (0.3, 4),
        'tron': (0, 0.35),
        'trx': (0, 0.35),
        'sol': (0.00008, 0.003),
        'ton': (0.008, 0.07),
        'twt': (0.08, 0.35),
        'doge': (0.08, 0.7),
        'ltc': (0.008, 0.07)
    }

    token_symbol = token_symbol.lower()

    # Ищем подходящий диапазон
    for key, value in fee_ranges_usd.items():
        if key in token_symbol or token_symbol in key:
            min_fee, max_fee = value
            break
    else:
        min_fee, max_fee = (0.5, 2)  # По умолчанию

    fee = random.uniform(min_fee, max_fee)

    if fee < 0.01:
        return round(fee, 6)
    elif fee < 1:
        return round(fee, 4)
    elif fee < 10:
        return round(fee, 3)
    else:
        return round(fee, 2)


def parse_date_input(text):
    try:
        formats = ['%Y-%m-%d %H:%M', '%Y-%m-%d', '%d.%m.%Y %H:%M', '%d.%m.%Y']
        for fmt in formats:
            try:
                return datetime.strptime(text.strip(), fmt)
            except ValueError:
                continue
    except:
        pass
    return None


def parse_time_input(text):
    try:
        text = text.strip()
        text = ' '.join(text.split())

        if " " in text:
            hour_str, minute_str = text.split()
        elif ":" in text:
            hour_str, minute_str = text.split(":")
        else:
            hour_str = text
            minute_str = "00"

        hour = int(hour_str)
        minute = int(minute_str)

        if not (0 <= hour < 24 and 0 <= minute < 60):
            return None

        return hour, minute

    except (ValueError, IndexError):
        return None


def get_crypto_type_from_symbol(symbol):
    """Определение типа крипты по символу токена"""
    symbol = symbol.lower()

    if 'trx' in symbol or 'tron' in symbol:
        return 'tron'
    elif 'btc' in symbol or 'bitcoin' in symbol:
        return 'btc'
    elif 'eth' in symbol or 'ether' in symbol or 'erc20' in symbol:
        return 'eth'
    elif 'bnb' in symbol or 'bep20' in symbol:
        return 'bnb'
    elif 'matic' in symbol or 'polygon' in symbol:
        return 'eth'  # Используем ETH формат
    elif 'sol' in symbol or 'solana' in symbol:
        return 'eth'  # Solana тоже base58
    elif 'doge' in symbol or 'dogecoin' in symbol:
        return 'btc'  # Doge похож на BTC
    elif 'ltc' in symbol or 'litecoin' in symbol:
        return 'btc'
    else:
        return None  # Неизвестный тип
