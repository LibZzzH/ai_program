import sqlite3

import utils.db as db


def test_init_db_creates_schema_migration_record(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")

    db.init_db()

    conn = db.get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE name = ?",
            ("settings_user_primary_key",),
        ).fetchone()
        settings_cols = conn.execute("PRAGMA table_info(settings)").fetchall()
    finally:
        conn.close()

    assert row is not None
    assert {col["name"] for col in settings_cols if col["pk"]} == {"key", "user_id"}


def test_init_db_migrates_legacy_settings_table(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT ''
        );
        INSERT INTO settings (key, value) VALUES ('theme', 'dark');
    """)
    conn.commit()
    conn.close()

    monkeypatch.setattr(db, "DB_PATH", db_path)

    db.init_db()

    conn = db.get_connection()
    try:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ? AND user_id = ?",
            ("theme", "default"),
        ).fetchone()
        settings_cols = conn.execute("PRAGMA table_info(settings)").fetchall()
    finally:
        conn.close()

    assert row["value"] == "dark"
    assert {col["name"] for col in settings_cols if col["pk"]} == {"key", "user_id"}
