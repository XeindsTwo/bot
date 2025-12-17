from datetime import datetime
from app.db import get_tokens, execute_query


def format_transaction_short(tx: dict) -> str:
    """Краткое форматирование транзакции"""
    tx_type = "📥" if tx["type"] == "income" else "📤"

    # Находим имя токена
    token_name = tx["token"]
    tokens = get_tokens()
    for token in tokens:
        if token[1] == tx["token"]:  # token[1] = symbol
            token_name = token[2]  # token[2] = name
            break

    date = datetime.strptime(tx["date"], '%Y-%m-%d %H:%M').strftime('%d.%m %H:%M')

    # Форматируем сумму
    amount = tx['amount']
    formatted_amount = f"${amount:,.2f}"

    return f"{tx_type} {token_name}: <code>{formatted_amount}</code> ({date})"


def format_transaction_detail(tx: dict) -> str:
    """Детальное форматирование транзакции"""
    tx_type = "📥 Получение" if tx["type"] == "income" else "📤 Отправка"

    # Находим имя токена и адрес
    token_name = tx["token"]
    token_address = ""
    tokens = get_tokens()
    for token in tokens:
        if token[1] == tx["token"]:
            token_name = token[2]
            token_address = token[4]  # address
            break

    date = datetime.strptime(tx["date"], '%Y-%m-%d %H:%M').strftime('%d.%m.%Y %H:%M')

    status_emoji = {
        "pending": "⏳",
        "completed": "✅",
        "failed": "❌"
    }.get(tx.get("status", "pending"), "⏳")

    # Форматируем сумму
    amount = tx['amount']
    formatted_amount = f"${amount:,.2f}"

    text = (
        f"<b>{tx_type}</b>\n\n"
        f"• <b>Токен:</b> {token_name}\n"
        f"• <b>Сумма:</b> <code>{formatted_amount}</code>\n"
        f"• <b>Дата:</b> {date}\n"
        f"• <b>Статус:</b> {status_emoji} {tx.get('status', 'pending')}\n"
    )

    if tx["type"] == "income":
        text += f"• <b>От кого:</b>\n<code>{tx['from_address']}</code>\n"
    else:
        text += f"• <b>Отправитель:</b>\n<code>{token_address if token_address else 'Адрес не указан'}</code>\n"
        text += f"• <b>Получатель:</b>\n<code>{tx['to_address']}</code>\n"

    if tx.get("fee", 0) > 0:
        fee = tx['fee']
        formatted_fee = f"${fee:,.2f}"
        text += f"• <b>Комиссия:</b> <code>{formatted_fee}</code>\n"

    if tx.get("tx_hash"):
        text += f"• <b>Хеш:</b>\n<code>{tx['tx_hash']}</code>\n"

    if tx.get("explorer_link"):
        text += f"• <b>Explorer:</b> {tx['explorer_link']}"

    return text


def get_total_transactions_count() -> int:
    """Получить общее количество транзакций"""
    result = execute_query("SELECT COUNT(*) as total FROM transactions")
    return result[0]["total"] if result else 0


def get_transactions_page(page: int = 1, limit: int = 20) -> tuple[list, int, int]:
    """Получить страницу транзакций"""
    offset = (page - 1) * limit

    result = execute_query(
        "SELECT * FROM transactions ORDER BY date DESC LIMIT ? OFFSET ?",
        (limit, offset)
    )

    total = get_total_transactions_count()
    transactions = []

    if result:
        for row in result:
            transactions.append(dict(row))

    total_pages = (total + limit - 1) // limit  # Округление вверх

    return transactions, total_pages, total


def get_history_stats() -> dict:
    """Получить статистику истории - ВАЖНО: total_outcome включает комиссии"""
    result = execute_query("""
                           SELECT COUNT(*)                                                                  as total,
                                  SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END)                     as total_income,
                                  SUM(CASE WHEN type = 'outcome' THEN amount + COALESCE(fee, 0) ELSE 0 END) as total_outcome
                           FROM transactions
                           """)

    if result:
        row = result[0]
        return {
            "total": row["total"] or 0,
            "total_income": float(row["total_income"] or 0),
            "total_outcome": float(row["total_outcome"] or 0)
        }

    return {"total": 0, "total_income": 0, "total_outcome": 0}