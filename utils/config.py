CATEGORIES = ["PPT", "写作", "会议", "编程", "设计", "邮件", "学习", "阅读", "其他"]

DEFAULT_CATEGORIES = list(CATEGORIES)


import os

_ENV_LOADED = False
try:
    from dotenv import load_dotenv
    _ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    load_dotenv(_ENV_FILE, override=True)
    _ENV_LOADED = True
except ImportError:
    _ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(_ENV_FILE):
        with open(_ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key, val = key.strip(), val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
        _ENV_LOADED = True

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-plus")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

DEFAULT_AI_PROVIDER = os.getenv("AI_PROVIDER", "deepseek").lower()


def get_ai_provider():
    provider_id = DEFAULT_AI_PROVIDER
    if provider_id in AI_PROVIDERS:
        return provider_id, AI_PROVIDERS[provider_id]
    return None, None


AI_PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "api_key": OPENAI_API_KEY,
        "base_url": OPENAI_BASE_URL,
        "model": OPENAI_MODEL,
    },
    "qwen": {
        "name": "通义千问",
        "api_key": QWEN_API_KEY,
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": QWEN_MODEL,
    },
    "deepseek": {
        "name": "DeepSeek",
        "api_key": DEEPSEEK_API_KEY,
        "base_url": "https://api.deepseek.com",
        "model": DEEPSEEK_MODEL,
    },
}


def get_categories():
    """返回包含自定义类别的完整列表"""
    import streamlit as st
    custom = st.session_state.get("custom_categories", [])
    result = list(DEFAULT_CATEGORIES)
    for c in custom:
        if c not in result:
            result.append(c)
    return result

ROAST_QUOTES = [
    "你上次也是这么说的，结果呢？",
    "你的时间感，被狗吃了吗？",
    "30分钟写周报？你光发呆就要40分钟。",
    "别骗自己了，数据不会说谎。",
    "你的'很快'和实际的'很快'差了3倍。",
    "又双叒叕低估了？意料之中。",
    "计划谬误晚期患者，建议直接住院。",
]

GLOBAL_CSS = """
<style>
    :root {
        --bg: #F5F7FA;
        --surface: #FFFFFF;
        --sidebar-bg: #FAFBFC;
        --text: #1E293B;
        --text-strong: #2D2D2D;
        --text-secondary: #64748B;
        --text-muted: #94A3B8;
        --border: #E2E8F0;
        --border-light: #F1F5F9;
        --border-hover: #CBD5E1;
        --accent: #FF6B35;
        --accent-hover: #E55A2B;
        --green: #10B981;
        --red: #EF4444;
        --orange: #F59E0B;
        --shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
        --shadow-md: 0 2px 8px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
        --shadow-lg: 0 4px 16px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04);
        --radius-sm: 8px;
        --radius: 12px;
        --radius-lg: 16px;
        --btn-bg: #FFFFFF;
        --btn-text: #475569;
        --btn-hover-bg: #F1F5F9;
        --btn-hover-text: #1E293B;
        --btn-hover-border: #CBD5E1;
        --btn2-bg: #EEF2FF;
        --btn2-text: #4F46E5;
        --btn2-border: #C7D2FE;
        --btn2-hover-bg: #E0E7FF;
        --btn2-hover-border: #A5B4FC;
        --btn2-hover-text: #4338CA;
        --tag-green-bg: #D1FAE5;
        --tag-green-text: #059669;
        --tag-orange-bg: #FEF3C7;
        --tag-orange-text: #D97706;
        --tag-red-bg: #FEE2E2;
        --tag-red-text: #DC2626;
        --quote-bg: #FEF2F2;
        --cal-bg: #F1F5F9;
        --cal-text: #64748B;
        --cal-reality-bg: #FEF3C7;
        --cal-reality-text: #D97706;
        --cal-blown-bg: #FEE2E2;
        --cal-blown-text: #DC2626;
        --segmented-bg: #FAFAFA;
        --segmented-active-bg: #1E293B;
        --segmented-active-text: #FFFFFF;
        --scrollbar-thumb: #CBD5E1;
        --scrollbar-thumb-hover: #94A3B8;
        --toggle-bg: #FFFFFF;
        --toggle-text: #6B6B6B;
        --toggle-hover-bg: #F2F0EB;
        --toggle-hover-text: #2D2D2D;
        --timer-bg: #FFFFFF;
        --timer-text: #2D2D2D;
        --timer-meta: #8E8E8E;
        --timer-clock: #52B788;
        --timer-overtime-bg: #FFF5F5;
        --timer-overtime-border: #E63946;
        --timer-overtime-clock: #E63946;
        --timer-progress-bg: #E2E8F0;
        --timer-progress-fill: #52B788;
        --timer-progress-label: #8E8E8E;
        --text-faint: #BDBDBD;
        --bg-subtle: #F5F5F5;
        --bg-card: #F8F9FA;
        --progress-bg: #E8ECF1;
        --timeline-bg: #F8F8F8;
        --timeline-line: #E0E0E0;
        --yellow-bg: #FFF8E1;
        --yellow-text: #795548;
        --challenge-border: #E8E8E8;
        --challenge-done-border: #52B788;
    }
    .stApp {
        background: var(--bg);
    }
    header[data-testid="stHeader"] {
        display: none;
    }
    #MainMenu {
        display: none;
    }
    footer {
        display: none;
    }
    .main .block-container {
        padding-top: 0.5rem;
        max-width: 56rem;
    }
    * {
        font-family: 'Inter', 'Noto Sans SC', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .card {
        background: var(--surface);
        border-radius: var(--radius-lg);
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: var(--shadow-md);
        border: 1px solid var(--border);
        transition: box-shadow 0.2s ease;
    }
    .card:hover {
        box-shadow: var(--shadow-lg);
    }
    .card-sm {
        background: var(--surface);
        border-radius: var(--radius);
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: var(--shadow-sm);
        border: 1px solid var(--border);
    }
    section[data-testid="stSidebar"] > div {
        background: var(--sidebar-bg);
        border-right: 1px solid var(--border);
    }
    section[data-testid="stSidebar"] > div > div[data-testid="stVerticalBlock"] {
        display: flex !important;
        flex-direction: column !important;
        min-height: 100vh !important;
    }
    section[data-testid="stSidebar"] > div > div[data-testid="stVerticalBlock"] > div:last-child {
        margin-top: auto !important;
        position: sticky !important;
        bottom: 0 !important;
        background: var(--sidebar-bg) !important;
        z-index: 10 !important;
        padding-top: 8px !important;
        border-top: 1px solid var(--border) !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        border: none !important;
        background: var(--surface) !important;
        border-radius: var(--radius) !important;
        box-shadow: var(--shadow-md) !important;
        padding: 20px 24px !important;
        margin-bottom: 16px !important;
        transition: box-shadow 0.2s ease !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        box-shadow: var(--shadow-lg) !important;
    }
    .st-key-left_card, .st-key-right_card, .st-key-edit_form, .st-key-actual_input_card {
        border: none !important;
        background: var(--surface) !important;
        border-radius: var(--radius) !important;
        box-shadow: var(--shadow-md) !important;
        padding: 20px 24px !important;
        margin-bottom: 16px !important;
    }
    [class*="st-key-task_"] {
        border: none !important;
        background: var(--surface) !important;
        border-radius: var(--radius) !important;
        box-shadow: var(--shadow-md) !important;
        padding: 20px 24px !important;
        margin-bottom: 16px !important;
        transition: box-shadow 0.2s ease, transform 0.15s ease !important;
    }
    [class*="st-key-task_"]:hover {
        box-shadow: var(--shadow-lg) !important;
        transform: translateY(-1px) !important;
    }
    .sidebar-toggle-btn {
        position: fixed;
        left: 0;
        top: 50%;
        transform: translateY(-50%);
        z-index: 9998;
        width: 26px;
        height: 56px;
        background: var(--toggle-bg);
        border: 1px solid rgba(0,0,0,0.08);
        border-left: none;
        border-radius: 0 8px 8px 0;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 13px;
        color: var(--toggle-text);
        box-shadow: var(--shadow-md);
        transition: all 0.2s;
        user-select: none;
    }
    .sidebar-toggle-btn:hover {
        background: var(--toggle-hover-bg);
        color: var(--toggle-hover-text);
        width: 30px;
    }
    div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"] button {
        text-align: left !important;
        padding: 12px 16px !important;
        border-radius: 10px !important;
        font-size: 15px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
        border: 1px solid transparent !important;
        margin-bottom: 3px !important;
    }
    div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"] button[kind="secondary"] {
        background: transparent !important;
        color: var(--text-secondary) !important;
    }
    div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"] button[kind="secondary"]:hover {
        background: var(--border-light) !important;
        color: var(--text) !important;
    }
    div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"] button[kind="primary"] {
        background: var(--border-light) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        border-left: 3px solid var(--accent) !important;
        box-shadow: var(--shadow-sm) !important;
        font-weight: 600 !important;
    }
    div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"] button[kind="primary"]:hover {
        background: var(--border) !important;
        border-color: var(--border-hover) !important;
        border-left-color: var(--accent-hover) !important;
    }
    .stProgress > div > div {
        background: linear-gradient(90deg, var(--green), var(--orange), var(--red));
    }
    .stProgress > div {
        border-radius: var(--radius-sm) !important;
        background: var(--border) !important;
    }
    .stProgress > div > div {
        border-radius: var(--radius-sm) !important;
    }
    .mono-timer {
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        font-size: 72px;
        font-weight: 700;
        text-align: center;
        color: var(--text);
        letter-spacing: 4px;
    }
    .mono-timer.warning {
        color: var(--red);
    }
    .hallucination-tag {
        display: inline-block;
        padding: 3px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.3px;
    }
    .hallucination-tag.green  { background: var(--tag-green-bg); color: var(--tag-green-text); }
    .hallucination-tag.orange { background: var(--tag-orange-bg); color: var(--tag-orange-text); }
    .hallucination-tag.red    { background: var(--tag-red-bg); color: var(--tag-red-text); }
    .quote-card {
        border-left: 4px solid var(--red);
        padding: 14px 18px;
        margin: 12px 0 16px 0;
        background: var(--quote-bg);
        border-radius: 0 var(--radius) var(--radius) 0;
        font-style: italic;
        color: var(--text-secondary);
        font-size: 14px;
        line-height: 1.7;
        white-space: pre-wrap;
        word-wrap: break-word;
        overflow-wrap: break-word;
        max-height: none;
        overflow: visible;
    }
    .calibration-preview {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 16px 0;
    }
    .cal-box {
        text-align: center;
        padding: 12px 16px;
        border-radius: var(--radius);
        min-width: 80px;
    }
    .cal-box.estimate {
        background: var(--cal-bg);
        color: var(--cal-text);
    }
    .cal-box.reality {
        background: var(--cal-reality-bg);
        color: var(--cal-reality-text);
        font-weight: 700;
    }
    .cal-box.reality.blown {
        background: var(--cal-blown-bg);
        color: var(--cal-blown-text);
    }
    .cal-arrow {
        font-size: 24px;
        color: var(--red);
    }
    .cal-ratio {
        font-size: 14px;
        font-weight: 700;
        color: var(--cal-blown-text);
        background: var(--cal-blown-bg);
        padding: 2px 8px;
        border-radius: var(--radius-sm);
    }
    .timeline-bar {
        height: 28px;
        border-radius: 6px;
        margin: 4px 0;
        position: relative;
    }
    .timeline-bar.original {
        background: rgba(0,0,0,0.06);
        border: 1px dashed rgba(0,0,0,0.12);
    }
    .timeline-bar.calibrated {
        background: linear-gradient(90deg, var(--orange), var(--red));
        box-shadow: 0 1px 4px rgba(239,68,68,0.2);
    }
    .timeline-cut {
        height: 28px;
        border-radius: 0 6px 6px 0;
        background: repeating-linear-gradient(
            -45deg, transparent, transparent 4px,
            var(--cal-blown-bg) 4px, var(--cal-blown-bg) 8px
        );
        border: 1px dashed var(--red);
    }
    .segmented-btn {
        border-radius: var(--radius-sm);
        border: 1px solid var(--border);
        background: var(--segmented-bg);
        padding: 4px 0;
        transition: all 0.15s ease;
    }
    .segmented-btn:hover {
        background: var(--border-light);
    }
    .segmented-btn.active {
        background: var(--segmented-active-bg);
        color: var(--segmented-active-text);
        border-color: var(--segmented-active-bg);
    }
    .quick-time-btn button {
        font-size: 12px !important;
        padding: 2px 0 !important;
        border-radius: 6px !important;
        background: var(--border-light) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-secondary) !important;
        transition: all 0.15s ease !important;
    }
    .quick-time-btn button:hover {
        background: var(--border) !important;
        color: var(--text) !important;
        border-color: var(--border-hover) !important;
    }

    .stButton > button {
        border-radius: 10px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
        border: 1px solid var(--border) !important;
        background: var(--btn-bg) !important;
        color: var(--btn-text) !important;
    }
    .stButton > button:hover {
        background: var(--btn-hover-bg) !important;
        border-color: var(--btn-hover-border) !important;
        color: var(--btn-hover-text) !important;
    }
    .stButton > button:active {
        transform: scale(0.98) !important;
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--accent), var(--accent-hover)) !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 8px rgba(255,107,53,0.25) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, var(--accent-hover), #D1491E) !important;
        box-shadow: 0 4px 14px rgba(255,107,53,0.35) !important;
        transform: translateY(-1px) !important;
    }

    .stButton > button[kind="secondary"] {
        background: var(--btn2-bg) !important;
        color: var(--btn2-text) !important;
        border: 1px solid var(--btn2-border) !important;
        font-weight: 500 !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background: var(--btn2-hover-bg) !important;
        border-color: var(--btn2-hover-border) !important;
        color: var(--btn2-hover-text) !important;
    }

    input[type="text"], input[type="number"], input[type="password"],
    input[type="email"], textarea, .stTextInput input, .stTextArea textarea {
        border-radius: 10px !important;
        border: 1px solid var(--border) !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    }
    input[type="text"]:focus, input[type="number"]:focus, input[type="password"]:focus,
    input[type="email"]:focus, textarea:focus, .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px rgba(255,107,53,0.12) !important;
        outline: none !important;
    }

    .stSelectbox [data-baseweb="select"] {
        border-radius: 10px !important;
    }

    .stDateInput input {
        border-radius: 10px !important;
    }

    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: transparent;
    }
    ::-webkit-scrollbar-thumb {
        background: var(--scrollbar-thumb);
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: var(--scrollbar-thumb-hover);
    }

    .stTabs [data-baseweb="tab"] {
        font-weight: 500 !important;
        color: var(--text-secondary) !important;
    }
    .stTabs [aria-selected="true"] {
        color: var(--accent) !important;
    }

    .st-emotion-cache-1qg05tj {
        font-size: 14px !important;
    }
    @keyframes pulse-dot {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.4; transform: scale(1.6); }
    }
    @keyframes fade-in-up {
        0% { opacity: 0; transform: translateY(12px); }
        100% { opacity: 1; transform: translateY(0); }
    }
    @keyframes fade-out-up {
        0% { opacity: 1; transform: translateY(0); }
        100% { opacity: 0; transform: translateY(-12px); }
    }
</style>
"""


def _parse_time_str(val):
    if isinstance(val, int):
        return (val, 0)
    val = str(val)
    if ':' in val:
        parts = val.split(':')
        return (int(parts[0]), int(parts[1]))
    return (int(val), 0)


def get_work_slots(work_start="9:00", work_end="18:00", lunch_start="12:00", lunch_end="13:00"):
    from datetime import datetime
    ws_h, ws_m = _parse_time_str(work_start)
    we_h, we_m = _parse_time_str(work_end)
    ls_h, ls_m = _parse_time_str(lunch_start)
    le_h, le_m = _parse_time_str(lunch_end)
    now = datetime.now()
    return [
        (now.replace(hour=ws_h, minute=ws_m, second=0, microsecond=0),
         now.replace(hour=ls_h, minute=ls_m, second=0, microsecond=0)),
        (now.replace(hour=le_h, minute=le_m, second=0, microsecond=0),
         now.replace(hour=we_h, minute=we_m, second=0, microsecond=0)),
    ]


def get_available_minutes(work_start="9:00", work_end="18:00", lunch_start="12:00", lunch_end="13:00"):
    slots = get_work_slots(work_start, work_end, lunch_start, lunch_end)
    return sum(int((e - s).total_seconds() / 60) for s, e in slots)


def hallucination_tag_class(ratio):
    if ratio < 1.2:
        return "green"
    elif ratio < 1.8:
        return "orange"
    else:
        return "red"