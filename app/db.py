import sqlite3
import logging
from contextlib import contextmanager
from typing import Any, Optional, List

DB_PATH = "bot.db"
logger = logging.getLogger(__name__)


class ConnectionPool:
    def __init__(self, database: str, max_connections: int = 5):
        self.database = database
        self.max_connections = max_connections
        self._connections = []
        self._in_use = set()

    def get_connection(self) -> sqlite3.Connection:
        for conn in self._connections:
            if id(conn) not in self._in_use:
                self._in_use.add(id(conn))
                return conn

        if len(self._connections) < self.max_connections:
            conn = sqlite3.connect(self.database, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self._connections.append(conn)
            self._in_use.add(id(conn))
            return conn

        raise RuntimeError("Достигнут лимит соединений в пуле")

    def return_connection(self, conn: sqlite3.Connection):
        if id(conn) in self._in_use:
            self._in_use.remove(id(conn))


_connection_pool = ConnectionPool(DB_PATH)


@contextmanager
def get_db_connection():
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
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка транзакции: {e}")
            raise


def execute_query(query: str, params: tuple = ()) -> Optional[List[Any]]:
    try:
        with get_db_cursor() as cursor:
            cursor.execute(query, params)
            if query.strip().upper().startswith(('SELECT', 'PRAGMA')):
                return cursor.fetchall()
    except Exception as e:
        logger.error(f"Ошибка выполнения запроса '{query}': {e}")
        return None


def executemany_query(query: str, params_list: List[tuple]) -> bool:
    try:
        with get_db_cursor() as cursor:
            cursor.executemany(query, params_list)
            return True
    except Exception as e:
        logger.error(f"Ошибка массовой вставки '{query}': {e}")
        return False


def add_new_columns():
    """Добавляем новые колонки если их нет"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("PRAGMA table_info(tokens)")
            columns = [col[1] for col in cursor.fetchall()]

            if 'full_name' not in columns:
                cursor.execute("ALTER TABLE tokens ADD COLUMN full_name TEXT DEFAULT ''")
                print("Добавлена колонка full_name")

            if 'network' not in columns:
                cursor.execute("ALTER TABLE tokens ADD COLUMN network TEXT DEFAULT ''")
                print("Добавлена колонка network")

            # Обновляем записи дефолтными значениями
            token_defaults = {
                "bnb": {"full_name": "BNB", "network": "BNB Smart Chain"},
                "btc": {"full_name": "Bitcoin", "network": "Bitcoin"},
                "eth": {"full_name": "Ethereum", "network": "Ethereum"},
                "matic": {"full_name": "Polygon", "network": "Polygon"},
                "tron": {"full_name": "TRON", "network": "TRON"},
                "twt": {"full_name": "Trust Wallet Token", "network": "BNB Smart Chain"},
                "usdt_erc20": {"full_name": "USDT", "network": "Ethereum"},
                "usdt_trc20": {"full_name": "USDT", "network": "TRON"},
                "usdt_bep20": {"full_name": "USDT", "network": "BNB Smart Chain"},
                "ton": {"full_name": "TON", "network": "TON"},
                "sol": {"full_name": "Solana", "network": "Solana"}
            }

            for token, defaults in token_defaults.items():
                cursor.execute(
                    "UPDATE tokens SET full_name = ?, network = ? WHERE token = ? AND (full_name = '' OR network = '')",
                    (defaults["full_name"], defaults["network"], token)
                )
    except Exception as e:
        print(f"Ошибка добавления колонок: {e}")


def init_db():
    init_queries = [
        """CREATE TABLE IF NOT EXISTS tokens
           (
               id        INTEGER PRIMARY KEY,
               token     TEXT UNIQUE,
               name      TEXT,
               enabled   BOOLEAN DEFAULT 0,
               address   TEXT    DEFAULT '',
               balance   REAL    DEFAULT 0,
               locked    BOOLEAN DEFAULT 0,
               full_name TEXT    DEFAULT '',
               network   TEXT    DEFAULT ''
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
            for query in init_queries:
                cursor.execute(query)

            for token, name, enabled, locked in default_tokens:
                cursor.execute(
                    "INSERT OR IGNORE INTO tokens (token, name, enabled, locked) VALUES (?, ?, ?, ?)",
                    (token, name, enabled, locked)
                )

            for token, name in admin_tokens:
                cursor.execute(
                    "INSERT OR IGNORE INTO tokens (token, name, locked) VALUES (?, ?, 0)",
                    (token, name)
                )

        add_new_columns()

        logger.info("База данных успешно инициализирована")
        return True
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}", exc_info=True)
        return False


def get_tokens() -> List[sqlite3.Row]:
    result = execute_query(
        "SELECT id, token, name, enabled, address, balance, locked, full_name, network FROM tokens"
    )
    return result or []


def update_token(token_id: int, enabled: Optional[bool] = None, address: Optional[str] = None) -> bool:
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
    return result is not None


def get_token_by_id(token_id: int) -> Optional[sqlite3.Row]:
    result = execute_query(
        "SELECT id, token, name, enabled, address, balance, locked, full_name, network FROM tokens WHERE id = ?",
        (token_id,)
    )
    return result[0] if result else None


def update_balance(token_id: int, delta: float) -> bool:
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
        source: str = "bot",
        **kwargs
) -> bool:
    if source == "bot":
        status = "confirmed"
    else:
        status = "pending"

    query = """
            INSERT INTO transactions
            (token, type, amount, date, from_address, to_address, tx_hash, fee, explorer_link, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) \
            """
    params = (
        token, tx_type, amount, date,
        kwargs.get('from_addr', ''),
        kwargs.get('to_addr', ''),
        kwargs.get('tx_hash', ''),
        kwargs.get('fee', 0),
        kwargs.get('explorer_link', ''),
        status
    )

    result = execute_query(query, params)
    return result is not None


def get_transactions(limit: int = 50) -> List[sqlite3.Row]:
    result = execute_query(
        "SELECT * FROM transactions ORDER BY date DESC LIMIT ?",
        (limit,)
    )
    return result or []


def update_transaction_status(tx_id: int, status: str) -> bool:
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                UPDATE transactions 
                SET status = ? 
                WHERE id = ?
            """, (status, tx_id))
            return True
    except Exception as e:
        logger.error(f"[ERROR] update_transaction_status: {str(e)}")
        return False


def update_token_balance(token_id: int, new_balance_usd: float):
    conn = None
    try:
        conn = _connection_pool.get_connection()
        cursor = conn.cursor()

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
        if conn:
            _connection_pool.return_connection(conn)


def get_transaction_by_id(transaction_id: int):
    """Получить транзакцию по ID"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                           SELECT id,
                                  token,
                                  type,
                                  amount,
                                  date,
                                  from_address,
                                  to_address,
                                  tx_hash,
                                  fee,
                                  explorer_link,
                                  status
                           FROM transactions
                           WHERE id = ?
                           """, (transaction_id,))

            row = cursor.fetchone()

            if row:
                return list(row)
            return None

    except Exception as e:
        logger.error(f"[ERROR] get_transaction_by_id: {str(e)}")
        return None


def get_pending_transactions():
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM transactions 
                WHERE status = 'pending'
                ORDER BY date DESC
            """)
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"[ERROR] get_pending_transactions: {str(e)}")
        return []


def get_transactions_by_token(token_symbol: str, limit: int = 100, offset: int = 0):
    """Получает транзакции по конкретному токену с пагинацией"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        normalized_symbol = token_symbol.lower()

        symbol_mapping = {
            "trx": "tron",
            "pol": "matic",
            "usdt": ["usdt_erc20", "usdt_trc20", "usdt_bep20"]
        }

        if normalized_symbol in symbol_mapping:
            if normalized_symbol == "usdt":
                query = """
                        SELECT * \
                        FROM transactions
                        WHERE token IN ('usdt_erc20', 'usdt_trc20', 'usdt_bep20')
                        ORDER BY date DESC
                        LIMIT ? OFFSET ? \
                        """
                cursor.execute(query, (limit, offset))
            else:
                db_symbol = symbol_mapping[normalized_symbol]
                query = """
                        SELECT * \
                        FROM transactions
                        WHERE token = ?
                        ORDER BY date DESC
                        LIMIT ? OFFSET ? \
                        """
                cursor.execute(query, (db_symbol, limit, offset))
        else:
            query = """
                    SELECT * \
                    FROM transactions
                    WHERE token = ?
                    ORDER BY date DESC
                    LIMIT ? OFFSET ? \
                    """
            cursor.execute(query, (normalized_symbol, limit, offset))

        transactions = cursor.fetchall()
        conn.close()
        return transactions

    except Exception as e:
        print(f"[ERROR] get_transactions_by_token: {e}")
        return []


# И добавь нормальную функцию get_transaction_count_by_token:
def get_transaction_count_by_token(symbol: str):
    """Получаем общее количество транзакций для токена"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        normalized_symbol = symbol.lower()

        symbol_mapping = {
            "trx": "tron",
            "pol": "matic",
            "usdt": ["usdt_erc20", "usdt_trc20", "usdt_bep20"]
        }

        if normalized_symbol in symbol_mapping:
            if normalized_symbol == "usdt":
                query = """
                        SELECT COUNT(*) \
                        FROM transactions
                        WHERE token IN ('usdt_erc20', 'usdt_trc20', 'usdt_bep20')
                        """
                cursor.execute(query)
            else:
                db_symbol = symbol_mapping[normalized_symbol]
                query = "SELECT COUNT(*) FROM transactions WHERE token = ?"
                cursor.execute(query, (db_symbol,))
        else:
            query = "SELECT COUNT(*) FROM transactions WHERE token = ?"
            cursor.execute(query, (normalized_symbol,))

        count = cursor.fetchone()[0]
        conn.close()
        return count

    except Exception as e:
        print(f"[ERROR] get_transaction_count_by_token: {e}")
        return 0


def deduct_token_balance(token_id: int, amount_usd: float) -> bool:
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT balance FROM tokens WHERE id = ?", (token_id,))
            row = cursor.fetchone()

            if not row:
                return False

            current_balance = row[0]

            if current_balance < amount_usd:
                return False

            new_balance = current_balance - amount_usd
            cursor.execute("UPDATE tokens SET balance = ? WHERE id = ?", (new_balance, token_id))
            return True
    except Exception as e:
        logger.error(f"Ошибка списания баланса: {e}")
        return False


def get_transaction_by_hash(tx_hash: str):
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                           SELECT id,
                                  token,
                                  type,
                                  amount,
                                  date,
                                  from_address,
                                  to_address,
                                  tx_hash,
                                  fee,
                                  explorer_link,
                                  status
                           FROM transactions
                           WHERE tx_hash = ?
                           """, (tx_hash,))

            row = cursor.fetchone()
            if row:
                return list(row)
            return None
    except Exception as e:
        logger.error(f"[ERROR] get_transaction_by_hash: {str(e)}")
        return None