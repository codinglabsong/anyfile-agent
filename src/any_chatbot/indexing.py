from dotenv import load_dotenv
from pathlib import Path

from langchain_core.vectorstores import InMemoryVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import DirectoryLoader, UnstructuredFileLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

BASE = Path(__file__).parent.parent.parent
DATA = BASE / "data"


def index_text_docs(
    data_pth: Path = DATA,
):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = InMemoryVectorStore(embeddings)

    # Load the text documents
    loader = DirectoryLoader(
        str(data_pth),
        glob=[
            "**/*.pdf",
            "**/*.docx",
            "**/*.pptx",
            "**/*.md",
            "**/*.html",
            "**/*.txt",
            "**/*.png",
            "**/*.jpg",
            "**/*.jpeg",
            "**/*.tiff",
        ],
        loader_cls=UnstructuredFileLoader,
    )
    print(f"Loading files from {data_pth}")
    docs = loader.load()
    print(f"Loaded {len(docs)} files")

    # Split the texts
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        add_start_index=True,
        separators=["\n\n", "\n", " ", ""],
    )
    all_splits = text_splitter.split_documents(docs)
    print(len(all_splits))

    # index the docs
    ids = vector_store.add_documents(documents=all_splits)
    print(len(ids))

    return embeddings, vector_store
