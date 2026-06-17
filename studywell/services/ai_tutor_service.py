import json
import os
from typing import Any

import httpx

SYSTEM_PROMPT = (
    "You are Chulk - AI Study Bot, a friendly and encouraging student being taught by the user. "
    "When referring to yourself, always use the name Chulk. "
    "Your job is to judge whether the user's teaching is accurate and clear. "
    "The lesson context will include curriculum and subject (IB, A Level, or IGCSE). "
    "Stay inside that curriculum's scope and terminology. "
    "Never switch topics, never chat about unrelated things, and never role-play anything else. "
    "If user message is off-topic, set verdict to off_topic and ask them to return to the lesson. "
    "Respond ONLY in valid JSON with keys: verdict, feedback, reassurance, follow_up_question, resources. "
    "Allowed verdict values: correct, needs_work, off_topic. "
    "Feedback must be concise, specific, educational, and warm in tone. "
    "Reassurance should sound supportive and motivating, never harsh. "
    "Use friendly language such as 'Great effort', 'Nice try', or 'Good progress' where appropriate. "
    "resources must be an array with 1 to 4 short syllabus-aligned resource suggestions for the specific part being learned. "
    "Each resource should be one plain string, for example: 'IB CS: Review HL pseudocode trace tables'."
)


def _get_config() -> tuple[str, str, str]:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()

    # Optional local hardcoded key file kept out of git.
    try:
        from local_secrets import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL  # type: ignore

        if not api_key:
            api_key = str(DEEPSEEK_API_KEY).strip()
        base_url = str(DEEPSEEK_BASE_URL).strip() or base_url
        model = str(DEEPSEEK_MODEL).strip() or model
    except Exception:
        pass

    return api_key, base_url.rstrip("/"), model


def _fallback_response() -> dict[str, Any]:
    return {
        "verdict": "needs_work",
        "feedback": "I could not parse the model response. Try explaining your idea in 2-4 precise steps.",
        "reassurance": "You are doing the right thing by teaching it out loud.",
        "follow_up_question": "What is the key definition in one sentence?",
        "resources": [
            "Use your syllabus guide and revise the exact learning objective for this subtopic.",
        ],
    }


async def evaluate_teaching(
    *,
    topic: str,
    mode: str,
    user_message: str,
    history: list[dict[str, str]],
) -> dict[str, Any]:
    api_key, base_url, model = _get_config()
    if not api_key:
        return {
            "verdict": "off_topic",
            "feedback": "DeepSeek key is not configured on server.",
            "reassurance": "Add your key in local_secrets.py or DEEPSEEK_API_KEY and retry.",
            "follow_up_question": "",
            "resources": [],
        }

    topic_line = topic.strip() or "General study concept"
    mode_key = (mode or "listen").strip().lower()
    if mode_key not in {"listen", "teacher"}:
        mode_key = "listen"

    mode_instruction = (
        "Mode: listen. The user is teaching you. Evaluate if their explanation is correct. "
        "Use verdict correct/needs_work/off_topic. "
        "If the user has not yet attempted an explanation and is only setting up or asking what to do, use verdict guide instead of needs_work."
        if mode_key == "listen"
        else "Mode: teacher. The user asks to learn a part and you should teach it clearly and kindly. "
        "Use verdict guide unless off-topic. In follow_up_question, ask a quick check question."
    )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": mode_instruction},
        {
            "role": "system",
            "content": (
                "Current lesson topic from user: "
                f"{topic_line}. "
                "Reject unrelated conversation. If uncertain, ask a clarifying follow-up question."
            ),
        },
    ]

    for item in history[-8:]:
        role = item.get("role", "")
        content = item.get("content", "")
        if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
            messages.append({"role": role, "content": content[:1200]})

    messages.append({"role": "user", "content": user_message[:1800]})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 400,
    }

    url = f"{base_url}/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    raw = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not isinstance(raw, str) or not raw.strip():
        return _fallback_response()

    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()

    try:
        parsed = json.loads(text)
    except Exception:
        return _fallback_response()

    verdict = str(parsed.get("verdict", "needs_work")).strip().lower()
    allowed = {"correct", "needs_work", "off_topic", "guide"}
    if verdict not in allowed:
        verdict = "guide" if mode_key == "teacher" else "needs_work"

    raw_resources = parsed.get("resources", [])
    resources: list[str] = []
    if isinstance(raw_resources, list):
        for item in raw_resources:
            if isinstance(item, str) and item.strip():
                resources.append(item.strip()[:220])
    resources = resources[:4]

    return {
        "verdict": verdict,
        "feedback": str(parsed.get("feedback", "")).strip()[:1200],
        "reassurance": str(parsed.get("reassurance", "")).strip()[:600],
        "follow_up_question": str(parsed.get("follow_up_question", "")).strip()[:600],
        "resources": resources,
    }
