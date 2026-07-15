from datetime import datetime, timedelta
from dao.settings_dao import get_setting


def reschedule_tasks(today_tasks, available_slots, rest_minutes=0):
    if not available_slots:
        today_now = datetime.now()
        ws = get_setting("work_start_hour", "9:00")
        we = get_setting("work_end_hour", "18:00")
        ls = get_setting("lunch_start_hour", "12:00")
        le = get_setting("lunch_end_hour", "13:00")
        ws_h, ws_m = (int(x) for x in ws.split(":"))
        we_h, we_m = (int(x) for x in we.split(":"))
        ls_h, ls_m = (int(x) for x in ls.split(":"))
        le_h, le_m = (int(x) for x in le.split(":"))
        available_slots = [
            (today_now.replace(hour=ws_h, minute=ws_m, second=0, microsecond=0),
             today_now.replace(hour=ls_h, minute=ls_m, second=0, microsecond=0)),
            (today_now.replace(hour=le_h, minute=le_m, second=0, microsecond=0),
             today_now.replace(hour=we_h, minute=we_m, second=0, microsecond=0)),
        ]

    scheduled = []
    overflow = []
    warnings = []

    fixed_tasks = []
    auto_tasks = []
    today = datetime.now().replace(second=0, microsecond=0)

    for task in today_tasks:
        if 'calibrated_minutes' not in task:
            continue
        st = task.get('scheduled_start')
        if st:
            try:
                h, m = map(int, st.split(':'))
                task['_fixed_start'] = today.replace(hour=h, minute=m, second=0, microsecond=0)
                fixed_tasks.append(task)
            except:
                auto_tasks.append(task)
        else:
            auto_tasks.append(task)

    available_blocks = list(available_slots)

    for task in fixed_tasks:
        fixed_start = task['_fixed_start']
        duration = timedelta(minutes=task['calibrated_minutes'])
        fixed_end = fixed_start + duration
        placed = False

        new_blocks = []
        for (s_start, s_end) in available_blocks:
            if fixed_end <= s_start or fixed_start >= s_end:
                new_blocks.append((s_start, s_end))
                continue
            if fixed_start >= s_start and fixed_end <= s_end:
                if fixed_start > s_start:
                    new_blocks.append((s_start, fixed_start))
                if fixed_end < s_end:
                    new_blocks.append((fixed_end, s_end))
                placed = True
            elif fixed_start < s_start and fixed_end > s_end:
                continue
            elif fixed_start < s_start:
                new_blocks.append((fixed_end, s_end))
                placed = True
            else:
                new_blocks.append((s_start, fixed_start))
                placed = True

        if placed:
            available_blocks = new_blocks
            task['scheduled_start'] = fixed_start.strftime('%H:%M')
            task['scheduled_end'] = fixed_end.strftime('%H:%M')
            scheduled.append(task)
        else:
            overflow.append(task)

    available_blocks.sort(key=lambda x: x[0])
    slot_idx = 0
    current_time = available_blocks[0][0] if available_blocks else None

    for task in auto_tasks:
        if not available_blocks:
            overflow.append(task)
            continue

        duration = timedelta(minutes=task['calibrated_minutes'])
        task_end = current_time + duration

        while slot_idx < len(available_blocks):
            slot_start, slot_end = available_blocks[slot_idx]
            if current_time < slot_start:
                current_time = slot_start
                task_end = current_time + duration

            if task_end <= slot_end:
                task['scheduled_start'] = current_time.strftime('%H:%M')
                task['scheduled_end'] = task_end.strftime('%H:%M')
                scheduled.append(task)
                current_time = task_end + timedelta(minutes=rest_minutes)
                break
            else:
                slot_idx += 1
                if slot_idx < len(available_blocks):
                    current_time = available_blocks[slot_idx][0]
                    task_end = current_time + duration
        else:
            overflow.append(task)
            ratio = task.get('expansion_ratio', 1.0)
            if ratio > 1.5:
                warnings.append(
                    f"'{task['description']}' 校准后需要 {task['calibrated_minutes']} 分钟，今日已排不下，已被挤到明天。"
                )

    return scheduled, overflow, warnings


def reschedule_with_calendar(today_tasks, calendar_service, work_start_h=9, work_end_h=18,
                             lunch_start_h=12, lunch_end_h=13,
                             work_start_m=0, work_end_m=0,
                             lunch_start_m=0, lunch_end_m=0, rest_minutes=0):
    from datetime import date
    available_slots = calendar_service.get_available_slots(
        date.today(), work_start_h, work_end_h, lunch_start_h, lunch_end_h,
        work_start_m, work_end_m, lunch_start_m, lunch_end_m
    )

    if not available_slots:
        today = datetime.now()
        available_slots = [
            (today.replace(hour=work_start_h, minute=0, second=0, microsecond=0),
             today.replace(hour=lunch_start_h, minute=0, second=0, microsecond=0)),
            (today.replace(hour=lunch_end_h, minute=0, second=0, microsecond=0),
             today.replace(hour=work_end_h, minute=0, second=0, microsecond=0)),
        ]

    return reschedule_tasks(today_tasks, available_slots, rest_minutes)