import random
import string
from datetime import datetime, timedelta
import hashlib


def generate_tx_hash():
    """Генерация реалистичного хеша транзакции по SHA-256 (64 hex символа)"""
    # Создаём случайные данные
    random_data = str(random.random()) + str(datetime.now().timestamp())

    # Хешируем по SHA-256
    hash_object = hashlib.sha256(random_data.encode())
    hex_digest = hash_object.hexdigest()

    # Проверяем что получилось 64 символа (стандарт для SHA-256)
    if len(hex_digest) != 64:
        # Если что-то пошло не так, генерируем вручную
        hex_digest = ''.join(random.choices('0123456789abcdef', k=64))

    # Добавляем префикс 0x для Ethereum-подобных сетей
    return f"0x{hex_digest}"


def generate_fee_for_token(token_symbol):
    """Генерация реалистичной комиссии для конкретного токена"""
    fee_ranges = {
        # EVM сети (комиссия в нативном токене)
        'eth': (0.001, 0.03),  # ETH
        'bnb': (0.0001, 0.001),  # BNB
        'matic': (0.01, 0.1),  # MATIC

        # USDT в разных сетях (комиссия в нативном токене сети)
        'usdt_erc20': (0.001, 0.02),  # ETH для газа
        'usdt_bep20': (0.0001, 0.001),  # BNB для газа
        'usdt_trc20': (1, 10),  # TRX для энергии

        # Другие сети
        'btc': (0.00001, 0.0003),  # BTC
        'tron': (1, 10),  # TRX
        'sol': (0.000001, 0.00001),  # SOL
        'ton': (0.05, 0.3),  # TON
    }

    # Получаем диапазон для токена или используем дефолтный
    min_fee, max_fee = fee_ranges.get(token_symbol.lower(), (0.001, 0.01))

    # Генерируем случайную комиссию в диапазоне
    fee = random.uniform(min_fee, max_fee)

    # Округляем в зависимости от токена
    if token_symbol.lower() in ['btc', 'eth', 'bnb']:
        return round(fee, 6)
    elif token_symbol.lower() in ['usdt_trc20', 'tron']:
        return round(fee, 2)  # TRX обычно целые числа
    else:
        return round(fee, 4)


def generate_fee():
    """Старая функция для обратной совместимости"""
    return round(random.uniform(0.001, 0.01), 6)


def parse_date_input(text):
    try:
        # Пытаемся парсить разные форматы
        formats = ['%Y-%m-%d %H:%M', '%Y-%m-%d', '%d.%m.%Y %H:%M', '%d.%m.%Y']

        for fmt in formats:
            try:
                return datetime.strptime(text.strip(), fmt)
            except ValueError:
                continue
    except:
        pass

    return None