import streamlit as st
import json
import html as _html
import textwrap
from services.achievements import (
    get_achievements_by_category, get_achievements,
    BADGE_CATEGORIES, ACHIEVEMENTS
)
from dao.settings_dao import get_setting

RARITY_MAP = {
    "task_master": "gold",
    "streak": "gold",
    "challenge": "gold",
    "accuracy": "purple",
    "speed": "blue",
    "time_mgmt": "green",
    "category": "blue",
}

RARITY_COLORS = {
    "gold": "#F59E0B",
    "purple": "#8B5CF6",
    "blue": "#3B82F6",
    "green": "#10B981",
}

RARITY_LABELS = {
    "gold": "传奇",
    "purple": "史诗",
    "blue": "稀有",
    "green": "普通",
}

MILESTONE_SERIES = {
    "streak": ["streak_3", "streak_7", "streak_15", "streak_30"],
    "challenge": ["challenge_1", "challenge_3", "challenge_7", "challenge_15", "challenge_30"],
}


def _get_rarity(badge):
    return RARITY_MAP.get(badge.get("category", ""), "green")


def _render_progress_dots(badge, earned_badges):
    category = badge.get("category", "")
    if category not in MILESTONE_SERIES:
        return ""
    series = MILESTONE_SERIES[category]
    badge_id = badge.get("id", "")
    if badge_id not in series:
        return ""
    total = len(series)
    earned_set = {b["id"] for b in earned_badges if b["earned"]}
    earned_count = sum(1 for sid in series[:series.index(badge_id) + 1] if sid in earned_set)
    dots_html = ""
    for k in range(total):
        filled = k < earned_count
        color = "#F59E0B" if filled else "#D1D5DB"
        size = "10px" if filled else "8px"
        dots_html += (
            f"<span style='display:inline-block;width:{size};height:{size};"
            f"border-radius:50%;background:{color};margin:0 2px;"
            f"transition:all 0.3s;'></span>"
        )
    return f"<div style='margin-top:6px;'>{dots_html}</div>"


def render_badge_wall():
    st.markdown(
        '<h2 style="margin-bottom:4px;">🏆 徽章墙</h2>'
        '<p style="color:var(--timer-meta);font-size:14px;margin-bottom:16px;">'
        '完成任务、达成成就来解锁徽章，悬停卡片查看详情</p>',
        unsafe_allow_html=True
    )

    st.markdown(
        """<style>
        .badge-card {
            transition: transform 0.25s ease, box-shadow 0.25s ease;
        }
        .badge-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.12) !important;
        }
        </style>""",
        unsafe_allow_html=True
    )

    achievements_by_cat = get_achievements_by_category()
    all_achievements = get_achievements()
    total_badges = len(ACHIEVEMENTS)
    earned_count = sum(1 for a in all_achievements if a["earned"])
    pct = int(earned_count / total_badges * 100) if total_badges > 0 else 0

    st.markdown(
        f"""
        <div style="
            background:linear-gradient(135deg,#667eea,#764ba2);
            border-radius:14px;padding:20px 24px;margin-bottom:20px;color:#FFFFFF;
        ">
            <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
                <div style="font-size:48px;">🏆</div>
                <div style="flex:1;min-width:200px;">
                    <div style="font-size:14px;opacity:0.85;margin-bottom:4px;">
                        已收集 <b style="font-size:20px;">{earned_count}</b> / {total_badges} 枚徽章
                    </div>
                    <div style="
                        height:10px;background:rgba(255,255,255,0.25);border-radius:5px;
                        overflow:hidden;position:relative;
                    ">
                        <div style="
                            width:{pct}%;height:100%;background:#FFFFFF;border-radius:5px;
                            transition:width 0.6s ease;
                        "></div>
                    </div>
                    <div style="font-size:12px;opacity:0.7;margin-top:4px;text-align:right;">
                        {pct}% 完成
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    rarity_legend = "".join(
        f"<span style='display:inline-flex;align-items:center;gap:4px;margin-right:12px;font-size:12px;'>"
        f"<span style='width:10px;height:10px;border-radius:2px;background:{RARITY_COLORS[rid]};'></span>"
        f"{RARITY_LABELS[rid]}</span>"
        for rid in ["gold", "purple", "blue", "green"]
    )
    st.markdown(
        f"<div style='margin-bottom:12px;color:var(--text-muted);'>{rarity_legend}</div>",
        unsafe_allow_html=True
    )

    challenge_completions_json = get_setting("challenge_completions", "[]")
    completions = json.loads(challenge_completions_json)
    if completions:
        challenge_total = 5
        challenge_earned = sum(1 for a in all_achievements
                               if a["earned"] and a.get("category") == "challenge")
        dots = "".join(
            f"<span style='display:inline-block;width:10px;height:10px;border-radius:50%;"
            f"margin:0 3px;background:{bg};'></span>"
            for k in range(challenge_total)
            for bg in [("#F59E0B" if k < challenge_earned else "#D1D5DB")]
        )
        st.markdown(
            f"""
            <div style="
                background:var(--bg-card);border:1px solid var(--challenge-border);
                border-radius:10px;padding:14px 18px;margin-bottom:16px;
            ">
                <div style="font-size:14px;font-weight:600;color:var(--text-strong);margin-bottom:4px;">
                    🎲 已累计完成 {len(completions)} 次每日挑战
                </div>
                <div style="margin-top:4px;">{dots}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    tabs = st.tabs([cat["name"] for cat in BADGE_CATEGORIES])

    for i, cat in enumerate(BADGE_CATEGORIES):
        with tabs[i]:
            cat_data = achievements_by_cat.get(cat["id"], {})
            badges = cat_data.get("badges", [])
            cat_earned = sum(1 for b in badges if b["earned"])
            cat_total = len(badges)

            if cat_total == 0:
                st.info("暂无此类徽章")
                continue

            rarity = RARITY_MAP.get(cat["id"], "green")
            rarity_color = RARITY_COLORS[rarity]
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">'
                f'<span style="font-size:13px;color:var(--text-secondary);">{cat["desc"]}</span>'
                f'<span style="font-size:12px;font-weight:600;color:{rarity_color};">'
                f'{cat_earned}/{cat_total}</span>'
                f'<span style="font-size:11px;color:var(--text-muted);">已解锁</span>'
                f'</div>',
                unsafe_allow_html=True
            )

            cols = st.columns(4)
            for j, badge in enumerate(badges):
                with cols[j % 4]:
                    _render_badge_card(badge, cat["color"], all_achievements)


def _render_badge_card(badge, accent_color, all_achievements=None):
    earned = badge["earned"]
    earned_at = badge.get("earned_at", "")
    category = badge.get("category", "")
    rarity = _get_rarity(badge)
    rarity_color = RARITY_COLORS[rarity]
    badge_name = _html.escape(badge['name'])
    badge_desc = _html.escape(badge['desc'])
    badge_emoji = badge['emoji']

    if earned:
        bg_color = "var(--surface)"
        border_color = rarity_color
        emoji_filter = "none"
        card_opacity = "1"
        text_color = "var(--text-strong)"
        sub_color = "var(--text-secondary)"
        status_badge = (
            f"<div style='font-size:10px;color:{rarity_color};margin-top:4px;font-weight:600;'>"
            f"✅ {earned_at}</div>"
        )
        tooltip_text = _html.escape(f"{badge['desc']}  |  ✅ 已解锁 · {earned_at}")
    else:
        bg_color = "var(--bg-card)"
        border_color = "var(--border)"
        emoji_filter = "grayscale(1) opacity(0.35)"
        card_opacity = "0.7"
        text_color = "var(--text-muted)"
        sub_color = "var(--text-faint)"
        status_badge = (
            f"<div style='font-size:10px;color:var(--text-muted);margin-top:4px;'>"
            f"🔒 未解锁</div>"
        )
        tooltip_text = _html.escape(f"{badge['desc']}  |  🔒 未解锁")

    progress_dots = ""
    if all_achievements and not earned:
        progress_dots = _render_progress_dots(badge, all_achievements)

    top_bar_opacity = "1" if earned else "0.3"

    st.markdown(
        textwrap.dedent(f"""\
        <div class="badge-card" title="{tooltip_text}"
        style="
            background:{bg_color};
            border:2px solid {border_color};
            border-radius:14px;
            padding:16px 10px 12px 10px;
            margin-bottom:10px;
            text-align:center;
            cursor:default;
            opacity:{card_opacity};
            position:relative;
            overflow:hidden;
        "
        >
            <div style="
                position:absolute;top:0;left:0;right:0;height:3px;
                background:linear-gradient(90deg,{rarity_color},transparent);
                opacity:{top_bar_opacity};
            "></div>
            <div style="font-size:38px;filter:{emoji_filter};margin:4px 0 6px 0;
                transition:transform 0.3s ease;">
                {badge_emoji}
            </div>
            <div style="font-size:13px;font-weight:700;color:{text_color};margin-bottom:2px;">
                {badge_name}
            </div>
            <div style="font-size:10px;color:{sub_color};line-height:1.4;margin-bottom:2px;">
                {badge_desc}
            </div>
            {status_badge + progress_dots}
        </div>"""),
        unsafe_allow_html=True
    )