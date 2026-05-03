import os
import time
import json
import urllib.request
import pandas as pd
import streamlit as st
from databricks.sdk import WorkspaceClient
from databricks.sdk.config import Config

st.set_page_config(
    page_title="Genie",
    page_icon="🧞",
    layout="wide",
)

SPACE_ID = os.environ.get("AWM_GENIE_SPACE", "")

_DONE = {"COMPLETED", "QUERY_RESULT_IS_READY", "COMPLETED_WITH_QUERY_RESULT"}
_FAIL = {"FAILED", "CANCELLED"}


@st.cache_resource
def _client() -> WorkspaceClient:
    return WorkspaceClient(config=Config(http_timeout_seconds=600))


def _status_val(status) -> str:
    return status.value if hasattr(status, "value") else str(status or "UNKNOWN")


def _ask(question: str, conv_id: str | None) -> dict:
    client = _client()
    if conv_id:
        resp = client.genie.create_message(SPACE_ID, conv_id, question)
        new_conv_id = conv_id
    else:
        resp = client.genie.start_conversation(SPACE_ID, question)
        new_conv_id = resp.conversation_id

    message_id = resp.message_id if hasattr(resp, "message_id") else resp.id

    msg = None
    for _ in range(30):
        msg = client.genie.get_message(SPACE_ID, new_conv_id, message_id)
        sv = _status_val(msg.status)
        if sv in _DONE:
            break
        if sv in _FAIL:
            return {"conv_id": new_conv_id, "answer": f"Genie error: {sv}", "df": None, "sql": None, "suggested": []}
        time.sleep(2)

    answer, sql_text, df, suggested = None, None, None, []

    for att in msg.attachments or []:
        if hasattr(att, "text") and att.text:
            answer = (answer or "") + att.text.content

        if hasattr(att, "query") and att.query:
            sql_text = att.query.query
            if sql_text:
                try:
                    warehouse_id = os.environ.get("DATABRICKS_WAREHOUSE_ID", "")
                    r = client.statement_execution.execute_statement(
                        warehouse_id=warehouse_id,
                        statement=sql_text,
                        wait_timeout="50s",
                    )
                    if r.status and _status_val(r.status.state) == "SUCCEEDED":
                        cols = [c.name for c in r.manifest.schema.columns]
                        raw_rows = r.result.data_array if r.result and r.result.data_array else []
                        df = pd.DataFrame(raw_rows, columns=cols)
                except Exception:
                    pass

        # Suggested questions — SDK path
        try:
            if hasattr(att, "suggested_questions") and att.suggested_questions:
                sq = att.suggested_questions
                if hasattr(sq, "questions"):
                    suggested = list(sq.questions)
                elif isinstance(sq, dict) and "questions" in sq:
                    suggested = sq["questions"]
        except Exception:
            pass

    # REST fallback for suggested questions
    if not suggested:
        try:
            host = client.config.host.rstrip("/")
            auth = client.config.authenticate()
            token = None
            if isinstance(auth, dict):
                token = auth.get("Authorization", "").replace("Bearer ", "")
            elif hasattr(auth, "token"):
                token = auth.token
            if token:
                url = f"{host}/api/2.0/genie/spaces/{SPACE_ID}/conversations/{new_conv_id}/messages/{message_id}"
                req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
                with urllib.request.urlopen(req) as r:
                    raw = json.loads(r.read().decode())
                    for att in raw.get("attachments", []):
                        if "suggested_questions" in att:
                            sq = att["suggested_questions"]
                            if isinstance(sq, dict) and "questions" in sq:
                                suggested = sq["questions"]
                                break
        except Exception:
            pass

    if not answer and hasattr(msg, "content") and msg.content:
        answer = msg.content

    return {
        "conv_id": new_conv_id,
        "answer": answer,
        "df": df,
        "sql": sql_text,
        "suggested": suggested or [],
    }


# ── Session state ─────────────────────────────────────────────────────────────

if "genie_conv_id" not in st.session_state:
    st.session_state.genie_conv_id = None
if "genie_messages" not in st.session_state:
    st.session_state.genie_messages = []


# ── Header ────────────────────────────────────────────────────────────────────

st.title("Ask Your Portfolio")
st.caption("Powered by Databricks Genie · Natural language queries over `ahtsa.awm`")

if not SPACE_ID:
    st.error("`AWM_GENIE_SPACE` environment variable is not set. Check app.yaml.")
    st.stop()

# ── Conversation history ──────────────────────────────────────────────────────

for msg in st.session_state.genie_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("df") is not None:
            st.dataframe(msg["df"], use_container_width=True)
        if msg.get("sql"):
            with st.expander("SQL", expanded=False):
                st.code(msg["sql"], language="sql")

# ── Suggested question buttons ────────────────────────────────────────────────

if st.session_state.genie_messages:
    last = st.session_state.genie_messages[-1]
    if last["role"] == "assistant" and last.get("suggested"):
        cols = st.columns(len(last["suggested"]))
        for i, q in enumerate(last["suggested"]):
            if cols[i].button(q, key=f"sq_{i}_{q[:20]}"):
                st.session_state.genie_pending = q
                st.rerun()

# ── Chat input ────────────────────────────────────────────────────────────────

pending = st.session_state.pop("genie_pending", None)
user_input = st.chat_input("Ask about your portfolio…") or pending

if user_input:
    st.session_state.genie_messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            result = _ask(user_input, st.session_state.genie_conv_id)

        st.session_state.genie_conv_id = result["conv_id"]

        answer = result["answer"] or "*(No text response)*"
        st.markdown(answer)

        if result["df"] is not None:
            st.dataframe(result["df"], use_container_width=True)

        if result["sql"]:
            with st.expander("SQL", expanded=False):
                st.code(result["sql"], language="sql")

    st.session_state.genie_messages.append({
        "role": "assistant",
        "content": answer,
        "df": result["df"],
        "sql": result["sql"],
        "suggested": result["suggested"],
    })

    st.rerun()

# ── Reset ─────────────────────────────────────────────────────────────────────

if st.session_state.genie_messages:
    if st.button("Clear conversation", type="secondary"):
        st.session_state.genie_conv_id = None
        st.session_state.genie_messages = []
        st.rerun()
