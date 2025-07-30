from setuptools import setup, find_packages

setup(
    name="any_chatbot",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "ipykernel",
        "langchain",
        "langchain-community",
        "langchain-google-genai",
        "langchain-pinecone",
        "pypdf",
        "python-dotenv",
        "pinecone",
        "langgraph",
        "unstructured[pdf,docx,pptx,md,image]",
        "duckdb",
        "duckdb-engine",
        "openpyxl",
        "faiss-cpu",
        "langgraph-checkpoint-sqlite",
        "gradio",
    ],
)
