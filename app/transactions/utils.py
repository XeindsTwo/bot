import random
import string
from datetime import datetime, timedelta
import hashlib


def validate_crypto_address(address, crypto_type=None):
    """
    Валидация крипто-адресов
    crypto_type: 'tron', 'btc', 'eth', 'bnb' или None (автоопределение)
    """
    address = address.strip()

    # Общие проверки
    if not address:
        return False, "❌ Адрес не может быть пустым"

    if len(address) < 10:
        return False, "❌ Адрес слишком короткий"

    # Определяем тип по префиксу если не указан
    if crypto_type is None:
        if address.startswith('T'):
            crypto_type = 'tron'
        elif address.startswith(('1', '3', 'bc1')):
            crypto_type = 'btc'
        elif address.startswith(('0x', '0X')):
            crypto_type = 'eth'
        elif address.startswith('bnb'):
            crypto_type = 'bnb'
        else:
            crypto_type = 'unknown'

    # Валидация по типу
    if crypto_type == 'tron':
        if not address.startswith('T'):
            return False, "❌ TRON адрес должен начинаться с 'T'"
        if len(address) < 26:
            return False, f"❌ TRON адрес слишком короткий ({len(address)} символов). Минимум 26"
        # Проверка символов (только hex)
        allowed_chars = set('0123456789abcdefABCDEF')
        address_clean = address[1:]  # Убираем T
        invalid_chars = set(address_clean) - allowed_chars
        if invalid_chars:
            return False, f"❌ Неверные символы в TRON адресе: {''.join(invalid_chars)}\n💡 Используйте только цифры 0-9 и буквы a-f/A-F"
        return True, "✅ TRON адрес валиден"

    elif crypto_type == 'btc':
        if not address.startswith(('1', '3', 'bc1')):
            return False, "❌ BTC адрес должен начинаться с '1', '3' или 'bc1'"
        if len(address) < 26 or len(address) > 90:
            return False, f"❌ BTC адрес неверной длины ({len(address)} символов). Должно быть 26-90 символов"

        # Проверка для Legacy/SegWit адресов (не bech32)
        if not address.startswith('bc1'):
            allowed_chars = set('123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz')
            invalid_chars = set(address) - allowed_chars
            if invalid_chars:
                bad_chars = ''.join([c for c in invalid_chars if c not in '0OIl'])
                if bad_chars:
                    return False, f"❌ Неверные символы в BTC адресе: {bad_chars}"
        return True, "✅ BTC адрес валиден"

    elif crypto_type == 'eth':
        if not address.startswith('0x'):
            return False, "❌ ETH адрес должен начинаться с '0x'"
        if len(address) != 42:
            return False, f"❌ ETH адрес должен быть 42 символа (получено {len(address)})"
        # Проверка hex символов
        hex_part = address[2:]
        try:
            int(hex_part, 16)
        except ValueError:
            return False, "❌ Неверный формат HEX в ETH адресе"
        return True, "✅ ETH адрес валиден"

    elif crypto_type == 'bnb':
        if not address.startswith('bnb'):
            return False, "❌ BNB адрес должен начинаться с 'bnb'"
        if len(address) != 42:
            return False, f"❌ BNB адрес должен быть 42 символа"
        return True, "✅ BNB адрес валиден"

    return True, "✅ Адрес принят (базовая проверка)"


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
        'eth': (0.15, 0.7),
        'bnb': (0.02, 0.15),
        'matic': (0.001, 0.02),
        'usdt_erc20': (0.5, 5),
        'usdt_bep20': (0.02, 0.2),
        'usdt_trc20': (0.2, 1),
        'btc': (1, 10),
        'tron': (0, 0.5),
        'trx': (0, 0.5),
        'sol': (0.0001, 0.005),
        'ton': (0.01, 0.1),
        'twt': (0.1, 0.5),
        'doge': (0.1, 1),
        'ltc': (0.01, 0.1)
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