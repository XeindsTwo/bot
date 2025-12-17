import re


def validate_crypto_address(address: str) -> bool:
    """Базовая валидация крипто-адреса (упрощённая версия)"""
    if not address or not address.strip():
        return False

    address = address.strip()

    # Ethereum/BSC/Polygon (0x...)
    if address.startswith('0x'):
        return len(address) == 42 and all(c in '0123456789abcdefABCDEF' for c in address[2:])

    # Bitcoin (начинается с 1, 3, bc1)
    if address.startswith('1') or address.startswith('3') or address.startswith('bc1'):
        return 26 <= len(address) <= 35

    # Tron (начинается с T)
    if address.startswith('T'):
        return len(address) == 34

    # Solana (длинные адреса)
    if len(address) >= 32 and len(address) <= 44:
        return True

    # Для остальных просто возвращаем True (чтобы не блокировать ввод)
    return True


def format_balance(balance: float) -> str:
    """Форматирует баланс для отображения"""
    if balance == 0:
        return "0"
    elif balance < 0.001:
        return f"{balance:.6f}"
    elif balance < 1:
        return f"{balance:.4f}"
    elif balance < 1000:
        return f"{balance:.2f}"
    else:
        return f"{balance:,.0f}".replace(",", " ")


# Добавь ещё эти функции если они используются в income
def parse_time_input(text: str):
    """Парсит время из текста"""
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


def parse_date_input(text: str):
    """Парсит дату из текста"""
    from datetime import datetime
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