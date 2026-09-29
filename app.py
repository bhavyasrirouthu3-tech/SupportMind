"""
app.py - the SupportMind screen.

    streamlit run app.py

Left:  chat with the support agent
Right: what the agent remembered from Hindsight for this answer
"""

import json

import streamlit as st

import agent
import memory

st.set_page_config(page_title="SupportMind", page_icon="📡", layout="wide")

st.markdown("""
<style>
.mem-card {border-left: 3px solid #0F7B78; background: rgba(15,123,120,0.07);
           padding: 8px 12px; margin-bottom: 8px; border-radius: 0 6px 6px 0; font-size: 0.9rem;}
.mem-card.playbook {border-left-color: #C98A1B; background: rgba(201,138,27,0.08);}
.mem-date {color: #6B7A8C; font-size: 0.78rem;}
.mem-off {border: 1px dashed #9AA5B1; padding: 14px; border-radius: 6px; color: #6B7A8C;}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_customers():
    with open("data/customers.json", encoding="utf-8") as f:
        return json.load(f)["customers"]


customers = load_customers()

# ---------------------------------------------------------------- state
if "chats" not in st.session_state:
    st.session_state.chats = {}          # customer_id -> list of messages
if "recalled" not in st.session_state:
    st.session_state.recalled = {}       # customer_id -> {"customer": [...], "playbook": [...]}

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.title("📡 SupportMind")
    st.caption("Support agent for SwiftNet Fiber that remembers every customer.")

    labels = [f"{c['name']} · {c['city']}" for c in customers]
    idx = st.selectbox("Customer on chat", range(len(customers)), format_func=lambda i: labels[i])
    customer = customers[idx]
    cid = customer["id"]

    memory_on = st.toggle("Memory", value=True,
                          help="Turn off to see how the agent behaves without Hindsight.")


chat = st.session_state.chats.setdefault(cid, [])

# ---------------------------------------------------------------- handle new message
prompt = st.chat_input(f"Type as {customer['name']}...")

if prompt:
    chat.append({"role": "user", "content": prompt})

    customer_mem, playbook_mem = None, None
    if memory_on:
        with st.spinner("Recalling memories..."):
            try:
                customer_mem = memory.recall_customer(cid, prompt)
                playbook_mem = memory.recall_playbook(f"{customer['router']}: {prompt}")
            except Exception as e:
                st.warning(f"Memory recall failed, answering without it: {e}")
                customer_mem, playbook_mem = [], []
        st.session_state.recalled[cid] = {"customer": customer_mem, "playbook": playbook_mem}
    else:
        st.session_state.recalled.pop(cid, None)

    with st.spinner("Thinking..."):
        try:
            answer = agent.reply(customer, chat[:-1], prompt, customer_mem, playbook_mem)
        except Exception as e:
            answer = f"⚠️ The AI could not answer right now ({e}). Please try again."

    chat.append({"role": "assistant", "content": answer})

    if memory_on and not answer.startswith("⚠️"):
        try:
            memory.retain_chat_turn(cid, customer["name"], prompt, answer)
        except Exception as e:
            st.warning(f"Could not save this chat to memory: {e}")

# ---------------------------------------------------------------- sidebar actions
# (placed after the new message is handled, so the buttons see the latest chat)
with st.sidebar:
    st.divider()

    if st.button("✅ Mark issue as resolved", use_container_width=True, disabled=len(chat) < 2):
        with st.spinner("Saving what worked..."):
            try:
                summary = agent.summarize_resolution(chat)
                memory.retain_resolution(cid, customer["name"], customer["router"],
                                         summary["issue"], summary["fix"])
                st.success(f"Saved to memory.\n\n**Issue:** {summary['issue']}\n\n**Fix:** {summary['fix']}")
            except Exception as e:
                st.error(f"Could not save the resolution: {e}")

    if st.button("🗑️ Clear this chat", use_container_width=True):
        st.session_state.chats[cid] = []
        st.session_state.recalled.pop(cid, None)
        st.rerun()

    st.divider()
    st.caption("Demo tip: ask the same question with Memory off, then on.")


# ---------------------------------------------------------------- layout
st.subheader(f"{customer['name']}")
st.caption(f"{customer['id']}  |  {customer['plan']}  |  {customer['router']}  |  {customer['city']}")

left, right = st.columns([3, 2], gap="large")

with left:
    if not chat:
        st.info("Start the conversation from the box below, as if you are the customer.")
    for m in chat:
        with st.chat_message(m["role"], avatar="🙂" if m["role"] == "user" else "📡"):
            st.markdown(m["content"])

with right:
    st.markdown("#### What the agent remembers")

    if not memory_on:
        st.markdown('<div class="mem-off">Memory is off. The agent only sees the account '
                    'basics above, like a new support agent on day one.</div>',
                    unsafe_allow_html=True)
    else:
        recalled = st.session_state.recalled.get(cid)
        if not recalled:
            st.caption("Send a message to see which memories Hindsight recalls for it.")
        else:
            st.markdown("**About this customer**")
            if not recalled["customer"]:
                st.caption("Nothing relevant found.")
            for m in recalled["customer"]:
                st.markdown(f'<div class="mem-card">{m["text"]}'
                            f'<div class="mem-date">{m["date"]} · {m["type"]}</div></div>',
                            unsafe_allow_html=True)

            st.markdown("**Fixes that worked for others**")
            if not recalled["playbook"]:
                st.caption("Nothing relevant found.")
            for m in recalled["playbook"]:
                st.markdown(f'<div class="mem-card playbook">{m["text"]}'
                            f'<div class="mem-date">{m["date"]}</div></div>',
                            unsafe_allow_html=True)
