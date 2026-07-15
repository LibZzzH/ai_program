from datetime import date, datetime
from utils.db import get_connection, get_current_user_id
from models.calendar_event import CalendarEvent

ALL_SOURCES = ('manual', 'google', 'caldav')
EXTERNAL_SOURCES = ('google', 'caldav')


def add_calendar_event(user_id, source, title, start_time, end_time, is_busy=True, external_id=None) -> CalendarEvent:
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO calendar_events (user_id, source, title, start_time, end_time, is_busy, external_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, source, title,
         start_time.isoformat() if isinstance(start_time, datetime) else start_time,
         end_time.isoformat() if isinstance(end_time, datetime) else end_time,
         1 if is_busy else 0, external_id)
    )
    conn.commit()
    event_id = cursor.lastrowid
    row = conn.execute("SELECT * FROM calendar_events WHERE id = ?", (event_id,)).fetchone()
    conn.close()
    return CalendarEvent.from_row(dict(row)) if row else CalendarEvent()


def _get_events(user_id, start_str, end_str, include_manual=True):
    sources = ALL_SOURCES if include_manual else EXTERNAL_SOURCES
    placeholders = ','.join('?' * len(sources))
    conn = get_connection()
    rows = conn.execute(
        f"SELECT * FROM calendar_events WHERE user_id = ? AND source IN ({placeholders}) "
        "AND start_time >= ? AND start_time <= ? AND is_busy = 1 ORDER BY start_time ASC",
        (user_id, *sources, start_str, end_str)
    ).fetchall()
    conn.close()
    return [CalendarEvent.from_row(dict(r)) for r in rows]


def get_events_by_date(user_id, dt, include_manual=True) -> list[CalendarEvent]:
    day_start = f"{dt.isoformat()} 00:00:00"
    day_end = f"{dt.isoformat()} 23:59:59"
    return _get_events(user_id, day_start, day_end, include_manual)


def get_events_by_range(user_id, start_date, end_date, include_manual=True) -> list[CalendarEvent]:
    return _get_events(
        user_id,
        f"{start_date.isoformat()} 00:00:00",
        f"{end_date.isoformat()} 23:59:59",
        include_manual
    )


def delete_calendar_event(event_id, user_id):
    conn = get_connection()
    conn.execute("DELETE FROM calendar_events WHERE id = ? AND user_id = ?", (event_id, user_id))
    conn.commit()
    conn.close()


def sync_events(user_id, events, source):
    conn = get_connection()
    for e in events:
        conn.execute(
            "INSERT OR REPLACE INTO calendar_events "
            "(user_id, source, title, start_time, end_time, is_busy, external_id) "
            "VALUES (?, ?, ?, ?, ?, 1, ?)",
            (user_id, source, e.get('title', ''), e['start'], e['end'], e.get('id', ''))
        )
    conn.commit()
    conn.close()