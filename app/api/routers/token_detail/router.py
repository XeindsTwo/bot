from fastapi import APIRouter, HTTPException, Query
from app.db import get_transactions_by_token, get_transaction_count_by_token
from .price_service import fetch_binance_price
from .chart_service import generate_chart_data_1d
from .mapping_service import (
    find_token_by_symbol,
    get_display_symbol,
    get_network_for_frontend
)

router = APIRouter(prefix="/api/token", tags=["token"])


def format_transactions(transactions, price: float):
    """Форматируем транзакции"""
    formatted = []

    for tx in transactions:
        if len(tx) >= 11:
            status = tx[10]
        else:
            status = "confirmed"

        usd_amount = float(tx[3]) if tx[3] else 0
        token_amount_display = usd_amount / price if price > 0 else usd_amount

        formatted.append({
            "id": tx[0],
            "type": tx[2],
            "amount_usd": usd_amount,
            "amount_token": round(token_amount_display, 6),
            "date": tx[4],
            "from_address": tx[5] if tx[5] else "",
            "to_address": tx[6] if tx[6] else "",
            "tx_hash": tx[7] if tx[7] else "",
            "fee": float(tx[8]) if tx[8] else 0,
            "explorer_link": tx[9] if tx[9] else "",
            "status": status
        })

    return formatted


@router.get("/{symbol}")
async def get_token_detail(symbol: str):
    """Полная информация о токене"""
    try:
        # Ищем токен
        token, db_symbol = find_token_by_symbol(symbol)
        if not token:
            raise HTTPException(status_code=404, detail=f"Token '{symbol}' not found")

        # Получаем цену
        if db_symbol.startswith("usdt_"):
            price_data = {
                "price": 1.0,
                "change_24h": 0.0,
                "high_24h": 1.0,
                "low_24h": 1.0,
                "volume_24h": 1000000
            }
        else:
            price_data = await fetch_binance_price(db_symbol)
            if not price_data:
                raise HTTPException(
                    status_code=503,
                    detail=f"Не удалось получить данные о цене для {symbol} с Binance"
                )

        # Баланс
        balance_usd = float(token[5]) if token[5] else 0
        token_amount = balance_usd / price_data["price"] if price_data["price"] > 0 else 0

        # Транзакции
        transactions = get_transactions_by_token(db_symbol, limit=30)
        formatted_transactions = format_transactions(transactions, price_data["price"])

        # Display символ и сеть
        display_symbol = get_display_symbol(db_symbol)

        # Берем network из БД (колонка 8)
        db_network = token[8] if len(token) > 8 else ""
        network_for_frontend = get_network_for_frontend(db_symbol, db_network)

        # Генерируем график
        if price_data and "price" in price_data and "change_24h" in price_data:
            chart_data = generate_chart_data_1d(price_data["price"], price_data["change_24h"])
        else:
            chart_data = []

        return {
            "success": True,
            "token": {
                "id": token[0],
                "symbol": display_symbol,
                "db_symbol": db_symbol,
                "name": token[2],
                "full_name": token[7] if len(token) > 7 and token[7] else token[2],
                "network": network_for_frontend,
                "address": token[4] if token[4] else "",
                "enabled": bool(token[3]),
                "locked": bool(token[6]),

                "balance_usd": round(balance_usd, 2),
                "token_amount": round(token_amount, 8),

                "current_price": round(price_data["price"], 4),
                "price_change_24h": round(price_data["change_24h"], 2),
                "price_change_amount": round(price_data["price"] * price_data["change_24h"] / 100, 4),
                "high_24h": round(price_data["high_24h"], 4),
                "low_24h": round(price_data["low_24h"], 4),
                "volume_24h": round(price_data["volume_24h"], 2),

                "is_stablecoin": db_symbol.startswith("usdt_"),
                "is_up": price_data["change_24h"] >= 0
            },
            "transactions": formatted_transactions,
            "chart_data": chart_data
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] get_token_detail: {e}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@router.get("/{symbol}/price")
async def get_token_price_only(symbol: str):
    """Получаем только цену токена"""
    try:
        db_symbol = symbol.lower()

        if db_symbol == "pol":
            db_symbol = "matic"
        elif db_symbol == "trx":
            db_symbol = "tron"

        if db_symbol.startswith("usdt") or db_symbol == "usdt":
            return {
                "success": True,
                "symbol": symbol.upper(),
                "price": 1.0,
                "change_24h": 0.0
            }

        price_data = await fetch_binance_price(db_symbol)
        if price_data:
            return {
                "success": True,
                "symbol": symbol.upper(),
                "price": price_data["price"],
                "change_24h": price_data["change_24h"]
            }
        else:
            raise HTTPException(
                status_code=503,
                detail=f"Не удалось получить цену для {symbol}"
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] get_token_price_only: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/{symbol}/transactions")
async def get_token_transactions(
        symbol: str,
        page: int = Query(1, ge=1, description="Номер страницы"),
        limit: int = Query(20, ge=1, le=100, description="Количество транзакций на страницу")
):
    """Получаем транзакции по конкретному токену с пагинацией"""
    try:
        # Ищем токен
        token, db_symbol = find_token_by_symbol(symbol)
        if not token:
            raise HTTPException(status_code=404, detail=f"Token '{symbol}' not found")

        # Получаем текущую цену для конвертации
        if db_symbol.startswith("usdt_"):
            current_price = 1.0
        else:
            price_data = await fetch_binance_price(db_symbol)
            current_price = price_data["price"] if price_data else 1.0

        # Рассчитываем offset для пагинации
        offset = (page - 1) * limit

        # Получаем транзакции
        transactions = get_transactions_by_token(db_symbol, limit, offset)
        total_count = get_transaction_count_by_token(db_symbol)

        # Форматируем транзакции
        formatted_transactions = []
        for tx in transactions:
            if len(tx) >= 11:
                status = tx[10]
            else:
                status = "confirmed"

            usd_amount = float(tx[3]) if tx[3] else 0
            token_amount_display = usd_amount / current_price if current_price > 0 else usd_amount

            formatted_transactions.append({
                "id": tx[0],
                "type": tx[2],
                "amount_usd": usd_amount,
                "amount_token": round(token_amount_display, 6),
                "date": tx[4],
                "from_address": tx[5] if tx[5] else "",
                "to_address": tx[6] if tx[6] else "",
                "tx_hash": tx[7] if tx[7] else "",
                "fee": float(tx[8]) if tx[8] else 0,
                "explorer_link": tx[9] if tx[9] else "",
                "status": status
            })

        # Рассчитываем общее количество страниц
        total_pages = (total_count + limit - 1) // limit  # Округление вверх

        return {
            "success": True,
            "token": {
                "symbol": symbol.upper(),
                "db_symbol": db_symbol,
                "current_price": current_price
            },
            "pagination": {
                "page": page,
                "limit": limit,
                "total_items": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            },
            "transactions": formatted_transactions
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] get_token_transactions: {e}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@router.get("/{symbol}/transactions/latest")
async def get_latest_token_transactions(
        symbol: str,
        limit: int = Query(5, ge=1, le=50, description="Количество последних транзакций")
):
    """Получаем последние транзакции по токену (для виджета)"""
    try:
        token, db_symbol = find_token_by_symbol(symbol)
        if not token:
            raise HTTPException(status_code=404, detail=f"Token '{symbol}' not found")

        # Получаем текущую цену
        if db_symbol.startswith("usdt_"):
            current_price = 1.0
        else:
            price_data = await fetch_binance_price(db_symbol)
            current_price = price_data["price"] if price_data else 1.0

        # Получаем последние транзакции
        transactions = get_transactions_by_token(db_symbol, limit, 0)

        # Форматируем
        formatted_transactions = []
        for tx in transactions:
            if len(tx) >= 11:
                status = tx[10]
            else:
                status = "confirmed"

            usd_amount = float(tx[3]) if tx[3] else 0
            token_amount_display = usd_amount / current_price if current_price > 0 else usd_amount

            formatted_transactions.append({
                "id": tx[0],
                "type": tx[2],
                "amount_usd": usd_amount,
                "amount_token": round(token_amount_display, 6),
                "date": tx[4],
                "from_address": tx[5] if tx[5] else "",
                "to_address": tx[6] if tx[6] else "",
                "status": status,
                "is_deposit": tx[2] == "deposit"
            })

        return {
            "success": True,
            "token": symbol.upper(),
            "transactions": formatted_transactions,
            "total_count": len(formatted_transactions)
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] get_latest_token_transactions: {e}")
        return {
            "success": False,
            "error": str(e),
            "transactions": []
        }
