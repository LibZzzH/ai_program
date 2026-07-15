import streamlit as st
from utils.helpers import avatar_html


def render_topbar():
    user = st.session_state.get("current_user")
    if isinstance(user, dict):
        user_id = user.get("id", "")
        user_name = user.get("name", user_id)
    elif user is not None:
        user_id = getattr(user, "id", "")
        user_name = getattr(user, "name", user_id)
    else:
        user_id = ""
        user_name = ""

    avatar = avatar_html(user_id, user_name, 28) if user_id else ""

    st.markdown("""
    <style>
    .fixed-topbar {
        position: fixed; top: 0; left: 0; right: 0; z-index: 9998;
        background: var(--surface); border-bottom: 1px solid var(--border);
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        height: 48px; display: flex; align-items: center; justify-content: space-between;
        padding: 0 24px; transition: left 0.3s ease;
        backdrop-filter: blur(8px);
    }
    .fixed-topbar-title {
        font-size: 18px; font-weight: 600; color: var(--text-strong);
        letter-spacing: -0.3px;
    }
    .fixed-topbar-user {
        display: flex; align-items: center; gap: 10px;
        font-size: 13px; color: var(--text-strong);
    }
    .fixed-topbar-logout {
        background: none; border: 1px solid var(--border); border-radius: 6px;
        padding: 4px 14px; font-size: 12px; color: var(--text-secondary); cursor: pointer;
        transition: all 0.15s; font-family: inherit;
    }
    .fixed-topbar-logout:hover {
        background: var(--quote-bg); border-color: var(--tag-red-bg); color: var(--tag-red-text);
    }
    .main .block-container {
        padding-top: 60px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    html = (
        '<div class="fixed-topbar" id="topbar">'
        '<div class="fixed-topbar-title">⏰ 时间感知幻觉破除器</div>'
        '<div class="fixed-topbar-user">'
        + avatar +
        '<span>' + user_name + '</span>'
        '<button class="fixed-topbar-logout" onclick="window.location.href=\'?logout=1\'">🚪 退出</button>'
        '</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

    st.components.v1.html("""
    <script>
    (function() {
        function adjustTopbar() {
            var topbar = parent.document.getElementById('topbar');
            if (!topbar) return;
            var sidebar = parent.document.querySelector('[data-testid="stSidebar"]');
            if (!sidebar) return;
            var rect = sidebar.getBoundingClientRect();
            if (rect.width > 0 && rect.right > 0) {
                topbar.style.left = rect.right + 'px';
            } else {
                topbar.style.left = '0px';
            }
        }
        adjustTopbar();
        setTimeout(adjustTopbar, 100);
        setTimeout(adjustTopbar, 500);
        setTimeout(adjustTopbar, 1000);
        var sidebar = parent.document.querySelector('[data-testid="stSidebar"]');
        if (sidebar) {
            var observer = new MutationObserver(adjustTopbar);
            observer.observe(sidebar, { attributes: true, attributeFilter: ['style', 'class', 'aria-expanded'] });
            if (sidebar.parentElement) {
                observer.observe(sidebar.parentElement, { attributes: true, childList: true, subtree: true });
            }
        }
        window.addEventListener('resize', adjustTopbar);
    })();
    </script>
    """, height=0)