import streamlit as st
import html as _html

from services.task_manager import get_today_tasks
from services.calibration import calibrate_all_tasks_with_info
from services.streak import get_streak, get_month_heatmap
from services.achievements import get_achievements
from dao.settings_dao import get_setting
from utils.config import get_available_minutes


def render_sidebar():
    with st.sidebar:
        render_streak_section()
        render_navigation()
        render_daily_egg()
        render_theme_toggle()


def render_sidebar_status(today_tasks):
    calibrated = calibrate_all_tasks_with_info(today_tasks) if today_tasks else []
    total_cal = sum(t['calibrated_minutes'] for t in calibrated)
    total_est = sum(t['estimated_minutes'] for t in calibrated)
    available = get_available_minutes(
        get_setting("work_start_hour", "9:00"),
        get_setting("work_end_hour", "18:00"),
        get_setting("lunch_start_hour", "12:00"),
        get_setting("lunch_end_hour", "13:00"),
    )

    avg_ratio = total_cal / total_est if total_est > 0 else 1.0
    usage_pct = min(total_cal / available * 100, 100) if available > 0 else 0
    remaining = max(available - total_cal, 0)
    remaining_h = remaining / 60
    scheduled_h = total_cal / 60
    available_h = available / 60
    done = sum(1 for t in calibrated if t['status'] == 'done')
    total = len(calibrated)

    if avg_ratio <= 0.8:
        hallucination_label = "\u9ad8\u4f30\u4e86"
        hallucination_color = "var(--orange)"
    elif avg_ratio >= 1.3:
        hallucination_label = "\u4f4e\u4f30\u4e86"
        hallucination_color = "var(--orange)"
    elif 0.9 <= avg_ratio <= 1.1:
        hallucination_label = "\u9884\u4f30\u7cbe\u51c6"
        hallucination_color = "var(--green)"
    else:
        hallucination_label = "\u6709\u504f\u5dee"
        hallucination_color = "var(--orange)"

    pct_color = "var(--red)" if usage_pct > 100 else ("var(--orange)" if usage_pct > 80 else "var(--green)")
    done_text = "\u2705 \u5168\u90e8\u5b8c\u6210" if done == total and total > 0 else f"\u2705 {done}/{total} \u5df2\u5b8c\u6210"
    done_color = "var(--green)" if done == total and total > 0 else "var(--text-secondary)"

    with st.container(border=True):
        st.markdown("\U0001f4ca **\u4eca\u65e5\u72b6\u6001**")

        st.markdown(
            f"<div style='display:flex;align-items:center;gap:12px;margin:8px 0;'>"
            f"<span style='font-size:26px;font-weight:700;color:var(--text-primary);'>"
            f"\u23f1 {remaining_h:.1f}<span style='font-size:14px;font-weight:400;color:var(--text-secondary);'>h</span></span>"
            f"<span style='color:var(--text-secondary);'>|</span>"
            f"<span style='font-size:15px;font-weight:600;color:{done_color};'>"
            f"\U0001f4cb {done}/{total} \u5df2\u5b8c\u6210</span>"
            f"</div>",
            unsafe_allow_html=True
        )

        st.markdown(
            f"<div style='font-size:12px;color:var(--text-secondary);margin:0 0 6px 0;'>"
            f"\u6392\u671f <b style='color:var(--text-primary);'>{scheduled_h:.1f}h</b>"
            f" / \u53ef\u652f\u914d <b style='color:var(--text-primary);'>{available_h:.1f}h</b>"
            f"<span title='\u5df2\u6392\u671f = \u6240\u6709\u4efb\u52a1\u6821\u51c6\u540e\u65f6\u95f4\u603b\u548c\uff1b\u4eca\u65e5\u53ef\u652f\u914d = \u5de5\u4f5c\u65f6\u95f4 - \u5348\u4f11\u65f6\u95f4' "
            f"style='cursor:help;margin-left:4px;'>\u2460</span>"
            f"</div>",
            unsafe_allow_html=True
        )

        st.markdown(
            f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:6px;'>"
            f"<span style='font-size:13px;color:{hallucination_color};'>"
            f"\u5e7b\u89c9 {avg_ratio:.1f}x\uff08\u26a0\ufe0f {hallucination_label}\uff09</span>"
            f"<span style='color:var(--text-secondary);'>|</span>"
            f"<span style='font-size:13px;color:{pct_color};'>\u8d1f\u8f7d {usage_pct:.0f}%</span>"
            f"</div>",
            unsafe_allow_html=True
        )

        if usage_pct >= 100:
            overflow_tasks = [t for t in calibrated if t['status'] == 'todo']
            worst = max(overflow_tasks, key=lambda t: t.get('calibrated_minutes', 0), default=None)
            if worst:
                st.caption(f"\U0001f480 \u300c{worst['description'][:12]}\u300d\u8fd8\u8981\u9a97\u4f60 {worst['calibrated_minutes']} \u5206\u949f")

        if st.session_state.timer_running:
            current_task = next((t for t in today_tasks if t['id'] == st.session_state.timer_task_id), None)
            if current_task:
                elapsed = st.session_state.timer_elapsed_seconds
                elapsed_min = int(elapsed / 60)
                est = current_task.get('calibrated_minutes') or current_task.get('estimated_minutes') or 0
                remaining_t = max(est - elapsed_min, 0)
                st.markdown(
                    f"<div class='card-sm' style='background:var(--timer-overtime-bg);'>"
                    f"<div style='font-size:12px;color:var(--text-muted);'>\U0001f534 \u6b63\u5728\u8ba1\u65f6</div>"
                    f"<div style='font-weight:600;'>{current_task['description'][:18]}</div>"
                    f"<div style='font-size:12px;color:var(--text-muted);'>\u5df2\u8fc7 {elapsed_min}min \u00b7 \u5269\u4f59 ~{remaining_t}min</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )


def render_navigation():
    st.markdown(
        "<div style='font-size:11px;text-transform:uppercase;letter-spacing:1px;"
        "color:var(--text-muted);margin-bottom:8px;'>\u5bfc\u822a</div>",
        unsafe_allow_html=True
    )

    nav_items = [
        ("\U0001f4cb  \u4eca\u65e5\u8ba1\u5212", "today"),
        ("\U0001f4ca  \u5386\u53f2\u590d\u76d8", "history"),
        ("\U0001f4dd  \u5168\u90e8\u4efb\u52a1", "all_tasks"),
        ("\U0001f3c6  \u5fbd\u7ae0\u5899", "badges"),
        ("\u23f1  \u5feb\u901f\u8ba1\u65f6", "quick_timer"),
        ("\u2699\ufe0f  \u8bbe\u7f6e", "settings"),
    ]

    for label, page_id in nav_items:
        is_current = st.session_state.page == page_id
        display_label = f"\u25b8 {label}" if is_current else f"  {label}"
        btn_type = "primary" if is_current else "secondary"
        if st.button(
            display_label,
            type=btn_type,
            use_container_width=True,
            key=f"nav_{page_id}"
        ):
            if not is_current:
                st.session_state.page = page_id
                st.rerun()


def render_streak_section():
    streak = get_streak()
    level = streak["level"]
    current_streak = streak["current_streak"]

    achievements = get_achievements()
    earned_count = sum(1 for a in achievements if a["earned"])
    total_ach = len(achievements)

    flame_emoji = "\U0001f525" if current_streak > 0 else "\U0001f4a4"

    if level["next"]:
        progress = level["progress"]
        next_name = level["next"]
        remaining = max(level["next_days"] - current_streak, 0)
    else:
        progress = 1.0
        next_name = "\u6ee1\u7ea7"
        remaining = 0

    with st.container(border=True):
        st.markdown(
            f'<div style="display:flex;align-items:baseline;gap:6px;margin-bottom:10px;">'
            f'<span style="font-size:15px;">{flame_emoji}</span>'
            f'<span style="font-size:18px;font-weight:700;color:var(--text-strong);">{current_streak}</span>'
            f'<span style="font-size:11px;color:var(--text-secondary);">\u5929</span>'
            f'<span style="color:var(--border-subtle);margin:0 2px;">\u00b7</span>'
            f'<span style="font-size:12px;">\U0001f3c6</span>'
            f'<span style="font-size:16px;font-weight:700;color:var(--text-strong);">{earned_count}</span>'
            f'<span style="font-size:11px;color:var(--text-secondary);">/{total_ach}</span>'
            f'<span style="color:var(--border-subtle);margin:0 2px;">\u00b7</span>'
            f'<span style="font-size:12px;">{level["emoji"]}</span>'
            f'<span style="font-size:14px;font-weight:600;color:var(--text-strong);">{level["name"]}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

        bar_pct = int(progress * 100)
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;margin:2px 0;">'
            f'<span style="font-size:12px;">{level["emoji"]} {level["name"]}</span>'
            f'<span style="font-size:11px;color:var(--text-secondary);">\u2192</span>'
            f'<span style="font-size:12px;font-weight:500;">{next_name}</span>'
            f'<span style="font-size:11px;color:var(--text-secondary);margin-left:auto;">{bar_pct}%</span>'
            f'</div>'
            f'<div style="width:100%;height:5px;background:var(--progress-bg);border-radius:3px;overflow:hidden;margin-bottom:2px;">'
            f'<div style="width:{bar_pct}%;height:100%;background:var(--text-muted);border-radius:3px;transition:width 0.3s;"></div>'
            f'</div>',
            unsafe_allow_html=True
        )

        if remaining > 0:
            st.markdown(
                f'<div style="font-size:11px;color:var(--text-secondary);margin-top:2px;">'
                f'\u8fd8\u9700 <b style="color:var(--text-secondary);">{remaining}</b> \u5929\u5347\u7ea7\u5230 <b style="color:var(--text-secondary);">{next_name}</b>'
                f'</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div style="font-size:11px;color:var(--green);margin-top:2px;">'
                f'\u2728 \u5df2\u8fbe\u5230\u6700\u9ad8\u7b49\u7ea7'
                f'</div>',
                unsafe_allow_html=True
            )

    render_achievements_popover()


def render_daily_egg():
    from services.challenge import get_today_challenge, roll_challenge, complete_challenge

    challenge = get_today_challenge()
    if challenge:
        status_icon = "\u2705" if challenge.get("completed") else "\U0001f3b2"
        with st.container(border=True):
            st.markdown(
                f'<div style="font-size:12px;color:var(--text-muted);margin-bottom:4px;">'
                f'{status_icon} \u4eca\u65e5\u5f69\u86cb</div>'
                f'<div style="font-size:13px;color:var(--text-strong);line-height:1.4;">{challenge["text"]}</div>',
                unsafe_allow_html=True
            )
            if not challenge.get("completed"):
                if st.button("\u2705 \u5b8c\u6210", key="sidebar_complete_challenge", use_container_width=True):
                    result = complete_challenge()
                    if result:
                        from services.achievements import award_challenge_badge
                        challenge_badges = award_challenge_badge()
                        st.toast(f"\U0001f389 \u6311\u6218\u5b8c\u6210\uff1a{result['text'][:20]}...", icon="\U0001f3c6")
                        for badge in challenge_badges:
                            st.toast(f"\U0001f389 \u83b7\u5f97\u6210\u5c31\uff1a{badge['emoji']} {badge['name']}\uff01", icon="\U0001f3c6")
                        st.session_state.challenge_celebration = result['text']
                        st.rerun()
    else:
        with st.container(border=True):
            st.markdown(
                '<div style="font-size:12px;color:var(--text-muted);margin-bottom:4px;">'
                '\U0001f3b2 \u4eca\u65e5\u5f69\u86cb</div>'
                '<div style="font-size:13px;color:var(--text-strong);line-height:1.4;">'
                '\u968f\u673a\u6311\u6218\uff0c\u5b8c\u6210\u5f97\u5fbd\u7ae0</div>',
                unsafe_allow_html=True
            )
            if st.button("\U0001f3b2 \u62bd\u53d6", key="sidebar_roll_challenge", use_container_width=True):
                result = roll_challenge()
                st.toast(f"\U0001f3b2 \u6311\u6218\u5df2\u62bd\u53d6\uff1a{result['text'][:20]}...", icon="\U0001f3af")
                st.rerun()


def render_theme_toggle():
    st.divider()
    is_dark = st.session_state.get("dark_mode", False)
    icon = "\U0001f319" if not is_dark else "\u2600\ufe0f"
    label = "\U0001f319 \u6697\u9ed1\u6a21\u5f0f" if not is_dark else "\u2600\ufe0f \u4eae\u8272\u6a21\u5f0f"
    if st.button(label, key="theme_toggle_sidebar", use_container_width=True):
        st.session_state.dark_mode = not is_dark
        st.rerun()





def render_achievements_popover():
    achievements = get_achievements()
    earned_count = sum(1 for a in achievements if a["earned"])
    total = len(achievements)
    recent_earned = [a for a in achievements if a["earned"]][-8:]

    with st.popover("\U0001f3c6 \u5fbd\u7ae0", use_container_width=True):
        if recent_earned:
            st.markdown(
                '<p style="font-size:12px;color:var(--text-muted);margin-bottom:6px;">'
                '\u6700\u8fd1\u83b7\u5f97\u7684\u5fbd\u7ae0</p>',
                unsafe_allow_html=True
            )
            cols = st.columns(min(len(recent_earned), 4))
            for i, ach in enumerate(recent_earned):
                escaped_desc = _html.escape(ach["desc"])
                escaped_name = _html.escape(ach["name"])
                with cols[i % 4]:
                    st.markdown(
                        f'<div title="{escaped_desc}\n\u83b7\u5f97\u4e8e {ach["earned_at"]}" '
                        f'style="text-align:center;padding:2px 0;cursor:default;">'
                        f'<span style="font-size:22px;">{ach["emoji"]}</span><br>'
                        f'<span style="font-size:9px;color:var(--text-strong);">{escaped_name}</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
        else:
            st.markdown(
                '<p style="font-size:13px;color:var(--text-muted);margin-bottom:8px;">'
                '\u8fd8\u6ca1\u6709\u83b7\u5f97\u5fbd\u7ae0\uff0c\u5f00\u59cb\u5b8c\u6210\u4efb\u52a1\u5427 \u2728</p>',
                unsafe_allow_html=True
            )

        st.markdown(
            f'<p style="font-size:11px;color:var(--text-muted);margin-top:8px;">'
            f'\u5df2\u89e3\u9501 {earned_count}/{total} \u4e2a\u5fbd\u7ae0</p>',
            unsafe_allow_html=True
        )

        if st.button("\U0001f3c6 \u67e5\u770b\u5168\u90e8\u5fbd\u7ae0", use_container_width=True, type="primary", key="goto_badges"):
            st.session_state.page = "badges"
            st.rerun()


def render_mini_calendar_heatmap():
    from datetime import date, timedelta, datetime, timezone
    import calendar

    beijing_tz = timezone(timedelta(hours=8))
    today = datetime.now(beijing_tz).date()

    if st.session_state.get("calendar_year") is None:
        st.session_state.calendar_year = today.year
    if st.session_state.get("calendar_month") is None:
        st.session_state.calendar_month = today.month

    year = st.session_state.calendar_year
    month = st.session_state.calendar_month

    is_current = (year == today.year and month == today.month)

    heatmap = get_month_heatmap(year=year, month=month)

    cal = calendar.Calendar(firstweekday=6)
    month_days = list(cal.itermonthdates(year, month))

    week_day_names = ["\u65e5", "\u4e00", "\u4e8c", "\u4e09", "\u56db", "\u4e94", "\u516d"]

    max_count = max(heatmap.values()) if heatmap else 1

    def _green_intensity(dt, count):
        if dt.month != month:
            return "transparent", "var(--text-faint)"
        if dt > today:
            return "var(--bg-subtle)", "var(--text-faint)"
        if dt.isoformat() in heatmap:
            intensity = min(1.0, count / max(5, max_count))
            r = int(235 - intensity * 185)
            g = int(245 - intensity * 95)
            b = int(235 - intensity * 155)
            return f"rgb({r},{g},{b})", "#FFFFFF" if intensity > 0.5 else "var(--text-strong)"
        return "var(--border)", "var(--timer-meta)"

    col_prev, col_title, col_next, col_today = st.columns([1, 3, 1, 1.5])
    with col_prev:
        if st.button("\u25c0", key="cal_prev", use_container_width=True, help="\u4e0a\u4e2a\u6708"):
            if month == 1:
                st.session_state.calendar_year = year - 1
                st.session_state.calendar_month = 12
            else:
                st.session_state.calendar_month = month - 1
            st.rerun()
    with col_title:
        st.markdown(
            f'<p style="text-align:center;font-size:13px;font-weight:600;'
            f'color:var(--text-strong);margin:6px 0 2px 0;">'
            f'\U0001f4c5 {year}\u5e74{month}\u6708</p>',
            unsafe_allow_html=True
        )
    with col_next:
        next_disabled = is_current
        if st.button("\u25b6", key="cal_next", use_container_width=True, help="\u4e0b\u4e2a\u6708", disabled=next_disabled):
            if month == 12:
                st.session_state.calendar_year = year + 1
                st.session_state.calendar_month = 1
            else:
                st.session_state.calendar_month = month + 1
            st.rerun()
    with col_today:
        if not is_current:
            if st.button("\u4eca\u5929", key="cal_today", use_container_width=True):
                st.session_state.calendar_year = today.year
                st.session_state.calendar_month = today.month
                st.rerun()
        else:
            st.markdown(
                '<p style="text-align:center;font-size:11px;color:var(--text-faint);'
                'margin:4px 0;">\u5f53\u524d</p>',
                unsafe_allow_html=True
            )

    header_html = '<div style="display:flex;gap:3px;margin-bottom:3px;">'
    for d in week_day_names:
        header_html += f'<span style="flex:1;text-align:center;font-size:10px;color:var(--text-faint2);">{d}</span>'
    header_html += '</div>'
    st.markdown(header_html, unsafe_allow_html=True)

    weeks = []
    current_week = []
    for dt in month_days:
        current_week.append(dt)
        if dt.weekday() == 5:
            weeks.append(current_week)
            current_week = []
    if current_week:
        weeks.append(current_week)

    for week in weeks:
        parts = []
        for dt in week:
            count = heatmap.get(dt.isoformat(), 0)
            bg, fg = _green_intensity(dt, count)
            day_label = str(dt.day)
            if dt == today:
                day_label = f"<b>{dt.day}</b>"
            parts.append(
                f'<span title="{dt.isoformat()}: {count}\u4e2a\u4efb\u52a1" '
                f'style="flex:1;display:inline-flex;align-items:center;'
                f'justify-content:center;font-size:11px;color:{fg};background:{bg};'
                f'border-radius:4px;aspect-ratio:1;cursor:default;">{day_label}</span>'
            )
        week_html = f'<div style="display:flex;gap:3px;margin-bottom:3px;">{"".join(parts)}</div>'
        st.markdown(week_html, unsafe_allow_html=True)

    st.markdown(
        '<div style="display:flex;align-items:center;gap:4px;margin-top:4px;">'
        '<span style="font-size:9px;color:var(--text-faint2);">\u5c11</span>'
        '<span style="width:12px;height:12px;background:#F0F0F0;border-radius:2px;display:inline-block;"></span>'
        '<span style="width:12px;height:12px;background:#C6E6C6;border-radius:2px;display:inline-block;"></span>'
        '<span style="width:12px;height:12px;background:#7BC67B;border-radius:2px;display:inline-block;"></span>'
        '<span style="width:12px;height:12px;background:#2E7D32;border-radius:2px;display:inline-block;"></span>'
        '<span style="font-size:9px;color:var(--text-faint2);">\u591a</span>'
        '</div>',
        unsafe_allow_html=True
    )