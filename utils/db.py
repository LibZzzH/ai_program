import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data.db"

DEFAULT_USER_ID = "default"
logger = logging.getLogger(__name__)


def get_current_user_id():
    try:
        import streamlit as st
        if st.session_state.get("logged_in") and st.session_state.get("current_user"):
            user = st.session_state.current_user
            return user["id"] if isinstance(user, dict) else user.id
    except Exception:
        logger.debug("Falling back to default user id", exc_info=True)
    return DEFAULT_USER_ID


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def db_connection(commit=False):
    conn = get_connection()
    try:
        yield conn
        if commit:
            conn.commit()
    except Exception:
        if commit:
            conn.rollback()
        raise
    finally:
        conn.close()


def _column_exists(conn, table_name, column_name):
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row["name"] == column_name for row in rows)


def _add_column_if_missing(conn, table_name, column_name, column_type):
    if _column_exists(conn, table_name, column_name):
        return False
    conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
    return True


def _has_migration(conn, name):
    row = conn.execute(
        "SELECT 1 FROM schema_migrations WHERE name = ?",
        (name,),
    ).fetchone()
    return row is not None


def _record_migration(conn, name):
    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations (name) VALUES (?)",
        (name,),
    )


def _settings_has_user_primary_key(conn):
    rows = conn.execute("PRAGMA table_info(settings)").fetchall()
    pk_cols = {row["name"] for row in rows if row["pk"]}
    return {"key", "user_id"}.issubset(pk_cols)


def _migrate_settings_primary_key(conn):
    migration = "settings_user_primary_key"
    if _has_migration(conn, migration) or _settings_has_user_primary_key(conn):
        _record_migration(conn, migration)
        return

    conn.execute("SAVEPOINT migrate_settings")
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings_new (
                key TEXT NOT NULL,
                user_id TEXT NOT NULL DEFAULT 'default',
                value TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (key, user_id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        conn.execute("""
            INSERT OR IGNORE INTO settings_new (key, user_id, value)
            SELECT key, COALESCE(user_id, 'default'), value FROM settings
        """)
        conn.execute("DROP TABLE settings")
        conn.execute("ALTER TABLE settings_new RENAME TO settings")
        _record_migration(conn, migration)
        conn.execute("RELEASE migrate_settings")
    except Exception:
        conn.execute("ROLLBACK TO migrate_settings")
        logger.exception("Failed to migrate settings primary key")
        raise


def init_db():
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name TEXT PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL DEFAULT '',
                name TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                avatar TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'default',
                category TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                estimated_minutes INTEGER NOT NULL DEFAULT 0,
                calibrated_minutes INTEGER,
                actual_minutes INTEGER,
                status TEXT NOT NULL DEFAULT 'todo',
                created_date DATE NOT NULL DEFAULT (date('now', 'localtime')),
                completed_date DATE,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                scheduled_start TEXT DEFAULT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                notes TEXT DEFAULT '',
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT NOT NULL,
                user_id TEXT NOT NULL DEFAULT 'default',
                value TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (key, user_id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS calendar_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'default',
                source TEXT NOT NULL DEFAULT 'manual',
                title TEXT NOT NULL DEFAULT '',
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                is_busy INTEGER NOT NULL DEFAULT 1,
                external_id TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS streak_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'default',
                task_date TEXT NOT NULL,
                done_count INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                UNIQUE(user_id, task_date),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)

        _add_column_if_missing(conn, "tasks", "scheduled_start", "TEXT DEFAULT NULL")
        _add_column_if_missing(conn, "tasks", "notes", "TEXT DEFAULT ''")
        _add_column_if_missing(conn, "tasks", "user_id", "TEXT NOT NULL DEFAULT 'default'")
        _add_column_if_missing(conn, "settings", "user_id", "TEXT NOT NULL DEFAULT 'default'")
        _add_column_if_missing(conn, "users", "password_hash", "TEXT NOT NULL DEFAULT ''")
        _add_column_if_missing(conn, "users", "avatar", "TEXT NOT NULL DEFAULT ''")

        conn.execute("""
            INSERT OR IGNORE INTO users (id, password_hash, name, email)
            VALUES ('default', '', '默认用户', '')
        """)

        _migrate_settings_primary_key(conn)
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("Database initialization failed")
        raise
    finally:
        conn.close()
