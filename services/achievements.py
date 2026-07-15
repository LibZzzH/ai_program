import json
from datetime import date, datetime
from utils.db import get_connection, get_current_user_id
from dao.settings_dao import get_setting, set_setting
from dao.streak_dao import get_today_log

BADGE_CATEGORIES = [
    {
        "id": "task_master",
        "name": "🏆 任务达人",
        "desc": "完成任务的里程碑",
        "color": "#FF6B6B",
    },
    {
        "id": "time_mgmt",
        "name": "⏰ 时间管理",
        "desc": "特定时间段完成任务的成就",
        "color": "#4ECDC4",
    },
    {
        "id": "accuracy",
        "name": "🎯 精准预估",
        "desc": "预估与实际用时匹配的成就",
        "color": "#45B7D1",
    },
    {
        "id": "streak",
        "name": "🔥 连续打卡",
        "desc": "连续完成任务的毅力成就",
        "color": "#FFA07A",
    },
    {
        "id": "challenge",
        "name": "🎲 挑战达人",
        "desc": "完成每日彩蛋挑战的成就",
        "color": "#DDA0DD",
    },
    {
        "id": "speed",
        "name": "🏃 速度激情",
        "desc": "极速完成任务的成就",
        "color": "#FFD700",
    },
    {
        "id": "category",
        "name": "🎨 分类专精",
        "desc": "不同分类任务的成就",
        "color": "#87CEEB",
    },
]

ACHIEVEMENTS = [
    # ===== 任务达人 =====
    {"id": "first_done", "name": "初出茅庐", "emoji": "🌟", "desc": "完成第一个任务", "category": "task_master"},
    {"id": "three_done", "name": "效率之星", "emoji": "⭐", "desc": "一天内完成 3 个任务", "category": "task_master"},
    {"id": "five_done", "name": "任务收割机", "emoji": "🚀", "desc": "一天内完成 5 个任务", "category": "task_master"},
    {"id": "ten_done", "name": "任务粉碎机", "emoji": "💥", "desc": "一天内完成 10 个任务", "category": "task_master"},
    {"id": "all_done", "name": "完美一天", "emoji": "🏆", "desc": "今日任务全部完成", "category": "task_master"},
    {"id": "over_achiever", "name": "超额完成", "emoji": "🌟", "desc": "完成比计划多 2 个以上的任务", "category": "task_master"},
    {"id": "first_of_day", "name": "开门红", "emoji": "🥇", "desc": "完成今天的第一个任务", "category": "task_master"},

    # ===== 时间管理 =====
    {"id": "early_bird", "name": "早鸟达人", "emoji": "🐦", "desc": "早上 9 点前完成一个任务", "category": "time_mgmt"},
    {"id": "early_riser", "name": "闻鸡起舞", "emoji": "🐓", "desc": "早上 7 点前完成一个任务", "category": "time_mgmt"},
    {"id": "morning_3", "name": "上午收割", "emoji": "☀️", "desc": "中午 12 点前完成 3 个任务", "category": "time_mgmt"},
    {"id": "afternoon_3", "name": "下午冲刺", "emoji": "🌤️", "desc": "下午 2-6 点间完成 3 个任务", "category": "time_mgmt"},
    {"id": "evening_1", "name": "晚间彩蛋", "emoji": "🌙", "desc": "晚上 8 点后完成一个任务", "category": "time_mgmt"},
    {"id": "night_owl", "name": "夜猫子", "emoji": "🦉", "desc": "晚上 10 点后完成一个任务", "category": "time_mgmt"},
    {"id": "lunch_break", "name": "午休不休息", "emoji": "🍱", "desc": "午餐时间(12-13点)完成一个任务", "category": "time_mgmt"},

    # ===== 精准预估 =====
    {"id": "accurate", "name": "神枪手", "emoji": "🎯", "desc": "实际用时与预估误差 < 10%", "category": "accuracy"},
    {"id": "double_accuracy", "name": "双倍精准", "emoji": "🎯", "desc": "连续两个任务误差都 < 10%", "category": "accuracy"},
    {"id": "consistent", "name": "稳定发挥", "emoji": "📏", "desc": "连续 3 个任务误差都在 20% 以内", "category": "accuracy"},
    {"id": "perfect_ratio", "name": "完美比例", "emoji": "💯", "desc": "今天所有任务的总误差 < 15%", "category": "accuracy"},
    {"id": "exact_time", "name": "分毫不差", "emoji": "🎯", "desc": "实际用时与预估完全一致（误差=0）", "category": "accuracy"},
    {"id": "fast_worker", "name": "闪电侠", "emoji": "⚡", "desc": "实际用时比预估少 50% 以上", "category": "accuracy"},
    {"id": "overestimate", "name": "过度乐观", "emoji": "🤡", "desc": "实际用时是预估 2 倍以上", "category": "accuracy"},
    {"id": "underestimate", "name": "隐藏高手", "emoji": "😎", "desc": "实际用时不到预估 30%", "category": "accuracy"},

    # ===== 连续打卡 =====
    {"id": "streak_3", "name": "三日连击", "emoji": "🔥", "desc": "连续 3 天完成任务", "category": "streak"},
    {"id": "streak_7", "name": "周冠军", "emoji": "👑", "desc": "连续 7 天完成任务", "category": "streak"},
    {"id": "streak_15", "name": "半月坚持", "emoji": "💪", "desc": "连续 15 天完成任务", "category": "streak"},
    {"id": "streak_30", "name": "月度之星", "emoji": "🏅", "desc": "连续 30 天完成任务", "category": "streak"},
    {"id": "comeback", "name": "卷土重来", "emoji": "🔄", "desc": "昨天断签，今天重新开始打卡", "category": "streak"},

    # ===== 挑战达人 =====
    {"id": "challenge_1", "name": "初尝挑战", "emoji": "🎲", "desc": "完成 1 次每日彩蛋挑战", "category": "challenge"},
    {"id": "challenge_3", "name": "挑战爱好者", "emoji": "🎯", "desc": "完成 3 次每日彩蛋挑战", "category": "challenge"},
    {"id": "challenge_7", "name": "挑战达人", "emoji": "🏅", "desc": "完成 7 次每日彩蛋挑战", "category": "challenge"},
    {"id": "challenge_15", "name": "挑战大师", "emoji": "👑", "desc": "完成 15 次每日彩蛋挑战", "category": "challenge"},
    {"id": "challenge_30", "name": "挑战传说", "emoji": "🌟", "desc": "完成 30 次每日彩蛋挑战", "category": "challenge"},

    # ===== 速度激情 =====
    {"id": "speed_run", "name": "极速挑战", "emoji": "🏃", "desc": "5 分钟内完成一个任务", "category": "speed"},
    {"id": "one_hour", "name": "一小时奇迹", "emoji": "⏰", "desc": "一小时内完成 3 个任务", "category": "speed"},
    {"id": "half_day", "name": "半日奇迹", "emoji": "⏳", "desc": "半天内完成 5 个任务", "category": "speed"},
    {"id": "quick_decision", "name": "快速决策", "emoji": "⚡", "desc": "创建任务后 30 秒内开始", "category": "speed"},
    {"id": "back_to_back", "name": "无缝衔接", "emoji": "🔗", "desc": "完成一个任务后 1 分钟内开始下一个", "category": "speed"},

    # ===== 分类专精 =====
    {"id": "multi_category", "name": "彩虹任务", "emoji": "🌈", "desc": "一天内完成 3 个不同分类的任务", "category": "category"},
    {"id": "category_king", "name": "分类之王", "emoji": "👑", "desc": "今天 80% 的任务属于同一个分类", "category": "category"},
    {"id": "balanced", "name": "平衡大师", "emoji": "⚖️", "desc": "今天完成的任务分布在 3+ 个分类", "category": "category"},
    {"id": "code_wizard", "name": "代码魔法师", "emoji": "💻", "desc": "完成一个【编程】分类的任务", "category": "category"},
    {"id": "design_guru", "name": "设计大师", "emoji": "🎨", "desc": "完成一个【设计】分类的任务", "category": "category"},
    {"id": "writer", "name": "笔耕不辍", "emoji": "✍️", "desc": "完成一个【写作】分类的任务", "category": "category"},
    {"id": "learner", "name": "学无止境", "emoji": "📚", "desc": "完成一个【学习】分类的任务", "category": "category"},
    {"id": "meeting_killer", "name": "会议杀手", "emoji": "💼", "desc": "完成一个【会议】分类的任务", "category": "category"},
    {"id": "ppt_master", "name": "PPT 狂魔", "emoji": "📊", "desc": "完成一个【PPT】分类的任务", "category": "category"},
]


def _uid(user_id):
    return user_id or get_current_user_id()


def get_achievements(user_id=None):
    uid = _uid(user_id)
    earned_json = get_setting("achievements", "{}", uid)
    earned = json.loads(earned_json)

    result = []
    for ach in ACHIEVEMENTS:
        earned_at = earned.get(ach["id"])
        result.append({
            **ach,
            "earned": earned_at is not None,
            "earned_at": earned_at,
        })
    return result


def get_achievements_by_category(user_id=None):
    all_achievements = get_achievements(user_id)
    result = {}
    for cat in BADGE_CATEGORIES:
        result[cat["id"]] = {
            **cat,
            "badges": [a for a in all_achievements if a.get("category") == cat["id"]],
        }
    return result


def check_and_award(user_id=None):
    from datetime import timezone, timedelta
    beijing_tz = timezone(timedelta(hours=8))
    today = datetime.now(beijing_tz).date().isoformat()
    uid = _uid(user_id)
    earned_json = get_setting("achievements", "{}", uid)
    earned = json.loads(earned_json)

    new_achievements = []
    for ach in ACHIEVEMENTS:
        if ach["id"] in earned:
            continue
        if _check_condition(ach["id"], uid):
            earned[ach["id"]] = today
            new_achievements.append(ach)

    if new_achievements:
        set_setting("achievements", json.dumps(earned, ensure_ascii=False), uid)

    return new_achievements


def award_challenge_badge(user_id=None):
    from datetime import timezone, timedelta
    beijing_tz = timezone(timedelta(hours=8))
    today = datetime.now(beijing_tz).date().isoformat()
    uid = _uid(user_id)
    earned_json = get_setting("achievements", "{}", uid)
    earned = json.loads(earned_json)

    challenge_completions_json = get_setting("challenge_completions", "[]", uid)
    completions = json.loads(challenge_completions_json)

    if today not in completions:
        completions.append(today)
        set_setting("challenge_completions", json.dumps(completions, ensure_ascii=False), uid)

    total = len(completions)
    new_badges = []

    challenge_badges = [
        ("challenge_1", 1),
        ("challenge_3", 3),
        ("challenge_7", 7),
        ("challenge_15", 15),
        ("challenge_30", 30),
    ]

    for badge_id, threshold in challenge_badges:
        if badge_id not in earned and total >= threshold:
            earned[badge_id] = today
            for ach in ACHIEVEMENTS:
                if ach["id"] == badge_id:
                    new_badges.append(ach)
                    break

    if new_badges:
        set_setting("achievements", json.dumps(earned, ensure_ascii=False), uid)

    return new_badges


def _check_condition(ach_id: str, uid: str) -> bool:
    from datetime import timezone, timedelta
    beijing_tz = timezone(timedelta(hours=8))
    now = datetime.now(beijing_tz)
    today = now.date().isoformat()
    conn = get_connection()

    # ===== 任务达人 =====
    if ach_id == "first_done":
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM tasks WHERE user_id = ? AND status = 'done'",
            (uid,)
        ).fetchone()
        conn.close()
        return row['cnt'] >= 1

    if ach_id in ("three_done", "five_done", "ten_done"):
        threshold = {"three_done": 3, "five_done": 5, "ten_done": 10}[ach_id]
        log = get_today_log(uid)
        return (log.done_count if log else 0) >= threshold

    if ach_id == "all_done":
        total = conn.execute(
            "SELECT COUNT(*) as cnt FROM tasks WHERE user_id = ? AND created_date = ?",
            (uid, today)
        ).fetchone()['cnt']
        done = conn.execute(
            "SELECT COUNT(*) as cnt FROM tasks WHERE user_id = ? AND created_date = ? AND status = 'done'",
            (uid, today)
        ).fetchone()['cnt']
        conn.close()
        return total > 0 and done >= total

    if ach_id == "over_achiever":
        total = conn.execute(
            "SELECT COUNT(*) as cnt FROM tasks WHERE user_id = ? AND created_date = ?",
            (uid, today)
        ).fetchone()['cnt']
        done = conn.execute(
            "SELECT COUNT(*) as cnt FROM tasks WHERE user_id = ? AND created_date = ? AND status = 'done'",
            (uid, today)
        ).fetchone()['cnt']
        conn.close()
        return done >= total + 2

    if ach_id == "first_of_day":
        conn.close()
        return True

    # ===== 时间管理 =====
    if ach_id == "early_bird":
        conn.close()
        return now.hour < 9

    if ach_id == "early_riser":
        conn.close()
        return now.hour < 7

    if ach_id == "morning_3":
        if now.hour < 12:
            conn.close()
            return False
        log = get_today_log(uid)
        conn.close()
        return (log.done_count if log else 0) >= 3

    if ach_id == "afternoon_3":
        if now.hour < 18:
            conn.close()
            return False
        log = get_today_log(uid)
        conn.close()
        return (log.done_count if log else 0) >= 3

    if ach_id == "evening_1":
        conn.close()
        return now.hour >= 20

    if ach_id == "night_owl":
        conn.close()
        return now.hour >= 22

    if ach_id == "lunch_break":
        conn.close()
        return 12 <= now.hour < 13

    # ===== 精准预估 =====
    if ach_id == "accurate":
        rows = conn.execute("""
            SELECT estimated_minutes, actual_minutes FROM tasks
            WHERE user_id = ? AND status = 'done'
              AND actual_minutes IS NOT NULL AND estimated_minutes > 0
            ORDER BY completed_date DESC LIMIT 10
        """, (uid,)).fetchall()
        conn.close()
        for r in rows:
            if r['estimated_minutes'] > 0:
                error = abs(r['actual_minutes'] - r['estimated_minutes']) / r['estimated_minutes']
                if error < 0.10:
                    return True
        return False

    if ach_id == "double_accuracy":
        rows = conn.execute("""
            SELECT estimated_minutes, actual_minutes FROM tasks
            WHERE user_id = ? AND status = 'done'
              AND actual_minutes IS NOT NULL AND estimated_minutes > 0
            ORDER BY completed_date DESC LIMIT 10
        """, (uid,)).fetchall()
        conn.close()
        count = 0
        for r in rows:
            if r['estimated_minutes'] > 0:
                error = abs(r['actual_minutes'] - r['estimated_minutes']) / r['estimated_minutes']
                if error < 0.10:
                    count += 1
                    if count >= 2:
                        return True
                else:
                    count = 0
        return False

    if ach_id == "consistent":
        rows = conn.execute("""
            SELECT estimated_minutes, actual_minutes FROM tasks
            WHERE user_id = ? AND status = 'done'
              AND actual_minutes IS NOT NULL AND estimated_minutes > 0
            ORDER BY completed_date DESC LIMIT 10
        """, (uid,)).fetchall()
        conn.close()
        count = 0
        for r in rows:
            if r['estimated_minutes'] > 0:
                error = abs(r['actual_minutes'] - r['estimated_minutes']) / r['estimated_minutes']
                if error <= 0.20:
                    count += 1
                    if count >= 3:
                        return True
                else:
                    count = 0
        return False

    if ach_id == "perfect_ratio":
        rows = conn.execute("""
            SELECT estimated_minutes, actual_minutes FROM tasks
            WHERE user_id = ? AND status = 'done'
              AND actual_minutes IS NOT NULL AND estimated_minutes > 0
              AND completed_date = ?
        """, (uid, today)).fetchall()
        conn.close()
        if not rows:
            return False
        total_est = sum(r['estimated_minutes'] for r in rows)
        total_act = sum(r['actual_minutes'] for r in rows)
        if total_est > 0:
            error = abs(total_act - total_est) / total_est
            return error < 0.15
        return False

    if ach_id == "exact_time":
        rows = conn.execute("""
            SELECT estimated_minutes, actual_minutes FROM tasks
            WHERE user_id = ? AND status = 'done'
              AND actual_minutes IS NOT NULL AND estimated_minutes > 0
            ORDER BY completed_date DESC LIMIT 10
        """, (uid,)).fetchall()
        conn.close()
        for r in rows:
            if r['actual_minutes'] == r['estimated_minutes']:
                return True
        return False

    if ach_id == "fast_worker":
        rows = conn.execute("""
            SELECT estimated_minutes, actual_minutes FROM tasks
            WHERE user_id = ? AND status = 'done'
              AND actual_minutes IS NOT NULL AND estimated_minutes > 0
            ORDER BY completed_date DESC LIMIT 10
        """, (uid,)).fetchall()
        conn.close()
        for r in rows:
            if r['estimated_minutes'] > 0 and r['actual_minutes'] < r['estimated_minutes'] * 0.5:
                return True
        return False

    if ach_id == "overestimate":
        rows = conn.execute("""
            SELECT estimated_minutes, actual_minutes FROM tasks
            WHERE user_id = ? AND status = 'done'
              AND actual_minutes IS NOT NULL AND estimated_minutes > 0
            ORDER BY completed_date DESC LIMIT 10
        """, (uid,)).fetchall()
        conn.close()
        for r in rows:
            if r['estimated_minutes'] > 0 and r['actual_minutes'] > r['estimated_minutes'] * 2:
                return True
        return False

    if ach_id == "underestimate":
        rows = conn.execute("""
            SELECT estimated_minutes, actual_minutes FROM tasks
            WHERE user_id = ? AND status = 'done'
              AND actual_minutes IS NOT NULL AND estimated_minutes > 0
            ORDER BY completed_date DESC LIMIT 10
        """, (uid,)).fetchall()
        conn.close()
        for r in rows:
            if r['estimated_minutes'] > 0 and r['actual_minutes'] < r['estimated_minutes'] * 0.3:
                return True
        return False

    # ===== 连续打卡 =====
    if ach_id in ("streak_3", "streak_7", "streak_15", "streak_30"):
        from services.streak import get_streak
        streak = get_streak(uid)
        conn.close()
        threshold = {"streak_3": 3, "streak_7": 7, "streak_15": 15, "streak_30": 30}[ach_id]
        return streak["current_streak"] >= threshold

    if ach_id == "comeback":
        from services.streak import get_streak
        streak = get_streak(uid)
        conn.close()
        return streak["current_streak"] == 1

    # ===== 速度激情 =====
    if ach_id == "speed_run":
        row = conn.execute("""
            SELECT actual_minutes FROM tasks
            WHERE user_id = ? AND status = 'done'
              AND actual_minutes IS NOT NULL AND actual_minutes <= 5
            ORDER BY completed_date DESC LIMIT 1
        """, (uid,)).fetchone()
        conn.close()
        return row is not None

    if ach_id == "one_hour":
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM streak_log WHERE user_id = ? AND task_date = ?",
            (uid, today)
        ).fetchone()
        conn.close()
        return (row['cnt'] if row else 0) >= 3

    if ach_id == "half_day":
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM streak_log WHERE user_id = ? AND task_date = ?",
            (uid, today)
        ).fetchone()
        conn.close()
        return (row['cnt'] if row else 0) >= 5

    if ach_id == "quick_decision":
        conn.close()
        return True

    if ach_id == "back_to_back":
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM streak_log WHERE user_id = ? AND task_date = ?",
            (uid, today)
        ).fetchone()
        conn.close()
        return (row['cnt'] if row else 0) >= 2

    # ===== 分类专精 =====
    if ach_id == "multi_category":
        rows = conn.execute("""
            SELECT DISTINCT category FROM tasks
            WHERE user_id = ? AND created_date = ? AND status = 'done'
        """, (uid, today)).fetchall()
        conn.close()
        categories = set(r['category'] for r in rows if r['category'])
        return len(categories) >= 3

    if ach_id == "category_king":
        rows = conn.execute("""
            SELECT category, COUNT(*) as cnt FROM tasks
            WHERE user_id = ? AND created_date = ? AND status = 'done'
            GROUP BY category
        """, (uid, today)).fetchall()
        conn.close()
        if not rows:
            return False
        total = sum(r['cnt'] for r in rows)
        max_cat = max(r['cnt'] for r in rows)
        return total > 0 and (max_cat / total) >= 0.8

    if ach_id == "balanced":
        rows = conn.execute("""
            SELECT DISTINCT category FROM tasks
            WHERE user_id = ? AND created_date = ? AND status = 'done'
        """, (uid, today)).fetchall()
        conn.close()
        categories = set(r['category'] for r in rows if r['category'])
        return len(categories) >= 3

    if ach_id == "code_wizard":
        row = conn.execute("""
            SELECT COUNT(*) as cnt FROM tasks
            WHERE user_id = ? AND status = 'done' AND category = '编程'
        """, (uid,)).fetchone()
        conn.close()
        return row['cnt'] >= 1

    if ach_id == "design_guru":
        row = conn.execute("""
            SELECT COUNT(*) as cnt FROM tasks
            WHERE user_id = ? AND status = 'done' AND category = '设计'
        """, (uid,)).fetchone()
        conn.close()
        return row['cnt'] >= 1

    if ach_id == "writer":
        row = conn.execute("""
            SELECT COUNT(*) as cnt FROM tasks
            WHERE user_id = ? AND status = 'done' AND category = '写作'
        """, (uid,)).fetchone()
        conn.close()
        return row['cnt'] >= 1

    if ach_id == "learner":
        row = conn.execute("""
            SELECT COUNT(*) as cnt FROM tasks
            WHERE user_id = ? AND status = 'done' AND category = '学习'
        """, (uid,)).fetchone()
        conn.close()
        return row['cnt'] >= 1

    if ach_id == "meeting_killer":
        row = conn.execute("""
            SELECT COUNT(*) as cnt FROM tasks
            WHERE user_id = ? AND status = 'done' AND category = '会议'
        """, (uid,)).fetchone()
        conn.close()
        return row['cnt'] >= 1

    if ach_id == "ppt_master":
        row = conn.execute("""
            SELECT COUNT(*) as cnt FROM tasks
            WHERE user_id = ? AND status = 'done' AND category = 'PPT'
        """, (uid,)).fetchone()
        conn.close()
        return row['cnt'] >= 1

    conn.close()
    return False