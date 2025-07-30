"""Gradio-based web app for Anyfile-Agent: upload documents, index them, and chat interactively."""

import atexit
import asyncio
import gc
import shutil
import sqlite3
import uuid
import duckdb
import gradio as gr
from pathlib import Path
from typing import Generator, List, Tuple

from any_chatbot.indexing import embed_and_index_all_docs
from any_chatbot.prompts import system_message
from any_chatbot.tools import initialize_retrieve_tool, initialize_sql_toolkit
from any_chatbot.utils import load_environ_vars

from langchain.chat_models import init_chat_model
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import create_react_agent

load_environ_vars()
ROOT = Path(__file__).parent
TMP_DIR = ROOT / "tmp"
TMP_DIR.mkdir(exist_ok=True)


class Session:
    """Session state for file uploads, indexing, and chat history."""

    def __init__(self):
        """Initialize session IDs, paths, and database connections."""
        self.sid = uuid.uuid4().hex
        self.db_path = TMP_DIR / "csv_excel_to_db.duckdb"
        self.index_path = TMP_DIR / "faiss_index"
        self.hist_db_path = TMP_DIR / "hist.db"
        self.hist_db = sqlite3.connect(self.hist_db_path, check_same_thread=False)
        self.agent = None
        self.sql_engines: List = []

    def cleanup(self):
        """Dispose SQL engines, close history DB, reset agent, and remove tmp directory."""
        # dispose any SQLAlchemy/SQL-toolkit engines
        for eng in self.sql_engines:
            try:
                eng.dispose(close=True)
            except Exception:
                pass
        self.sql_engines.clear()
        # close agent history db
        try:
            self.hist_db.close()
        except Exception:
            pass
        # map agent to none
        self.agent = None
        # delete the tmp dir itself
        shutil.rmtree(TMP_DIR, ignore_errors=True)


# initialize session
sess = Session()


# shutdown hook that is called when session ends
@atexit.register
def _purge_all():
    """Cleanup session data on program exit."""
    sess.cleanup()


def _safe_copy(src: Path, dst_dir: Path):
    """Copy a file to dst_dir, avoiding name collisions by appending a random suffix."""
    dst = dst_dir / src.name
    if dst.exists():
        dst = dst.with_name(f"{dst.stem}_{uuid.uuid4().hex[:4]}{dst.suffix}")
    shutil.copy2(src, dst)


# upload & sync
def cb_upload_and_sync(files: List[gr.File]) -> Generator[Tuple[str, list], None, None]:
    """Handle uploaded files: copy to temp, index docs, build agent, and yield status updates.

    Args:
        files: List of uploaded files from the Gradio interface.

    Yields:
        Tuples of (status_message, chat_history).
    """
    # GUARDRAIL FOR EMPTY FILES
    if not files:
        yield "⚠️ No files selected.", []
        return

    # RESETTING TMP_DIR
    sess.cleanup()
    TMP_DIR.mkdir(exist_ok=True)
    sess.__init__()

    # PREPARE UPLOADED FILES
    # copy uploaded files to TMP_DIR
    for f in files:
        _safe_copy(Path(f.name), TMP_DIR)
    yield "📂 Files uploaded. Indexing...", []
    # shutdown DuckDB internals
    try:
        duckdb.shutdown()
    except Exception:
        pass
    # force garbage collection
    gc.collect()

    # INDEXING
    # embedding and indexing uploaded documents
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    _, vector_store = embed_and_index_all_docs(
        data_dir=TMP_DIR,
        db_path=sess.db_path,
        index_path=sess.index_path,
        load_data=True,
    )
    asyncio.set_event_loop(None)
    loop.close()

    # CREATING AGENT
    yield "🤖 Building agent...", []
    # build llm
    llm = init_chat_model("gemini-2.5-flash", model_provider="google_genai")
    # load tools
    retrieve = initialize_retrieve_tool(vector_store)
    sql_tools = initialize_sql_toolkit(llm, sess.db_path)
    # store on-disk state engines to be properly sess.cleanip() later
    for tool in sql_tools:
        eng = getattr(tool, "engine", None) or getattr(
            getattr(tool, "db", None), "engine", None
        )
        if eng:
            sess.sql_engines.append(eng)
    memory = SqliteSaver(sess.hist_db)
    # build agent
    sess.agent = create_react_agent(
        llm, tools=[retrieve, *sql_tools], prompt=system_message, checkpointer=memory
    )
    yield "✅ Sync complete!", []


# chat
def cb_chat(hist: List[dict], msg: str) -> Tuple[List[dict], str]:
    """Handle user messages: stream agent response and update conversation history.

    Args:
        hist: Conversation history as a list of role/content dicts.
        msg: New user message.

    Returns:
        A tuple of (updated_history, clear_input_str).
    """
    if sess.agent is None:
        hist.append(
            {
                "role": "assistant",
                "content": "Please upload files and click 'Upload & Sync' first.",
            }
        )
        return hist, ""
    hist.append({"role": "user", "content": msg})
    messages = [{"role": m["role"], "content": m["content"]} for m in hist]
    reply = ""
    for event in sess.agent.stream(
        {"messages": messages},
        stream_mode="values",
        config={"configurable": {"thread_id": sess.sid}},
    ):
        reply = event["messages"][-1].content
    hist.append({"role": "assistant", "content": reply})
    return hist, ""


# UI
with gr.Blocks(theme="default") as demo:
    gr.Markdown("## Learn-Anything Chatbot Agent - Upload and Ask About Your Files")
    with gr.Row():
        file_box = gr.Files(file_count="multiple", label="Files to upload")
        sync_btn = gr.Button("Upload & Sync")
    status_md = gr.Markdown()
    chatbox = gr.Chatbot(label="Chat", type="messages", height=400)
    user_in = gr.Textbox(placeholder="Ask...", scale=8)

    sync_btn.click(cb_upload_and_sync, [file_box], [status_md, chatbox])
    user_in.submit(cb_chat, [chatbox, user_in], [chatbox, user_in])

if __name__ == "__main__":
    demo.queue().launch()
