import streamlit as st
from services.auth import (
    get_user, update_profile, change_password, get_user_stats
)
from utils.helpers import avatar_html


def render_profile_page():
    user = st.session_state.get("current_user")
    if not user:
        st.warning("请先登录")
        return

    if isinstance(user, dict):
        user_id = user["id"]
        user_name = user.get("name", "")
        user_email = user.get("email", "")
        user_created = user.get("created_at", "")
    else:
        user_id = user.id
        user_name = user.name or ""
        user_email = user.email or ""
        user_created = user.created_at or ""

    st.markdown(
        "<h2 style='font-weight:300;color:var(--text-strong);'>👤 个人中心</h2>",
        unsafe_allow_html=True
    )

    with st.container(border=True):
        col_avatar, col_info = st.columns([1, 3])
        with col_avatar:
            st.markdown(
                f"<div style='display:flex;justify-content:center;padding:8px;'>"
                f"{avatar_html(user_id, user_name, 100)}"
                f"</div>",
                unsafe_allow_html=True
            )

        with col_info:
            stats = get_user_stats(user_id)
            st.markdown(f"### {user_name or user_id}")
            st.caption(f"@{user_id}")
            if user_email:
                st.caption(f"📧 {user_email}")
            st.caption(f"🕐 注册于 {user_created[:10]}")

            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                st.metric("总任务", stats["task_count"])
            with col_s2:
                st.metric("已完成", stats["done_count"])
            with col_s3:
                st.metric("平均膨胀", f"{stats['avg_ratio']:.1f}x")

    st.divider()

    tab1, tab2 = st.tabs(["✏️ 编辑资料", "🔒 修改密码"])

    with tab1:
        with st.container(border=True):
            st.subheader("编辑个人资料")

            new_name = st.text_input("昵称", value=user_name, key="profile_name",
                                     placeholder="你的昵称")
            new_email = st.text_input("邮箱", value=user_email, key="profile_email",
                                      placeholder="your@email.com")

            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("💾 保存", type="primary", use_container_width=True, key="save_profile"):
                    update_profile(user_id, name=new_name.strip(), email=new_email.strip())
                    st.session_state.current_user = get_user(user_id)
                    st.success("资料已更新")
                    st.rerun()

    with tab2:
        with st.container(border=True):
            st.subheader("修改密码")

            old_pwd = st.text_input("原密码", type="password", key="old_pwd",
                                    placeholder="输入当前密码")
            col_a, col_b = st.columns(2)
            with col_a:
                new_pwd = st.text_input("新密码", type="password", key="new_pwd",
                                        placeholder="至少6个字符",
                                        help="至少6个字符，最多64个字符")
            with col_b:
                confirm_pwd = st.text_input("确认新密码", type="password", key="confirm_pwd",
                                            placeholder="再次输入新密码")

            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("🔒 修改密码", type="primary", use_container_width=True, key="change_pwd"):
                    if not old_pwd:
                        st.error("请输入原密码")
                    elif not new_pwd:
                        st.error("请输入新密码")
                    elif new_pwd != confirm_pwd:
                        st.error("两次输入的新密码不一致")
                    else:
                        success, msg = change_password(user_id, old_pwd, new_pwd)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

    st.divider()
    if st.button("🚪 退出登录", type="secondary", use_container_width=True, key="btn_logout_profile"):
        from services.calibration import clear_engine_cache
        from services.auth import clear_remember_token
        from utils.cookies import clear_remember_cookie
        uid = user_id
        if uid:
            clear_remember_token(uid)
        clear_engine_cache()
        st.session_state.logged_in = False
        st.session_state.current_user = None
        st.session_state.page = "today"
        clear_remember_cookie()
        st.query_params.clear()
        st.session_state.rt_token = ""
        st.rerun()