import hashlib
from html import escape
from utils.config import DEFAULT_CATEGORIES


def get_categories():
    import streamlit as st
    custom = st.session_state.get("custom_categories", [])
    result = list(DEFAULT_CATEGORIES)
    for c in custom:
        if c not in result:
            result.append(c)
    return result


def hallucination_tag_class(ratio):
    if ratio < 1.2:
        return "green"
    elif ratio < 1.8:
        return "orange"
    else:
        return "red"


def avatar_html(user_id: str, name: str, size: int = 32) -> str:
    initial = escape((name or user_id or "?")[0].upper())
    hue = int(hashlib.md5(user_id.encode()).hexdigest(), 16) % 360
    return f"""<div style="width:{size}px;height:{size}px;border-radius:50%;
    background:hsl({hue},55%,55%);display:inline-flex;align-items:center;justify-content:center;
    color:#fff;font-size:{size//2}px;font-weight:700;flex-shrink:0;user-select:none;
    box-shadow:0 2px 12px hsla({hue},55%,55%,0.35);">{initial}</div>"""
