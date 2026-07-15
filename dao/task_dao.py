from datetime import date
from utils.db import get_connection, get_current_user_id


def _uid(user_id):
    if user_id is None:
        return get_current_user_id()
    return user_id


def add_task(category, description, estimated_minutes, created_date=None, scheduled_start=None, notes="", user_id=None):
    if created_date is None:
        created_date = date.today().isoformat()
    uid = _uid(user_id)
    conn = get_connection()
    max_order = conn.execute(
        "SELECT COALESCE(MAX(sort_order), -1) FROM tasks WHERE created_date = ? AND user_id = ?",
        (created_date, uid)
    ).fetchone()[0]
    cursor = conn.execute(
        "INSERT INTO tasks (user_id, category, description, estimated_minutes, created_date, scheduled_start, notes, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (uid, category, description, estimated_minutes, created_date, scheduled_start, notes, max_order + 1)
    )
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    return task_id


def get_today_tasks(user_id=None):
    uid = _uid(user_id)
    today = date.today().isoformat()
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM tasks WHERE created_date = ? AND user_id = ? ORDER BY sort_order ASC",
        (today, uid)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_tasks_by_date(dt, user_id=None):
    uid = _uid(user_id)
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM tasks WHERE created_date = ? AND user_id = ? ORDER BY sort_order ASC",
        (dt, uid)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_tasks(user_id=None):
    uid = _uid(user_id)
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM tasks WHERE user_id = ? ORDER BY created_date DESC, sort_order ASC",
        (uid,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_task_status(task_id, status, user_id=None, start_time=None, end_time=None):
    uid = _uid(user_id)
    conn = get_connection()
    if status == 'doing' and start_time:
        conn.execute(
            "UPDATE tasks SET status = ?, start_time = ? WHERE id = ? AND user_id = ?",
            (status, start_time, task_id, uid)
        )
    elif status == 'done' and end_time:
        conn.execute(
            "UPDATE tasks SET status = ?, end_time = ?, completed_date = date('now', 'localtime') WHERE id = ? AND user_id = ?",
            (status, end_time, task_id, uid)
        )
    else:
        conn.execute("UPDATE tasks SET status = ? WHERE id = ? AND user_id = ?", (status, task_id, uid))
    conn.commit()
    conn.close()


def set_actual_minutes(task_id, actual_minutes, user_id=None):
    uid = _uid(user_id)
    conn = get_connection()
    conn.execute(
        "UPDATE tasks SET actual_minutes = ? WHERE id = ? AND user_id = ?",
        (actual_minutes, task_id, uid)
    )
    conn.commit()
    conn.close()


def set_calibrated_minutes(task_id, calibrated_minutes, user_id=None):
    uid = _uid(user_id)
    conn = get_connection()
    conn.execute(
        "UPDATE tasks SET calibrated_minutes = ? WHERE id = ? AND user_id = ?",
        (calibrated_minutes, task_id, uid)
    )
    conn.commit()
    conn.close()


def update_task(task_id, user_id=None, category=None, description=None, estimated_minutes=None, notes=None, created_date=None):
    uid = _uid(user_id)
    conn = get_connection()
    fields = []
    values = []
    if category is not None:
        fields.append("category = ?")
        values.append(category)
    if description is not None:
        fields.append("description = ?")
        values.append(description)
    if estimated_minutes is not None:
        fields.append("estimated_minutes = ?")
        values.append(estimated_minutes)
    if notes is not None:
        fields.append("notes = ?")
        values.append(notes)
    if created_date is not None:
        fields.append("created_date = ?")
        values.append(created_date)
    if fields:
        values.append(task_id)
        values.append(uid)
        conn.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE id = ? AND user_id = ?", values)
        conn.commit()
    conn.close()


def delete_task(task_id, user_id=None):
    uid = _uid(user_id)
    conn = get_connection()
    conn.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, uid))
    conn.commit()
    conn.close()


def reorder_tasks(task_ids, user_id=None):
    uid = _uid(user_id)
    conn = get_connection()
    for idx, task_id in enumerate(task_ids):
        conn.execute(
            "UPDATE tasks SET sort_order = ? WHERE id = ? AND user_id = ?",
            (idx, task_id, uid)
        )
    conn.commit()
    conn.close()


def get_category_history(category, user_id=None):
    uid = _uid(user_id)
    conn = get_connection()
    rows = conn.execute(
        "SELECT estimated_minutes, actual_minutes FROM tasks WHERE category = ? AND status = 'done' AND actual_minutes IS NOT NULL AND user_id = ?",
        (category, uid)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_category_tasks_full(category, user_id=None, limit=10):
    uid = _uid(user_id)
    conn = get_connection()
    rows = conn.execute(
        "SELECT description, estimated_minutes, actual_minutes FROM tasks "
        "WHERE category = ? AND status = 'done' AND actual_minutes IS NOT NULL AND user_id = ? "
        "ORDER BY created_date DESC LIMIT ?",
        (category, uid, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_done_history(user_id=None):
    uid = _uid(user_id)
    conn = get_connection()
    rows = conn.execute(
        "SELECT estimated_minutes, actual_minutes FROM tasks WHERE status = 'done' AND actual_minutes IS NOT NULL AND user_id = ?",
        (uid,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_category_stats(user_id=None):
    uid = _uid(user_id)
    conn = get_connection()
    rows = conn.execute("""
        SELECT category,
               COUNT(*) as count,
               AVG(estimated_minutes) as avg_estimated,
               AVG(actual_minutes) as avg_actual,
               AVG(CAST(actual_minutes AS REAL) / NULLIF(estimated_minutes, 0)) as avg_ratio
        FROM tasks
        WHERE status = 'done' AND actual_minutes IS NOT NULL AND user_id = ?
        GROUP BY category
        HAVING count >= 1
        ORDER BY avg_ratio DESC
    """, (uid,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_daily_summary(dt=None, user_id=None):
    uid = _uid(user_id)
    if dt is None:
        dt = date.today().isoformat()
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM tasks WHERE created_date = ? AND user_id = ? ORDER BY sort_order ASC",
        (dt, uid)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def move_task_up(task_id, user_id=None):
    uid = _uid(user_id)
    conn = get_connection()
    conn.execute("BEGIN")
    try:
        task = conn.execute(
            "SELECT sort_order, created_date FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, uid)
        ).fetchone()
        if not task or task['sort_order'] <= 0:
            conn.rollback()
            conn.close()
            return
        current_order = task['sort_order']
        created_date = task['created_date']
        prev = conn.execute(
            "SELECT id, sort_order FROM tasks WHERE created_date = ? AND user_id = ? AND sort_order < ? ORDER BY sort_order DESC LIMIT 1",
            (created_date, uid, current_order)
        ).fetchone()
        if prev:
            conn.execute(
                "UPDATE tasks SET sort_order = ? WHERE id = ? AND user_id = ?",
                (current_order, prev['id'], uid)
            )
            conn.execute(
                "UPDATE tasks SET sort_order = ? WHERE id = ? AND user_id = ?",
                (prev['sort_order'], task_id, uid)
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def move_task_down(task_id, user_id=None):
    uid = _uid(user_id)
    conn = get_connection()
    conn.execute("BEGIN")
    try:
        task = conn.execute(
            "SELECT sort_order, created_date FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, uid)
        ).fetchone()
        if not task:
            conn.rollback()
            conn.close()
            return
        current_order = task['sort_order']
        created_date = task['created_date']
        next_task = conn.execute(
            "SELECT id, sort_order FROM tasks WHERE created_date = ? AND user_id = ? AND sort_order > ? ORDER BY sort_order ASC LIMIT 1",
            (created_date, uid, current_order)
        ).fetchone()
        if next_task:
            conn.execute(
                "UPDATE tasks SET sort_order = ? WHERE id = ? AND user_id = ?",
                (current_order, next_task['id'], uid)
            )
            conn.execute(
                "UPDATE tasks SET sort_order = ? WHERE id = ? AND user_id = ?",
                (next_task['sort_order'], task_id, uid)
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_task_by_id(task_id, user_id=None):
    uid = _uid(user_id)
    conn = get_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, uid)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_tasks_by_date_range(start_date, end_date, user_id=None):
    uid = _uid(user_id)
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM tasks WHERE created_date >= ? AND created_date <= ? AND user_id = ? ORDER BY created_date ASC, sort_order ASC",
        (start_date, end_date, uid)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_completed_tasks_by_category(category, user_id=None, limit=50):
    uid = _uid(user_id)
    conn = get_connection()
    rows = conn.execute(
        "SELECT estimated_minutes, actual_minutes, description, created_date "
        "FROM tasks WHERE category = ? AND status = 'done' AND actual_minutes IS NOT NULL AND user_id = ? "
        "ORDER BY created_date DESC LIMIT ?",
        (category, uid, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_ratios_by_category(category, user_id=None, limit=20):
    uid = _uid(user_id)
    conn = get_connection()
    rows = conn.execute(
        "SELECT CAST(actual_minutes AS REAL) / NULLIF(estimated_minutes, 0) AS ratio, created_date "
        "FROM tasks WHERE category = ? AND status = 'done' AND actual_minutes IS NOT NULL AND user_id = ? "
        "ORDER BY created_date DESC LIMIT ?",
        (category, uid, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_task_count(user_id=None):
    uid = _uid(user_id)
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_id = ?",
        (uid,)
    ).fetchone()
    conn.close()
    return row[0] if row else 0


def delete_all_tasks(user_id=None):
    uid = _uid(user_id)
    conn = get_connection()
    conn.execute("DELETE FROM tasks WHERE user_id = ?", (uid,))
    conn.commit()
    conn.close()