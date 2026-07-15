import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import time as time_module

from services.task_manager import get_all_tasks, edit_task, remove_task, get_category_stats
from dao.task_dao import update_task_status, delete_task, set_actual_minutes
from services.roast_generator import generate_daily_review, generate_ai_daily_review
from dao.settings_dao import get_setting
from utils.helpers import get_categories


def render_history_review():
    st.markdown(
        "<h2 style='font-weight:300;color:var(--text-strong);'>\U0001f4ca \u5386\u53f2\u590d\u76d8</h2>",
        unsafe_allow_html=True
    )

    all_tasks = get_all_tasks()
    if not all_tasks:
        st.info("暂无历史数据")
        return

    done_tasks = [t for t in all_tasks if t['status'] == 'done' and t.get('actual_minutes')]
    if not done_tasks:
        st.info("暂无已完成任务")
        return

    dates = sorted(set(t['created_date'] for t in done_tasks))
    min_date = datetime.strptime(dates[0], "%Y-%m-%d").date() if dates else date.today()
    max_date = datetime.strptime(dates[-1], "%Y-%m-%d").date() if dates else date.today()

    if "review_date_range" not in st.session_state:
        st.session_state.review_date_range = (max(min_date, max_date - timedelta(days=7)), max_date)

    quick_cols = st.columns([1, 1, 1, 2])
    with quick_cols[0]:
        if st.button("📅 近7天", use_container_width=True, key="quick_7d"):
            st.session_state.review_date_range = (max(min_date, max_date - timedelta(days=7)), max_date)
            st.rerun()
    with quick_cols[1]:
        if st.button("📅 近30天", use_container_width=True, key="quick_30d"):
            st.session_state.review_date_range = (max(min_date, max_date - timedelta(days=30)), max_date)
            st.rerun()
    with quick_cols[2]:
        if st.button("📅 全部", use_container_width=True, key="quick_all"):
            st.session_state.review_date_range = (min_date, max_date)
            st.rerun()

    date_range = st.date_input(
        "选择日期范围",
        value=st.session_state.review_date_range,
        min_value=min_date,
        max_value=max_date,
        key="review_date_picker"
    )

    if isinstance(date_range, tuple) and len(date_range) == 2:
        if date_range != st.session_state.review_date_range:
            st.session_state.review_date_range = date_range
        start_date, end_date = date_range
        start_str = start_date.isoformat() if hasattr(start_date, 'isoformat') else start_date
        end_str = end_date.isoformat() if hasattr(end_date, 'isoformat') else end_date
        range_tasks = [t for t in done_tasks if start_str <= t['created_date'] <= end_str]
    else:
        single_date = date_range if hasattr(date_range, 'isoformat') else datetime.strptime(str(date_range), "%Y-%m-%d").date()
        start_str = single_date.isoformat()
        end_str = start_str
        range_tasks = [t for t in done_tasks if t['created_date'] == start_str]

    if range_tasks:
        render_review_table(range_tasks, f"{start_str} ~ {end_str}" if isinstance(date_range, tuple) and len(date_range) == 2 else f"{start_str} 复盘")
    else:
        st.info("所选日期范围内暂无已完成任务")

    if len(dates) > 1:
        from ui.sidebar import render_mini_calendar_heatmap

        st.subheader("📈 数据洞察")
        cal_col, left_col, right_col = st.columns([1.2, 1, 1])

        with cal_col:
            render_mini_calendar_heatmap()

        with left_col:
            daily_ratios = []
            filtered_dates = sorted(set(t['created_date'] for t in range_tasks)) if range_tasks else sorted(dates)
            for d in filtered_dates:
                day_tasks = [t for t in done_tasks if t['created_date'] == d]
                total_est = sum(t['estimated_minutes'] for t in day_tasks)
                total_act = sum(t['actual_minutes'] for t in day_tasks)
                ratio = total_act / total_est if total_est > 0 else 0
                daily_ratios.append({"日期": d, "膨胀系数": ratio})
            if daily_ratios:
                st.markdown(
                    "<div style='font-size:12px;color:var(--timer-meta);margin-bottom:4px;'>📈 膨胀系数趋势</div>",
                    unsafe_allow_html=True
                )
                fig = px.line(pd.DataFrame(daily_ratios), x="日期", y="膨胀系数", markers=True)
                fig.add_hline(y=1.0, line_dash="dash", line_color="#52B788", annotation_text="理想线")
                fig.update_traces(line_color="#FF6B35")
                fig.update_layout(height=280, margin=dict(l=0, r=0, t=10, b=0))
                st.plotly_chart(fig, use_container_width=True)

        with right_col:
            cat_stats = get_category_stats()
            if cat_stats:
                st.markdown(
                    "<div style='font-size:12px;color:var(--timer-meta);margin-bottom:4px;'>🎭 最擅长自我欺骗的任务</div>",
                    unsafe_allow_html=True
                )
                cat_df = pd.DataFrame(cat_stats)
                cat_df = cat_df.sort_values("avg_ratio", ascending=True)
                colors = []
                for r in cat_df["avg_ratio"]:
                    if r < 1.2:
                        colors.append("#52B788")
                    elif r < 1.8:
                        colors.append("#FF6B35")
                    else:
                        colors.append("#E63946")
                fig2 = go.Figure()
                fig2.add_trace(go.Bar(
                    y=cat_df["category"],
                    x=cat_df["avg_ratio"],
                    orientation="h",
                    marker_color=colors,
                    text=[f"{r:.1f}x" for r in cat_df["avg_ratio"]],
                    textposition="outside",
                    textfont=dict(size=11, color="#2D2D2D"),
                    hovertemplate="%{y}: %{x:.2f}x<br>共 %{customdata} 个任务",
                    customdata=cat_df["count"],
                ))
                fig2.add_vline(x=1.0, line_dash="dash", line_color="#52B788", annotation_text="理想")
                fig2.update_layout(
                    height=280,
                    margin=dict(l=0, r=40, t=10, b=0),
                    xaxis_title=None,
                    yaxis_title=None,
                    xaxis=dict(tickformat=".1f"),
                    showlegend=False,
                )
                st.plotly_chart(fig2, use_container_width=True)


def render_review_table(tasks, title):
    def _ratio_color(ratio):
        if ratio < 1.2:
            return "#52B788", "#EEF9F3", "🟢"
        elif ratio < 1.8:
            return "#FF6B35", "#FFF3ED", "🟠"
        else:
            return "#E63946", "#FFF0F0", "🔴"

    def _ratio_bar(ratio):
        max_display = 3.0
        pct = min(ratio / max_display * 100, 100)
        color, _, _ = _ratio_color(ratio)
        return f"""<div style="flex:1;min-width:60px;height:6px;background:var(--border);border-radius:3px;overflow:hidden;">
            <div style="width:{pct}%;height:100%;background:{color};border-radius:3px;transition:width 0.3s;"></div></div>"""

    rows_html = ""
    for t in tasks:
        act = t.get('actual_minutes', 0)
        est = t.get('estimated_minutes', 1)
        ratio = act / est if est > 0 else 0
        color, bg, icon = _ratio_color(ratio)
        diff = act - est
        diff_str = f"+{diff}min" if diff > 0 else (f"{diff}min" if diff < 0 else "±0")
        diff_color = "var(--red)" if diff > 0 else ("var(--green)" if diff < 0 else "var(--timer-meta)")

        rows_html += f"""<div style="display:flex;align-items:center;gap:16px;padding:14px 0;border-bottom:1px solid rgba(0,0,0,0.05);">
            <div style="flex:2;min-width:0;">
                <div style="font-size:14px;font-weight:500;color:var(--text-strong);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
                     title="{t['description']}">{t['description']}</div>
                <div style="font-size:11px;color:var(--timer-meta);margin-top:2px;">{t['created_date']}</div>
            </div>
            <div style="flex:1;text-align:center;">
                <span style="display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:500;
                    background:var(--toggle-hover-bg);color:var(--toggle-text);">{t['category']}</span>
            </div>
            <div style="flex:1;text-align:center;font-size:13px;color:var(--text-strong);font-weight:500;">
                {est}min <span style="color:var(--text-faint);font-size:11px;">→</span> {act}min
            </div>
            <div style="flex:1;text-align:center;font-size:12px;font-weight:600;color:{diff_color};">
                {diff_str}
            </div>
            <div style="flex:1.5;display:flex;align-items:center;gap:8px;min-width:0;">
                <span style="font-size:18px;flex-shrink:0;">{icon}</span>
                <span style="font-size:13px;font-weight:600;color:{color};flex-shrink:0;min-width:36px;text-align:center;">{ratio:.1f}x</span>
                {_ratio_bar(ratio)}
            </div>
        </div>"""

    total_est = sum(t['estimated_minutes'] for t in tasks)
    total_act = sum(t['actual_minutes'] for t in tasks)
    overall = total_act / total_est if total_est > 0 else 0
    o_color, o_bg, o_icon = _ratio_color(overall)

    st.markdown(f"""<div class="card" style="padding:20px 24px 16px;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
            <div style="font-size:14px;font-weight:500;color:var(--text-strong);">📋 {title}</div>
            <div style="font-size:12px;color:var(--timer-meta);">共 {len(tasks)} 条</div>
        </div>
        <div style="display:flex;align-items:center;gap:16px;padding:10px 0 6px;border-bottom:2px solid rgba(0,0,0,0.06);font-size:11px;font-weight:600;color:var(--text-faint);text-transform:uppercase;">
            <div style="flex:2;">任务</div>
            <div style="flex:1;text-align:center;">类别</div>
            <div style="flex:1;text-align:center;">估 → 实</div>
            <div style="flex:1;text-align:center;">偏差</div>
            <div style="flex:1.5;text-align:center;">膨胀</div>
        </div>
        {rows_html}
        <div style="display:flex;align-items:center;justify-content:space-between;margin-top:16px;padding-top:14px;border-top:2px solid rgba(0,0,0,0.06);">
            <div style="display:flex;gap:32px;">
                <div><span style="font-size:11px;color:var(--timer-meta);">总估计</span><br><span style="font-size:18px;font-weight:700;color:var(--text-strong);">{total_est}min</span></div>
                <div><span style="font-size:11px;color:var(--timer-meta);">总实际</span><br><span style="font-size:18px;font-weight:700;color:var(--text-strong);">{total_act}min</span></div>
                <div><span style="font-size:11px;color:var(--timer-meta);">平均膨胀</span><br><span style="font-size:18px;font-weight:700;color:{o_color};">{o_icon} {overall:.1f}x</span></div>
            </div>
            <div style="flex-shrink:0;display:flex;gap:12px;font-size:11px;color:var(--timer-meta);">
                <span>🟢 准确</span><span>🟠 偏高</span><span>🔴 严重</span>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)


@st.dialog("确认删除")
def delete_task_dialog(task_id, task_desc):
    from html import escape
    st.markdown(
        f'<div style="font-size:14px;color:var(--text-strong);margin-bottom:4px;">'
        f'\u786e\u5b9a\u8981\u5220\u9664\u4efb\u52a1</div>'
        f'<div style="background:var(--quote-bg);border:1px solid var(--tag-red-bg);border-radius:8px;padding:12px;margin-bottom:16px;">'
        f'<span style="font-size:15px;font-weight:600;color:var(--tag-red-text);">\u300c{escape(task_desc)}\u300d</span>'
        f'</div>'
        f'<div style="font-size:13px;color:var(--text-secondary);margin-bottom:16px;">\u26a0\ufe0f \u6b64\u64cd\u4f5c\u4e0d\u53ef\u6062\u590d</div>',
        unsafe_allow_html=True
    )
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("\u786e\u8ba4\u5220\u9664", type="primary", use_container_width=True):
            delete_task(task_id)
            st.session_state.all_selected.discard(task_id)
            st.session_state.delete_target_id = None
            st.session_state.delete_target_desc = None
            st.rerun()
    with col2:
        if st.button("\u53d6\u6d88", use_container_width=True):
            st.session_state.delete_target_id = None
            st.session_state.delete_target_desc = None
            st.rerun()


def render_all_tasks_page():
    st.markdown(
        "<h2 style='font-weight:300;color:var(--text-strong);'>📝 全部任务</h2>",
        unsafe_allow_html=True
    )

    delete_target = st.session_state.get("delete_target_id")
    if delete_target:
        delete_task_dialog(delete_target, st.session_state.get("delete_target_desc", ""))

    all_tasks = get_all_tasks()
    if not all_tasks:
        st.info("暂无任务记录")
        return

    # ==================== 汇总统计栏 ====================
    total = len(all_tasks)
    todo_count = sum(1 for t in all_tasks if t['status'] == 'todo')
    doing_count = sum(1 for t in all_tasks if t['status'] == 'doing')
    done_count = sum(1 for t in all_tasks if t['status'] == 'done')

    stat_cols = st.columns(4, gap="small")
    stat_cols[0].metric("📋 总数", total)
    stat_cols[1].metric("⏳ 待办", todo_count)
    stat_cols[2].metric("🔄 进行中", doing_count)
    stat_cols[3].metric("✅ 已完成", done_count)
    st.markdown("<hr style='margin:8px 0;'>", unsafe_allow_html=True)

    # ==================== 筛选栏 ====================
    filter_col1, filter_col2, filter_col3, filter_col4, filter_col5 = st.columns([1.5, 1.5, 1.5, 1.2, 1.5])
    with filter_col1:
        search = st.text_input("🔍 搜索", placeholder="关键词...", key="all_search", label_visibility="collapsed")
    with filter_col2:
        date_range = st.date_input(
            "日期范围",
            value=(),
            key="all_date_range",
            label_visibility="collapsed"
        )
    with filter_col3:
        if st.session_state.get("selected_category"):
            cat_filter = []
            st.info(f"🔍 {st.session_state.selected_category}")
        else:
            cat_filter = st.multiselect(
                "类别", get_categories(),
                default=[],
                key="all_cat_filter",
                label_visibility="collapsed",
                placeholder="类别筛选..."
            )
    with filter_col4:
        sort_options = ["日期 ↓", "日期 ↑", "状态", "类别", "耗时 ↓"]
        sort_by = st.selectbox("排序", sort_options, key="all_sort", label_visibility="collapsed")
    with filter_col5:
        status_filter = st.multiselect(
            "状态",
            ["todo", "doing", "done"],
            default=[],
            format_func=lambda x: {"todo": "⏳ 待办", "doing": "🔄 进行中", "done": "✅ 完成"}[x],
            key="all_status_filter",
            label_visibility="collapsed",
            placeholder="状态筛选..."
        )

    if st.session_state.get("selected_category"):
        if st.button("✕ 清除类别筛选", key="clear_cat"):
            st.session_state.selected_category = None
            st.rerun()

    # ==================== 过滤逻辑 ====================
    filtered = all_tasks
    if search:
        filtered = [t for t in filtered if search.lower() in t['description'].lower()]
    if cat_filter:
        filtered = [t for t in filtered if t['category'] in cat_filter]
    if st.session_state.get("selected_category"):
        filtered = [t for t in filtered if t['category'] == st.session_state.selected_category]
    if len(date_range) == 2:
        d1, d2 = date_range[0], date_range[1]
        filtered = [t for t in filtered if d1 <= date.fromisoformat(t['created_date']) <= d2]
    if status_filter:
        filtered = [t for t in filtered if t['status'] in status_filter]

    # ==================== 排序逻辑 ====================
    if sort_by == "日期 ↓":
        filtered.sort(key=lambda t: t['created_date'], reverse=True)
    elif sort_by == "日期 ↑":
        filtered.sort(key=lambda t: t['created_date'])
    elif sort_by == "状态":
        status_order = {"doing": 0, "todo": 1, "done": 2}
        filtered.sort(key=lambda t: status_order.get(t['status'], 9))
    elif sort_by == "类别":
        filtered.sort(key=lambda t: t.get('category', ''))
    elif sort_by == "耗时 ↓":
        filtered.sort(key=lambda t: t.get('calibrated_minutes', t.get('estimated_minutes', 0)), reverse=True)

    # ==================== 分页计算 ====================
    PAGE_SIZE = 20
    total_pages = max(1, (len(filtered) + PAGE_SIZE - 1) // PAGE_SIZE)
    if "all_page" not in st.session_state:
        st.session_state.all_page = 1
    page = st.session_state.all_page
    if page > total_pages:
        page = total_pages
        st.session_state.all_page = page

    start_idx = (page - 1) * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, len(filtered))
    paged = filtered[start_idx:end_idx]

    # ==================== 批量操作 ====================
    if "all_selected" not in st.session_state:
        st.session_state.all_selected = set()
    if "batch_confirm_delete" not in st.session_state:
        st.session_state.batch_confirm_delete = False

    batch_col1, batch_col2, batch_col3, batch_col4 = st.columns([1, 1, 1, 5])
    with batch_col1:
        if st.button("☑ 全选", key="select_all", use_container_width=True, disabled=len(paged) == 0):
            st.session_state.all_selected = {t['id'] for t in paged}
            st.rerun()
    with batch_col2:
        if st.button("☐ 取消", key="deselect_all", use_container_width=True, disabled=len(st.session_state.all_selected) == 0):
            st.session_state.all_selected.clear()
            st.rerun()
    with batch_col3:
        if st.session_state.all_selected:
            if st.button("✅ 完成", key="batch_done", use_container_width=True):
                for tid in list(st.session_state.all_selected):
                    update_task_status(tid, 'done', end_time=datetime.now().isoformat())
                st.session_state.all_selected.clear()
                st.rerun()
    with batch_col4:
        if st.session_state.all_selected:
            if st.button("🗑 批量删除", key="batch_delete", use_container_width=True, type="secondary"):
                st.session_state.batch_confirm_delete = True
                st.rerun()

    if st.session_state.batch_confirm_delete and st.session_state.all_selected:
        st.warning(f"⚠️ 确定要删除选中的 {len(st.session_state.all_selected)} 个任务吗？此操作不可撤销。")
        cf_col1, cf_col2, cf_col3 = st.columns([1, 1, 6])
        with cf_col1:
            if st.button("✅ 确认删除", key="batch_confirm_yes", use_container_width=True, type="primary"):
                for tid in list(st.session_state.all_selected):
                    delete_task(tid)
                st.session_state.all_selected.clear()
                st.session_state.batch_confirm_delete = False
                st.rerun()
        with cf_col2:
            if st.button("❌ 取消", key="batch_confirm_no", use_container_width=True):
                st.session_state.batch_confirm_delete = False
                st.rerun()

    st.markdown("<hr style='margin:4px 0;'>", unsafe_allow_html=True)

    # ==================== 任务列表 ====================
    if not paged:
        st.info("没有匹配的任务")
        return

    status_icon_map = {"todo": "⏳", "doing": "🔄", "done": "✅"}
    status_label_map = {"todo": "待办", "doing": "进行中", "done": "已完成"}
    status_color_map = {"todo": "var(--toggle-text)", "doing": "var(--orange)", "done": "var(--green)"}

    st.markdown("""
    <style>
    .status-badge { display:inline-block; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:500; }
    .cat-badge { display:inline-block; padding:2px 8px; border-radius:12px; font-size:11px; background:var(--toggle-hover-bg); color:var(--toggle-text); }
    .note-hint { font-size:11px; color:var(--text-faint); font-style:italic; }
    .note-text { font-size:11px; color:var(--timer-meta); }
    .task-row { border-bottom:1px solid var(--border); padding:8px 0; }
    .task-row:last-child { border-bottom:none; }
    </style>
    """, unsafe_allow_html=True)

    header_cols = st.columns([0.3, 2.5, 0.7, 0.8, 0.6, 0.6, 0.6, 0.8, 1.2, 1.2])
    headers = ["", "任务描述", "状态", "类别", "预估", "校准", "实际", "日期", "备注", "操作"]
    for i, h in enumerate(headers):
        with header_cols[i]:
            st.markdown(
                f"<div style='font-size:11px;color:var(--toggle-text);font-weight:600;'>{h}</div>",
                unsafe_allow_html=True
            )
    st.markdown("<hr style='margin:4px 0 8px 0;border-color:var(--challenge-border);'>", unsafe_allow_html=True)

    for t in paged:
        tid = t['id']
        is_checked = tid in st.session_state.all_selected
        status_icon = status_icon_map.get(t['status'], "⏳")
        status_label = status_label_map.get(t['status'], t['status'])
        status_color = status_color_map.get(t['status'], "var(--toggle-text)")
        note = t.get('notes', '') or ''
        note_display = note[:30] + ('...' if len(note) > 30 else '') if note else ''
        desc = t['description'] or ''
        desc_short = desc[:28] + ('...' if len(desc) > 28 else '')
        cal = t.get('calibrated_minutes')
        act = t.get('actual_minutes')

        row_cols = st.columns([0.3, 2.5, 0.7, 0.8, 0.6, 0.6, 0.6, 0.8, 1.2, 1.2])

        with row_cols[0]:
            checked = st.checkbox("", value=is_checked, key=f"sel_{tid}", label_visibility="collapsed")
            if checked and tid not in st.session_state.all_selected:
                st.session_state.all_selected.add(tid)
            elif not checked and tid in st.session_state.all_selected:
                st.session_state.all_selected.discard(tid)

        with row_cols[1]:
            st.markdown(
                f"<span style='font-size:13px;' title='{desc}'>{status_icon} {desc_short}</span>",
                unsafe_allow_html=True
            )

        with row_cols[2]:
            st.markdown(
                f"<span class='status-badge' style='background:color-mix(in srgb,{status_color} 15%,transparent);color:{status_color};'>"
                f"{status_label}</span>",
                unsafe_allow_html=True
            )

        with row_cols[3]:
            st.markdown(
                f"<span class='cat-badge'>{t.get('category', '-')}</span>",
                unsafe_allow_html=True
            )

        with row_cols[4]:
            st.markdown(f"<span style='font-size:12px;color:var(--text-strong);'>{t['estimated_minutes']}min</span>", unsafe_allow_html=True)

        with row_cols[5]:
            st.markdown(f"<span style='font-size:12px;color:var(--text-strong);'>{f'{cal}min' if cal else '-'}</span>", unsafe_allow_html=True)

        with row_cols[6]:
            st.markdown(f"<span style='font-size:12px;color:var(--text-strong);'>{f'{act}min' if act else '-'}</span>", unsafe_allow_html=True)

        with row_cols[7]:
            st.markdown(f"<span style='font-size:11px;color:var(--timer-meta);'>{t['created_date']}</span>", unsafe_allow_html=True)

        with row_cols[8]:
            if note_display:
                st.markdown(f"<span class='note-text' title='{note}'>{note_display}</span>", unsafe_allow_html=True)
            else:
                st.markdown("<span class='note-hint'>-</span>", unsafe_allow_html=True)

        with row_cols[9]:
            action_cols = st.columns([1, 1, 1])
            with action_cols[0]:
                with st.popover("📋", key=f"detail_pop_{tid}", use_container_width=True):
                    _render_task_detail(t)
            with action_cols[1]:
                with st.popover("✏️", key=f"edit_pop_{tid}", use_container_width=True):
                    _render_inline_edit(t)
            with action_cols[2]:
                if st.button("🗑", key=f"del_{tid}", help="删除此任务", use_container_width=True):
                    st.session_state.delete_target_id = tid
                    st.session_state.delete_target_desc = t['description']
                    st.rerun()

        st.markdown("<div style='height:1px;background:var(--border);margin:2px 0;'></div>", unsafe_allow_html=True)

    # ==================== 分页控件（底部） ====================
    st.markdown("<hr style='margin:4px 0;'>", unsafe_allow_html=True)
    page_col1, page_col2, page_col3 = st.columns([1, 2, 1])
    with page_col1:
        st.caption(f"共 {len(filtered)} 条，第 {page}/{total_pages} 页")
    with page_col2:
        if total_pages > 1:
            btn_cols = st.columns(7)
            if btn_cols[0].button("◀◀", key="first_page", disabled=page <= 1, use_container_width=True):
                st.session_state.all_page = 1
                st.rerun()
            if btn_cols[1].button("◀", key="prev_page", disabled=page <= 1, use_container_width=True):
                st.session_state.all_page = max(1, page - 1)
                st.rerun()
            btn_cols[2].markdown(
                f"<div style='text-align:center;line-height:38px;font-weight:600;'>{page}</div>",
                unsafe_allow_html=True
            )
            if btn_cols[3].button("▶", key="next_page", disabled=page >= total_pages, use_container_width=True):
                st.session_state.all_page = min(total_pages, page + 1)
                st.rerun()
            if btn_cols[4].button("▶▶", key="last_page", disabled=page >= total_pages, use_container_width=True):
                st.session_state.all_page = total_pages
                st.rerun()
    with page_col3:
        go_page = st.number_input("跳转", min_value=1, max_value=total_pages, value=page, key="go_page", label_visibility="collapsed")
        if go_page != page:
            st.session_state.all_page = go_page
            st.rerun()


def _render_task_detail(t):
    status_labels = {"todo": "⏳ 待办", "doing": "🔄 进行中", "done": "✅ 完成"}
    st.markdown(f"### {t['description']}")
    st.markdown(f"**状态**: {status_labels.get(t['status'], t['status'])}")
    st.markdown(f"**类别**: {t.get('category', '-')}")
    st.markdown(f"**创建日期**: {t['created_date']}")
    st.markdown(f"**预估耗时**: {t['estimated_minutes']} min")
    if t.get('actual_minutes'):
        st.markdown(f"**实际耗时**: {t['actual_minutes']} min")
    if t.get('calibrated_minutes'):
        st.markdown(f"**校准耗时**: {t['calibrated_minutes']} min")
    if t.get('start_time'):
        st.markdown(f"**开始时间**: {t['start_time']}")
    if t.get('end_time'):
        st.markdown(f"**结束时间**: {t['end_time']}")
    if t.get('calibration_sample_count'):
        st.markdown(f"**校准样本数**: {t['calibration_sample_count']}")
    st.divider()
    st.markdown("**📝 备注**")
    note = t.get('notes', '') or ''
    if note:
        st.markdown(f"*{note}*")
    else:
        st.caption("暂无备注")


def _render_inline_edit(t):
    tid = t['id']
    new_cat = st.selectbox(
        "类别", get_categories(),
        index=get_categories().index(t['category']) if t['category'] in get_categories() else 0,
        key=f"edit_cat_{tid}"
    )
    new_desc = st.text_input("描述", value=t['description'], key=f"edit_desc_{tid}")
    new_est = st.number_input("预估分钟", value=t['estimated_minutes'], min_value=1, max_value=480, key=f"edit_est_{tid}")
    new_status = st.selectbox(
        "状态", ["todo", "doing", "done"],
        index=["todo", "doing", "done"].index(t['status']),
        format_func=lambda x: {"todo": "⏳ 待办", "doing": "🔄 进行中", "done": "✅ 完成"}[x],
        key=f"edit_status_{tid}"
    )
    new_actual = st.number_input(
        "实际耗时 (分钟)", value=t.get('actual_minutes') or 0,
        min_value=0, max_value=1440, key=f"edit_actual_{tid}"
    )
    new_notes = st.text_area("备注", value=t.get('notes', '') or '', key=f"edit_notes_{tid}",
                             placeholder="可选：记录具体做了什么...", height=68)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 保存", key=f"save_{tid}", use_container_width=True, type="primary"):
            edit_task(tid, category=new_cat, description=new_desc.strip(), estimated_minutes=new_est, notes=new_notes)
            update_task_status(tid, new_status)
            if new_actual > 0:
                set_actual_minutes(tid, new_actual)
            st.success("保存成功")
            time_module.sleep(0.5)
            st.rerun()
    with col2:
        if st.button("❌ 取消", key=f"cancel_edit_{tid}", use_container_width=True):
            st.rerun()


def render_quick_timer():
    from services.task_manager import create_task, get_today_tasks
    from dao.task_dao import update_task_status, set_actual_minutes

    running = st.session_state.quick_timer_running
    paused = st.session_state.quick_timer_paused
    stopped = st.session_state.quick_timer_stopped

    # --- Title ---
    st.markdown(
        '<h2 style="font-weight:300;color:var(--text-strong);margin-bottom:4px;">⏱ 快速计时</h2>'
        '<p style="color:var(--timer-meta);font-size:14px;margin-bottom:20px;">不想建任务？先计时，后补录</p>',
        unsafe_allow_html=True
    )

    # --- Calculate elapsed time ---
    if running and not paused:
        elapsed = int((datetime.now() - st.session_state.quick_timer_start).total_seconds()) + st.session_state.quick_timer_elapsed
    elif running and paused:
        elapsed = st.session_state.quick_timer_elapsed
    elif stopped:
        elapsed = st.session_state.quick_timer_final_elapsed
    else:
        elapsed = 0

    h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
    timer_color = "var(--text-muted)" if (paused and running) else "var(--text-strong)"

    # ========================
    # Card 1: Timer Core
    # ========================
    with st.container(border=True):
        st.markdown(
            f'<div style="text-align:center;font-size:56px;font-family:monospace;font-weight:700;'
            f'color:{timer_color};padding:20px 0;letter-spacing:4px;">{h:02d}:{m:02d}:{s:02d}</div>',
            unsafe_allow_html=True
        )

        if not running and not stopped:
            categories = get_categories()
            st.session_state.quick_timer_category = st.selectbox(
                "选择类别", categories,
                index=categories.index(st.session_state.quick_timer_category)
                if st.session_state.quick_timer_category in categories else 0
            )
            if st.button("▶ 开始", type="primary", use_container_width=True):
                st.session_state.quick_timer_running = True
                st.session_state.quick_timer_paused = False
                st.session_state.quick_timer_stopped = False
                st.session_state.quick_timer_start = datetime.now()
                st.session_state.quick_timer_elapsed = 0
                st.rerun()

        elif stopped:
            st.caption(f"计时已结束 · 类别: {st.session_state.quick_timer_category}")

        else:
            st.caption(f"类别: {st.session_state.quick_timer_category}")
            c1, c2, c3 = st.columns(3)
            with c1:
                btn_label = "▶ 继续" if paused else "⏸ 暂停"
                btn_type = "primary" if paused else "secondary"
                if st.button(btn_label, type=btn_type, use_container_width=True):
                    if paused:
                        st.session_state.quick_timer_paused = False
                        st.session_state.quick_timer_start = datetime.now()
                    else:
                        st.session_state.quick_timer_paused = True
                        st.session_state.quick_timer_elapsed = elapsed
                    st.rerun()
            with c2:
                if st.button("⏹ 停止", type="secondary", use_container_width=True):
                    st.session_state.quick_timer_running = False
                    st.session_state.quick_timer_paused = False
                    st.session_state.quick_timer_stopped = True
                    st.session_state.quick_timer_final_elapsed = elapsed
                    st.session_state.quick_timer_start = None
                    st.rerun()

    # ========================
    # Card 2: Post-timer Recording
    # ========================
    if stopped:
        with st.container(border=True):
            st.markdown(
                '<p style="font-weight:600;font-size:14px;color:var(--text-strong);margin-bottom:10px;">📝 事后补录</p>',
                unsafe_allow_html=True
            )
            desc = st.text_input("任务描述", placeholder="你刚才做了什么？", key="quick_timer_desc")
            categories = get_categories()
            cat = st.radio(
                "类别", categories, horizontal=True,
                key="quick_timer_rec_cat",
                index=categories.index(st.session_state.quick_timer_category)
                if st.session_state.quick_timer_category in categories else 0
            )
            if st.button("💾 保存并计入今日任务", type="primary", use_container_width=True):
                actual_min = max(1, st.session_state.quick_timer_final_elapsed // 60)
                task_desc = desc.strip() or f"快速计时 · {st.session_state.quick_timer_category}"
                create_task(cat, task_desc, actual_min)
                tasks = get_today_tasks()
                if tasks:
                    new_task = tasks[-1]
                    update_task_status(new_task['id'], 'done', end_time=datetime.now().isoformat())
                    set_actual_minutes(new_task['id'], actual_min)
                st.session_state.quick_timer_stopped = False
                st.session_state.quick_timer_final_elapsed = 0
                st.success(f"已保存！实际耗时 {actual_min} 分钟")
                time_module.sleep(1.5)
                st.rerun()

    # ========================
    # Card 3: Today's Quick Timer Records
    # ========================
    with st.container(border=True):
        st.markdown(
            '<p style="font-weight:600;font-size:14px;color:var(--text-strong);margin-bottom:10px;">📋 今日快速计时记录</p>',
            unsafe_allow_html=True
        )
        today_tasks = get_today_tasks()
        done_tasks = [t for t in today_tasks if t.get('status') == 'done']
        if not done_tasks:
            st.markdown(
                '<p style="color:var(--text-muted);font-size:13px;text-align:center;padding:20px;">今天还没有快速计时记录</p>',
                unsafe_allow_html=True
            )
        else:
            for t in reversed(done_tasks):
                actual = t.get('actual_minutes', 0) or 0
                desc = t.get('description', '')
                cat_name = t.get('category', '')
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:8px;padding:6px 0;'
                    f'border-bottom:1px solid var(--border);font-size:13px;">'
                    f'<span style="color:var(--text-muted);min-width:40px;">⏱</span>'
                    f'<span style="flex:1;color:var(--text-strong);">{desc}</span>'
                    f'<span style="color:var(--timer-meta);background:var(--bg-card);padding:2px 8px;'
                    f'border-radius:10px;font-size:11px;">{cat_name}</span>'
                    f'<span style="color:var(--timer-meta);min-width:45px;text-align:right;">{actual}min</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )

    # --- Auto-refresh when timer is running ---
    if running and not paused:
        time_module.sleep(1)
        st.rerun()