from app.db import get_tokens, get_token_by_id


def find_token_by_id(token_id: str):
    tokens = get_tokens()
    try:
        token_id_int = int(token_id)
        for token in tokens:
            if token[0] == token_id_int:
                return token
    except ValueError:
        for token in tokens:
            if str(token[0]) == token_id:
                return token
    return None


def format_token_info(token, show_balance: bool = True) -> str:
    token_id, symbol, name, enabled, address, balance, locked = token[:7]
    info_parts = []

    if locked == 1:
        info_parts.append(f"<b>🔒 {name} (системный)</b>")
        info_parts.append(f"<i>Всегда включен, можно изменить только адрес</i>")
    else:
        status_emoji = "🟢" if enabled else "🔴"
        status_text = "Включен" if enabled else "Выключен"
        info_parts.append(f"<b>{name}</b>")
        info_parts.append(f"• Статус: {status_emoji} {status_text}")

    if show_balance:
        info_parts.append(f"• Баланс: <code>{balance:,.2f}</code>")

    if address:
        info_parts.append(f"• Адрес кошелька:\n<code>{address}</code>")
    else:
        info_parts.append(f"• Адрес кошелька: <i>не указан</i>")

    return "\n".join(info_parts)


def format_main_menu_balance() -> str:
    tokens = get_tokens()
    enabled_tokens = [t for t in tokens if t[3] == 1]

    if not enabled_tokens:
        return "🚫 Нет активных токенов"

    total = sum(t[5] for t in enabled_tokens)

    if total == 0:
        return f"💰 <b>Общий баланс (включённые монеты/токены): $0</b>"
    elif total < 1:
        return f"💰 <b>Общий баланс (включённые монеты/токены): ${total:.4f}</b>"
    elif total < 1000:
        return f"💰 <b>Общий баланс (включённые монеты/токены): ${total:.2f}</b>"
    else:
        return f"💰 <b>Общий баланс (включённые монеты/токены): ${total:,.0f}</b>"


def format_detailed_balances() -> str:
    tokens = get_tokens()
    enabled_tokens = [t for t in tokens if t[3] == 1]

    if not enabled_tokens:
        return "🚫 Нет активных токенов"

    lines = ["💰 <b>ДЕТАЛЬНЫЕ БАЛАНСЫ</b>\n"]
    total = 0

    tokens_with_balance = [t for t in enabled_tokens if t[5] > 0]
    empty_tokens = [t for t in enabled_tokens if t[5] == 0]

    tokens_with_balance.sort(key=lambda t: t[5], reverse=True)
    all_tokens = tokens_with_balance + empty_tokens

    for token in all_tokens:
        token_id, symbol, name, enabled, address, balance, locked = token[:7]
        total += balance
        if balance > 0:
            lines.append(f"• {name}: <code>${balance:,.2f}</code>")
        else:
            lines.append(f"• {name}: $0.00")

    lines.append(f"\n<b>📊 ИТОГО: ${total:,.2f}</b>")
    return "\n".join(lines)