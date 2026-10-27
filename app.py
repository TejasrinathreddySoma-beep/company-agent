import importlib, pathlib, subprocess, sys
import streamlit as st
import agent

BASE = pathlib.Path(__file__).parent

st.set_page_config(page_title="Company Assistant", page_icon="🏢")
st.title("🏢 Company Assistant")
st.caption("Ask about company documents, your notes, email and calendar.")

if "history" not in st.session_state:
    st.session_state.history = []   # what the LLM sees
    st.session_state.shown = []     # what the page displays

# ---------- sidebar ----------
with st.sidebar:
    if not agent.online():
        st.caption("🔴 Offline: documents only")
    st.header("Quick questions")
    for example in ["What meetings do I have this week?",
                    "Show my recent emails",
                    "What documents do you have?"]:
        if st.button(example, use_container_width=True):
            st.session_state.pending = example

    st.divider()
    st.header("Knowledge base")
    files = st.file_uploader("Add documents", type=["pdf", "txt", "md", "docx"],
                             accept_multiple_files=True)
    if files and st.button("Save and re-index", use_container_width=True):
        (BASE / "docs").mkdir(exist_ok=True)
        for f in files:
            (BASE / "docs" / f.name).write_bytes(f.getbuffer())
        with st.spinner("Indexing documents..."):
            r = subprocess.run([sys.executable, "ingest.py"], cwd=BASE,
                               capture_output=True, text=True)
        if r.returncode == 0:
            importlib.reload(agent)       # reload the new index
            st.success(r.stdout.strip().splitlines()[-1])
        else:
            st.error(r.stderr[-500:])

    st.divider()
    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.history = []
        st.session_state.shown = []
        st.rerun()

# ---------- chat ----------
def show_sources(sources):
    if not sources:
        return
    with st.expander(f"📄 Sources ({len(sources)})"):
        for s in sources:
            st.markdown(f"**{s['source']}** · relevance {s['score']}")
            st.caption(s["text"][:400] + "...")

for role, text, sources in st.session_state.shown:
    with st.chat_message(role):
        st.write(text)
        if role == "assistant":
            show_sources(sources)

q = st.chat_input("Ask something...") or st.session_state.pop("pending", None)

if q:
    st.chat_message("user").write(q)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                answer, sources = agent.ask(q, st.session_state.history[-6:])
            except Exception as e:
                answer, sources = f"Something went wrong: {e}", []
        st.write(answer)
        show_sources(sources)

    # remember the turn (ask() only updates a copy of the history)
    st.session_state.history += [{"role": "user", "content": q},
                                 {"role": "assistant", "content": answer}]
    st.session_state.shown += [("user", q, []), ("assistant", answer, sources)]