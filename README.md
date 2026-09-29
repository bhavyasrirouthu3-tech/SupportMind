# SupportMind 📡

**A customer support agent that never makes a customer repeat themselves.**

SupportMind is a support chat agent for an internet provider (SwiftNet Fiber). It uses
[Hindsight](https://github.com/vectorize-io/hindsight) agent memory to remember every
customer's past problems, the fixes that worked, promises made to them, and how they
like to be helped. It also learns a shared playbook of fixes, so a solution found for
one customer helps the next one.

## The problem

Support agents (human or AI) usually start every chat from zero. The customer explains
their problem again, gets the same basic steps they already tried, and a promise made
last month is forgotten. That is the main reason customers get angry.

## Without memory vs with memory (example)

Customer Ravi types: *"My internet is slow again."*

| Memory OFF | Memory ON |
|---|---|
| "Sorry to hear that. Please restart your router and run a speed test." | "Hi Ravi, sorry it's slow again. Last time (after the power cut on 10 Sep) your router had reset its channel settings. Please restart it and reconnect your laptop to **SwiftNet_5G**, that fixed it in 5 minutes before." |

Customer Priya types: *"Check my bill."*

- **Memory OFF:** a generic billing answer.
- **Memory ON:** the agent remembers the duplicate OTT charge, the 10% loyalty discount promised in July that was never applied, and the open billing ticket, then apologises and addresses it first.

## How it works

```
Customer message
      │
      ▼
recall()  ── customer bank:  history, preferences, promises, mood
      │  └─ playbook bank:  fixes that worked for similar problems
      ▼
Groq LLM (gpt-oss-120b) answers using those memories
      │
      ▼
retain()  ── every chat turn is saved to the customer's bank
      │
"Mark issue as resolved"
      ▼
retain()  ── the confirmed fix is saved to the customer bank AND the shared playbook
```

### How Hindsight memory is used

| Where | Hindsight call | Why |
|---|---|---|
| `seed_memory.py` | `create_bank`, `retain` | Loads 15 customers and 27 past tickets with their real dates |
| `memory.recall_customer` | `recall` | Finds what matters about this customer for this message |
| `memory.recall_playbook` | `recall` | Finds fixes that worked for other customers with the same router |
| `memory.retain_chat_turn` | `retain` | Saves every conversation, so the next chat knows about this one |
| `memory.retain_resolution` | `retain` | Saves confirmed fixes, which is how the agent improves over time |

Each customer has their own memory bank (privacy and clean recall). The playbook bank
is shared across the team.

## Project structure

```
app.py              Streamlit chat screen + "What the agent remembers" panel
agent.py            Builds the prompt with memories and calls Groq (with a backup model)
memory.py           All Hindsight code: banks, recall, retain
seed_memory.py      One-time loader for customer history
test_connection.py  Checks your API keys work
data/customers.json 15 realistic customers with ticket history
```

## Setup

You need Python 3.10+.

```bash
# 1. install libraries
pip install -r requirements.txt

# 2. add your keys
cp .env.example .env        # on Windows: copy .env.example .env
#    then open .env and paste your Hindsight and Groq keys

# 3. check the keys work
python test_connection.py

# 4. load customer history into Hindsight (only once)
python seed_memory.py

# 5. wait 1-2 minutes, then start the app
streamlit run app.py
```

Get keys here:
- Hindsight Cloud: [ui.hindsight.vectorize.io](https://ui.hindsight.vectorize.io) → Connect → Create API Key
- Groq: [console.groq.com](https://console.groq.com) → API Keys

## Demo script (2 minutes)

1. Pick **Ravi Kumar**. Turn **Memory off**. Type "My internet is slow again". Generic answer.
2. Turn **Memory on**. Same message. The agent remembers the 5 GHz fix and the power-cut reset. The right panel shows the recalled memories.
3. Pick **Priya Reddy**, type "Why is my bill still wrong?". It remembers the unkept discount promise.
4. Solve a new problem in chat, click **Mark issue as resolved**, then start a new chat as another customer with the same router. The new fix appears under "Fixes that worked for others". The agent learned.

## Tech

- [Hindsight](https://hindsight.vectorize.io/) for agent memory ([what is agent memory?](https://vectorize.io/what-is-agent-memory))
- Groq (`openai/gpt-oss-120b`, fallback `qwen/qwen3-32b`)
- Streamlit
