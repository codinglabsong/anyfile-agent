# Learn Anything AI Chatbot

Learn Anything AI Chatbot lets you query your own documents using a language model. It indexes a folder of files, converts CSV and Excel sheets into a DuckDB database, and performs semantic search with Google Gemini embeddings. An interactive agent built with LangGraph combines retrieval and SQL queries so you can "chat" with your data.

## Features
- **Multi-format ingestion** – PDFs, Word docs, PowerPoint, Markdown, HTML, and plain text are split into searchable chunks. Images are processed through OCR so their text is also indexed.
- **Data summarization** – CSV and Excel files are loaded into DuckDB tables. Summary cards for each table are added to the vector index.
- **Embeddings & retrieval** – Documents are embedded with `GoogleGenerativeAIEmbeddings` and stored in a FAISS index for fast semantic search.
- **SQL integration** – The agent can issue DuckDB queries over your uploaded spreadsheets. Only `SELECT` and `PRAGMA` statements are allowed for safety.
- **Persistent conversations** – The ReAct agent from LangGraph saves its history to SQLite so you can resume chats.


## Installation
1. Install system packages needed for OCR (first time only):
   ```bash
   sudo apt update
   sudo apt install -y tesseract-ocr libtesseract-dev
   ```
2. Install the Python package and dependencies:
   ```bash
   pip install -e .
   pip install -r requirements-dev.txt  # optional dev tools
   ```

## Usage
1. Place the documents you want to search under `data/` directory.
2. Run the agent. The first run may take a while as it loads and indexes the files:
   ```bash
   bash scripts/run_agent.sh --ask "What kinds of files have I provided?" --load_data
   ```
3. For later sessions, omit `--load_data` to reuse the existing FAISS index and DuckDB database. If you have added more documents under `data/`, please load them again using `--load_data` for the first run.

## Supported File Types
- Text documents: PDF, DOCX, PPTX, Markdown, HTML, TXT
- Images: PNG, JPG, JPEG, TIFF (processed via OCR)
- Spreadsheets: CSV, XLSX

## Testing
Run formatting checks and unit tests with:
```bash
pre-commit run --all-files
pytest
```

## Repository Structure
- `src/any_chatbot/` – core modules for indexing, tools, and agent
- `scripts/` – helper script to launch the agent
- `notebooks/` – example notebooks for experiments
- `tests/` – unit tests for the indexing and tool utilities

## Requirements
- Python 3.10+
- A Google Gemini API key (`GOOGLE_API_KEY` environment variable)

## Contributing
Contributions are welcome! Feel free to open issues or pull requests.

## License
This project is licensed under the MIT License.