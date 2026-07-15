import streamlit as st

from utils.config import get_available_minutes
from dao.settings_dao import get_setting
from services.task_manager import edit_task


def render_today_timeline(scheduled, calibrated, overflow):
    """渲染今日时间轴组件，展示任务计划排期与实际时间占用。"""
    if not calibrated:
        return

    # 汇总估计总时长与校准后总时长
    total_est = sum(t['estimated_minutes'] for t in calibrated)
    total_cal = sum(t['calibrated_minutes'] for t in calibrated)
    # 计算当日可用工作时间（分钟），扣除午休等不可用时段
    available = get_available_minutes(
        get_setting("work_start_hour", "9:00"),
        get_setting("work_end_hour", "18:00"),
        get_setting("lunch_start_hour", "12:00"),
        get_setting("lunch_end_hour", "13:00"),
    )

    work_start_raw = get_setting("work_start_hour", "9:00")
    work_end_raw = get_setting("work_end_hour", "18:00")
    work_start = int(work_start_raw.split(":")[0])
    work_end = int(work_end_raw.split(":")[0])

    # 统计有多少任务具有足够的校准样本（≥3 次历史记录）
    calibrated_count = sum(1 for t in calibrated if t.get('calibration_sample_count', 0) >= 3)
    # 超过半数任务有校准数据则认为数据完整
    data_complete = calibrated_count >= len(calibrated) * 0.5

    with st.container():
        done_count = sum(1 for t in calibrated if t['status'] == 'done')
        total_count = len(calibrated)
        title_extra = f" · {done_count}/{total_count} 已完成" if total_count > 0 else ""
        st.markdown(
            f"<h3 style='font-weight:400;margin:0 0 12px 0;'>📊 今日时间轴{title_extra}</h3>",
            unsafe_allow_html=True
        )

        # 左右两列：估计总时长 vs 校准后总时长
        col_a, col_b = st.columns(2, gap="medium")
        with col_a:
            st.metric("你的估计", f"{total_est}min", delta=f"{total_est/60:.1f}h")
        with col_b:
            st.metric("校准后", f"{total_cal}min",
                      delta=f"{total_cal/60:.1f}h" + (" (基于不完整数据)" if not data_complete else ""),
                      delta_color="inverse")

        if not data_complete and calibrated_count > 0:
            st.caption("⚠️ 部分任务校准数据不足，校准时间仅供参考")

        # 校准后总时长超出可用时间时发出警告
        if total_cal > available:
            st.error(f"💔 超出可用时间 {total_cal - available} 分钟")

        # 渲染时间块：优先使用调度器排期结果（含 scheduled_start / scheduled_end）
        # 若无排期结果，则回退到有实际执行时间的任务（兼容旧数据）
        st.caption(
            f"🕐 工作时间：{work_start_raw} - {work_end_raw}"
            f" · 已排期 {len(scheduled)} 个任务"
            + (f" · {len(overflow)} 个溢出" if overflow else "")
        )
        if scheduled:
            _render_time_blocks(scheduled, work_start, work_end)
        else:
            timed_tasks = [t for t in calibrated if t.get('start_time')]
            if timed_tasks:
                _render_time_blocks(timed_tasks, work_start, work_end)

        # 展示溢出任务（当日排不下的任务）
        if overflow:
            st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
            st.markdown(
                f"<div style='border:1px solid var(--tag-red-bg);border-radius:10px;padding:10px 14px;"
                f"background:linear-gradient(135deg,var(--timer-overtime-bg) 0%,var(--quote-bg) 100%);'>"
                f"<div style='font-size:13px;font-weight:600;color:var(--red);margin-bottom:6px;'>"
                f"🫠 今日时间不够，以下任务被挤出：</div>"
                f"</div>",
                unsafe_allow_html=True
            )
            for t in overflow:
                col_info, col_btn = st.columns([3, 1])
                with col_info:
                    st.markdown(
                        f"<span style='font-size:12px;color:var(--red);'>📌 {t['description'][:25]}"
                        f" <span style='color:var(--orange);font-weight:500;'>⏱ {t['calibrated_minutes']}min</span></span>",
                        unsafe_allow_html=True
                    )
                with col_btn:
                    if st.button(f"📅 明天", key=f"move_tmr_{t['id']}", use_container_width=True):
                        from datetime import date, timedelta
                        tomorrow = (date.today() + timedelta(days=1)).isoformat()
                        edit_task(t['id'], created_date=tomorrow)
                        st.rerun()

    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)


def _render_time_blocks(timed_tasks, work_start, work_end):
    from datetime import datetime
    from textwrap import dedent

    total_minutes = (work_end - work_start) * 60
    if total_minutes <= 0:
        return

    status_colors = {"todo": "var(--blue)", "doing": "var(--blue)", "done": "var(--green)"}
    status_labels = {"todo": "计划中", "doing": "进行中", "done": "已完成"}

    blocks_html = ""
    legend_html = ""
    shown_statuses = set()

    for task in timed_tasks:
        start_time = task.get('start_time')
        end_time = task.get('end_time')
        scheduled_start = task.get('scheduled_start')
        scheduled_end = task.get('scheduled_end')

        st_dt = None
        if start_time:
            try:
                st_dt = datetime.fromisoformat(start_time) if "T" in str(start_time) else datetime.strptime(str(start_time)[:19], "%Y-%m-%d %H:%M:%S")
                start_minutes = st_dt.hour * 60 + st_dt.minute
                has_actual_start = True
            except Exception:
                start_minutes = None
                has_actual_start = False
        else:
            start_minutes = None
            has_actual_start = False

        if start_minutes is None and scheduled_start:
            try:
                parts = scheduled_start.split(":")
                start_minutes = int(parts[0]) * 60 + int(parts[1])
                has_actual_start = False
            except Exception:
                continue

        if start_minutes is None:
            continue

        if end_time and has_actual_start:
            try:
                et_dt = datetime.fromisoformat(end_time) if "T" in str(end_time) else datetime.strptime(str(end_time)[:19], "%Y-%m-%d %H:%M:%S")
                end_minutes = et_dt.hour * 60 + et_dt.minute
            except Exception:
                end_minutes = None
        else:
            end_minutes = None

        if end_minutes is None and not has_actual_start and scheduled_end:
            try:
                parts = scheduled_end.split(":")
                end_minutes = int(parts[0]) * 60 + int(parts[1])
            except Exception:
                end_minutes = None

        if end_minutes is None:
            end_minutes = start_minutes + max(task.get('calibrated_minutes', task.get('estimated_minutes', 30)), 15)

        start_minutes = max(start_minutes, work_start * 60)
        end_minutes = min(end_minutes, work_end * 60)

        left_pct = (start_minutes - work_start * 60) / total_minutes * 100
        width_pct = (end_minutes - start_minutes) / total_minutes * 100
        if width_pct < 1:
            width_pct = 1

        status = task.get('status', 'todo')
        color = status_colors.get(status, "var(--text-faint)")
        desc = task['description'][:12]
        cat = task.get('category', '')
        cal_min = task.get('calibrated_minutes', task.get('estimated_minutes', 0))
        done_prefix = "✅ " if status == "done" else ""
        block_opacity = "0.85" if status == "done" else "1"

        display_time = st_dt.strftime('%H:%M') if st_dt else scheduled_start

        end_hour = end_minutes // 60
        end_min = end_minutes % 60
        end_time_str = f"{end_hour:02d}:{end_min:02d}"
        display_start = display_time or f"{start_minutes // 60:02d}:{start_minutes % 60:02d}"
        est_min = task.get('estimated_minutes', 0)

        blocks_html += (
            f'<div class="tb-wrap" style="position:absolute;left:{left_pct:.1f}%;width:{width_pct:.1f}%;z-index:1;">'
            f'<div style="background:{color};border-radius:4px;height:28px;line-height:28px;'
            f'font-size:10px;color:#fff;padding:0 6px;overflow:hidden;white-space:nowrap;'
            f'text-overflow:ellipsis;box-sizing:border-box;cursor:pointer;opacity:{block_opacity};">'
            f'{done_prefix}{display_start} {desc}</div>'
            f'<div class="tb-tip">'
            f'<strong>{desc} · {cat}</strong><br>'
            f'⏱ 估计 {est_min}min · 校准 {cal_min}min<br>'
            f'🕐 {display_start} → {end_time_str} · {status_labels.get(status, status)}'
            f'</div></div>'
        )

        if status not in shown_statuses:
            shown_statuses.add(status)
            legend_html += (
                f'<span style="display:inline-block;width:10px;height:10px;'
                f'border-radius:2px;background:{color};margin-right:4px;vertical-align:middle;"></span>'
                f'<span style="font-size:10px;color:var(--timer-meta);margin-right:12px;">{status_labels.get(status, status)}</span>'
            )

    hour_markers = ""
    for h in range(work_start, work_end + 1):
        left_pct = (h - work_start) * 60 / total_minutes * 100
        hour_markers += (
            f'<div style="position:absolute;left:{left_pct:.1f}%;top:0;bottom:0;'
            f'width:1px;background:var(--timeline-line);"></div>'
            f'<div style="position:absolute;left:{left_pct:.1f}%;top:32px;'
            f'font-size:9px;color:var(--text-faint);transform:translateX(-50%);">{h}:00</div>'
        )

    html = dedent(f"""\
    <style>
    .tb-wrap {{ z-index:1; }}
    .tb-wrap:hover {{ z-index:999; }}
    .tb-tip {{
        visibility:hidden; opacity:0;
        position:absolute; bottom:calc(100% + 6px); left:50%;
        transform:translateX(-50%);
        background:#333; color:#fff; font-size:11px; line-height:1.5;
        padding:6px 10px; border-radius:6px; white-space:nowrap;
        pointer-events:none; z-index:1000;
        transition: opacity 0.18s ease, visibility 0.18s ease;
    }}
    .tb-tip::after {{
        content:''; position:absolute; top:100%; left:50%;
        transform:translateX(-50%);
        border:5px solid transparent; border-top-color:#333;
    }}
    .tb-wrap:hover .tb-tip {{ visibility:visible; opacity:1; }}
    </style>
    <div style="margin-top:8px;margin-bottom:4px;">
        <span style="font-size:11px;color:var(--timer-meta);">🕐 时间占用</span>
        {legend_html}
    </div>
    <div style="position:relative;height:48px;background:var(--timeline-bg);border-radius:8px;
                margin-bottom:4px;overflow:visible;">
        {hour_markers}
        {blocks_html}
    </div>
    """)
    st.markdown(html, unsafe_allow_html=True)