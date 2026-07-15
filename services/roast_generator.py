import random
import os
from dao.task_dao import get_all_done_history
from utils.config import AI_PROVIDERS


def generate_daily_review(today_tasks):
    done_tasks = [t for t in today_tasks if t.get('status') == 'done' and t.get('actual_minutes')]
    if not done_tasks:
        return [
            "今天还没完成任何任务，你是在摸鱼还是在摸鱼？",
            "一个任务都没完成？今天的你和昨天的你有什么区别？",
            "零产出的一天。你的时间都去哪了？刷短视频了吧？",
        ]

    comments = []

    total_estimated = sum(t.get('estimated_minutes', 0) for t in done_tasks)
    total_actual = sum(t.get('actual_minutes', 0) for t in done_tasks)

    if total_estimated > 0 and total_actual > 0:
        overall_ratio = total_actual / total_estimated
        if overall_ratio > 2.0:
            comments.append(
                f"今天你总共估了 {total_estimated} 分钟，实际干了 {total_actual} 分钟，膨胀率 {overall_ratio:.1f}x。"
                f"你的时间感知能力建议直接送进 ICU。"
            )
        elif overall_ratio > 1.5:
            comments.append(
                f"今天你总共估了 {total_estimated} 分钟，实际干了 {total_actual} 分钟，膨胀率 {overall_ratio:.1f}x。"
                f"你的时间感知能力，建议回炉重造。"
            )
        elif overall_ratio > 1.1:
            comments.append(
                f"今天估 {total_estimated} 分钟，实际 {total_actual} 分钟，偏差不大，但别骄傲，你只是偶尔正常了一次。"
            )
        else:
            comments.append(
                f"今天估 {total_estimated} 分钟，实际 {total_actual} 分钟。难得啊，你今天居然没怎么膨胀，继续保持！"
            )

    for task in done_tasks:
        est = task.get('estimated_minutes', 0)
        act = task.get('actual_minutes', 0)
        if est > 0 and act > 0 and act / est > 2.0:
            comments.append(
                f"「{task['description']}」估 {est} 分钟，实际 {act} 分钟——你当时是哪来的自信？"
            )

    todo_tasks = [t for t in today_tasks if t.get('status') == 'todo']
    if todo_tasks:
        todo_names = "、".join([t['description'] for t in todo_tasks[:3]])
        comments.append(f"还有 {len(todo_tasks)} 个任务没动：{todo_names}。明天又是充满幻觉的一天呢。")

    if not comments:
        comments.append("今天表现还行，但别太得意，历史数据可都记着呢。")

    return comments


def get_ai_prompt(today_tasks, roast_mode="扎心"):
    task_lines = []
    for i, t in enumerate(today_tasks, 1):
        est = t.get('estimated_minutes', 0)
        act = t.get('actual_minutes', '?')
        calibrated = t.get('calibrated_minutes', est)
        ratio = t.get('expansion_ratio', 1.0)
        status = "✅" if t.get('status') == 'done' else "⏳"
        task_lines.append(
            f"{status} {t['description']}（{t.get('category', '')}）"
            f"估{est}min 实际{act}min 膨胀{ratio:.1f}x"
        )
    tasks_text = "\n".join(task_lines)

    total_est = sum(t.get('estimated_minutes', 0) for t in today_tasks)
    total_act = sum(t.get('actual_minutes', 0) for t in today_tasks if t.get('actual_minutes'))
    done_count = sum(1 for t in today_tasks if t.get('status') == 'done')
    todo_count = sum(1 for t in today_tasks if t.get('status') == 'todo')

    if roast_mode == "温和":
        prompt = f"""你是温暖鼓励的时间管理教练。请根据用户今日的任务数据，写一段温和的反馈。

要求：
1. 语气温暖、包容、鼓励，禁用任何攻击性、讽刺、贬义的词汇
2. 先肯定用户成果（如完成率、实际用时等），再温和地提出一条改进建议
3. 句式参考："今天完成得很棒！如果下次能把预估时间压紧一点，效果会更好哦～"
4. 严禁出现"别得意""拖延的缩影""灾难""有本事挑战""懒鬼""废物"等字眼
5. 输出 3-4 句话，60-100 字

今日数据：共{len(today_tasks)}任务，完成{done_count}，待办{todo_count}，总估{total_est}min，实际{total_act}min
{task_lines}"""
    else:
        prompt = f"""你是毒舌时间管理教练。请根据用户今日的任务数据，写一段毒舌评论。

要求：
1. 必须引用具体数字（如完成率、超时比例、偏差百分比等），不能空洞
2. 至少包含 3 个完整句子，总字数 60-120 字
3. 风格犀利、一针见血，但给出有建设性的建议
4. 禁止客套话，禁止敷衍的一句话

今日数据：共{len(today_tasks)}任务，完成{done_count}，待办{todo_count}，总估{total_est}min，实际{total_act}min
{task_lines}"""
    return prompt


def call_ai_api(prompt, provider, system_prompt=None):
    if not provider.get("api_key"):
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None
    if system_prompt is None:
        system_prompt = "你是毒舌时间管理教练。只输出JSON：{\"roast\":\"一段毒舌评论，至少3句话，60-120字，必须引用具体数据\"}，禁止输出其他内容。"
    client_params = {"api_key": provider["api_key"]}
    if provider.get("base_url"):
        client_params["base_url"] = provider["base_url"]
    client = OpenAI(**client_params)
    response = client.chat.completions.create(
        model=provider["model"],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
        max_tokens=300,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


def generate_ai_daily_review(today_tasks, roast_mode="扎心", enabled_providers=None):
    import streamlit as st
    import json
    prompt = get_ai_prompt(today_tasks, roast_mode)

    if roast_mode == "温和":
        system_prompt = "你是温暖鼓励的时间管理教练。只输出JSON：{\"roast\":\"一段温和的反馈，3-4句话，60-100字，先肯定再建议\"}，禁止输出其他内容。"
    else:
        system_prompt = "你是毒舌时间管理教练。只输出JSON：{\"roast\":\"一段毒舌评论，至少3句话，60-120字，必须引用具体数据\"}，禁止输出其他内容。"

    from utils.config import get_ai_provider

    preferred_id, preferred_provider = get_ai_provider()
    if preferred_provider and preferred_provider.get("api_key"):
        try:
            result = call_ai_api(prompt, preferred_provider, system_prompt)
            if result:
                data = json.loads(result)
                return [data.get("roast", result)]
        except json.JSONDecodeError:
            return [result]
        except Exception as e:
            st.toast(f"❌ {preferred_provider['name']} 调用失败", icon="❌")

    if enabled_providers is None:
        enabled_providers = {pid: bool(p["api_key"]) for pid, p in AI_PROVIDERS.items()}

    for provider_id, provider in AI_PROVIDERS.items():
        if provider_id == preferred_id:
            continue
        if not enabled_providers.get(provider_id, False):
            continue
        if not provider.get("api_key"):
            continue
        try:
            result = call_ai_api(prompt, provider, system_prompt)
            if result:
                data = json.loads(result)
                return [data.get("roast", result)]
        except json.JSONDecodeError:
            return [result]
        except Exception:
            continue

    return None


def get_or_generate_daily_quote():
    import json
    from datetime import date

    today_str = date.today().isoformat()
    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "daily_quotes.json")

    os.makedirs(os.path.dirname(json_path), exist_ok=True)

    quotes = {}
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                quotes = json.load(f)
        except (json.JSONDecodeError, IOError):
            quotes = {}

    if today_str in quotes and quotes[today_str]:
        return quotes[today_str]

    quote = _generate_ai_quote()
    if not quote:
        from utils.config import ROAST_QUOTES
        import hashlib
        idx = int(hashlib.md5(today_str.encode()).hexdigest(), 16) % len(ROAST_QUOTES)
        quote = "「" + ROAST_QUOTES[idx] + "」"

    quotes[today_str] = quote
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(quotes, f, ensure_ascii=False, indent=2)
    except IOError:
        pass

    return quote


_DAILY_QUOTE_PROMPT = """你是一个毒舌但内心温暖的时间管理教练。请生成一句今日鸡汤，要求：
1. 幽默犀利，带点自嘲和讽刺，但最终是积极向上的
2. 与时间管理、拖延症、自我欺骗、效率相关
3. 中文，20-40字，一句话即可
4. 风格参考：像鲁迅、王小波写鸡汤，表面扎心实则治愈
5. 不要加引号、不要加署名、不要加任何前缀
直接输出这句话。"""


def _generate_ai_quote():
    import streamlit as st
    from utils.config import get_ai_provider

    preferred_id, preferred_provider = get_ai_provider()
    if preferred_provider and preferred_provider.get("api_key"):
        try:
            result = call_ai_api(_DAILY_QUOTE_PROMPT, preferred_provider)
            if result:
                return result.strip()
        except Exception:
            pass

    for provider_id, provider in AI_PROVIDERS.items():
        if provider_id == preferred_id:
            continue
        enabled = st.session_state.get("ai_enabled_providers", {}).get(provider_id, False)
        if not enabled:
            continue
        if not provider.get("api_key"):
            continue
        try:
            result = call_ai_api(_DAILY_QUOTE_PROMPT, provider)
            if result:
                return result.strip()
        except Exception:
            continue
    return None