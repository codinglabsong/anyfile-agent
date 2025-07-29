import os
import re
import logging
import pandas as pd
import duckdb
import shutil
from dotenv import load_dotenv
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import DirectoryLoader, UnstructuredFileLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

load_dotenv()
logger = logging.getLogger(__name__)

BASE = Path(__file__).parent.parent.parent
DATA = BASE / "data"


def load_and_split_text_docs(data_dir):
    text_chunks = []
    globs = [
        "**/*.pdf",
        "**/*.docx",
        "**/*.pptx",
        "**/*.md",
        "**/*.html",
        "**/*.txt",
    ]
    # gaudrail if no files matched
    if not any(next(data_dir.rglob(p), None) for p in globs):
        logger.info(f"No text files found under {data_dir}; skipping.")
        return text_chunks

    logger.info(f"Detected text files under {data_dir}")
    loader = DirectoryLoader(
        str(data_dir),
        glob=globs,
        loader_cls=UnstructuredFileLoader,
    )
    logger.info("Loading text files...")
    docs = loader.load()
    logger.info(f"Loaded {len(docs)} text files")
    # split
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        add_start_index=True,
        separators=["\n\n", "\n", " ", ""],
    )
    text_chunks = text_splitter.split_documents(docs)
    logger.info(f"Split text chunks: {len(text_chunks)}")
    # tag
    for chunk in text_chunks:
        chunk.metadata["source_type"] = "text_chunk"

    return text_chunks


def load_image_docs_as_text(data_dir):
    image_text_docs = []
    globs = [
        "**/*.png",
        "**/*.jpg",
        "**/*.jpeg",
        "**/*.tiff",
    ]
    # gaudrail if no files matched
    if not any(next(data_dir.rglob(p), None) for p in globs):
        logger.info(f"No images found under {data_dir}; skipping.")
        return image_text_docs

    logger.info(f"Detected images under {data_dir}")
    loader = DirectoryLoader(
        str(data_dir),
        glob=globs,
        loader_cls=UnstructuredFileLoader,
    )
    logger.info("Loading images' OCR texts...")
    image_text_docs = loader.load()
    logger.info(f"Loaded {len(image_text_docs)} image files")
    # tag
    for img in image_text_docs:
        img.metadata["source_type"] = "image_text"

    return image_text_docs


def _tbl(name: str) -> str:
    """make a safe SQL table name"""
    name = re.sub(r"[^0-9a-zA-Z_]+", "_", name).strip("_")
    if not name or name[0].isdigit():
        name = f"t_{name}"
    return name.lower()


def build_duckdb_and_summary_cards(
    data_dir: Path,
    db_path: Path,
) -> list[Document]:
    summary_cards = []
    # skip if there are no .csv/.xlsx/.xls files
    patterns = ("*.csv", "*.xlsx", "*.xls")
    if not any(next(data_dir.rglob(p), None) for p in patterns):
        logger.info(f"No CSV or Excel files found under {data_dir}; skipping.")
        return summary_cards
    logger.info(f"Detected CSV/Excel files under {data_dir}")
    logger.info("Loading CSV/Excel files...")
    # ensure the DB folder exists
    os.makedirs(db_path.parent, exist_ok=True)
    # empty the entire DB
    if db_path.exists():
        db_path.unlink()
    # start from an empty fresh DB
    with duckdb.connect(str(db_path)) as con:
        # ingest .csv files into DuckDB (overwrite on rerun)
        for fp in data_dir.rglob("*.csv"):
            table = _tbl(fp.stem)
            fp_sql = fp.as_posix().replace("'", "''")  # escape single quotes
            con.execute(
                f"""
                CREATE OR REPLACE TABLE {table} AS
                SELECT * FROM read_csv_auto('{fp_sql}', header=true)
                """
            )

        # XLSX ingestion via pandas
        for fp in data_dir.rglob("*.xlsx"):
            try:
                xls = pd.ExcelFile(fp)  # lists sheet names
            except Exception as e:
                logger.info(f"Skip {fp.name}: {e}")
                continue

            # One table per sheet
            for sheet in xls.sheet_names:
                try:
                    df = pd.read_excel(fp, sheet_name=sheet)
                except Exception as e:
                    logger.info(f"Skip {fp.name}:{sheet}: {e}")
                    continue

                tmp_name = f"_tmp_{_tbl(fp.stem)}_{_tbl(sheet)}"
                con.register(tmp_name, df)

                table = _tbl(f"{fp.stem}__{sheet}")
                con.execute(
                    f"""
                    CREATE OR REPLACE TABLE {table} AS 
                    SELECT * FROM {tmp_name}"""
                )
                con.unregister(tmp_name)

        for fp in data_dir.rglob("*.xls"):
            # .xls not supported by DuckDB
            logger.info(f"Skip {fp.name}: .xls not supported by DuckDB.")

        # build summary cards from DuckDB
        tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
        for tbl in tables:
            # DESCRIBE/PRAGMA to get columns & types
            schema_rows = con.execute(f"DESCRIBE {tbl}").fetchall()
            col_names = [r[0] for r in schema_rows]
            col_types = [r[1] for r in schema_rows]
            nrows = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            preview_df = con.execute(f"SELECT * FROM {tbl} LIMIT 5").df()

            col_str = ", ".join(f"{n}:{t}" for n, t in zip(col_names, col_types))
            preview_txt = preview_df.to_string(index=False)

            text = (
                f"TABLE CARD — {tbl}\n"
                f"Columns (Length: {len(col_names)}; Format: 'column_name:data_type'): {col_str}\n"
                f"Rows: {nrows}\n\n"
                f"Sample rows (up to 5):\n{preview_txt}\n"
            )

            summary_cards.append(
                Document(
                    page_content=text,
                    metadata={
                        "source_type": "table_summary",
                        "table": tbl,
                        "db_path": str(db_path),
                    },
                )
            )

    return summary_cards


def embed_and_index_all_docs(
    data_dir: Path = DATA,
    db_path: Path = DATA / "generated_db" / "csv_excel_to_db.duckdb",
    index_path: Path = DATA / "generated_db" / "faiss_index",
    load_data: bool = False,
):
    # load embeedings and vector store
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

    if not load_data and index_path.exists():
        # load existing FAISS index
        vector_store = FAISS.load_local(
            index_path, embeddings, allow_dangerous_deserialization=True
        )
        logger.info("Loaded existing FAISS index and database.")
    else:
        # delete old FAISS index if it exists
        if index_path.exists():
            logger.info("Reseting previous index...")
            shutil.rmtree(index_path)

        # LOAD AND SPLIT TEXT DOCS
        text_chunks = load_and_split_text_docs(data_dir)
        # LOAD IMAGES (OCR converts image -> text)
        image_text_docs = load_image_docs_as_text(data_dir)
        # LOAD AND SPLIT CSV/EXCEL DOCS
        summary_cards = build_duckdb_and_summary_cards(data_dir, db_path)

        # vector_store.add_documents(text_chunks + image_text_docs + summary_cards)
        vector_store = FAISS.from_documents(
            text_chunks + image_text_docs + summary_cards, embeddings
        )
        vector_store.save_local(index_path)
        logger.info("Built and saved new FAISS index.")

    return embeddings, vector_store
