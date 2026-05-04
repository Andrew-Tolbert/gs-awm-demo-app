import os
import time
import json
import urllib.request
import pandas as pd
import streamlit as st
from lib.db import workspace_client

st.set_page_config(page_title="Genie", page_icon="🧞", layout="wide")

SPACE_ID     = os.environ.get("AWM_GENIE_SPACE", "")
_DONE_STATUS = {"COMPLETED", "QUERY_RESULT_IS_READY", "COMPLETED_WITH_QUERY_RESULT"}
_FAIL_STATUS = {"FAILED", "CANCELLED"}


# ── Genie API helpers ─────────────────────────────────────────────────────────

def _status(obj) -> str:
    return obj.value if hasattr(obj, "value") else str(obj or "UNKNOWN")


def _extract_suggested_questions_via_rest(
    conv_id: str, message_id: str
) -> list[str]:
    """Fall back to REST API when the SDK object doesn't expose suggested_questions."""
    client = workspace_client()
    try:
        host  = client.config.host.rstrip("/")
        auth  = client.config.authenticate()
        token = (
            auth.get("Authorization", "").replace("Bearer ", "")
            if isinstance(auth, dict)
            else getattr(auth, "token", None)
        )
        if not token:
            return []
        url = (
            f"{host}/api/2.0/genie/spaces/{SPACE_ID}"
            f"/conversations/{conv_id}/messages/{message_id}"
        )
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req) as resp:
            raw = json.loads(resp.read().decode())
        for att in raw.get("attachments", []):
            sq = att.get("suggested_questions")
            if isinstance(sq, dict) and "questions" in sq:
                return sq["questions"]
    except Exception:
        pass
    return []


def _execute_sql(sql: str) -> pd.DataFrame | None:
    """Re-execute a Genie-generated SQL query for reliable tabular results."""
    warehouse_id = os.environ.get("DATABRICKS_WAREHOUSE_ID", "")
    if not warehouse_id:
        return None
    try:
        result = workspace_client().statement_execution.execute_statement(
            warehouse_id=warehouse_id,
            statement=sql,
            wait_timeout="50s",
        )
        if result.status and _status(result.status.state) == "SUCCEEDED":
            cols = [c.name for c in result.manifest.schema.columns]
            rows = result.result.data_array if result.result and result.result.data_array else []
            return pd.DataFrame(rows, columns=cols)
    except Exception:
        pass
    return None


def ask_genie(question: str, conv_id: str | None) -> dict:
    """Send a question to the Genie space and return a structured response."""
    client = workspace_client()

    if conv_id:
        resp       = client.genie.create_message(SPACE_ID, conv_id, question)
        new_conv_id = conv_id
    else:
        resp        = client.genie.start_conversation(SPACE_ID, question)
        new_conv_id = resp.conversation_id

    message_id = resp.message_id if hasattr(resp, "message_id") else resp.id

    # Poll until the message is ready
    msg = None
    for _ in range(30):
        msg = client.genie.get_message(SPACE_ID, new_conv_id, message_id)
        sv  = _status(msg.status)
        if sv in _DONE_STATUS:
            break
        if sv in _FAIL_STATUS:
            return {"conv_id": new_conv_id, "answer": f"Genie error: {sv}",
                    "df": None, "sql": None, "suggested": []}
        time.sleep(2)

    answer, sql_text, df, suggested = None, None, None, []

    for att in msg.attachments or []:
        if hasattr(att, "text") and att.text:
            answer = (answer or "") + att.text.content

        if hasattr(att, "query") and att.query:
            sql_text = att.query.query
            if sql_text:
                df = _execute_sql(sql_text)

        try:
            if hasattr(att, "suggested_questions") and att.suggested_questions:
                sq = att.suggested_questions
                if hasattr(sq, "questions"):
                    suggested = list(sq.questions)
                elif isinstance(sq, dict) and "questions" in sq:
                    suggested = sq["questions"]
        except Exception:
            pass

    if not suggested:
        suggested = _extract_suggested_questions_via_rest(new_conv_id, message_id)

    if not answer and hasattr(msg, "content") and msg.content:
        answer = msg.content

    return {
        "conv_id":   new_conv_id,
        "answer":    answer,
        "df":        df,
        "sql":       sql_text,
        "suggested": suggested or [],
    }


# ── Session state ─────────────────────────────────────────────────────────────

st.session_state.setdefault("genie_conv_id",  None)
st.session_state.setdefault("genie_messages", [])


# ── Header ────────────────────────────────────────────────────────────────────

st.title("Ask Your Portfolio")
st.caption("Powered by Databricks Genie · Natural language queries over `ahtsa.awm`")

if not SPACE_ID:
    st.error("`AWM_GENIE_SPACE` environment variable is not set. Check `app.yaml`.")
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


# ── Suggested question chips ──────────────────────────────────────────────────

if st.session_state.genie_messages:
    last = st.session_state.genie_messages[-1]
    if last["role"] == "assistant" and last.get("suggested"):
        cols = st.columns(len(last["suggested"]))
        for i, q in enumerate(last["suggested"]):
            if cols[i].button(q, key=f"sq_{i}_{q[:20]}"):
                st.session_state.genie_pending = q
                st.rerun()


# ── Chat input ────────────────────────────────────────────────────────────────

pending    = st.session_state.pop("genie_pending", None)
user_input = st.chat_input("Ask about your portfolio…") or pending

if user_input:
    st.session_state.genie_messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            result = ask_genie(user_input, st.session_state.genie_conv_id)

        st.session_state.genie_conv_id = result["conv_id"]
        answer = result["answer"] or "*(No text response)*"

        st.markdown(answer)
        if result["df"] is not None:
            st.dataframe(result["df"], use_container_width=True)
        if result["sql"]:
            with st.expander("SQL", expanded=False):
                st.code(result["sql"], language="sql")

    st.session_state.genie_messages.append({
        "role":      "assistant",
        "content":   answer,
        "df":        result["df"],
        "sql":       result["sql"],
        "suggested": result["suggested"],
    })
    st.rerun()


# ── Reset ─────────────────────────────────────────────────────────────────────

if st.session_state.genie_messages:
    if st.button("Clear conversation", type="secondary"):
        st.session_state.genie_conv_id  = None
        st.session_state.genie_messages = []
        st.rerun()
