from app.db import get_tokens

# Маппинг отображаемых символов
DISPLAY_SYMBOLS = {
    "matic": "POL",
    "tron": "TRX",
}


def create_symbol_mapping():
    """Создаем маппинг всех возможных вариантов символов"""
    db_tokens = get_tokens()
    symbol_mapping = {}

    for t in db_tokens:
        db_symbol = t[1]

        # Основной символ для отображения
        if db_symbol == "matic":
            display_symbol = "POL"
        elif db_symbol == "tron":
            display_symbol = "TRX"
        elif db_symbol.startswith("usdt_"):
            display_symbol = "USDT"
        else:
            display_symbol = db_symbol.upper()

        # Добавляем все возможные варианты поиска
        symbol_mapping[display_symbol.lower()] = t
        symbol_mapping[db_symbol.lower()] = t

        # Особые случаи
        if db_symbol == "matic":
            symbol_mapping["pol"] = t
        elif db_symbol == "tron":
            symbol_mapping["trx"] = t
        elif db_symbol == "usdt_erc20":
            symbol_mapping["usdt"] = t
            symbol_mapping["usdt_eth"] = t
        elif db_symbol == "usdt_trc20":
            symbol_mapping["usdt_tron"] = t
        elif db_symbol == "usdt_bep20":
            symbol_mapping["usdt_bnb"] = t
            symbol_mapping["usdt_bsc"] = t

    return symbol_mapping


def find_token_by_symbol(symbol: str):
    """Ищем токен по символу"""
    symbol_mapping = create_symbol_mapping()

    if symbol.isdigit():
        # Поиск по ID
        token_id = int(symbol)
        db_tokens = get_tokens()
        for t in db_tokens:
            if t[0] == token_id:
                return t, t[1]
    else:
        # Поиск по символу
        token = symbol_mapping.get(symbol.lower())
        if token:
            return token, token[1]

    return None, ""


def get_display_symbol(db_symbol: str) -> str:
    """Получаем символ для отображения на фронте"""
    if db_symbol == "matic":
        return "POL"
    elif db_symbol == "tron":
        return "TRX"
    elif db_symbol.startswith("usdt_"):
        return "USDT"
    return db_symbol.upper()


def get_network_for_frontend(db_symbol: str, db_network: str = "") -> str:
    """Определяем сеть для фронта - ТОЛЬКО если указана в БД"""

    # 1. Если в БД network пустой → возвращаем пустую строку
    if not db_network or db_network.strip() == "":
        return ""

    # 2. Для USDT токенов - возвращаем сеть из БД
    if db_symbol.startswith("usdt_"):
        return db_network.lower()  # "eth", "bnb", "tron"

    # 3. Для TWT - возвращаем сеть из БД
    if db_symbol == "twt":
        return db_network.lower()  # "bnb"

    # 4. Для остальных - пусто (даже если что-то записано)
    return ""