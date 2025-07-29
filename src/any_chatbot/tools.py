from typing import Tuple, List
from pathlib import Path

from langchain_core.tools import tool
from langchain.vectorstores.base import VectorStore
from langchain.schema import Document
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit

BASE = Path(__file__).parent.parent.parent
DATA = BASE / "data"


def initialize_retrieve_tool(vector_store: VectorStore):
    @tool(
        description="Retrieve information related to a query",
        response_format="content_and_artifact",
    )
    def retrieve(query: str) -> Tuple[str, List[Document]]:
        retrieved_docs = vector_store.similarity_search(query, k=3)
        serialized = "\n\n".join(
            (f"Source: {doc.metadata}\nContent: {doc.page_content}")
            for doc in retrieved_docs
        )
        return serialized, retrieved_docs

    return retrieve


def initialize_sql_toolkit(
    llm,
    db_path: Path = DATA / "csv_excel_to_db" / "my_data.duckdb",
):
    db = SQLDatabase.from_uri(f"duckdb:///{db_path}")
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    tools = toolkit.get_tools()
    return tools
