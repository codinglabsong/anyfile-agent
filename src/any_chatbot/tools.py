from typing import Tuple, List
from langchain_core.tools import tool
from langchain.vectorstores.base import VectorStore
from langchain.schema import Document


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
