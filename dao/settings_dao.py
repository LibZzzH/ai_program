from utils.db import get_connection, get_current_user_id


def _uid(user_id):
    if user_id is None:
        return get_current_user_id()
    return user_id


def get_setting(key, default='', user_id=None):
    conn = get_connection()
    row = conn.execute(
        "SELECT value FROM settings WHERE key = ? AND user_id = ?",
        (key, _uid(user_id))
    ).fetchone()
    conn.close()
    return row['value'] if row else default


def set_setting(key, value, user_id=None):
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, user_id, value) VALUES (?, ?, ?)",
        (key, _uid(user_id), str(value))
    )
    conn.commit()
    conn.close()


def get_all_settings(user_id=None):
    conn = get_connection()
    rows = conn.execute(
        "SELECT key, value FROM settings WHERE user_id = ?",
        (_uid(user_id),)
    ).fetchall()
    conn.close()
    return {r['key']: r['value'] for r in rows}


def delete_setting(key, user_id=None):
    conn = get_connection()
    conn.execute(
        "DELETE FROM settings WHERE key = ? AND user_id = ?",
        (key, _uid(user_id))
    )
    conn.commit()
    conn.close()