"""Utility helpers that turn a FAISS vector store or DuckDB database into LangChain tools usable by the agent."""

from typing import Tuple, List, Literal
from pathlib import Path

from langchain_core.tools import tool
from langchain.vectorstores.base import VectorStore
from langchain.schema import Document
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit

BASE = Path(__file__).parent.parent.parent
DATA = BASE / "data"


def initialize_retrieve_tool(vector_store: VectorStore):
    """Return a LangChain `@tool` that performs semantic search.

    Args:
        vector_store: A pre-built FAISS (or compatible) vector store.

    Returns:
        The decorated `retrieve` function ready to be passed into an agent.
    """

    @tool(
        description=(
            """
            Semantic search over your docs. ONLY valid tags are
            "text_chunk" (chunks over pdf, word, txt, etc),
            "image_text" (texts extracted through OCR per image), or
            "table_summary" (summary cards of excel sheets or csv files)
            """
        ),
        response_format="content_and_artifact",
    )
    def retrieve(
        query: str, tag: Literal["text_chunk", "image_text", "table_summary"]
    ) -> Tuple[str, List[Document]]:
        retrieved_docs = vector_store.similarity_search(
            query,
            k=5,
            filter={"source_type": tag},
        )
        serialized = "\n\n".join(
            (f"Source: {doc.metadata}\nContent: {doc.page_content}")
            for doc in retrieved_docs
        )
        return serialized, retrieved_docs

    return retrieve


def is_safe_sql(query: str) -> bool:
    """Reject queries that contain DML/DDL keywords.

    Args:
        query: Arbitrary SQL supplied by the LLM.

    Returns:
        True if the query looks safe (SELECT/PRAGMA), else False.
    """
    forbidden = ["insert", "update", "delete", "drop", "alter", "create", "replace"]
    # Make sure to only block whole words (e.i., don't block 'updated_at')
    return not any(f" {word} " in f" {query.lower()} " for word in forbidden)


def initialize_sql_toolkit(
    llm,
    db_path: Path = DATA / "generated_db" / "csv_excel_to_db.duckdb",
):
    """Wrap DuckDB in a LangChain `SQLDatabaseToolkit` with a safety filter.

    Args:
        llm: The chat model that will power SQL-aware tools.
        db_path: Location of the DuckDB file created during indexing.

    Returns:
        A list of LangChain tools for schema look-up and SELECT queries.
    """
    db = SQLDatabase.from_uri(f"duckdb:///{db_path}")

    # Monkey-path the run method to include safety filter
    original_run = db.run

    def safe_run(query: str, *args, **kwargs):
        if not is_safe_sql(query):
            return "Query blocked: Only SELECT/PRAGMA queries are allowed."
        return original_run(query, *args, **kwargs)

    db.run = safe_run

    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    tools = toolkit.get_tools()
    return tools
