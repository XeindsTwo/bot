# migrate.py в папке app/
import sqlite3
import os

DB_PATH = "../bot.db"  # или "../bot.db" если база на уровень выше


def migrate_database():
    """Добавляет новые колонки к существующей таблице tokens"""

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Проверяем какие колонки уже есть
        cursor.execute("PRAGMA table_info(tokens)")
        existing_columns = [col[1] for col in cursor.fetchall()]

        print(f"Текущие колонки в таблице tokens: {existing_columns}")

        # Добавляем full_name если нет
        if 'full_name' not in existing_columns:
            cursor.execute("ALTER TABLE tokens ADD COLUMN full_name TEXT DEFAULT ''")
            print("✅ Добавлена колонка full_name")
        else:
            print("✅ Колонка full_name уже существует")

        # Добавляем network если нет
        if 'network' not in existing_columns:
            cursor.execute("ALTER TABLE tokens ADD COLUMN network TEXT DEFAULT ''")
            print("✅ Добавлена колонка network")
        else:
            print("✅ Колонка network уже существует")

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
                "UPDATE tokens SET full_name = ?, network = ? WHERE token = ?",
                (defaults["full_name"], defaults["network"], token)
            )
            print(f"✅ Обновлен токен {token}: full_name='{defaults['full_name']}', network='{defaults['network']}'")

        conn.commit()

        # Проверяем результат
        cursor.execute("SELECT token, full_name, network FROM tokens")
        tokens = cursor.fetchall()

        print("\n📊 Результат миграции:")
        print("-" * 60)
        for token in tokens:
            print(f"{token[0]:<15} | full_name='{token[1]:<20}' | network='{token[2]}'")

        print("-" * 60)
        print(f"✅ Миграция успешно завершена! Обновлено {len(tokens)} токенов.")

    except sqlite3.Error as e:
        print(f"❌ Ошибка SQLite: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    finally:
        if conn:
            conn.close()

    return True


if __name__ == "__main__":
    print("🚀 Начинаю миграцию базы данных...")

    # Проверяем что файл базы существует
    if not os.path.exists(DB_PATH):
        # Пробуем на уровень выше
        DB_PATH = "../bot.db"
        if not os.path.exists(DB_PATH):
            print(f"❌ Файл базы данных не найден!")
            exit(1)

    success = migrate_database()

    if success:
        print("\n🎉 Миграция успешно выполнена!")
    else:
        print("\n💥 Миграция завершилась с ошибкой!")