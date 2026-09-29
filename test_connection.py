"""
test_connection.py - run this first to check your API keys work.

    python test_connection.py
"""

import time

import agent
import memory

print("1) Testing Groq (the AI brain)...")
try:
    answer = agent._chat([{"role": "user", "content": "Say hello in 5 words."}])
    print(f"   ✓ Groq works: {answer}")
except Exception as e:
    print(f"   ✗ Groq failed: {e}")

print("\n2) Testing Hindsight (the memory)...")
try:
    client = memory.get_client()
    client.retain(bank_id="supportmind-test", content="The test customer's favourite colour is blue.")
    time.sleep(3)
    result = client.recall(bank_id="supportmind-test", query="What colour does the customer like?")
    texts = [r.text for r in result.results]
    print(f"   ✓ Hindsight works. It remembered: {texts[:2]}")
except Exception as e:
    print(f"   ✗ Hindsight failed: {e}")

print("\nIf both show ✓ you are ready. Next: python seed_memory.py")
