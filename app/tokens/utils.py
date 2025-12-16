import re


def validate_crypto_address(address: str) -> bool:
    """Базовая валидация крипто-адреса"""
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

    # Solana (базовая длина)
    if len(address) >= 32 and len(address) <= 44:
        return True

    return True  # Для неизвестных форматов просто пропускаем


def format_balance(balance: float, symbol: str = "") -> str:
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