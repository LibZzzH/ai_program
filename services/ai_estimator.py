import json
import logging
import os
import re
from utils.config import AI_PROVIDERS
from utils.db import get_current_user_id

logger = logging.getLogger(__name__)
AI_TIMEOUT_SECONDS = float(os.getenv("AI_TIMEOUT_SECONDS", "20"))


def _call_ai(prompt, provider):
    if not provider.get("api_key"):
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None
    client_params = {"api_key": provider["api_key"]}
    if provider.get("base_url"):
        client_params["base_url"] = provider["base_url"]
    client = OpenAI(**client_params, timeout=AI_TIMEOUT_SECONDS)
    response = client.chat.completions.create(
        model=provider["model"],
        messages=[
            {
                "role": "system",
                "content": "你是一个时间管理专家，擅长根据历史数据为用户的任务预估合理耗时。回复简洁专业，只返回要求的 JSON 格式。",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=300,
    )
    return response.choices[0].message.content


def gather_context(category, description, user_id=None):
    uid = user_id if user_id is not None else get_current_user_id()
    from dao.task_dao import get_category_history, get_all_done_history, get_category_tasks_full
    from services.calibration import get_category_expansion_ratio

    cat_rows = get_category_history(category, uid)
    cat_ratio = get_category_expansion_ratio(category, uid)
    cat_sample_count = len(cat_rows)
    cat_typical_actual = (
        round(sum(r["actual_minutes"] for r in cat_rows) / len(cat_rows))
        if cat_rows
        else None
    )

    all_rows = get_all_done_history(uid)
    global_ratio = 1.0
    if all_rows:
        valid = [
            r["actual_minutes"] / r["estimated_minutes"]
            for r in all_rows
            if r.get("estimated_minutes", 0) > 0
        ]
        if valid:
            global_ratio = round(sum(valid) / len(valid), 2)
    global_sample_count = len(all_rows)

    similar = []
    try:
        full_tasks = get_category_tasks_full(category, uid, limit=10)
    except Exception:
        full_tasks = []
    desc_chars = set(description.lower())
    for r in full_tasks:
        task_chars = set(r["description"].lower())
        overlap = len(desc_chars & task_chars)
        if overlap >= 1:
            similar.append(
                {
                    "description": r["description"],
                    "estimated_minutes": r["estimated_minutes"],
                    "actual_minutes": r["actual_minutes"],
                    "ratio": (
                        round(r["actual_minutes"] / r["estimated_minutes"], 1)
                        if r["estimated_minutes"] > 0
                        else 0
                    ),
                }
            )

    return {
        "category": category,
        "description": description,
        "cat_ratio": cat_ratio,
        "cat_sample_count": cat_sample_count,
        "cat_typical_actual": cat_typical_actual,
        "global_ratio": global_ratio,
        "global_sample_count": global_sample_count,
        "similar_tasks": similar[:5],
    }


def build_estimation_prompt(ctx):
    similar_text = ""
    if ctx["similar_tasks"]:
        similar_lines = []
        for t in ctx["similar_tasks"]:
            similar_lines.append(
                f"  - 「{t['description']}」估 {t['estimated_minutes']}min → 实际 {t['actual_minutes']}min（{t['ratio']}x）"
            )
        similar_text = "\n".join(similar_lines)

    return f"""你是一个时间预估专家。根据用户的历史数据，为以下任务给出合理的预估时间。

【任务描述】{ctx['description']}
【类别】{ctx['category']}

【该类别历史数据】
- 历史样本数：{ctx['cat_sample_count']} 条
- 平均膨胀系数：{ctx['cat_ratio']}x
- 典型实际耗时：{ctx['cat_typical_actual'] or '暂无'} 分钟

【用户全局数据】
- 总样本数：{ctx['global_sample_count']} 条
- 全局膨胀系数：{ctx['global_ratio']}x

【相似历史任务】
{similar_text if similar_text else '暂无相似任务'}

请严格按以下 JSON 格式返回（只返回 JSON，不要其他文字）：
{{"minutes": 45, "reasoning": "一句话解释你的预估依据，不超过50字"}}"""


def _parse_response(text):
    if not text:
        return None
    match = re.search(r'\{[^{}]*"minutes"\s*:\s*\d+[^{}]*\}', text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            return {
                "minutes": int(data["minutes"]),
                "reasoning": data.get("reasoning", ""),
            }
        except (json.JSONDecodeError, KeyError, ValueError):
            pass
    nums = re.findall(r"\b(\d{1,3})\b", text)
    if nums:
        return {"minutes": int(nums[0]), "reasoning": text[:100]}
    return None


def _statistics_fallback(ctx, ai_errors=None):
    if ctx["cat_typical_actual"]:
        minutes = round(ctx["cat_typical_actual"] / max(ctx["cat_ratio"], 0.5))
    elif ctx["cat_sample_count"] >= 3:
        minutes = round(30 / max(ctx["cat_ratio"], 0.5))
    else:
        minutes = 30
    minutes = max(minutes, 5)
    return {
        "minutes": minutes,
        "reasoning": f"基于 {ctx['cat_sample_count']} 条历史数据，该类别平均膨胀 {ctx['cat_ratio']}x，建议 {minutes} 分钟",
        "source": "stats",
        "ai_errors": ai_errors or [],
    }


def estimate_time(description, category, user_id=None):
    ctx = gather_context(category, description, user_id)
    prompt = build_estimation_prompt(ctx)
    ai_errors = []

    from utils.config import get_ai_provider

    preferred_id, preferred_provider = get_ai_provider()
    if preferred_provider and preferred_provider.get("api_key"):
        try:
            result = _call_ai(prompt, preferred_provider)
            if result:
                parsed = _parse_response(result)
                if parsed:
                    return {**parsed, "source": "ai"}
        except Exception as exc:
            provider_name = preferred_provider.get("name", preferred_id)
            ai_errors.append(f"{provider_name}: {exc.__class__.__name__}")
            logger.warning("AI estimate failed for provider %s", provider_name, exc_info=True)

    for pid, provider in AI_PROVIDERS.items():
        if pid == preferred_id:
            continue
        if not provider.get("api_key"):
            continue
        try:
            result = _call_ai(prompt, provider)
            if result:
                parsed = _parse_response(result)
                if parsed:
                    return {**parsed, "source": "ai"}
        except Exception as exc:
            provider_name = provider.get("name", pid)
            ai_errors.append(f"{provider_name}: {exc.__class__.__name__}")
            logger.warning("AI estimate failed for provider %s", provider_name, exc_info=True)
            continue

    return _statistics_fallback(ctx, ai_errors)