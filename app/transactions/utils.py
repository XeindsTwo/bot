import random
import string
from datetime import datetime, timedelta
import hashlib


def generate_tx_hash():
    random_data = str(random.random()) + str(datetime.now().timestamp())
    hash_object = hashlib.sha256(random_data.encode())
    hex_digest = hash_object.hexdigest()

    if len(hex_digest) != 64:
        hex_digest = ''.join(random.choices('0123456789abcdef', k=64))

    return f"0x{hex_digest}"


def generate_fee_for_token(token_symbol):
    fee_ranges_usd = {
        'eth': (0.15, 0.7),  # средний простой ETH-трансфер ~$0.3-0.5
        'bnb': (0.02, 0.15),  # BNB Smart Chain перевод ≈ центы
        'matic': (0.001, 0.02),  # Polygon ≈ доли цента
        'usdt_erc20': (0.5, 5),  # USDT ERC-20 типично ~$1-$3, может выше
        'usdt_bep20': (0.02, 0.2),  # USDT на BNB Chain ≈ $0.05-$0.1
        'usdt_trc20': (0.2, 1),  # USDT TRC-20 ≈ ~$0.3-$1
        'btc': (1, 10),  # BTC обычный перевод $1-$10
        'tron': (0, 0.5),  # TRX почти бесплатно/центовые
        'sol': (0.0001, 0.005),
        'ton': (0.01, 0.1),  # обычно очень дешево
        'twt': (0.1, 0.5)
    }

    min_fee, max_fee = fee_ranges_usd.get(token_symbol.lower(), (0.5, 2))
    fee = random.uniform(min_fee, max_fee)

    if fee < 0.01:
        return round(fee, 4)
    elif fee < 1:
        return round(fee, 3)
    elif fee < 10:
        return round(fee, 2)
    else:
        return round(fee, 1)


def generate_fee():
    return round(random.uniform(0.001, 0.01), 6)


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
