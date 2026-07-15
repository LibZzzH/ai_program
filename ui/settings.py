import streamlit as st
import pandas as pd
import json

from services.task_manager import get_all_tasks
from dao.settings_dao import get_setting, set_setting


def render_settings_page():
    st.markdown(
        "<h2 style='font-weight:300;color:var(--text-strong);margin-bottom:4px;'>⚙️ 设置</h2>"
        "<p style='color:var(--text-muted);font-size:14px;'>管理你的工作时间、AI 配置和导出数据</p>",
        unsafe_allow_html=True
    )

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["⏰ 工作时间", "📐 校准策略", "🤖 AI 配置", "📤 导出", "🧪 演示数据"]
    )

    with tab1:
        _render_work_hours()
    with tab2:
        _render_calibration()
    with tab3:
        _render_ai_config()
    with tab4:
        _render_export()
    with tab5:
        _render_demo_data()


def _render_work_hours():
    st.markdown("### 调整每日可用时间范围")

    ws = _parse_stored_time(get_setting("work_start_hour", "9:00"), 9, 0)
    we = _parse_stored_time(get_setting("work_end_hour", "18:00"), 18, 0)
    ls = _parse_stored_time(get_setting("lunch_start_hour", "12:00"), 12, 0)
    le = _parse_stored_time(get_setting("lunch_end_hour", "13:00"), 13, 0)

    st.markdown("**上班 / 下班**")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ws_h = st.number_input("上班·时", 0, 23, ws[0], key="ws_h")
    with c2:
        ws_m = st.number_input("上班·分", 0, 55, (ws[1] // 5) * 5, 5, key="ws_m")
    with c3:
        we_h = st.number_input("下班·时", 0, 23, we[0], key="we_h")
    with c4:
        we_m = st.number_input("下班·分", 0, 55, (we[1] // 5) * 5, 5, key="we_m")
    st.caption(f"⏰ {ws_h:02d}:{ws_m:02d}  —  {we_h:02d}:{we_m:02d}")

    st.markdown("**午休**")
    c5, c6, c7, c8 = st.columns(4)
    with c5:
        ls_h = st.number_input("午始·时", 0, 23, ls[0], key="ls_h")
    with c6:
        ls_m = st.number_input("午始·分", 0, 55, (ls[1] // 5) * 5, 5, key="ls_m")
    with c7:
        le_h = st.number_input("午终·时", 0, 23, le[0], key="le_h")
    with c8:
        le_m = st.number_input("午终·分", 0, 55, (le[1] // 5) * 5, 5, key="le_m")
    st.caption(f"⏰ {ls_h:02d}:{ls_m:02d}  —  {le_h:02d}:{le_m:02d}")
    st.divider()
    st.markdown("**☕ 任务间休息时间**")
    current_rest = int(get_setting("rest_between_minutes", "0"))
    rest_options = [0, 5, 10, 15, 20, 30]
    rest_idx = rest_options.index(current_rest) if current_rest in rest_options else 0
    rest_min = st.selectbox("每个任务之间预留（分钟）", rest_options, 
                            index=rest_idx, key="rest_min", 
                            help="完成一个任务后，自动留出休息时间再开始下一个")
    if st.button("💾 保存", use_container_width=True):
        set_setting("work_start_hour", f"{ws_h}:{ws_m:02d}")
        set_setting("work_end_hour", f"{we_h}:{we_m:02d}")
        set_setting("lunch_start_hour", f"{ls_h}:{ls_m:02d}")
        set_setting("lunch_end_hour", f"{le_h}:{le_m:02d}")
        set_setting("rest_between_minutes", str(rest_min))
        st.success("已保存")
        st.rerun()


def _parse_stored_time(val, default_h, default_m):
    s = str(val)
    if ':' in s:
        parts = s.split(':')
        return (int(parts[0]), int(parts[1]))
    return (default_h if not s else int(s), default_m)


def _render_calibration():
    st.markdown("### 选择时间预估校准算法")
    from services.calibration import get_engine
    from utils.db import get_current_user_id

    engine = get_engine()
    info = engine.get_strategy_info()
    current_strategy = info["current"]

    total_tasks = 0
    from dao.task_dao import get_all_done_history
    done_rows = get_all_done_history()
    if done_rows:
        total_tasks = len(done_rows)

    st.caption(f"👤 当前用户: {get_current_user_id()} | 已完成任务: {total_tasks} 个")

    strategy_labels = [f"{s} — {info['descriptions'][s]}" for s in info["available"]]
    strategy_map = dict(zip(strategy_labels, info["available"]))
    current_label = next((k for k, v in strategy_map.items() if v == current_strategy), strategy_labels[0])
    selected_label = st.selectbox("选择校准算法", strategy_labels,
                                  index=strategy_labels.index(current_label), key="cal_strategy")
    selected_strategy = strategy_map[selected_label]
    if selected_strategy != current_strategy:
        set_setting("calibration_strategy", selected_strategy)
        engine.strategy = selected_strategy
        st.success(f"已切换为：{selected_strategy}")
        st.rerun()


def _render_ai_config():
    import os
    st.markdown("### 管理 AI 模型提供方")

    env = {}
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")

    QWEN_API_KEY = env.get("QWEN_API_KEY", "")
    OPENAI_API_KEY = env.get("OPENAI_API_KEY", "")
    OPENAI_MODEL = env.get("OPENAI_MODEL", "gpt-3.5-turbo")
    QWEN_MODEL = env.get("QWEN_MODEL", "qwen-plus")
    DEEPSEEK_API_KEY = env.get("DEEPSEEK_API_KEY", "")
    DEEPSEEK_MODEL = env.get("DEEPSEEK_MODEL", "deepseek-chat")

    providers = {
        "openai": {
            "name": "OpenAI",
            "api_key": OPENAI_API_KEY,
            "model": OPENAI_MODEL,
        },
        "qwen": {
            "name": "通义千问",
            "api_key": QWEN_API_KEY,
            "model": QWEN_MODEL,
        },
        "deepseek": {
            "name": "DeepSeek",
            "api_key": DEEPSEEK_API_KEY,
            "model": DEEPSEEK_MODEL,
        },
    }

    any_configured = False
    for pid, provider in providers.items():
        has_key = bool(provider["api_key"])
        if has_key:
            any_configured = True

        default_enabled = has_key and st.session_state.ai_enabled_providers.get(pid, True)
        enabled = st.checkbox(
            f"{provider['name']} ({provider['model']})" + (" ✅" if has_key else " ⚠️ 未配置"),
            value=default_enabled,
            key=f"ai_provider_{pid}",
            disabled=not has_key,
        )
        st.session_state.ai_enabled_providers[pid] = enabled

    if not any_configured:
        st.caption("请在 .env 中配置至少一个 API Key")


def _render_export():
    st.markdown("### 导出所有任务数据")
    tasks = get_all_tasks()
    df = pd.DataFrame(tasks)
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "📥 导出 CSV", df.to_csv(index=False).encode('utf-8'),
            "tasks.csv", "text/csv",
            key="dl_csv", use_container_width=True
        )
    with col2:
        st.download_button(
            "📥 导出 JSON", json.dumps(tasks, ensure_ascii=False, indent=2, default=str),
            "tasks.json", "application/json",
            key="dl_json", use_container_width=True
        )


def _render_demo_data():
    st.markdown("### 冷启动体验：注入模拟历史数据，立刻看到校准效果")
    from services.task_manager import generate_demo_data, clear_demo_data
    from dao.task_dao import get_task_count
    from utils.db import get_current_user_id

    uid = get_current_user_id()
    task_count = get_task_count(user_id=uid)
    st.caption(f"👤 当前账号: **{uid}** | 任务数: {task_count}")

    if st.session_state.get("demo_data_loaded"):
        st.info("📊 这是演示数据。开始记录你自己的任务后，点击下方按钮清除。")
        if st.button("🗑️ 清除演示数据", use_container_width=True, key="clear_demo"):
            success, msg = clear_demo_data(user_id=uid)
            st.session_state.demo_data_loaded = False
            st.success(msg)
            st.rerun()
    else:
        if task_count > 0:
            st.warning(f"⚠️ 当前已有 {task_count} 条任务记录。加载演示数据会混在一起，建议先清除旧数据。")
        if st.button("📥 加载演示数据", use_container_width=True, key="load_demo"):
            success, msg = generate_demo_data(user_id=uid)
            if success:
                st.session_state.demo_data_loaded = True
                st.success(msg)
            else:
                st.warning(msg)
            st.rerun()