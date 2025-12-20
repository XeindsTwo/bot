import sqlite3
import logging
from contextlib import contextmanager
from typing import Any, Optional, List, Tuple

DB_PATH = "bot.db"
logger = logging.getLogger(__name__)


# ========== УПРАВЛЕНИЕ ПОДКЛЮЧЕНИЯМИ ==========
class ConnectionPool:
    """Простой пул соединений для SQLite для снижения накладных расходов"""

    def __init__(self, database: str, max_connections: int = 5):
        self.database = database
        self.max_connections = max_connections
        self._connections = []
        self._in_use = set()

    def get_connection(self) -> sqlite3.Connection:
        """Получить соединение из пула или создать новое"""
        # Ищем свободное соединение
        for conn in self._connections:
            if id(conn) not in self._in_use:
                self._in_use.add(id(conn))
                return conn

        if len(self._connections) < self.max_connections:
            conn = sqlite3.connect(self.database, check_same_thread=False)
            conn.row_factory = sqlite3.Row  # Для удобства доступа по имени столбца
            self._connections.append(conn)
            self._in_use.add(id(conn))
            logger.debug(f"Создано новое соединение. Всего в пуле: {len(self._connections)}")
            return conn

        raise RuntimeError("Достигнут лимит соединений в пуле")

    def return_connection(self, conn: sqlite3.Connection):
        """Вернуть соединение в пул"""
        if id(conn) in self._in_use:
            self._in_use.remove(id(conn))


# Глобальный пул соединений
_connection_pool = ConnectionPool(DB_PATH)


@contextmanager
def get_db_connection():
    """Контекстный менеджер для безопасной работы с БД"""
    conn = None
    try:
        conn = _connection_pool.get_connection()
        yield conn
    except Exception as e:
        logger.error(f"Ошибка БД: {e}", exc_info=True)
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            _connection_pool.return_connection(conn)


@contextmanager
def get_db_cursor():
    """Контекстный менеджер для работы с курсором"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()  # Фиксируем транзакцию при успехе
        except Exception as e:
            conn.rollback()  # Откатываем при ошибке [citation:5][citation:8]
            logger.error(f"Ошибка транзакции: {e}")
            raise


# ========== БЕЗОПАСНЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С БД ==========
def execute_query(query: str, params: tuple = ()) -> Optional[List[Any]]:
    """Безопасное выполнение запроса с параметрами"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(query, params)  # Параметризованный запрос[citation:2][citation:9]
            if query.strip().upper().startswith(('SELECT', 'PRAGMA')):
                return cursor.fetchall()
    except Exception as e:
        logger.error(f"Ошибка выполнения запроса '{query}': {e}")
        return None


def executemany_query(query: str, params_list: List[tuple]) -> bool:
    """Безопасное выполнение массовой вставки"""
    try:
        with get_db_cursor() as cursor:
            cursor.executemany(query, params_list)  # Параметризованный запрос[citation:2]
            return True
    except Exception as e:
        logger.error(f"Ошибка массовой вставки '{query}': {e}")
        return False


# ========== ИНИЦИАЛИЗАЦИЯ БД ==========
def init_db():
    """Инициализация базы данных с использованием транзакций"""
    init_queries = [
        """CREATE TABLE IF NOT EXISTS tokens
           (
               id      INTEGER PRIMARY KEY,
               token   TEXT UNIQUE,
               name    TEXT,
               enabled BOOLEAN DEFAULT 0,
               address TEXT    DEFAULT '',
               balance REAL    DEFAULT 0,
               locked  BOOLEAN DEFAULT 0
           )""",
        """CREATE TABLE IF NOT EXISTS transactions
           (
               id            INTEGER PRIMARY KEY,
               token         TEXT,
               type          TEXT,
               amount        REAL,
               date          TEXT,
               from_address  TEXT,
               to_address    TEXT,
               tx_hash       TEXT,
               fee           REAL,
               explorer_link TEXT,
               status        TEXT DEFAULT 'pending'
           )"""
    ]

    default_tokens = [
        ("bnb", "BNB", 1, 1),
        ("btc", "BTC", 1, 1),
        ("eth", "ETH", 1, 1),
        ("matic", "Polygon", 1, 1),
        ("tron", "TRON", 1, 1),
        ("twt", "TWT", 1, 1)
    ]

    admin_tokens = [
        ("usdt_erc20", "USDT (ERC20)"),
        ("usdt_trc20", "USDT (TRC20)"),
        ("usdt_bep20", "USDT (BEP20)"),
        ("ton", "TON"),
        ("sol", "SOL")
    ]

    try:
        with get_db_cursor() as cursor:
            # Создаем таблицы
            for query in init_queries:
                cursor.execute(query)

            # Вставляем дефолтные токены (игнорируем дубликаты)
            for token, name, enabled, locked in default_tokens:
                cursor.execute(
                    "INSERT OR IGNORE INTO tokens (token, name, enabled, locked) VALUES (?, ?, ?, ?)",
                    (token, name, enabled, locked)
                )

            # Вставляем админские токены
            for token, name in admin_tokens:
                cursor.execute(
                    "INSERT OR IGNORE INTO tokens (token, name, locked) VALUES (?, ?, 0)",
                    (token, name)
                )

        logger.info("База данных успешно инициализирована")
        return True
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}", exc_info=True)
        return False


# ========== ОСНОВНЫЕ ФУНКЦИИ ==========
def get_tokens() -> List[sqlite3.Row]:
    """Получить все токены (возвращает Row объекты для доступа по имени)"""
    result = execute_query(
        "SELECT id, token, name, enabled, address, balance, locked FROM tokens"
    )
    return result or []


def update_token(token_id: int, enabled: Optional[bool] = None, address: Optional[str] = None) -> bool:
    """БЕЗОПАСНОЕ обновление токена по ID"""
    updates = []
    params = []

    if enabled is not None:
        updates.append("enabled = ?")
        params.append(1 if enabled else 0)

    if address is not None:
        updates.append("address = ?")
        params.append(address)

    if not updates:
        return True

    params.append(token_id)
    query = f"UPDATE tokens SET {', '.join(updates)} WHERE id = ?"

    result = execute_query(query, tuple(params))
    return result is not None  # execute_query возвращает None при ошибке


def get_token_by_id(token_id: int) -> Optional[sqlite3.Row]:
    """Получить токен по ID"""
    result = execute_query(
        "SELECT id, token, name, enabled, address, balance, locked FROM tokens WHERE id = ?",
        (token_id,)
    )
    return result[0] if result else None


def update_balance(token_id: int, delta: float) -> bool:
    """Обновить баланс токена атомарно"""
    result = execute_query(
        "UPDATE tokens SET balance = balance + ? WHERE id = ?",
        (delta, token_id)
    )
    return result is not None


def create_transaction(
        token: str,
        tx_type: str,
        amount: float,
        date: str,
        **kwargs
) -> bool:
    """Создать запись о транзакции"""
    query = """
            INSERT INTO transactions
            (token, type, amount, date, from_address, to_address, tx_hash, fee, explorer_link)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) \
            """
    params = (
        token, tx_type, amount, date,
        kwargs.get('from_addr', ''),
        kwargs.get('to_addr', ''),
        kwargs.get('tx_hash', ''),
        kwargs.get('fee', 0),
        kwargs.get('explorer_link', '')
    )

    result = execute_query(query, params)
    return result is not None


def get_transactions(limit: int = 50) -> List[sqlite3.Row]:
    """Получить последние транзакции"""
    result = execute_query(
        "SELECT * FROM transactions ORDER BY date DESC LIMIT ?",
        (limit,)
    )
    return result or []


def update_transaction_status(tx_id: int, status: str) -> bool:
    """Обновить статус транзакции"""
    result = execute_query(
        "UPDATE transactions SET status = ? WHERE id = ?",
        (status, tx_id)
    )
    return result is not None


def update_token_balance(token_id: int, new_balance_usd: float):
    """
    Обновляет баланс токена в USD
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
                       UPDATE tokens
                       SET balance = ?
                       WHERE id = ?
                       """, (new_balance_usd, token_id))

        conn.commit()
        return True
    except Exception as e:
        print(f"Ошибка обновления токена {token_id}: {e}")
        return False
    finally:
        conn.close()