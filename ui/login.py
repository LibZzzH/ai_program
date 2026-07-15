import streamlit as st
from services.auth import login_user, register_user, migrate_default_to_user, generate_remember_token
from utils.cookies import set_remember_cookie


LOGIN_CSS = """
<style>
    .stApp { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .stApp > header { background: transparent !important; }
    .stApp > .st-emotion-cache-1cypcdb { background: transparent !important; }

    @keyframes float {
        0%, 100% { transform: translateY(0px) rotate(0deg); }
        25% { transform: translateY(-20px) rotate(5deg); }
        75% { transform: translateY(-10px) rotate(-3deg); }
    }
    @keyframes pulse {
        0%, 100% { opacity: 0.3; }
        50% { opacity: 0.7; }
    }
    @keyframes slideUp {
        from { opacity: 0; transform: translateY(30px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes bgShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    .floating-emoji {
        position: fixed; font-size: 40px; pointer-events: none; z-index: 0;
        animation: float 6s ease-in-out infinite;
    }
    .floating-emoji:nth-child(1) { top: 10%; left: 8%; animation-delay: 0s; }
    .floating-emoji:nth-child(2) { top: 20%; right: 10%; animation-delay: 1.5s; font-size: 50px; }
    .floating-emoji:nth-child(3) { bottom: 25%; left: 12%; animation-delay: 3s; font-size: 35px; }
    .floating-emoji:nth-child(4) { top: 40%; right: 15%; animation-delay: 4.5s; }
    .floating-emoji:nth-child(5) { bottom: 15%; right: 8%; animation-delay: 2s; font-size: 45px; }

    .particle {
        position: fixed; width: 4px; height: 4px; background: rgba(255,255,255,0.5);
        border-radius: 50%; pointer-events: none; z-index: 0;
        animation: pulse 3s ease-in-out infinite;
    }
    .particle:nth-child(6) { top: 15%; left: 20%; animation-delay: 0s; }
    .particle:nth-child(7) { top: 30%; left: 70%; animation-delay: 0.8s; width: 3px; height: 3px; }
    .particle:nth-child(8) { top: 60%; left: 25%; animation-delay: 1.6s; width: 5px; height: 5px; }
    .particle:nth-child(9) { top: 75%; left: 65%; animation-delay: 2.4s; }
    .particle:nth-child(10) { top: 45%; left: 45%; animation-delay: 3.2s; width: 3px; height: 3px; }
    .particle:nth-child(11) { top: 85%; left: 40%; animation-delay: 1.2s; width: 2px; height: 2px; }
    .particle:nth-child(12) { top: 5%; left: 55%; animation-delay: 2.8s; width: 3px; height: 3px; }

    .tagline {
        text-align: center; color: rgba(255,255,255,0.75); font-size: 14px;
        margin-bottom: 20px; font-style: italic; letter-spacing: 0.5px;
    }

    [data-testid="stTabs"] {
        max-width: 420px; margin: 0 auto;
        background: rgba(255,255,255,0.97);
        border-radius: 20px;
        padding: 32px 32px 24px 32px;
        box-shadow: 0 24px 64px rgba(0,0,0,0.12), 0 8px 16px rgba(0,0,0,0.06);
        animation: slideUp 0.6s ease-out;
        backdrop-filter: blur(20px);
    }

    [data-testid="stTabs"] > div:first-child {
        justify-content: center; gap: 0;
    }
    [data-testid="stTabs"] button {
        font-size: 16px; font-weight: 600; padding: 8px 28px;
        border-radius: 10px 10px 0 0; border: none;
        background: transparent; color: #94A3B8;
        transition: color 0.2s ease;
    }
    [data-testid="stTabs"] button[aria-selected="true"] {
        color: #667eea; border-bottom: 3px solid #667eea;
    }

    [data-testid="stTabs"] .stButton > button {
        width: 100%; border-radius: 12px; height: 46px; font-weight: 600;
        font-size: 15px; border: none; transition: all 0.3s ease;
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: #fff;
        background-size: 200% 200%;
        animation: bgShift 4s ease infinite;
        box-shadow: 0 4px 15px rgba(102,126,234,0.3);
    }
    [data-testid="stTabs"] .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102,126,234,0.45);
    }
    [data-testid="stTabs"] .stButton > button:active {
        transform: translateY(0);
    }

    [data-testid="stTabs"] .stTextInput > div > div {
        border-radius: 12px;
        border: 1px solid #E2E8F0;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    [data-testid="stTabs"] .stTextInput > div > div:focus-within {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102,126,234,0.15);
    }

    .card-title {
        font-size: 22px; font-weight: 700; color: #1E293B;
        text-align: center; margin-bottom: 4px;
    }
    .card-subtitle {
        color: #64748B; font-size: 13px; text-align: center;
        margin-bottom: 20px;
    }
    .card-footer {
        text-align: center; color: #94A3B8; font-size: 11px;
        padding-top: 12px; margin-top: 16px;
        border-top: 1px solid #F1F5F9;
    }

    [data-testid="stTabs"] .stCheckbox label {
        color: #64748B !important;
        font-size: 13px !important;
    }

    .stAlert {
        border-radius: 10px !important;
    }
</style>
"""


def render_login_page():
    st.markdown(LOGIN_CSS, unsafe_allow_html=True)

    st.markdown(
        '<div class="floating-emoji">⏰</div>'
        '<div class="floating-emoji">📊</div>'
        '<div class="floating-emoji">🎯</div>'
        '<div class="floating-emoji">💡</div>'
        '<div class="floating-emoji">🚀</div>'
        '<div class="particle"></div><div class="particle"></div><div class="particle"></div>'
        '<div class="particle"></div><div class="particle"></div><div class="particle"></div>'
        '<div class="particle"></div>',
        unsafe_allow_html=True
    )

    st.markdown(
        "<h1 style='text-align:center;color:#fff;font-size:36px;font-weight:300;"
        "margin-top:40px;margin-bottom:0;'>⏰ 时间校准器</h1>"
        "<p class='tagline'>打破时间幻觉，直面真实效率</p>",
        unsafe_allow_html=True
    )

    tab1, tab2 = st.tabs(["🔑 登录", "✨ 注册"])

    with tab1:
        _render_login_content()
    with tab2:
        _render_register_content()


def _render_login_content():
    st.markdown('<div class="card-title">登录</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-subtitle">输入账号密码，继续你的时间管理之旅</div>',
        unsafe_allow_html=True
    )

    username = st.text_input("用户名", placeholder="输入用户名", key="login_username",
                             label_visibility="collapsed")
    password = st.text_input("密码", type="password", placeholder="输入密码", key="login_password",
                             label_visibility="collapsed")

    remember = st.checkbox("💾 记住我（三天内自动登录）", key="remember_me")

    if st.button("🚀 登  录", key="login_btn", use_container_width=True):
        if not username or not password:
            st.error("请填写用户名和密码")
        else:
            success, msg, user = login_user(username, password)
            if success:
                st.session_state.logged_in = True
                st.session_state.current_user = user
                migrate_default_to_user(user["id"])
                token = generate_remember_token(user["id"])
                st.query_params["rt"] = f"{user['id']}:{token}"
                st.session_state.rt_token = f"{user['id']}:{token}"
                # 即使不勾选“记住我”，也写入 session cookie，避免普通刷新就掉登录。
                # 勾选“记住我”则保留 3 天。
                set_remember_cookie(f"{user['id']}:{token}", days=3 if remember else None)
                st.rerun()
            else:
                st.error(msg)

    st.markdown(
        '<div class="card-footer">你的数据，只属于你 🔒</div>',
        unsafe_allow_html=True
    )


def _render_register_content():
    st.markdown('<div class="card-title">创建账号</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-subtitle">开启你的时间管理之旅 🎯</div>',
        unsafe_allow_html=True
    )

    reg_username = st.text_input("用户 ID", placeholder="至少 2 个字符", key="reg_username")
    reg_name = st.text_input("昵称", placeholder="怎么称呼你？", key="reg_name")
    reg_password = st.text_input("密码", type="password", placeholder="至少 4 个字符", key="reg_password")
    reg_password2 = st.text_input("确认密码", type="password", placeholder="再次输入密码", key="reg_password2")

    if st.button("✨ 注  册", key="reg_btn", use_container_width=True):
        if not reg_username or not reg_password:
            st.error("请填写用户 ID 和密码")
        elif reg_password != reg_password2:
            st.error("两次输入的密码不一致")
        else:
            success, msg = register_user(reg_username, reg_password, reg_name)
            if success:
                login_ok, _, user = login_user(reg_username, reg_password)
                if login_ok and user:
                    st.session_state.logged_in = True
                    st.session_state.current_user = user
                    migrate_default_to_user(user["id"])
                    token = generate_remember_token(user["id"])
                    st.query_params["rt"] = f"{user['id']}:{token}"
                    st.session_state.rt_token = f"{user['id']}:{token}"
                    set_remember_cookie(f"{user['id']}:{token}", days=3)
                    st.success(f"注册成功！欢迎 {user['name']} 🎉")
                    st.rerun()
            else:
                st.error(msg)

    st.markdown(
        '<div class="card-footer">你的数据，只属于你 🔒</div>',
        unsafe_allow_html=True
    )