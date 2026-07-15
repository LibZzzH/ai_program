from datetime import date, timedelta, datetime, timezone
from utils.db import get_current_user_id
from dao import streak_dao
from models.achievement import StreakLog


def _uid(user_id):
    return user_id or get_current_user_id()


def _today_beijing() -> date:
    beijing_tz = timezone(timedelta(hours=8))
    return datetime.now(beijing_tz).date()


def record_completion(user_id=None) -> StreakLog:
    return streak_dao.record_completion(user_id)


def get_streak(user_id=None):
    uid = _uid(user_id)
    today = _today_beijing()
    dates = streak_dao.get_streak_dates(uid)

    if not dates:
        return {"current_streak": 0, "total_days": 0, "level": _get_level(0), "today_done": False}

    dates = sorted(set(dates))
    total_days = len(dates)
    today_str = today.isoformat()
    today_done = dates[-1] == today_str if dates else False

    current_streak = 0
    check_date = today if today_done else today - timedelta(days=1)
    while check_date.isoformat() in dates:
        current_streak += 1
        check_date -= timedelta(days=1)

    return {
        "current_streak": current_streak,
        "total_days": total_days,
        "level": _get_level(total_days),
        "today_done": today_done,
    }


def get_month_heatmap(user_id=None, year=None, month=None):
    uid = _uid(user_id)
    today = _today_beijing()
    if year is None:
        year = today.year
    if month is None:
        month = today.month

    logs = streak_dao.get_month_logs(uid, year, month)
    return {log.task_date: log.done_count for log in logs}


def _get_level(total_days: int):
    if total_days >= 100:
        return {"name": "钻石", "emoji": "💎", "next": None, "next_days": 0, "progress": 1.0}
    elif total_days >= 60:
        return {"name": "黄金", "emoji": "🥇", "next": "钻石", "next_days": 100 - total_days,
                "progress": (total_days - 60) / 40}
    elif total_days >= 30:
        return {"name": "白银", "emoji": "🥈", "next": "黄金", "next_days": 60 - total_days,
                "progress": (total_days - 30) / 30}
    elif total_days >= 10:
        return {"name": "青铜", "emoji": "🥉", "next": "白银", "next_days": 30 - total_days,
                "progress": (total_days - 10) / 20}
    else:
        return {"name": "新手", "emoji": "🌱", "next": "青铜", "next_days": 10 - total_days,
                "progress": total_days / 10}