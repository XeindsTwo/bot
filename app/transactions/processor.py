import asyncio
import random
import logging
from datetime import datetime
from app.db import get_db_cursor, get_pending_transactions, update_transaction_status

logger = logging.getLogger(__name__)


async def process_pending_transactions():
    """Фоновая обработка pending транзакций"""
    while True:
        try:
            pending_txs = get_pending_transactions()

            for tx in pending_txs:
                tx_id = tx[0]
                tx_hash = tx[7] if len(tx) > 7 else ""

                # Рандомная задержка 5-10 секунд
                delay = random.uniform(5, 10)
                await asyncio.sleep(delay)

                # Меняем статус на confirmed
                update_transaction_status(tx_id, "confirmed")

                logger.info(f"Транзакция {tx_hash} подтверждена")

            # Ждем перед следующей проверкой
            await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"Ошибка обработки транзакций: {e}")
            await asyncio.sleep(5)


def start_transaction_processor():
    """Запуск процессора транзакций в фоне"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(process_pending_transactions())
    return loop