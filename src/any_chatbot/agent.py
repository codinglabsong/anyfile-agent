import argparse
import random
import sqlite3
from pathlib import Path

from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain.chat_models import init_chat_model

from any_chatbot.indexing import embed_and_index_all_docs
from any_chatbot.tools import initialize_retrieve_tool, initialize_sql_toolkit
from any_chatbot.prompts import system_message
from any_chatbot.utils import load_environ_vars

BASE = Path(__file__).parent.parent.parent


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for training and evaluation."""
    p = argparse.ArgumentParser()

    p.add_argument(
        "--ask",
        type=str,
        default=(
            "What kinds (images, text docs, or excel sheets) are available in the documents I have provided to you? Use the functional call to retrieve information for each type first.\n\n"
            # "What colums does the excel have? once you found the answer, tell me there types too.\n\n"
            # "Once you have that answer, I want you to calculate the median for each column.\n\n"
            "When you don't know while files the user is talking about, use the functional call to retrieve what data is available with a general prompt.\n\n"
            "You can refine your semantic search queries and try multiple times with different queries until you resonably determine the data is not available on the given documents.\n\n"
            "Base your answers only on the retrieved information thorugh the functional call you have. You can retreive MULTIPLE TIMES"
        ),
        help="Your input to agent",
    )
    p.add_argument(
        "--load_data",
        action="store_true",
        help="If set, (re)load and process all data files, rebuilding FAISS and DuckDB. If not set, just use existing data.",
    )
    p.add_argument(
        "--thread_id",
        type=str,
        default=str(random.random()),
        help="Your conversation history ID. Different IDs save different chat histories with agent",
    )
    p.add_argument(
        "--data_dir",
        type=Path,
        default=BASE / "data",
        help="Path to data dir where your files are uploaded",
    )
    p.add_argument(
        "--database_dir",
        type=Path,
        default=BASE / "data" / "generated_db" / "csv_excel_to_db.duckdb",
        help="Path to database dir where the sql version of CSV/EXCEL files are stored",
    )
    return p.parse_args()


def main() -> None:
    cfg = parse_args()
    load_environ_vars()
    # INDEXING
    _, vector_store = embed_and_index_all_docs(
        cfg.data_dir, cfg.database_dir, load_data=cfg.load_data
    )

    # BUILD LLM
    llm = init_chat_model("gemini-2.0-flash", model_provider="google_genai")

    # LOAD TOOLS
    retrieve_tool = initialize_retrieve_tool(vector_store)
    sql_tools = initialize_sql_toolkit(llm, cfg.database_dir)

    # BUILD AGENT
    # build persistent checkpointer
    con = sqlite3.connect(
        cfg.data_dir / "generated_db" / "agent_history.db", check_same_thread=False
    )
    memory = SqliteSaver(con)
    # build agent
    agent_executor = create_react_agent(
        llm, [retrieve_tool, *sql_tools], prompt=system_message, checkpointer=memory
    )

    # PROMPT
    # specify an ID for the thread
    config = {"configurable": {"thread_id": cfg.thread_id}}
    # stream conversation
    for event in agent_executor.stream(
        {"messages": [{"role": "user", "content": cfg.ask}]},
        stream_mode="values",
        config=config,
    ):
        event["messages"][-1].pretty_print()


if __name__ == "__main__":
    main()
