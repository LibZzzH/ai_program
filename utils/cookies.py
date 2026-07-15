"""Tiny helpers to set/clear top-level cookies from inside Streamlit v1 html iframes."""
import streamlit as st


def _build_cookie_value(name: str, value: str, days: int | None = None) -> str:
    if days is None:
        # Session cookie: no Expires/Max-Age attribute.
        return f"{name}={value};path=/;SameSite=Lax"
    import datetime
    expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days)
    return f"{name}={value};expires={expires.strftime('%a, %d %b %Y %H:%M:%S GMT')};path=/;SameSite=Lax"


def set_remember_cookie(token_data: str, days: int | None = None):
    """Set the remember_me cookie on the parent page.

    `days=None` creates a session cookie (survives page refresh, gone when the
    browser is closed). `days=3` matches the existing "记住我" behaviour.
    """
    cookie = _build_cookie_value("remember_me", token_data, days=days)
    st.components.v1.html(
        f"""
        <script>
        (function() {{
            try {{
                parent.document.cookie = {cookie!r};
            }} catch (e) {{
                console.error("Failed to set remember_me cookie:", e);
            }}
        }})();
        </script>
        """,
        height=0,
    )


def clear_remember_cookie():
    """Clear the remember_me cookie on the parent page."""
    st.components.v1.html(
        """
        <script>
        (function() {
            try {
                parent.document.cookie = "remember_me=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/;SameSite=Lax";
            } catch (e) {
                console.error("Failed to clear remember_me cookie:", e);
            }
        })();
        </script>
        """,
        height=0,
    )
