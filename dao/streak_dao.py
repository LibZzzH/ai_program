from datetime import date, timedelta, datetime
from models.achievement import StreakLog
from utils.db import get_connection, get_current_user_id


def _uid(user_id):
    return user_id or get_current_user_id()


def _today_beijing() -> date:
    from datetime import timezone, timedelta
    beijing_tz = timezone(timedelta(hours=8))
    return datetime.now(beijing_tz).date()


def record_completion(user_id=None) -> StreakLog:
    uid = _uid(user_id)
    today = _today_beijing().isoformat()
    conn = get_connection()
    conn.execute("""
        INSERT INTO streak_log (user_id, task_date, done_count)
        VALUES (?, ?, 1)
        ON CONFLICT(user_id, task_date) DO UPDATE SET done_count = done_count + 1
    """, (uid, today))
    conn.commit()

    row = conn.execute(
        "SELECT * FROM streak_log WHERE user_id = ? AND task_date = ?",
        (uid, today)
    ).fetchone()
    conn.close()
    return StreakLog.from_row(dict(row)) if row else StreakLog(user_id=uid, task_date=today, done_count=1)


def get_streak_dates(user_id=None) -> list[str]:
    uid = _uid(user_id)
    conn = get_connection()
    rows = conn.execute(
        "SELECT task_date FROM streak_log WHERE user_id = ? ORDER BY task_date DESC",
        (uid,)
    ).fetchall()
    conn.close()
    return [r['task_date'] for r in rows]


def get_month_logs(user_id=None, year: int | None = None, month: int | None = None) -> list[StreakLog]:
    uid = _uid(user_id)
    today = _today_beijing()
    if year is None:
        year = today.year
    if month is None:
        month = today.month

    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM streak_log WHERE user_id = ? "
        "AND task_date >= ? AND task_date < ? ORDER BY task_date",
        (uid, f"{year}-{month:02d}-01", f"{year}-{month+1:02d}-01" if month < 12
         else f"{year+1}-01-01")
    ).fetchall()
    conn.close()
    return [StreakLog.from_row(dict(r)) for r in rows]


def get_today_log(user_id=None) -> StreakLog | None:
    uid = _uid(user_id)
    today = _today_beijing().isoformat()
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM streak_log WHERE user_id = ? AND task_date = ?",
        (uid, today)
    ).fetchone()
    conn.close()
    return StreakLog.from_row(dict(row)) if row else None