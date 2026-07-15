import streamlit as st
from html import escape

from services.task_manager import create_task
from services.calibration import get_calibration_info
from services.ai_estimator import estimate_time
from utils.helpers import get_categories, hallucination_tag_class
from utils.config import AI_PROVIDERS
from utils.db import get_current_user_id


def render_task_creation_card(created_date=None):
    if st.session_state.get("_clear_task_form", False):
        for key in ["new_desc", "new_est_str", "new_cat_choice", "new_custom_cat", "ai_estimate", "ai_est_value",
                    "pending_desc", "pending_cat"]:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state._clear_task_form = False

    pending_desc = st.session_state.pop("pending_desc", None)
    pending_cat = st.session_state.pop("pending_cat", None)

    with st.container():
        st.markdown(
            "<h3 style='font-weight:400;margin:4px 0 20px 0;'>"
            "✨ 添加新任务</h3>",
            unsafe_allow_html=True
        )

        desc = st.text_input(
            "你要做什么？",
            placeholder="比如，做一个能让老板满意的PPT",
            value=pending_desc or "",
            key="new_desc",
            label_visibility="visible"
        )

        st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)

        categories = get_categories() + ["✏️ 自定义"]
        col_cat, col_time = st.columns([1, 1])
        with col_cat:
            cat_index = categories.index(pending_cat) if pending_cat and pending_cat in categories else 0
            cat_choice = st.selectbox("类别", categories, index=cat_index, key="new_cat_choice")
        with col_time:
            est_str = st.text_input(
                "预计分钟",
                value=st.session_state.get("ai_est_value", "60"),
                key="new_est_str",
                placeholder="60"
            )
            try:
                est_min = int(est_str) if est_str.strip() else 60
            except ValueError:
                est_min = 60

        if st.session_state.get("ai_estimate"):
            info = st.session_state.ai_estimate
            source_tag = "🤖 AI" if info.get("source") == "ai" else "📊 统计"
            with st.expander(f"{source_tag} 预估理由", expanded=True):
                if info.get("ai_errors"):
                    st.caption("AI 估算暂不可用，已使用历史统计兜底。")
                st.markdown(
                    f"""<div style="background:var(--toggle-hover-bg);border-radius:8px;padding:12px;font-size:13px;color:var(--text-strong);">
                    {escape(str(info.get('reasoning', '')))}
                    </div>""",
                    unsafe_allow_html=True,
                )

        cat = cat_choice
        if cat_choice == "✏️ 自定义":
            custom_cat = st.text_input(
                "输入新类别名称",
                placeholder="如：数学、英语、周报...",
                key="new_custom_cat"
            )
            if custom_cat.strip():
                cat = custom_cat.strip()
            else:
                cat = "其他"

        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

        use_custom_time = st.checkbox("🕐 设定开始时间（北京时间）", value=False, key="use_custom_time")
        scheduled_start = None
        if use_custom_time:
            from datetime import datetime
            now = datetime.now()
            col_h, col_m = st.columns(2)
            with col_h:
                start_h = st.number_input("时", 0, 23, now.hour, key="start_h")
            with col_m:
                start_m = st.number_input("分", 0, 55, (now.minute // 5) * 5, 5, key="start_m")
            scheduled_start = f"{start_h:02d}:{start_m:02d}"
            st.caption(f"⏰ 计划 {scheduled_start} 开始")

        st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)

        col_ai, col_add = st.columns([1, 1])
        with col_ai:
            any_ai_configured = any(p.get("api_key") for p in AI_PROVIDERS.values())
            if st.button(
                "🤖 AI 自动排期",
                disabled=not any_ai_configured,
                use_container_width=True,
                key="ai_estimate_btn",
                help="需要配置 AI Key" if not any_ai_configured else "根据历史数据智能预估耗时",
            ):
                if desc.strip():
                    with st.spinner("🔍 正在分析你的历史数据..."):
                        result = estimate_time(desc.strip(), cat_choice, get_current_user_id())
                        st.session_state.ai_estimate = result
                        st.session_state.ai_est_value = str(result["minutes"])
                        if "new_est_str" in st.session_state:
                            del st.session_state["new_est_str"]
                        st.rerun()
                else:
                    st.warning("请先输入任务描述")
            st.caption("根据历史数据自动调整任务顺序和时间")
        with col_add:
            if st.button("➕ 添加任务", type="primary", use_container_width=True, key="add_btn"):
                if desc.strip():
                    if cat_choice == "✏️ 自定义" and cat.strip() and cat not in get_categories():
                        if "custom_categories" not in st.session_state:
                            st.session_state.custom_categories = []
                        if cat not in st.session_state.custom_categories:
                            st.session_state.custom_categories.append(cat)
                    create_task(cat, desc.strip(), est_min, created_date=created_date, scheduled_start=scheduled_start)
                    st.session_state._clear_task_form = True
                    st.rerun()
                else:
                    st.warning("请输入任务描述")

        st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
        _render_recent_templates()
        st.divider()
        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

        _render_calibration_preview(cat, est_min)


def _render_recent_templates():
    from utils.db import get_connection, get_current_user_id

    conn = get_connection()
    user_id = get_current_user_id()
    rows = conn.execute(
        "SELECT description, category FROM tasks WHERE user_id = ? AND description != '' "
        "ORDER BY created_date DESC LIMIT 20",
        (user_id,)
    ).fetchall()
    conn.close()

    if not rows:
        return

    unique = []
    seen = set()
    for r in rows:
        desc = r["description"].strip()
        if desc and desc not in seen:
            seen.add(desc)
            unique.append({"description": desc, "category": r["category"]})
        if len(unique) >= 5:
            break

    if len(unique) < 2:
        return

    st.markdown(
        "<div style='font-size:12px;color:var(--timer-meta);margin-bottom:8px;'>"
        "\U0001f4cc \u6700\u8fd1\u5e38\u7528</div>",
        unsafe_allow_html=True
    )

    confirm = st.session_state.pop("_confirm_template", None)
    if confirm:
        with st.container(border=True):
            st.markdown(
                f'<div style="font-size:13px;color:var(--text-strong);margin-bottom:6px;">'
                f'\u2753 \u786e\u8ba4\u6dfb\u52a0\u8fd9\u4e2a\u4efb\u52a1\u5417\uff1f</div>'
                f'<div style="background:var(--bg-card);border-radius:6px;padding:10px 12px;margin-bottom:10px;">'
                f'<div style="font-size:14px;font-weight:600;color:var(--text-strong);">{escape(confirm["description"])}</div>'
                f'<div style="font-size:12px;color:var(--text-muted);margin-top:4px;">\U0001f4c2 {escape(confirm["category"])}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("\u2705 \u786e\u8ba4\u6dfb\u52a0", key="confirm_tpl_yes", use_container_width=True):
                    st.session_state.pending_desc = confirm["description"]
                    st.session_state.pending_cat = confirm["category"]
                    st.session_state.pop("new_desc", None)
                    st.session_state.pop("new_cat_choice", None)
                    if "new_est_str" not in st.session_state:
                        st.session_state.ai_est_value = "60"
                    st.rerun()
            with cc2:
                if st.button("\u274c \u53d6\u6d88", key="confirm_tpl_no", use_container_width=True):
                    st.rerun()
        return

    cols = st.columns(min(len(unique), 5))
    for i, template in enumerate(unique):
        with cols[i]:
            short_desc = template["description"][:10] + ("..." if len(template["description"]) > 10 else "")
            if st.button(
                f"{short_desc}",
                key=f"recent_{i}_{hash(template['description'])}",
                use_container_width=True,
                help=f"{template['description']} ({template['category']})"
            ):
                st.session_state._confirm_template = template
                st.rerun()


def _render_calibration_preview(cat, est_min):
    st.markdown(
        "<div style='font-size:12px;color:var(--timer-meta);margin-bottom:8px;'>"
        "📐 校准预览</div>",
        unsafe_allow_html=True
    )

    if not cat or not est_min:
        st.markdown(
            "<div style='text-align:center;padding:24px 0;color:var(--text-faint);'>"
            "选择类别并输入时间后<br>这里会显示校准预览</div>",
            unsafe_allow_html=True
        )
        return

    info = get_calibration_info(cat)
    ratio = info["ratio"]
    sample_count = info["sample_count"]
    strategy = info["strategy"]
    has_data = info["has_data"]
    calibrated_min = int(est_min * ratio)

    strategy_labels = {
        "median": "中位数",
        "mean": "均值",
        "weighted_recent": "加权近期",
        "ml_basic": "ML基础",
    }
    strategy_name = strategy_labels.get(strategy, strategy)
    safe_cat = escape(str(cat))
    safe_strategy_name = escape(str(strategy_name))

    if sample_count == 0:
        preview_html = f"""
        <div style="text-align:center;padding:16px;background:var(--yellow-bg);border-radius:10px;
            border:1px solid var(--orange);">
            <div style="font-size:24px;margin-bottom:6px;">🤷</div>
            <div style="font-size:13px;color:var(--yellow-text);line-height:1.6;">
                还没有「{safe_cat}」的历史数据<br>
                <span style="color:var(--text-muted);">完成至少一个任务后，校准数据将在此显示</span>
            </div>
            <div style="margin-top:8px;font-size:11px;color:var(--text-faint);">
                策略：{safe_strategy_name} · 暂用默认系数 1.0×
            </div>
        </div>
        """
        st.markdown(preview_html, unsafe_allow_html=True)
        return

    if sample_count <= 2:
        confidence = "低置信度"
        confidence_color = "var(--orange)"
        calibrated_min = est_min
    else:
        confidence = "高置信度"
        confidence_color = "var(--green)"

    diff = calibrated_min - est_min
    diff_sign = "+" if diff >= 0 else ""
    ratio_color = "var(--red)" if ratio > 1.5 else "var(--orange)" if ratio > 1.2 else "var(--green)"

    preview_html = f"""
    <div style="padding:16px;background:var(--surface);border-radius:10px;
        border:1px solid var(--border);">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
            <span style="font-size:13px;color:var(--text-strong);">
                ⏱ 校准偏差：<b style="color:{ratio_color};">{diff_sign}{diff} 分钟</b>（{ratio:.1f}×）
            </span>
            <span style="font-size:11px;color:var(--text-muted);background:var(--bg-subtle);padding:2px 8px;border-radius:4px;">
                {confidence} · {safe_strategy_name}
            </span>
        </div>
        <div style="display:flex;align-items:baseline;gap:12px;">
            <div style="text-align:center;">
                <div style="font-size:11px;color:var(--text-faint);">你的估计</div>
                <div style="font-size:20px;font-weight:600;color:var(--text-strong);">{est_min}<span style="font-size:13px;color:var(--text-muted);"> 分钟</span></div>
            </div>
            <div style="font-size:20px;color:var(--text-faint);">→</div>
            <div style="text-align:center;">
                <div style="font-size:11px;color:var(--text-faint);">校准后</div>
                <div style="font-size:20px;font-weight:600;color:{ratio_color};">{calibrated_min}<span style="font-size:13px;color:var(--text-muted);"> 分钟</span></div>
            </div>
            <div style="font-size:12px;color:var(--text-secondary);">
                基于 <b>{sample_count}</b> 条历史
            </div>
        </div>
    </div>
    """
    st.markdown(preview_html, unsafe_allow_html=True)