import re


def validate_crypto_address(address: str, token_symbol: str = "") -> tuple[bool, str]:
    """Улучшенная валидация крипто-адреса с подсказками"""
    if not address or not address.strip():
        return False, "Адрес не может быть пустым"

    address = address.strip()

    # Определяем тип адреса по символу токена
    token_symbol = token_symbol.lower() if token_symbol else ""

    # Ethereum/BSC/Polygon (0x...)
    if address.startswith('0x'):
        if len(address) != 42:
            return False, f"ETH/BSC адрес должен быть 42 символа (у вас {len(address)})"

        # Проверяем hex-символы
        if not re.match(r'^0x[0-9a-fA-F]{40}$', address):
            return False, "ETH/BSC адрес должен содержать только 0-9, a-f, A-F"

        return True, "✅ Ethereum/BSC адрес"

    # Bitcoin (начинается с 1, 3, bc1)
    elif address.startswith(('1', '3', 'bc1')):
        if not (26 <= len(address) <= 90):
            return False, f"BTC адрес должен быть 26-90 символов (у вас {len(address)})"

        # Базовые символы для BTC
        if not re.match(r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$|^bc1[ac-hj-np-z02-9]{11,87}$', address):
            return False, "Неверный формат BTC адреса"

        return True, "✅ Bitcoin адрес"

    # Tron (начинается с T)
    elif address.startswith('T'):
        if len(address) != 34:
            return False, f"TRON адрес должен быть 34 символа (у вас {len(address)})"

        if not re.match(r'^T[A-Za-z0-9]{33}$', address):
            return False, "Неверный формат TRON адреса"

        return True, "✅ TRON адрес"

    # TON (начинается с EQ или UQ)
    elif address.startswith(('EQ', 'UQ')):
        if not (48 <= len(address) <= 50):
            return False, f"TON адрес должен быть 48-50 символов (у вас {len(address)})"

        return True, "✅ TON адрес"

    # Solana (длинный адрес)
    elif len(address) >= 32 and len(address) <= 44:
        if not re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address):
            return False, "Неверный формат Solana адреса"
        return True, "✅ Solana адрес"

    # Для остальных - базовая проверка
    if len(address) < 26:
        return False, f"Адрес слишком короткий ({len(address)} символов)"

    if len(address) > 90:
        return False, f"Адрес слишком длинный ({len(address)} символов)"

    return True, "✅ Адрес принят (базовая проверка)"


def format_balance(balance: float, symbol: str = "") -> str:
    """Форматирует баланс для отображения"""
    if balance == 0:
        return "0" + (f" {symbol}" if symbol else "")
    elif abs(balance) < 0.001:
        formatted = f"{balance:.8f}"
    elif abs(balance) < 1:
        formatted = f"{balance:.6f}"
    elif abs(balance) < 1000:
        formatted = f"{balance:.4f}"
    elif abs(balance) < 1000000:
        formatted = f"{balance:.2f}"
    else:
        formatted = f"{balance:,.0f}".replace(",", " ")

    return formatted + (f" {symbol}" if symbol else "")


def truncate_address(address: str, start_len: int = 10, end_len: int = 10) -> str:
    """Обрезает адрес для отображения"""
    if not address:
        return ""

    if len(address) <= start_len + end_len + 3:
        return address

    return f"{address[:start_len]}...{address[-end_len:]}"