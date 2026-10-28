import json
import os
import re
from datetime import date
from typing import Optional

import httpx

PROMPT = """You turn raw meeting notes into structured delivery data.
Return ONLY a JSON object with these keys:
"items": list of objects with "title" (imperative, max 12 words), "owner" (string or null),
"due" (YYYY-MM-DD or null), "priority" (critical|high|medium|low), "kind" (task|bug|feature|spike),
"status" (todo|doing|review|done), "points" (1,2,3,5,8 or 13).
"decisions", "risks", "questions": lists of short strings.
"participants": list of first names.
Today is {today}. Resolve relative dates against it. Keep the language of the notes."""


def configured() -> bool:
    return bool(os.getenv("LLM_BASE_URL") or os.getenv("LLM_API_KEY"))


def extract(notes: str, today: date) -> Optional[dict]:
    base = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
    model = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
    headers = {"Content-Type": "application/json"}
    if os.getenv("LLM_API_KEY"):
        headers["Authorization"] = f"Bearer {os.environ['LLM_API_KEY']}"
    payload = {
        "model": model,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": PROMPT.format(today=today.isoformat())},
            {"role": "user", "content": notes},
        ],
    }
    try:
        response = httpx.post(f"{base}/chat/completions", json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        match = re.search(r"\{.*\}", content, re.S)
        data = json.loads(match.group(0)) if match else None
    except (httpx.HTTPError, KeyError, IndexError, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        return None
    return data
