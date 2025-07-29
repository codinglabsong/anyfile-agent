from typing import Tuple, List, Literal
from pathlib import Path
from enum import Enum
from typing_extensions import Annotated

from langchain_core.tools import tool
from langchain.vectorstores.base import VectorStore
from langchain.schema import Document
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit

BASE = Path(__file__).parent.parent.parent
DATA = BASE / "data"


class SourceTag(str, Enum):
    TEXT = "text_chunk"
    IMAGE = "image_text"
    TABLE = "table_summary"


def initialize_retrieve_tool(vector_store: VectorStore):
    @tool(
        description=(
            """
        Semantic search over your docs. Valid tags are
        "text_chunk", "image_text", and "table_summary".
        """
        ),
        response_format="content_and_artifact",
    )
    def retrieve(
        query: str,
        tag: Annotated[
            Literal["text_chunk", "image_text", "table_summary"],
            """
            Select between
            "text_chunk" (chunks over pdf, word, txt, etc),
            "image_text" (texts extracted through OCR per image), or
            "table_summary" (summary cards of excel sheets or csv files)
            """,
        ],
    ) -> Tuple[str, List[Document]]:
        """
        Args:
          query: keywords or natural-language question.
          tag: which subset to search ("text_chunk", "image_text", "table_summary").
        Returns:
          (summary_string, list_of_Documents)
        """
        retrieved_docs = vector_store.similarity_search(
            query,
            filter={"source_type": tag},
            k=2,
        )
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
