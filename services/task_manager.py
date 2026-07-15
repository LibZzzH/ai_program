from datetime import datetime
from utils.db import get_current_user_id
from dao import task_dao


def _uid(user_id):
    if user_id is None:
        return get_current_user_id()
    return user_id


def create_task(category, description, estimated_minutes, created_date=None, scheduled_start=None, notes="", user_id=None):
    task_dao.add_task(category, description, estimated_minutes, created_date, scheduled_start, notes, user_id=_uid(user_id))


def start_task(task_id, user_id=None):
    task_dao.update_task_status(task_id, 'doing', user_id=_uid(user_id), start_time=datetime.now().isoformat())


def complete_task(task_id, actual_minutes=None, user_id=None):
    end_time = datetime.now()
    uid = _uid(user_id)
    task_dao.update_task_status(task_id, 'done', user_id=uid, end_time=end_time.isoformat())
    if actual_minutes is not None:
        task_dao.set_actual_minutes(task_id, actual_minutes, user_id=uid)

    from services.streak import record_completion
    from services.achievements import check_and_award
    record_completion(uid)
    check_and_award(uid)


def edit_task(task_id, category=None, description=None, estimated_minutes=None, notes=None, created_date=None, user_id=None):
    task_dao.update_task(task_id, user_id=_uid(user_id), category=category, description=description,
                         estimated_minutes=estimated_minutes, notes=notes, created_date=created_date)


def remove_task(task_id, user_id=None):
    task_dao.delete_task(task_id, user_id=_uid(user_id))


def move_up(task_id, user_id=None):
    task_dao.move_task_up(task_id, user_id=_uid(user_id))


def move_down(task_id, user_id=None):
    task_dao.move_task_down(task_id, user_id=_uid(user_id))


def get_today_tasks(user_id=None):
    return task_dao.get_today_tasks(user_id=_uid(user_id))


def get_tasks_by_date(dt, user_id=None):
    return task_dao.get_tasks_by_date(dt, user_id=_uid(user_id))


def get_all_tasks(user_id=None):
    return task_dao.get_all_tasks(user_id=_uid(user_id))


def get_category_stats(user_id=None):
    return task_dao.get_category_stats(user_id=_uid(user_id))


def generate_demo_data(user_id=None):
    uid = _uid(user_id)
    from datetime import date, timedelta, datetime as dt
    from dao.task_dao import add_task, get_task_count, delete_all_tasks

    existing = get_task_count(uid)
    if existing > 0:
        return False, f"已有 {existing} 条真实任务，演示数据仅在空白账户下生成"

    today = date.today()
    today_str = today.isoformat()
    yesterday = (today - timedelta(days=1)).isoformat()
    now = dt.now()

    def _add(cat, desc, est, created_date, status="todo", actual=None, notes="", scheduled_start=None):
        task_id = add_task(cat, desc, est, created_date=created_date, scheduled_start=scheduled_start, notes=notes, user_id=uid)
        if task_id and status == "doing":
            start_task(task_id, user_id=uid)
        if task_id and status == "done":
            from dao.task_dao import update_task_status, set_actual_minutes
            update_task_status(task_id, "done", user_id=uid, end_time=created_date)
            if actual:
                set_actual_minutes(task_id, actual, user_id=uid)
        return task_id

    history_tasks = [
        ("PPT", "Q4 战略汇报 PPT", 30, 78, "结构定了，差美化"),
        ("PPT", "产品新功能发布会", 45, 110, "加了动效和视频"),
        ("PPT", "实习生培训课件", 20, 42, "只做了前 10 页"),
        ("PPT", "年度总结大会", 60, 140, "数据图表太多，做了两天"),
        ("写作", "月度工作周报", 30, 58, "这次写了 3 页"),
        ("写作", "技术方案文档", 60, 125, "架构图改了 4 版"),
        ("写作", "项目复盘报告", 45, 82, "访谈了 5 个同事"),
        ("写作", "产品需求文档 PRD", 90, 160, "功能点太多，写了 20 页"),
        ("会议", "跨部门需求评审会", 30, 42, "吵了半小时没结论"),
        ("会议", "1on1 周会", 15, 18, "主要聊了晋升"),
        ("会议", "Sprint 计划会", 45, 65, "估时花了太多时间"),
        ("编程", "修复登录模块 Bug", 20, 35, "最后发现是缓存问题"),
        ("编程", "数据迁移脚本", 40, 68, "Python → SQL，手动处理了 200 条脏数据"),
        ("编程", "接口性能优化", 60, 95, "加了 Redis 缓存，QPS 从 200 到 2000"),
        ("设计", "新功能原型图", 60, 95, "改了 5 版，PM 反复改需求"),
        ("设计", "App 图标设计", 30, 45, "画了 3 个方案"),
        ("学习", "技术分享会", 30, 40, "讲了微服务架构"),
        ("学习", "读《人月神话》", 45, 60, "做了笔记，收获很大"),
        ("邮件", "回复客户邮件", 20, 28, "附了报价单"),
        ("邮件", "整理收件箱", 10, 12, "删了 300 封垃圾邮件"),
        ("阅读", "浏览行业资讯", 30, 35, "看了 5 篇技术文章"),
        ("阅读", "读产品文档", 20, 25, "新竞品分析"),
    ]

    for i, (cat, desc, est, act, notes) in enumerate(history_tasks):
        day_offset = max(0, 22 - i)
        task_date = (today - timedelta(days=day_offset)).isoformat()
        _add(cat, desc, est, task_date, status="done", actual=act, notes=notes)

    today_demo = [
        ("编程", "实现用户反馈功能", 45, today_str, "todo", "后台接口已经有了，只差前端", "09:00"),
        ("写作", "本周工作总结", 30, today_str, "todo", "记得把上周遗留的也写上", "09:45"),
        ("会议", "产品评审会", 30, today_str, "doing", "准备原型展示", "10:15"),
        ("PPT", "客户提案 PPT", 60, today_str, "todo", "方案一和方案二都要做", "13:00"),
        ("设计", "登录页改版", 40, today_str, "todo", "参考竞品的新版设计", "14:00"),
        ("编程", "修复数据导出 Bug", 20, today_str, "todo", "", "14:40"),
        ("学习", "看 AI 技术分享视频", 30, today_str, "todo", "公司内部培训录像", "15:00"),
        ("邮件", "回复客户问题", 15, today_str, "todo", "关于交付时间", "15:30"),
        ("阅读", "技术周报", 20, today_str, "todo", "这周的 AI 资讯", "16:00"),
    ]

    for cat, desc, est, created_date, status, notes, scheduled_start in today_demo:
        _add(cat, desc, est, created_date, status=status, notes=notes, scheduled_start=scheduled_start)

    yesterday_demo = [
        ("编程", "代码审查", 30, yesterday, "done", 42, "审查了 3 个 PR，发现 2 个潜在问题"),
        ("写作", "日报", 10, yesterday, "done", 12, "今天效率还行"),
        ("会议", "站会", 15, yesterday, "done", 18, "讨论了昨天的线上问题"),
        ("设计", "图标资源整理", 20, yesterday, "done", 25, "统一了设计规范"),
    ]

    for cat, desc, est, created_date, status, act, notes in yesterday_demo:
        _add(cat, desc, est, created_date, status=status, actual=act, notes=notes)

    return True, f"已注入 {len(history_tasks) + len(today_demo) + len(yesterday_demo)} 条演示数据（含今日计划、历史记录、备注等）"


def clear_demo_data(user_id=None):
    from dao.task_dao import delete_all_tasks
    delete_all_tasks(_uid(user_id))
    return True, "演示数据已清除"