"""
agent.py - the AI "brain". It talks to Groq.

The key idea: before answering, we paste what Hindsight remembers into the
prompt. Same AI model, but with memory it behaves like it knows the customer.
"""

import json
import os
import re

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

MODELS = [
    os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
    "qwen/qwen3-32b",  # backup if the first model fails
]

_groq = None


def get_groq() -> Groq:
    global _groq
    if _groq is None:
        key = os.getenv("GROQ_API_KEY")
        if not key:
            raise RuntimeError("GROQ_API_KEY is missing. Add it to your .env file.")
        _groq = Groq(api_key=key)
    return _groq


def _chat(messages: list[dict], temperature: float = 0.4) -> str:
    """Call Groq. If one model fails, try the backup instead of crashing."""
    last_error = None
    for model in MODELS:
        try:
            resp = get_groq().chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=700,
            )
            text = resp.choices[0].message.content or ""
            # qwen models sometimes include <think>...</think>; remove it
            return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        except Exception as e:  # network error, rate limit, model error...
            last_error = e
    raise RuntimeError(f"All AI models failed. Last error: {last_error}")


def _format(memories: list[dict]) -> str:
    if not memories:
        return "(nothing)"
    return "\n".join(f"- [{m['date'] or 'undated'}] {m['text']}" for m in memories)


def build_system_prompt(customer: dict, customer_memories: list[dict] | None,
                        playbook_memories: list[dict] | None) -> str:
    base = (
        "You are the support agent for SwiftNet Fiber, an internet provider in "
        "Andhra Pradesh and Telangana. Be warm, clear and brief (under 120 words). "
        "Give numbered steps when troubleshooting. Never invent account facts.\n\n"
        f"Customer on this chat: {customer['name']} (ID {customer['id']}), "
        f"plan {customer['plan']}, router {customer['router']}, city {customer['city']}.\n"
    )

    if customer_memories is None:  # memory switched OFF
        return base + "\nYou have no history about this customer."

    return base + (
        "\nWHAT YOU REMEMBER ABOUT THIS CUSTOMER (from past conversations):\n"
        f"{_format(customer_memories)}\n\n"
        "FIXES THAT WORKED FOR SIMILAR PROBLEMS (team playbook):\n"
        f"{_format(playbook_memories or [])}\n\n"
        "How to use this memory:\n"
        "- If this looks like a problem they had before, say so and start with the fix that worked last time.\n"
        "- Follow their stated preferences (language style, contact method, timing, detail level).\n"
        "- If a promise was made to them and not kept, acknowledge it and apologise.\n"
        "- Never make them repeat information you already have.\n"
    )


def reply(customer: dict, history: list[dict], user_msg: str,
          customer_memories: list[dict] | None, playbook_memories: list[dict] | None) -> str:
    messages = [{"role": "system",
                 "content": build_system_prompt(customer, customer_memories, playbook_memories)}]
    messages += history[-8:]  # last few turns of this chat
    messages.append({"role": "user", "content": user_msg})
    return _chat(messages)


def summarize_resolution(history: list[dict]) -> dict:
    """Turn the chat into {'issue': ..., 'fix': ...} so we can save it to memory."""
    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in history)
    prompt = (
        "Read this support chat and return ONLY JSON like "
        '{"issue": "short problem description", "fix": "what solved it"}. '
        "No other text.\n\n" + transcript
    )
    raw = _chat([{"role": "user", "content": prompt}], temperature=0)
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(raw)
        return {"issue": str(data.get("issue", "")), "fix": str(data.get("fix", ""))}
    except json.JSONDecodeError:
        return {"issue": "see chat", "fix": raw[:300]}
