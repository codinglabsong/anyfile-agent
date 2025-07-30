"""Unit tests for Anyfile-Agent tools: initialize_retrieve_tool and is_safe_sql."""

from any_chatbot.tools import initialize_retrieve_tool, is_safe_sql
from langchain.schema import Document


class DummyStore:
    """A fake vector store capturing similarity_search calls for testing."""

    def __init__(self):
        self.calls = []

    def similarity_search(
        self, query: str, k: int = 5, filter: dict | None = None
    ) -> list[Document]:
        """Record the query parameters and return a dummy Document list."""
        self.calls.append((query, k, filter))
        return [Document(page_content="foo", metadata=filter)]


def test_initialize_retrieve_tool_invokes_vectorstore() -> None:
    """Test that the retrieve tool calls vector_store.similarity_search with correct args and returns expected output."""
    store = DummyStore()
    retrieve = initialize_retrieve_tool(store)
    text, docs = retrieve.func("hello", "text_chunk")

    assert store.calls == [("hello", 5, {"source_type": "text_chunk"})]
    assert docs[0].metadata["source_type"] == "text_chunk"
    assert "foo" in text


def test_is_safe_sql() -> None:
    """Test that is_safe_sql allows only SELECT/PRAGMA and rejects DML/DDL queries."""
    assert is_safe_sql("SELECT * FROM tbl")
    assert is_safe_sql("SELECT updated_at FROM tbl")
    assert not is_safe_sql("DROP TABLE tbl")
    assert not is_safe_sql("UPDATE tbl SET a=1")
