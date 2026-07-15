import json
import random
from datetime import date
from utils.db import get_current_user_id
from dao.settings_dao import get_setting, set_setting

CHALLENGES = [
    {"id": "lightning", "text": "⚡ 闪电战：完成一个预估 < 15 分钟的任务", "badge": "闪电战"},
    {"id": "reverse", "text": "🔄 反套路：把预估时间减半，挑战极限完成", "badge": "反套路"},
    {"id": "sniper", "text": "🎯 神枪手：实际用时与预估误差 < 5 分钟", "badge": "神枪手"},
    {"id": "early_9", "text": "🌅 晨间冲刺：早上 9 点前完成一个任务", "badge": "晨间冲刺"},
    {"id": "triple", "text": "🔥 三连击：连续完成 3 个任务不间断", "badge": "三连击"},
    {"id": "big_task", "text": "🏔️ 攀登者：完成一个预估 > 60 分钟的大任务", "badge": "攀登者"},
    {"id": "tiny_task", "text": "🐣 小菜一碟：完成一个预估 < 5 分钟的任务", "badge": "小菜一碟"},
    {"id": "category_new", "text": "🆕 拓荒者：在一个新分类下创建并完成任务", "badge": "拓荒者"},
    {"id": "pause_free", "text": "⏸️ 一气呵成：开始任务后不暂停，直到完成", "badge": "一气呵成"},
    {"id": "double_accuracy", "text": "🎯 双倍精准：连续两个任务误差都 < 10%", "badge": "双倍精准"},
    {"id": "morning_3", "text": "☀️ 上午收割：中午 12 点前完成 3 个任务", "badge": "上午收割"},
    {"id": "afternoon_3", "text": "🌤️ 下午冲刺：下午 2-6 点间完成 3 个任务", "badge": "下午冲刺"},
    {"id": "evening_1", "text": "🌙 晚间彩蛋：晚上 8 点后完成一个任务", "badge": "晚间彩蛋"},
    {"id": "overestimate", "text": "🤡 过度乐观：完成一个实际用时是预估 2 倍以上的任务", "badge": "过度乐观"},
    {"id": "underestimate", "text": "😎 隐藏高手：完成一个实际用时不到预估 30% 的任务", "badge": "隐藏高手"},
    {"id": "exact_time", "text": "🎯 分毫不差：实际用时与预估完全一致", "badge": "分毫不差"},
    {"id": "first_of_day", "text": "🥇 开门红：完成今天的第一个任务", "badge": "开门红"},
    {"id": "last_of_day", "text": "🏁 完美收官：完成今天的最后一个任务", "badge": "完美收官"},
    {"id": "speed_run", "text": "🏃 极速挑战：5 分钟内完成一个任务", "badge": "极速挑战"},
    {"id": "marathon", "text": "🏃‍♂️ 马拉松：连续工作 2 小时不中断", "badge": "马拉松"},
    {"id": "meeting_killer", "text": "💼 会议杀手：完成一个「会议」分类的任务", "badge": "会议杀手"},
    {"id": "code_wizard", "text": "💻 代码魔法师：完成一个「编程」分类的任务", "badge": "代码魔法师"},
    {"id": "design_guru", "text": "🎨 设计大师：完成一个「设计」分类的任务", "badge": "设计大师"},
    {"id": "writer", "text": "✍️ 笔耕不辍：完成一个「写作」分类的任务", "badge": "笔耕不辍"},
    {"id": "learner", "text": "📚 学无止境：完成一个「学习」分类的任务", "badge": "学无止境"},
    {"id": "ppt_master", "text": "📊 PPT 狂魔：完成一个「PPT」分类的任务", "badge": "PPT 狂魔"},
    {"id": "back_to_back", "text": "🔗 无缝衔接：完成一个任务后 1 分钟内开始下一个", "badge": "无缝衔接"},
    {"id": "happy_hour", "text": "🍺 快乐时光：下午 5 点后完成 2 个任务", "badge": "快乐时光"},
    {"id": "no_edit", "text": "📝 一次成型：创建任务后不编辑，直接完成", "badge": "一次成型"},
    {"id": "timer_champ", "text": "⏱️ 计时达人：使用计时器完成一个任务", "badge": "计时达人"},
    {"id": "weekend_warrior", "text": "⚔️ 周末战士：周六或周日完成 3 个任务", "badge": "周末战士"},
    {"id": "monday_grind", "text": "💪 周一动力：周一完成 4 个任务", "badge": "周一动力"},
    {"id": "friday_finish", "text": "🎉 周五狂欢：周五完成所有任务", "badge": "周五狂欢"},
    {"id": "multi_category", "text": "🌈 彩虹任务：一天内完成 3 个不同分类的任务", "badge": "彩虹任务"},
    {"id": "deep_work", "text": "🧠 深度工作：完成一个预估 > 90 分钟的任务", "badge": "深度工作"},
    {"id": "quick_decision", "text": "⚡ 快速决策：创建任务后 30 秒内开始", "badge": "快速决策"},
    {"id": "perfect_ratio", "text": "💯 完美比例：今天所有任务的总误差 < 15%", "badge": "完美比例"},
    {"id": "early_riser", "text": "🐓 闻鸡起舞：早上 7 点前完成一个任务", "badge": "闻鸡起舞"},
    {"id": "lunch_break", "text": "🍱 午休不休息：午餐时间完成一个任务", "badge": "午休不休息"},
    {"id": "zero_distraction", "text": "🧘 零干扰：一个任务从开始到完成不使用其他应用", "badge": "零干扰"},
    {"id": "half_day", "text": "⏳ 半日奇迹：半天内完成 5 个任务", "badge": "半日奇迹"},
    {"id": "repeater", "text": "🔄 熟能生巧：连续 3 天完成同一个分类的任务", "badge": "熟能生巧"},
    {"id": "night_owl_challenge", "text": "🦉 深夜食堂：凌晨 0-2 点完成一个任务", "badge": "深夜食堂"},
    {"id": "clean_slate", "text": "🧹 清空桌面：今天创建的所有任务全部完成", "badge": "清空桌面"},
    {"id": "over_achiever", "text": "🌟 超额完成：完成比计划多 2 个以上的任务", "badge": "超额完成"},
    {"id": "consistent", "text": "📏 稳定发挥：连续 3 个任务误差都在 20% 以内", "badge": "稳定发挥"},
    {"id": "one_hour", "text": "⏰ 一小时奇迹：一小时内完成 3 个任务", "badge": "一小时奇迹"},
    {"id": "break_taker", "text": "☕ 劳逸结合：两个任务之间休息 10 分钟以上", "badge": "劳逸结合"},
    {"id": "category_king", "text": "👑 分类之王：今天 80% 的任务属于同一个分类", "badge": "分类之王"},
    {"id": "balanced", "text": "⚖️ 平衡大师：今天完成的任务分布在 3+ 个分类", "badge": "平衡大师"},
    {"id": "comeback", "text": "🔄 卷土重来：昨天断签，今天重新开始", "badge": "卷土重来"},
    {"id": "fifty_fifty", "text": "🎲 五五开：今天恰好一半任务提前完成，一半延后", "badge": "五五开"},
]


def _uid(user_id):
    return user_id or get_current_user_id()


def get_today_challenge(user_id=None):
    uid = _uid(user_id)
    today = date.today().isoformat()

    challenge_json = get_setting("today_challenge", "{}", uid)
    data = json.loads(challenge_json)

    if data.get("date") == today:
        challenge_id = data.get("challenge_id")
        for c in CHALLENGES:
            if c["id"] == challenge_id:
                return {**c, "completed": data.get("completed", False)}

    return None


def roll_challenge(user_id=None):
    uid = _uid(user_id)
    today = date.today().isoformat()

    existing = get_today_challenge(uid)
    if existing:
        return existing

    challenge = random.choice(CHALLENGES)
    data = {
        "date": today,
        "challenge_id": challenge["id"],
        "completed": False,
    }
    set_setting("today_challenge", json.dumps(data, ensure_ascii=False), uid)
    return {**challenge, "completed": False}


def complete_challenge(user_id=None):
    uid = _uid(user_id)
    today = date.today().isoformat()

    challenge_json = get_setting("today_challenge", "{}", uid)
    data = json.loads(challenge_json)

    if data.get("date") != today:
        return None

    data["completed"] = True
    set_setting("today_challenge", json.dumps(data, ensure_ascii=False), uid)

    for c in CHALLENGES:
        if c["id"] == data["challenge_id"]:
            return c

    return None