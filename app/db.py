import sqlite3

DB_PATH = "bot.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ======= TOKENS =======
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS tokens
                   (
                       id      INTEGER PRIMARY KEY,
                       token   TEXT UNIQUE,
                       name    TEXT,
                       enabled BOOLEAN DEFAULT 0,
                       address TEXT    DEFAULT '',
                       balance REAL    DEFAULT 0,
                       locked  BOOLEAN DEFAULT 0
                   )
                   """)

    # Дефолтные токены (нельзя редактировать)
    default_tokens = [
        ("bnb", "BNB", 1, 1),
        ("btc", "BTC", 1, 1),
        ("eth", "ETH", 1, 1),
        ("matic", "Polygon", 1, 1),
        ("tron", "TRON", 1, 1),
        ("twt", "TWT", 1, 1)
    ]

    for t, name, enabled, locked in default_tokens:
        cursor.execute(
            "INSERT OR IGNORE INTO tokens (token, name, enabled, locked) VALUES (?, ?, ?, ?)",
            (t, name, enabled, locked)
        )

    # Админские токены (можно редактировать)
    admin_tokens = [
        ("usdt_erc20", "USDT (ERC20)"),
        ("usdt_trc20", "USDT (TRC20)"),
        ("usdt_bep20", "USDT (BEP20)"),
        ("ton", "TON"),
        ("sol", "SOL")
    ]
    for t, name in admin_tokens:
        cursor.execute(
            "INSERT OR IGNORE INTO tokens (token, name, locked) VALUES (?, ?, 0)",
            (t, name)
        )

    # ======= TRANSACTIONS =======
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS transactions
                   (
                       id            INTEGER PRIMARY KEY,
                       token         TEXT,
                       type          TEXT, -- 'income' или 'outcome'
                       amount        REAL,
                       date          TEXT,
                       from_address  TEXT,
                       to_address    TEXT,
                       tx_hash       TEXT,
                       fee           REAL,
                       explorer_link TEXT,
                       status        TEXT DEFAULT 'pending'
                   )
                   """)

    conn.commit()
    conn.close()


# ======= TOKENS =======
def get_tokens():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, token, name, enabled, address, balance, locked FROM tokens")
    result = cursor.fetchall()
    conn.close()
    return result


def update_token(token, enabled=None, address=None, name=None, balance=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if enabled is not None:
        cursor.execute("UPDATE tokens SET enabled=? WHERE token=?", (enabled, token))
    if address is not None:
        cursor.execute("UPDATE tokens SET address=? WHERE token=?", (address, token))
    if name is not None:
        cursor.execute("UPDATE tokens SET name=? WHERE token=?", (name, token))
    if balance is not None:
        cursor.execute("UPDATE tokens SET balance=? WHERE token=?", (balance, token))
    conn.commit()
    conn.close()


def get_token_by_id(token_id):
    """Получить токен по ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
                   SELECT id, token, name, enabled, address, balance, locked
                   FROM tokens
                   WHERE id = ?
                   """, (token_id,))
    result = cursor.fetchone()
    conn.close()
    return result


def update_balance(token_id_or_symbol, delta):
    """Обновляет баланс токена. Принимает либо ID, либо символ токена"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if isinstance(token_id_or_symbol, int):
        cursor.execute("UPDATE tokens SET balance = balance + ? WHERE id = ?",
                       (delta, token_id_or_symbol))
    else:
        cursor.execute("UPDATE tokens SET balance = balance + ? WHERE token = ?",
                       (delta, token_id_or_symbol))

    conn.commit()
    conn.close()


# ======= TRANSACTIONS =======
def create_transaction(token, tx_type, amount, date, from_addr="", to_addr="", tx_hash="", fee=0, explorer_link=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
                   INSERT INTO transactions
                   (token, type, amount, date, from_address, to_address, tx_hash, fee, explorer_link)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   """, (token, tx_type, amount, date, from_addr, to_addr, tx_hash, fee, explorer_link))
    conn.commit()
    conn.close()


def get_transactions(limit=50):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions ORDER BY date DESC LIMIT ?", (limit,))
    result = cursor.fetchall()
    conn.close()
    return result


def update_transaction_status(tx_id, status):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE transactions SET status=? WHERE id=?", (status, tx_id))
    conn.commit()
    conn.close()
