import streamlit as st
from datetime import datetime

from utils.db import init_db, get_current_user_id, get_connection
from utils.config import GLOBAL_CSS, get_work_slots
from utils.helpers import get_categories, hallucination_tag_class

from services.task_manager import (
    get_today_tasks, start_task, complete_task, edit_task, remove_task,
    move_up, move_down
)
from services.calibration import calibrate_all_tasks_with_info, get_category_expansion_ratio
from services.roast_generator import generate_daily_review, generate_ai_daily_review
from services.streak import record_completion
from services.achievements import check_and_award
from scheduler import reschedule_tasks
from dao.task_dao import update_task_status, set_actual_minutes, delete_task
from dao.settings_dao import get_setting

from ui.sidebar import render_sidebar, render_sidebar_status
from ui.topbar import render_topbar
from ui.task_creation import render_task_creation_card
from ui.timeline import render_today_timeline
from ui.timer import render_floating_timer
from ui.review import render_history_review, render_all_tasks_page, render_quick_timer
from ui.settings import render_settings_page
from ui.profile import render_profile_page
from ui.badges import render_badge_wall

st.set_page_config(
    page_title="时间感知幻觉破除器",
    page_icon="⏰",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_db()


def init_session_state():
    defaults = {
        "page": "today",
        "dark_mode": False,
        "celebration_trigger": None,
        "challenge_celebration": None,
        "timer_running": False,
        "timer_task_id": None,
        "timer_start": None,
        "timer_elapsed_seconds": 0,
        "show_actual_input": False,
        "actual_task_id": None,
        "elapsed_minutes": 30,
        "ai_enabled": True,
        "ai_enabled_providers": {},
        "edit_mode": False,
        "edit_task_id": None,
        "last_tick": None,
        "roast_mode": "扎心",
        "quick_timer_running": False,
        "quick_timer_start": None,
        "quick_timer_elapsed": 0,
        "quick_timer_category": "其他",
        "quick_timer_paused": False,
        "quick_timer_stopped": False,
        "quick_timer_final_elapsed": 0,
        "roast_popup": None,
        "selected_category": None,
        "calibration_preview": None,
        "logged_in": False,
        "current_user": None,
        "custom_categories": [],
        "demo_data_loaded": False,
        "calendar_year": None,
        "calendar_month": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def main():
    init_session_state()

    if st.query_params.get("logout") == "1":
        from services.auth import clear_remember_token
        from services.calibration import clear_engine_cache
        cu = st.session_state.get("current_user")
        if cu:
            uid = cu.get("id") if isinstance(cu, dict) else (cu.id if hasattr(cu, "id") else "")
            if uid:
                clear_remember_token(uid)
        clear_engine_cache()
        st.session_state.logged_in = False
        st.session_state.current_user = None
        st.session_state.rt_token = ""
        st.query_params.clear()
        st.session_state._logout_flag = True
        st.rerun()
        return

    if st.session_state.get("_logout_flag"):
        st.session_state._logout_flag = False
        from ui.login import render_login_page
        render_login_page()
        st.stop()

    if not st.session_state.get("logged_in"):
        try_auto_login()

    if not st.session_state.get("logged_in"):
        from services.calibration import clear_engine_cache
        clear_engine_cache()
        from ui.login import render_login_page
        render_login_page()
        return

    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
    inject_dark_mode_css()
    inject_celebration_css()

    from utils.config import AI_PROVIDERS
    configured = [p["name"] for p in AI_PROVIDERS.values() if p.get("api_key")]
    if not configured:
        st.warning("未配置任何 AI 模型的 API Key，AI 毒舌功能将不可用。请在 .env 文件中设置。")

    st.components.v1.html("""
    <script>
    (function() {
        var btn = document.createElement('div');
        btn.className = 'sidebar-toggle-btn';
        btn.innerHTML = '☰';
        btn.title = '展开侧边栏';
        btn.onclick = function() {
            var doc = parent.document;
            var toggle = doc.querySelector('[data-testid="collapsedControl"]');
            if (toggle) { toggle.click(); return; }
            toggle = doc.querySelector('button[kind="headerNoPadding"]');
            if (toggle) { toggle.click(); return; }
            toggle = doc.querySelector('[data-testid="stSidebarCollapseButton"]');
            if (toggle) { toggle.click(); return; }
            var btns = doc.querySelectorAll('header button');
            for (var i = 0; i < btns.length; i++) {
                if (btns[i].getAttribute('data-testid') && btns[i].getAttribute('data-testid').indexOf('Sidebar') !== -1) {
                    btns[i].click();
                    return;
                }
            }
        };
        parent.document.body.appendChild(btn);
    })();
    </script>
    """, height=0)

    render_topbar()
    render_floating_timer()
    render_sidebar()

    page = st.session_state.page

    if page == "today":
        render_today_page()
    elif page == "history":
        render_history_review()
    elif page == "all_tasks":
        render_all_tasks_page()
    elif page == "quick_timer":
        render_quick_timer()
    elif page == "settings":
        render_settings_page()
    elif page == "profile":
        if st.session_state.get("logged_in"):
            render_profile_page()
        else:
            st.warning("请先登录")
    elif page == "badges":
        render_badge_wall()

    inject_dark_mode_js()
    inject_celebration_trigger()


def render_today_page():
    from datetime import timedelta as td, datetime, timezone
    from services.roast_generator import get_or_generate_daily_quote
    from services.challenge import get_today_challenge, roll_challenge

    beijing_tz = timezone(td(hours=8))
    today = datetime.now(beijing_tz).date()
    if "view_date" not in st.session_state:
        st.session_state.view_date = today

    view_date = st.session_state.view_date
    view_date_str = view_date.isoformat()
    is_today = view_date == today
    is_future = view_date > today
    is_past = view_date < today

    quote = get_or_generate_daily_quote()
    st.markdown(
        f"<div class='daily-quote-card' style='background:linear-gradient(135deg,var(--bg-card),var(--bg));"
        f"border-radius:8px;padding:8px 16px;margin-bottom:12px;"
        f"border-left:3px solid var(--text-muted);'>"
        f"<span style='font-size:13px;color:var(--text-secondary);font-style:italic;line-height:1.5;'>"
        f"\U0001f4a1 \u300c{quote}\u300d</span>"
        f"</div>",
        unsafe_allow_html=True
    )

    date_cols = st.columns([1, 6, 1.5, 1.5])
    with date_cols[0]:
        prev_date = view_date - td(days=1)
        if st.button("\u25c0", key="btn_prev_day", use_container_width=True, help="\u524d\u4e00\u5929"):
            st.session_state.view_date = prev_date
            st.rerun()
    with date_cols[1]:
        date_label = f"\u4eca\u5929" if is_today else view_date.strftime("%m\u6708%d\u65e5")

        def _on_date_change():
            st.session_state.view_date = st.session_state.view_date_picker

        st.date_input(
            date_label,
            value=view_date,
            key="view_date_picker",
            on_change=_on_date_change,
            label_visibility="visible"
        )
    with date_cols[2]:
        next_date = view_date + td(days=1)
        if st.button("\u25b6", key="btn_next_day", use_container_width=True, help="\u540e\u4e00\u5929"):
            st.session_state.view_date = next_date
            st.rerun()
    with date_cols[3]:
        if not is_today:
            if st.button("\U0001f4c5 \u4eca\u5929", key="btn_today_jump", use_container_width=True):
                st.session_state.view_date = today
                st.rerun()

    if not is_today:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM tasks WHERE created_date = ? AND user_id = ? ORDER BY sort_order ASC",
            (view_date_str, get_current_user_id())
        ).fetchall()
        conn.close()
        day_tasks = [dict(r) for r in rows]
    else:
        day_tasks = get_today_tasks()
    calibrated = calibrate_all_tasks_with_info(day_tasks) if day_tasks else []

    status_priority = {"doing": 0, "todo": 1, "done": 2}
    calibrated.sort(key=lambda t: (
        status_priority.get(t.get("status", "todo"), 1),
        t.get("sort_order", 0),
    ))

    avg_ratio = 1.0
    calibrated_count = 0
    if calibrated:
        for t in calibrated:
            if t.get('calibration_sample_count', 0) >= 3:
                avg_ratio += t.get('expansion_ratio', 1.0)
                calibrated_count += 1
        if calibrated_count > 0:
            avg_ratio = avg_ratio / calibrated_count

    if is_future:
        day_label = "明天" if view_date == today + td(days=1) else view_date.strftime("%m月%d日")
        subtitle = f"提前规划 {day_label} 的任务，到当天自动显示。"
    elif is_past:
        day_label = "昨天" if view_date == today - td(days=1) else view_date.strftime("%m月%d日")
        subtitle = f"回顾 {day_label} 的任务记录。"
    elif not day_tasks or calibrated_count == 0:
        subtitle = "我还不了解你，先记几天看看。"
    elif avg_ratio > 1.5:
        subtitle = "你今天是不是又骗自己了？"
    elif avg_ratio > 1.2:
        subtitle = "开始暴露了，你的时间感正在被戳破。"
    elif avg_ratio > 1.0:
        subtitle = "目前还行，但别高兴太早。"
    else:
        subtitle = "面对现实吧，你的时间感没那么准。"

    page_title = "📋 今日计划" if is_today else f"📋 {view_date.strftime('%m月%d日')} 计划"
    st.markdown(
        f"<h2 style='font-weight:300;color:var(--text-strong);margin-bottom:4px;'>"
        f"{page_title}</h2>"
        f"<p style='color:var(--timer-meta);font-size:14px;'>{subtitle}</p>",
        unsafe_allow_html=True
    )

    if is_today:
        status_col, coach_col = st.columns([1, 1], gap="large")
        with status_col:
            render_sidebar_status(day_tasks)
        with coach_col:
            _render_ai_coach(day_tasks, calibrated)

    available_slots = get_work_slots(
        get_setting("work_start_hour", "9:00"),
        get_setting("work_end_hour", "18:00"),
        get_setting("lunch_start_hour", "12:00"),
        get_setting("lunch_end_hour", "13:00"),
    )
    if is_today and available_slots:
        now = datetime.now()
        available_slots = [
            (max(s[0], now), s[1]) for s in available_slots if s[1] > now
        ]
    scheduled, overflow, warnings = reschedule_tasks(calibrated, available_slots,
                                                           rest_minutes=int(get_setting("rest_between_minutes", "0"))) if calibrated else ([], [], [])

    left_col, right_col = st.columns([1, 1], gap="large", border=True)

    with left_col:
        render_task_creation_card(created_date=view_date_str)
        st.markdown(
            "<div style='text-align:center;padding:20px 10px;color:var(--text-muted);font-size:12px;'>"
            "<div style='font-size:24px;margin-bottom:8px;'>💡</div>"
            "先填入任务描述，再选择类别<br>点击「AI 自动排期」让系统帮你预估时间<br>最后点击「添加任务」加入计划"
            "</div>",
            unsafe_allow_html=True
        )

    with right_col:
        if not day_tasks:
            if is_future:
                st.info("还没有为这一天做计划，在左侧添加吧。")
            elif is_past:
                st.info("这一天没有任务记录。")
            else:
                st.info("今天还没有任务，在左侧创建第一个吧。")
        else:
            render_today_timeline(scheduled, calibrated, overflow)
            active_tasks = [t for t in calibrated if t['status'] != 'done']

            TASKS_PER_PAGE = 5
            page_key = f"task_page_{view_date_str}"
            if page_key not in st.session_state:
                st.session_state[page_key] = 1

            total_pages = max(1, (len(active_tasks) + TASKS_PER_PAGE - 1) // TASKS_PER_PAGE)
            current_page = st.session_state[page_key]
            if current_page > total_pages:
                current_page = total_pages
                st.session_state[page_key] = total_pages

            start_idx = (current_page - 1) * TASKS_PER_PAGE
            end_idx = start_idx + TASKS_PER_PAGE
            page_tasks = active_tasks[start_idx:end_idx]

            if total_pages > 1:
                pc1, pc2, pc3, pc4, pc5 = st.columns([1, 1, 2, 1, 1])
                with pc1:
                    if st.button("◀ 上一页", key=f"prev_{view_date_str}", use_container_width=True,
                                 disabled=(current_page <= 1)):
                        st.session_state[page_key] = max(1, current_page - 1)
                        st.rerun()
                with pc3:
                    st.markdown(
                        f"<div style='text-align:center;font-size:13px;color:var(--timer-meta);padding-top:6px;'>"
                        f"第 {current_page} / {total_pages} 页</div>",
                        unsafe_allow_html=True
                    )
                with pc5:
                    if st.button("下一页 ▶", key=f"next_{view_date_str}", use_container_width=True,
                                 disabled=(current_page >= total_pages)):
                        st.session_state[page_key] = min(total_pages, current_page + 1)
                        st.rerun()

            if st.session_state.get("challenge_celebration"):
                celebration_text = st.session_state.pop("challenge_celebration")
                st.markdown(
                    f"<div style='background:linear-gradient(135deg,var(--tag-green-bg) 0%,var(--tag-green-bg) 100%);"
                    f"border:1px solid var(--green);border-radius:10px;padding:10px 16px;"
                    f"margin-bottom:12px;animation:fade-in-up 0.5s ease-out;'>"
                    f"<span style='font-size:18px;margin-right:8px;'>🎉</span>"
                    f"<span style='font-size:14px;font-weight:600;color:var(--tag-green-text);'>挑战完成！</span>"
                    f"<span style='font-size:13px;color:var(--text-secondary);margin-left:8px;'>{celebration_text}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )

            render_task_cards(page_tasks)

            done_tasks = [t for t in calibrated if t['status'] == 'done']
            if done_tasks:
                with st.expander(f"✅ 已完成 ({len(done_tasks)})", expanded=False):
                    render_task_cards(done_tasks, is_collapsed=True)

        done_count = sum(1 for t in calibrated if t['status'] == 'done')
        total_count = len(calibrated)
        if is_today and done_count == total_count and total_count > 0:
            st.success(f"🎉 今日 {total_count} 个任务全部完成！你是最棒的！")
        elif is_future and total_count > 0:
            st.caption(f"📝 {total_count} 个任务已排好，到当天自动出现在今日计划中")

    if st.session_state.edit_task_id:
        render_edit_form(calibrated)
    if st.session_state.show_actual_input:
        render_actual_input()


def _render_ai_coach(today_tasks, calibrated):
    from services.roast_generator import generate_ai_daily_review

    roast = st.session_state.roast_mode
    is_gentle = roast == "温和"
    border_color = "var(--green)" if is_gentle else "var(--orange)"
    bg_tint = "var(--tag-green-bg)" if is_gentle else "var(--tag-orange-bg)"
    title = "🤖 AI 温和教练" if is_gentle else "🤖 AI 毒舌教练"
    subtitle = "给你温暖的鼓励和建设性的建议" if is_gentle else "基于你的任务完成情况，给你一针见血的反馈"

    with st.container(border=True, key="ai_coach"):
        coach_cols = st.columns([2, 1])
        with coach_cols[0]:
            st.markdown(
                f"<div style='font-weight:600;font-size:16px;margin-bottom:4px;'>{title}</div>"
                f"<div style='font-size:13px;color:var(--timer-meta);'>{subtitle}</div>",
                unsafe_allow_html=True
            )
        with coach_cols[1]:
            st.markdown('<span style="font-size:12px;color:var(--timer-meta);">教练语气</span>', unsafe_allow_html=True)
            new_mode = st.radio(
                "教练语气",
                options=["🔥 扎心", "🌸 温和"],
                index=0 if not is_gentle else 1,
                horizontal=True,
                label_visibility="collapsed",
                key="coach_mode_radio"
            )
            mode_value = "扎心" if "扎心" in new_mode else "温和"
            if mode_value != roast:
                st.session_state.roast_mode = mode_value
                st.rerun()
        st.session_state.ai_enabled = True

        st.markdown(
            f"<div style='height:3px;background:linear-gradient(90deg,{border_color},transparent);"
            f"border-radius:2px;margin:4px 0 8px 0;'></div>",
            unsafe_allow_html=True
        )

        btn_col1, btn_col2 = st.columns([1, 2])
        with btn_col1:
            btn_label = "💬 让教练鼓励我" if is_gentle else "💬 让教练骂醒我"
            if st.button(btn_label, use_container_width=True, type="secondary"):
                done = [t for t in today_tasks if t['status'] == 'done']
                if done:
                    with st.spinner("教练正在组织语言..."):
                        review = generate_ai_daily_review(done, roast_mode=st.session_state.roast_mode)
                        st.session_state.roast_popup = review
                else:
                    st.warning("还没完成任务，教练不想理你")

        if st.session_state.get("roast_popup"):
            text = st.session_state.roast_popup
            if isinstance(text, list):
                text = "  ".join(text)
            if text:
                quote_color = "var(--green)" if is_gentle else "var(--red)"
                quote_bg = "var(--tag-green-bg)" if is_gentle else "var(--quote-bg)"
                st.markdown(
                    f"<div class='quote-card' style='border-left-color:{quote_color};background:{quote_bg};'>{text}</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    "<div class='quote-card' style='font-style:normal;color:var(--text-muted);'>"
                    "教练今天词穷了，快去完成任务给他灵感！</div>",
                    unsafe_allow_html=True
                )
            if st.button("知道了", key="dismiss_roast_coach"):
                st.session_state.roast_popup = None
                st.rerun()


def _render_daily_challenge_compact():
    from services.challenge import get_today_challenge, roll_challenge, complete_challenge

    challenge = get_today_challenge()
    placeholder = st.empty()

    if challenge:
        with placeholder.container():
            status_icon = "✅" if challenge["completed"] else "🎯"
            st.markdown(
                f"""
                <div style="
                    background:var(--bg-card);border:1px solid var(--challenge-border);
                    border-radius:8px;padding:8px 12px;
                ">
                    <div style="font-size:11px;color:var(--timer-meta);margin-bottom:2px;">
                        {status_icon} 今日挑战
                    </div>
                    <div style="font-size:13px;color:var(--text-strong);line-height:1.4;font-weight:500;">
                        {challenge['text']}
                    </div>
                    {f"<div style='font-size:11px;color:var(--challenge-done-border);margin-top:4px;'>🎉 已完成</div>" if challenge["completed"] else ""}
                </div>
                """,
                unsafe_allow_html=True
            )
            if not challenge["completed"]:
                if st.button("✅ 完成", key="complete_challenge_compact_btn", use_container_width=False):
                    result = complete_challenge()
                    if result:
                        from services.achievements import award_challenge_badge
                        challenge_badges = award_challenge_badge()
                        st.toast(f"🎉 挑战完成：{result['text'][:20]}...", icon="🏆")
                        for badge in challenge_badges:
                            st.toast(f"🎉 获得成就：{badge['emoji']} {badge['name']}！", icon="🏆")
                        st.session_state.challenge_celebration = result['text']
                        placeholder.empty()
                        with placeholder.container():
                            st.markdown(
                                f"""
                                <div style="
                                    background:var(--bg-card);border:1px solid var(--challenge-done-border);
                                    border-radius:8px;padding:8px 12px;
                                ">
                                    <div style="font-size:11px;color:var(--timer-meta);margin-bottom:2px;">
                                        ✅ 今日挑战
                                    </div>
                                    <div style="font-size:13px;color:var(--text-strong);line-height:1.4;font-weight:500;">
                                        {result['text']}
                                    </div>
                                    <div style="font-size:11px;color:var(--challenge-done-border);margin-top:4px;">🎉 已完成</div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                        st.rerun()
    else:
        with placeholder.container():
            st.markdown(
                """
                <div style="
                    background:var(--bg-card);border:1px solid var(--challenge-border);
                    border-radius:8px;padding:8px 12px;
                ">
                    <div style="font-size:11px;color:var(--timer-meta);margin-bottom:2px;">
                        🎲 每日彩蛋
                    </div>
                    <div style="font-size:12px;color:var(--text-strong);line-height:1.4;">
                        随机挑战，完成得徽章
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            if st.button("🎲 抽取", key="roll_challenge_compact_btn", use_container_width=False):
                result = roll_challenge()
                st.toast(f"🎲 挑战已抽取：{result['text'][:20]}...", icon="🎯")
                placeholder.empty()
                with placeholder.container():
                    st.markdown(
                        f"""
                        <div style="
                            background:var(--bg-card);border:1px solid var(--challenge-border);
                            border-radius:8px;padding:8px 12px;
                        ">
                            <div style="font-size:11px;color:var(--timer-meta);margin-bottom:2px;">
                                🎯 今日挑战
                            </div>
                            <div style="font-size:13px;color:var(--text-strong);line-height:1.4;font-weight:500;">
                                {result['text']}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )


def _render_daily_challenge():
    from services.challenge import get_today_challenge, roll_challenge, complete_challenge

    challenge = get_today_challenge()
    placeholder = st.empty()

    if challenge:
        with placeholder.container():
            status_icon = "✅" if challenge["completed"] else "🎯"
            st.markdown(
                f"""
                <div style="
                    background:var(--bg-card);border:1px solid var(--challenge-border);
                    border-radius:10px;padding:12px 16px;margin-bottom:8px;
                ">
                    <div style="font-size:12px;color:var(--timer-meta);margin-bottom:4px;">
                        {status_icon} 今日挑战
                    </div>
                    <div style="font-size:15px;color:var(--text-strong);line-height:1.6;font-weight:500;">
                        {challenge['text']}
                    </div>
                    {f"<div style='font-size:12px;color:var(--challenge-done-border);margin-top:6px;'>🎉 挑战完成！</div>" if challenge["completed"] else ""}
                </div>
                """,
                unsafe_allow_html=True
            )
            if not challenge["completed"]:
                if st.button("✅ 完成挑战", use_container_width=True, type="primary", key="complete_challenge_btn"):
                    result = complete_challenge()
                    if result:
                        from services.achievements import award_challenge_badge
                        challenge_badges = award_challenge_badge()
                        st.toast(f"🎉 挑战完成：{result['text'][:20]}...", icon="🏆")
                        for badge in challenge_badges:
                            st.toast(f"🎉 获得成就：{badge['emoji']} {badge['name']}！", icon="🏆")
                        placeholder.empty()
                        with placeholder.container():
                            st.markdown(
                                f"""
                                <div style="
                                    background:var(--bg-card);border:1px solid var(--challenge-done-border);
                                    border-radius:10px;padding:12px 16px;margin-bottom:8px;
                                ">
                                    <div style="font-size:12px;color:var(--timer-meta);margin-bottom:4px;">
                                        ✅ 今日挑战
                                    </div>
                                    <div style="font-size:15px;color:var(--text-strong);line-height:1.6;font-weight:500;">
                                        {result['text']}
                                    </div>
                                    <div style="font-size:12px;color:var(--challenge-done-border);margin-top:6px;">🎉 挑战完成！</div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
    else:
        with placeholder.container():
            st.markdown(
                """
                <div style="
                    background:var(--bg-card);border:1px solid var(--challenge-border);
                    border-radius:10px;padding:12px 16px;margin-bottom:8px;
                ">
                    <div style="font-size:12px;color:var(--timer-meta);margin-bottom:4px;">
                        🎲 每日彩蛋挑战
                    </div>
                    <div style="font-size:14px;color:var(--text-strong);line-height:1.6;">
                        每天随机抽取一个挑战，完成可获得特殊徽章！
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            if st.button("🎲 抽取今日挑战", use_container_width=True, type="primary", key="roll_challenge_btn"):
                result = roll_challenge()
                st.toast(f"🎲 挑战已抽取：{result['text'][:20]}...", icon="🎯")
                placeholder.empty()
                with placeholder.container():
                    st.markdown(
                        f"""
                        <div style="
                            background:var(--bg-card);border:1px solid var(--challenge-border);
                            border-radius:10px;padding:12px 16px;margin-bottom:8px;
                        ">
                            <div style="font-size:12px;color:var(--timer-meta);margin-bottom:4px;">
                                🎯 今日挑战
                            </div>
                            <div style="font-size:15px;color:var(--text-strong);line-height:1.6;font-weight:500;">
                                {result['text']}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )


def render_task_cards(calibrated, is_collapsed=False):
    status_icon = {"todo": "⏳", "doing": "🔄", "done": "✅"}

    for task in calibrated:
        icon = status_icon.get(task['status'], "⏳")
        ratio = task.get('expansion_ratio', 1.0)
        tag_class = hallucination_tag_class(ratio)
        is_done = task['status'] == 'done'
        is_doing = task['status'] == 'doing'
        sample_count = task.get('calibration_sample_count', 0)
        has_calibration = sample_count >= 3 and ratio != 1.0

        with st.container(border=True, key=f"task_{task['id']}"):
            is_timer_task = st.session_state.timer_running and st.session_state.timer_task_id == task['id']
            if is_timer_task:
                est = task.get('calibrated_minutes') or task.get('estimated_minutes') or 1
                elapsed = st.session_state.timer_elapsed_seconds
                elapsed_min = elapsed / 60
                pct = min(elapsed_min / est * 100, 100)
                over = elapsed_min > est
                bar_color = "var(--red)" if over else "var(--green)"
                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:8px;'>"
                    f"<span style='display:inline-block;width:8px;height:8px;border-radius:50%;background:{bar_color};"
                    f"animation:pulse-dot 1.2s ease-in-out infinite;'></span>"
                    f"<span style='font-size:12px;font-weight:600;color:{bar_color};'>🔴 正在计时</span>"
                    f"<span style='font-size:12px;color:var(--text-secondary);'>"
                    f"已用 {elapsed_min:.0f}min / 预估 {est}min</span>"
                    f"</div>"
                    f"<div style='height:4px;background:var(--timer-progress-bg);border-radius:2px;margin-bottom:10px;'>"
                    f"<div style='height:4px;width:{pct:.0f}%;background:{bar_color};border-radius:2px;"
                    f"transition:width 0.3s;'></div></div>",
                    unsafe_allow_html=True
                )
            top_cols = st.columns([0.4, 5.6])
            with top_cols[0]:
                st.markdown(f"<div style='font-size:24px;line-height:1.6;'>{icon}</div>", unsafe_allow_html=True)
            with top_cols[1]:
                desc_style = "text-decoration:line-through;color:var(--timer-meta);" if is_done else ""
                cal_html = ""
                if has_calibration:
                    cal_html = (
                        f"<span style='font-size:13px;font-weight:600;color:var(--text-strong);margin-left:8px;'>"
                        f"校准 {task['calibrated_minutes']}min</span>"
                        f"<span class='hallucination-tag {tag_class}' style='font-size:12px;margin-left:6px;'>{ratio:.1f}x</span>"
                    )
                else:
                    cal_html = (
                        f"<span style='font-size:13px;color:var(--text-faint);margin-left:8px;'>校准 ---</span>"
                    )
                st.markdown(
                    f"<div style='font-weight:600;font-size:15px;color:var(--text-strong);{desc_style}'>"
                    f"{task['description']}</div>"
                    f"<div style='margin-top:2px;'>"
                    f"<span style='font-size:13px;color:var(--timer-meta);'>估计 {task['estimated_minutes']}min</span>"
                    f"{cal_html}"
                    f"</div>",
                    unsafe_allow_html=True
                )

            bottom_cols = st.columns([3, 1.2, 1.2, 0.6])
            with bottom_cols[0]:
                st.markdown(
                    f"<span style='display:inline-block;padding:2px 10px;border-radius:20px;"
                    f"font-size:11px;font-weight:500;background:var(--toggle-hover-bg);color:var(--toggle-text);'>"
                    f"⏱ {task['category']}</span>",
                    unsafe_allow_html=True
                )
            with bottom_cols[1]:
                if task['status'] == 'todo' and not is_collapsed:
                    st.markdown("""
                    <style>
                    .small-btn button {
                        font-size: 12px !important;
                        padding: 2px 10px !important;
                        min-height: unset !important;
                        height: auto !important;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    st.markdown('<div class="small-btn">', unsafe_allow_html=True)
                    if st.button("▶ 开始", key=f"start_{task['id']}", type="primary"):
                        update_task_status(task['id'], 'doing', start_time=datetime.now().isoformat())
                        st.session_state.timer_running = True
                        st.session_state.timer_task_id = task['id']
                        st.session_state.timer_start = datetime.now()
                        st.session_state.timer_elapsed_seconds = 0
                        st.session_state.last_tick = datetime.now()
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                elif task['status'] == 'doing' and not is_collapsed:
                    st.markdown("""
                    <style>
                    .small-btn button {
                        font-size: 12px !important;
                        padding: 2px 10px !important;
                        min-height: unset !important;
                        height: auto !important;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    st.markdown('<div class="small-btn">', unsafe_allow_html=True)
                    if st.button("✅ 完成", key=f"done_{task['id']}", type="primary"):
                        finish_task(task)
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
            with bottom_cols[2]:
                if not is_collapsed:
                    st.markdown("""
                    <style>
                    .small-popover button {
                        font-size: 12px !important;
                        padding: 2px 8px !important;
                        min-height: unset !important;
                        height: auto !important;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    st.markdown('<div class="small-popover">', unsafe_allow_html=True)
                    with st.popover("更多"):
                        if task['status'] == 'todo':
                            if st.button("✏️ 编辑", key=f"edit_{task['id']}", use_container_width=True):
                                st.session_state.edit_task_id = task['id']
                                st.rerun()
                            if st.button("⬆️ 上移", key=f"up_{task['id']}", use_container_width=True):
                                move_up(task['id'])
                                st.rerun()
                            if st.button("⬇️ 下移", key=f"down_{task['id']}", use_container_width=True):
                                move_down(task['id'])
                                st.rerun()
                            st.divider()
                        if st.button("🗑️ 删除", key=f"del_{task['id']}", use_container_width=True):
                            st.session_state[f"confirm_del_{task['id']}"] = True
                            st.rerun()
                        if st.session_state.get(f"confirm_del_{task['id']}"):
                            st.error(f"确定删除「{task['description'][:20]}」吗？")
                            col_y, col_n = st.columns(2)
                            with col_y:
                                if st.button("✅ 确认", key=f"confirm_yes_{task['id']}", use_container_width=True):
                                    delete_task(task['id'])
                                    st.session_state[f"confirm_del_{task['id']}"] = False
                                    st.rerun()
                            with col_n:
                                if st.button("❌ 取消", key=f"confirm_no_{task['id']}", use_container_width=True):
                                    st.session_state[f"confirm_del_{task['id']}"] = False
                                    st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

            if is_done and task.get('actual_minutes') and task['actual_minutes'] > 0:
                actual = task['actual_minutes']
                est = task['estimated_minutes']
                if est > 0:
                    dev = int((actual - est) / est * 100)
                    if dev > 0:
                        dev_str = f"实际花了 {actual}min，比估计多了 {dev}%"
                        dev_color = "var(--orange)"
                    elif dev < 0:
                        dev_str = f"实际花了 {actual}min，比估计少了 {abs(dev)}%"
                        dev_color = "var(--green)"
                    else:
                        dev_str = f"实际花了 {actual}min，与估计一致"
                        dev_color = "var(--toggle-text)"
                    st.markdown(
                        f"<div style='font-size:11px;color:{dev_color};margin-top:2px;'>{dev_str}</div>",
                        unsafe_allow_html=True
                    )

            start_time = task.get('start_time')
            end_time = task.get('end_time')
            if start_time or end_time:
                time_parts = []
                if start_time:
                    try:
                        st_dt = datetime.fromisoformat(start_time) if "T" in start_time else datetime.strptime(str(start_time)[:19], "%Y-%m-%d %H:%M:%S")
                        time_parts.append(f"🕐 {st_dt.strftime('%H:%M')}")
                    except Exception:
                        pass
                if end_time:
                    try:
                        et_dt = datetime.fromisoformat(end_time) if "T" in end_time else datetime.strptime(str(end_time)[:19], "%Y-%m-%d %H:%M:%S")
                        time_parts.append(f"🏁 {et_dt.strftime('%H:%M')}")
                    except Exception:
                        pass
                if start_time and end_time:
                    try:
                        st_dt = datetime.fromisoformat(start_time)
                        et_dt = datetime.fromisoformat(end_time)
                        duration = int((et_dt - st_dt).total_seconds() / 60)
                        time_parts.append(f"⏱ 耗时 {duration}min")
                    except Exception:
                        pass
                if time_parts:
                    st.markdown(
                        f"<div style='font-size:11px;color:var(--timer-meta);margin-top:4px;'>{' · '.join(time_parts)}</div>",
                        unsafe_allow_html=True
                    )


def finish_task(task):
    end_time = datetime.now()
    update_task_status(task['id'], 'done', end_time=end_time.isoformat())
    if st.session_state.timer_task_id == task['id']:
        elapsed = (end_time - st.session_state.timer_start).total_seconds() / 60
        set_actual_minutes(task['id'], int(elapsed))
        st.session_state.timer_running = False
        st.session_state.timer_task_id = None
        st.session_state.timer_start = None
        st.session_state.timer_elapsed_seconds = 0
        st.session_state.show_actual_input = True
        st.session_state.actual_task_id = task['id']
        st.session_state.elapsed_minutes = int(elapsed)
    else:
        st.session_state.show_actual_input = True
        st.session_state.actual_task_id = task['id']
        st.session_state.elapsed_minutes = task.get('estimated_minutes', 30)

    record_completion()
    new_badges = check_and_award()
    if new_badges:
        for badge in new_badges:
            st.toast(f"🎉 获得成就：{badge['emoji']} {badge['name']}！", icon="🏆")
    st.toast("✅ 打卡成功！", icon="🔥")
    st.session_state.celebration_trigger = True
    st.rerun()


def render_edit_form(calibrated):
    from services.task_manager import edit_task as svc_edit_task
    task = next((t for t in calibrated if t['id'] == st.session_state.edit_task_id), None)
    if task is None:
        st.session_state.edit_task_id = None
        return

    with st.container(border=True, key="edit_form"):
        st.subheader("✏️ 编辑任务")
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            new_desc = st.text_input("任务描述", value=task['description'], key="edit_desc")
        with col2:
            new_cat = st.selectbox("类别", get_categories(),
                                   index=get_categories().index(task['category']) if task['category'] in get_categories() else 0,
                                   key="edit_cat")
        with col3:
            new_est = st.number_input("估计时间", min_value=1, max_value=1440,
                                      value=task['estimated_minutes'], step=15, key="edit_est")
        col_a, col_b = st.columns([1, 5])
        with col_a:
            if st.button("💾 保存", type="primary", use_container_width=True):
                svc_edit_task(task['id'], category=new_cat, description=new_desc, estimated_minutes=new_est)
                st.session_state.edit_task_id = None
                st.rerun()
        with col_b:
            if st.button("取消", use_container_width=True):
                st.session_state.edit_task_id = None
                st.rerun()


def render_actual_input():
    with st.container(border=True, key="actual_input_card"):
        st.subheader("✏️ 确认实际耗时")
        act = st.number_input(
            "实际耗时（分钟）", min_value=1,
            value=max(1, st.session_state.get('elapsed_minutes', 30)),
            step=5, key="actual_input"
        )
        if st.button("确认", type="primary", key="confirm_actual"):
            set_actual_minutes(st.session_state.actual_task_id, act)
            st.session_state.show_actual_input = False
            st.session_state.actual_task_id = None
            st.rerun()


def inject_dark_mode_css():
    st.markdown("""
    <style>
    .dark-mode {
        --bg: #0F172A;
        --surface: #1E293B;
        --sidebar-bg: #1E293B;
        --text: #E2E8F0;
        --text-strong: #E2E8F0;
        --text-secondary: #94A3B8;
        --text-muted: #64748B;
        --border: #334155;
        --border-light: #1E293B;
        --border-hover: #475569;
        --btn-bg: #1E293B;
        --btn-text: #CBD5E1;
        --btn-hover-bg: #334155;
        --btn-hover-text: #E2E8F0;
        --btn-hover-border: #475569;
        --btn2-bg: #1E1B4B;
        --btn2-text: #A5B4FC;
        --btn2-border: #312E81;
        --btn2-hover-bg: #312E81;
        --btn2-hover-border: #4338CA;
        --btn2-hover-text: #C7D2FE;
        --tag-green-bg: #064E3B;
        --tag-green-text: #6EE7B7;
        --tag-orange-bg: #78350F;
        --tag-orange-text: #FCD34D;
        --tag-red-bg: #7F1D1D;
        --tag-red-text: #FCA5A5;
        --quote-bg: #2D1F1F;
        --cal-bg: #1E293B;
        --cal-text: #94A3B8;
        --cal-reality-bg: #78350F;
        --cal-reality-text: #FCD34D;
        --cal-blown-bg: #7F1D1D;
        --cal-blown-text: #FCA5A5;
        --segmented-bg: #1E293B;
        --segmented-active-bg: #E2E8F0;
        --segmented-active-text: #0F172A;
        --scrollbar-thumb: #475569;
        --scrollbar-thumb-hover: #64748B;
        --toggle-bg: #1E293B;
        --toggle-text: #94A3B8;
        --toggle-hover-bg: #334155;
        --toggle-hover-text: #E2E8F0;
        --timer-bg: #1E293B;
        --timer-text: #E2E8F0;
        --timer-meta: #94A3B8;
        --timer-clock: #52B788;
        --timer-overtime-bg: #1E1E1E;
        --timer-overtime-border: #E63946;
        --timer-overtime-clock: #E63946;
        --timer-progress-bg: #334155;
        --timer-progress-fill: #52B788;
        --timer-progress-label: #94A3B8;
        --text-faint: #64748B;
        --bg-subtle: #1E293B;
        --bg-card: #1E293B;
        --progress-bg: #334155;
        --timeline-bg: #1E293B;
        --timeline-line: #334155;
        --yellow-bg: #78350F;
        --yellow-text: #FCD34D;
        --challenge-border: #334155;
        --challenge-done-border: #10B981;
    }

    /* ============ 暗黑模式全局 ============ */
    .dark-mode body,
    .dark-mode .stApp,
    .dark-mode .main,
    .dark-mode [data-testid="stAppViewContainer"] {
        background-color: var(--bg) !important;
        color: var(--text) !important;
    }

    /* ============ 侧栏 ============ */
    .dark-mode [data-testid="stSidebar"],
    .dark-mode [data-testid="stSidebar"] > div,
    .dark-mode [data-testid="stSidebarContent"],
    .dark-mode [data-testid="stSidebarNav"] {
        background-color: var(--surface) !important;
    }
    .dark-mode [data-testid="stSidebar"] h1,
    .dark-mode [data-testid="stSidebar"] h2,
    .dark-mode [data-testid="stSidebar"] h3,
    .dark-mode [data-testid="stSidebar"] p,
    .dark-mode [data-testid="stSidebar"] label {
        color: var(--text) !important;
    }

    /* ============ 顶部栏 ============ */
    .dark-mode header {
        background-color: var(--surface) !important;
        border-bottom-color: var(--border) !important;
    }

    /* ============ 文字层级 ============ */
    .dark-mode h1, .dark-mode h2, .dark-mode h3, .dark-mode h4, .dark-mode h5, .dark-mode h6 {
        color: #F1F5F9 !important;
    }
    .dark-mode .stMarkdown > p,
    .dark-mode .stMarkdown > span {
        color: var(--text) !important;
    }
    .dark-mode .stCaption {
        color: var(--text-secondary) !important;
    }

    /* ============ 卡片和容器 ============ */
    .dark-mode div[data-testid="stForm"],
    .dark-mode div[data-testid="stExpander"],
    .dark-mode [data-testid="stNotification"] {
        background-color: var(--surface) !important;
        border-color: var(--border) !important;
    }

    /* ============ 按钮 ============ */
    .dark-mode .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--accent), var(--accent-hover)) !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    .dark-mode .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, var(--accent-hover), #D1491E) !important;
    }

    /* ============ 输入框 ============ */
    .dark-mode input, .dark-mode textarea, .dark-mode select,
    .dark-mode [data-baseweb="input"],
    .dark-mode [data-baseweb="textarea"],
    .dark-mode [data-baseweb="select"] {
        background-color: var(--bg) !important;
        color: var(--text) !important;
        border-color: var(--border) !important;
    }
    .dark-mode input::placeholder, .dark-mode textarea::placeholder {
        color: var(--text-muted) !important;
    }

    /* ============ 下拉选择框 ============ */
    .dark-mode [data-baseweb="popover"],
    .dark-mode [data-baseweb="menu"],
    .dark-mode [role="listbox"] {
        background-color: var(--surface) !important;
        color: var(--text) !important;
    }
    .dark-mode [role="option"] {
        color: var(--text) !important;
    }
    .dark-mode [role="option"]:hover {
        background-color: var(--border-hover) !important;
    }

    /* ============ 表格 / 数据框 ============ */
    .dark-mode .stDataFrame,
    .dark-mode .stTable,
    .dark-mode [data-testid="stTable"] {
        background-color: var(--surface) !important;
        color: var(--text) !important;
    }
    .dark-mode .stDataFrame th,
    .dark-mode .stTable th {
        background-color: var(--bg) !important;
        color: var(--text) !important;
    }
    .dark-mode .stDataFrame td,
    .dark-mode .stTable td {
        background-color: var(--surface) !important;
        color: var(--text) !important;
    }

    /* ============ 分割线 ============ */
    .dark-mode hr, .dark-mode [data-testid="stDivider"] {
        border-color: var(--border) !important;
    }

    /* ============ 弹出窗口 / Popover ============ */
    .dark-mode [data-testid="stPopover"],
    .dark-mode [data-baseweb="popover"] {
        background-color: var(--surface) !important;
    }
    .dark-mode [data-testid="stPopover"] *,
    .dark-mode [data-baseweb="popover"] * {
        color: var(--text) !important;
    }

    /* ============ Tab 标签页 ============ */
    .dark-mode .stTabs [data-baseweb="tab"] {
        background-color: transparent !important;
        color: var(--text-secondary) !important;
    }
    .dark-mode .stTabs [aria-selected="true"] {
        color: var(--accent) !important;
    }

    /* ============ 指标 / 进度条 ============ */
    .dark-mode .stMetric label,
    .dark-mode .stMetric [data-testid="stMetricLabel"] {
        color: var(--text-secondary) !important;
    }
    .dark-mode .stMetric [data-testid="stMetricValue"] {
        color: var(--text) !important;
    }

    /* ============ 单选框 / 复选框 ============ */
    .dark-mode .stCheckbox label,
    .dark-mode .stRadio label {
        color: var(--text) !important;
    }
    .dark-mode .stCheckbox label span,
    .dark-mode .stRadio label span {
        color: var(--text) !important;
    }

    /* ============ 日期选择器 ============ */
    .dark-mode [data-testid="stDateInput"] {
        color: var(--text) !important;
    }
    .dark-mode [data-testid="stDateInput"] input {
        background-color: var(--bg) !important;
        color: var(--text) !important;
    }

    /* ============ 数字输入 ============ */
    .dark-mode .stNumberInput input,
    .dark-mode .stNumberInput button {
        background-color: var(--bg) !important;
        color: var(--text) !important;
        border-color: var(--border) !important;
    }

    /* ============ 警告 / 信息框 ============ */
    .dark-mode .stAlert {
        background-color: var(--surface) !important;
        color: var(--text) !important;
        border-color: var(--border) !important;
    }
    .dark-mode .stAlert [data-testid="stNotification"] {
        background-color: var(--surface) !important;
    }

    /* ============ Toast ============ */
    .dark-mode [data-testid="stToast"] {
        background-color: var(--surface) !important;
        color: var(--text) !important;
    }

    /* ============ 代码块 ============ */
    .dark-mode code, .dark-mode pre {
        background-color: var(--bg) !important;
        color: var(--text) !important;
    }

    /* ============ 链接 ============ */
    .dark-mode a {
        color: #60A5FA !important;
    }

    /* ============ 侧栏底部固定用户卡片 ============ */
    .dark-mode section[data-testid="stSidebar"] > div > div[data-testid="stVerticalBlock"] > div:last-child {
        background: var(--surface) !important;
        border-top-color: var(--border) !important;
    }
    .dark-mode .daily-quote-card {
        background: linear-gradient(135deg, var(--surface), #1A2332) !important;
        border-left-color: var(--border-hover) !important;
    }
    .dark-mode .daily-quote-card span {
        color: var(--text-secondary) !important;
    }

    /* ============ 侧边栏日历热力图 ============ */
    .dark-mode .st-key-cal_prev button,
    .dark-mode .st-key-cal_next button,
    .dark-mode .st-key-cal_today button {
        background: var(--btn-bg) !important;
        color: var(--btn-text) !important;
        border-color: var(--border) !important;
    }
    </style>""", unsafe_allow_html=True)


def inject_celebration_css():
    st.markdown("""
    <style>
    @keyframes confetti-fall {
        0% { transform: translateY(-100vh) rotate(0deg); opacity: 1; }
        100% { transform: translateY(100vh) rotate(720deg); opacity: 0; }
    }
    @keyframes confetti-sway {
        0%, 100% { margin-left: 0; }
        25% { margin-left: 15px; }
        75% { margin-left: -15px; }
    }
    @keyframes task-shake {
        0%, 100% { transform: translateX(0); }
        10% { transform: translateX(-4px); }
        20% { transform: translateX(4px); }
        30% { transform: translateX(-4px); }
        40% { transform: translateX(4px); }
        50% { transform: translateX(-2px); }
        60% { transform: translateX(2px); }
        70% { transform: translateX(-1px); }
        80% { transform: translateX(1px); }
        90% { transform: translateX(0); }
    }
    @keyframes task-green-glow {
        0% { box-shadow: 0 0 0 0 rgba(82,183,136,0); }
        50% { box-shadow: 0 0 20px 4px rgba(82,183,136,0.5); }
        100% { box-shadow: 0 0 0 0 rgba(82,183,136,0); }
    }
    .confetti-container {
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        pointer-events: none; z-index: 99999; overflow: hidden;
        display: none;
    }
    .confetti-active .confetti-container {
        display: block;
    }
    .confetti-piece {
        position: absolute; top: -20px; width: 10px; height: 16px;
        border-radius: 2px; animation: confetti-fall 3s linear forwards,
                                      confetti-sway 2s ease-in-out infinite;
    }
    .task-done-shake {
        animation: task-shake 0.5s ease-in-out,
                   task-green-glow 0.8s ease-in-out;
    }
    </style>
    """, unsafe_allow_html=True)


def inject_dark_mode_js():
    is_dark = st.session_state.get("dark_mode", False)
    st.components.v1.html(f"""
    <script>
    (function() {{
        var body = parent.document.body;
        if ({str(is_dark).lower()}) {{
            body.classList.add('dark-mode');
        }} else {{
            body.classList.remove('dark-mode');
        }}
    }})();
    </script>
    """, height=0)


def inject_celebration_trigger():
    trigger = st.session_state.pop("celebration_trigger", None)
    if not trigger:
        return

    colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7",
              "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E9"]

    confetti_html = '<div class="confetti-container">'
    for i in range(40):
        left = (i * 7 + 3) % 100
        color = colors[i % len(colors)]
        delay = (i * 0.07) % 2
        size = 8 + (i % 8)
        rotation = (i * 37) % 360
        confetti_html += (
            f'<div class="confetti-piece" style="'
            f'left:{left}%;background:{color};width:{size}px;height:{size+4}px;'
            f'animation-delay:{delay}s;transform:rotate({rotation}deg);'
            f'"></div>'
        )
    confetti_html += '</div>'

    st.components.v1.html(f"""
    <script>
    (function() {{
        var body = parent.document.body;

        var container = document.createElement('div');
        container.innerHTML = `{confetti_html}`;
        while (container.firstChild) {{
            body.appendChild(container.firstChild);
        }}

        body.classList.add('confetti-active');

        var cards = body.querySelectorAll('[data-testid="stVerticalBlockBorderWrapper"]');
        if (cards.length > 0) {{
            var lastCard = cards[cards.length - 1];
            lastCard.classList.add('task-done-shake');
            setTimeout(function() {{
                lastCard.classList.remove('task-done-shake');
            }}, 800);
        }}

        setTimeout(function() {{
            body.classList.remove('confetti-active');
            var pieces = body.querySelectorAll('.confetti-piece');
            pieces.forEach(function(p) {{ p.remove(); }});
            var containers = body.querySelectorAll('.confetti-container');
            containers.forEach(function(c) {{ c.remove(); }});
        }}, 3500);
    }})();
    </script>
    """, height=0)


def try_auto_login():
    from services.auth import validate_remember_token

    token_data = None

    if "rt" in st.query_params:
        token_data = st.query_params.get("rt")
        if isinstance(token_data, list):
            token_data = token_data[0] if token_data else None

    if not token_data and "rt_token" in st.session_state:
        token_data = st.session_state.rt_token

    if not token_data:
        try:
            cookies = st.context.cookies
            token_data = cookies.get("remember_me", "")
            if isinstance(token_data, list):
                token_data = token_data[0] if token_data else ""
        except Exception:
            token_data = ""

    if not token_data or ":" not in token_data:
        return

    user_id, token = token_data.split(":", 1)
    user = validate_remember_token(user_id, token)
    if user:
        st.session_state.logged_in = True
        st.session_state.current_user = user
        st.query_params["rt"] = f"{user_id}:{token}"
        st.session_state.rt_token = f"{user_id}:{token}"


if __name__ == "__main__":
    main()