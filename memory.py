"""
memory.py - everything that talks to Hindsight lives here.

We use two kinds of memory banks:
  1. One bank PER CUSTOMER   -> remembers that customer's history, preferences, mood.
  2. One shared PLAYBOOK bank -> remembers fixes that worked, so the agent
                                 gets smarter for EVERY customer over time.
"""

import os
from datetime import datetime

from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()

HINDSIGHT_URL = os.getenv("HINDSIGHT_API_URL", "https://api.hindsight.vectorize.io")
HINDSIGHT_KEY = os.getenv("HINDSIGHT_API_KEY")

PLAYBOOK_BANK = "supportmind-playbook"

_client = None


def get_client() -> Hindsight:
    """Create the Hindsight client once and reuse it."""
    global _client
    if _client is None:
        if not HINDSIGHT_KEY:
            raise RuntimeError("HINDSIGHT_API_KEY is missing. Add it to your .env file.")
        _client = Hindsight(base_url=HINDSIGHT_URL, api_key=HINDSIGHT_KEY, timeout=60.0)
    return _client


def customer_bank(customer_id: str) -> str:
    """Each customer gets their own memory bank, e.g. 'supportmind-cust-sn-10231'."""
    return f"supportmind-cust-{customer_id.lower()}"


# ---------------------------------------------------------------- setup

def create_customer_bank(customer_id: str, name: str) -> None:
    get_client().create_bank(
        bank_id=customer_bank(customer_id),
        name=f"Customer {name}",
        mission=(
            f"I am the support memory for {name}, a SwiftNet Fiber internet customer. "
            "Track their problems, what fixed them, promises made to them, their "
            "preferences for how to be helped, and how they felt."
        ),
    )


def create_playbook_bank() -> None:
    get_client().create_bank(
        bank_id=PLAYBOOK_BANK,
        name="SwiftNet Support Playbook",
        mission=(
            "I am the shared troubleshooting memory of the SwiftNet Fiber support team. "
            "Track which fixes solved which problems, on which router models."
        ),
    )


# ---------------------------------------------------------------- recall

def _to_list(response, limit: int) -> list[dict]:
    items = []
    for r in (response.results or [])[:limit]:
        items.append({
            "text": r.text,
            "type": r.type,
            "date": str(r.occurred_start or r.mentioned_at or "")[:10],
        })
    return items


def recall_customer(customer_id: str, query: str, limit: int = 8) -> list[dict]:
    """What do we remember about THIS customer that is relevant to their message?"""
    response = get_client().recall(
        bank_id=customer_bank(customer_id),
        query=query,
        budget="mid",
        max_tokens=2048,
    )
    return _to_list(response, limit)


def recall_playbook(query: str, limit: int = 4) -> list[dict]:
    """Which fixes worked for similar problems for OTHER customers?"""
    response = get_client().recall(
        bank_id=PLAYBOOK_BANK,
        query=query,
        budget="low",
        max_tokens=1024,
    )
    return _to_list(response, limit)


# ---------------------------------------------------------------- retain

def retain_chat_turn(customer_id: str, name: str, user_msg: str, agent_reply: str) -> None:
    """Save one exchange of the conversation. Hindsight extracts the facts itself."""
    get_client().retain(
        bank_id=customer_bank(customer_id),
        content=f"{name} (customer): {user_msg}\nSupport agent: {agent_reply}",
        context="live support chat",
        timestamp=datetime.now(),
        retain_async=True,  # don't make the customer wait
    )


def retain_resolution(customer_id: str, name: str, router: str, issue: str, fix: str) -> None:
    """When a problem is solved, remember it for this customer AND in the shared playbook."""
    now = datetime.now()
    get_client().retain(
        bank_id=customer_bank(customer_id),
        content=f"Issue for {name} was resolved. Problem: {issue}. Fix that worked: {fix}.",
        context="ticket resolved",
        timestamp=now,
        retain_async=True,
    )
    get_client().retain(
        bank_id=PLAYBOOK_BANK,
        content=f"On router {router}, the problem '{issue}' was fixed by: {fix}.",
        context="confirmed fix",
        timestamp=now,
        retain_async=True,
    )
