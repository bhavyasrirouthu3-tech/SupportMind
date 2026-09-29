"""
seed_memory.py - run this ONCE before the demo.

It loads the past history of 15 customers from data/customers.json into
Hindsight, so the agent already "knows" them when you start the app.

    python seed_memory.py
"""

import json
from datetime import datetime

import memory


def main():
    with open("data/customers.json", encoding="utf-8") as f:
        data = json.load(f)

    client = memory.get_client()

    print("Creating shared playbook bank...")
    try:
        memory.create_playbook_bank()
    except Exception as e:
        print(f"  (bank may already exist, continuing) {e}")

    for c in data["customers"]:
        print(f"\nLoading {c['name']} ({c['id']})")
        bank = memory.customer_bank(c["id"])

        try:
            memory.create_customer_bank(c["id"], c["name"])
        except Exception as e:
            print(f"  (bank may already exist, continuing) {e}")

        # 1) who the customer is
        client.retain(
            bank_id=bank,
            content=" ".join(c["profile"]) +
                    f" {c['name']} is on the {c['plan']} plan with a {c['router']} router in {c['city']}.",
            context="customer profile from CRM",
            retain_async=True,
        )

        # 2) every past ticket, with its real date
        for t in c["tickets"]:
            when = datetime.fromisoformat(t["date"])
            client.retain(
                bank_id=bank,
                content=(f"Support ticket on {t['date']}. {c['name']} reported: {t['issue']} "
                         f"Resolution: {t['resolution']} Customer mood: {t['sentiment']}."),
                context="past support ticket",
                timestamp=when,
                retain_async=True,
            )

            # 3) fixes also go into the shared playbook
            client.retain(
                bank_id=memory.PLAYBOOK_BANK,
                content=f"On router {c['router']}, problem '{t['issue']}' was handled by: {t['resolution']}",
                context="past fix",
                timestamp=when,
                retain_async=True,
            )
            print(f"  ✓ ticket {t['date']}")

    print("\nDone! Hindsight is processing the memories in the background.")
    print("Wait about 1-2 minutes, then start the app with:  streamlit run app.py")


if __name__ == "__main__":
    main()
