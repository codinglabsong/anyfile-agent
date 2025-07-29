from any_chatbot.indexing import _tbl, build_duckdb_and_summary_cards
from pathlib import Path


def test_tbl_cleaning():
    assert _tbl("my table!") == "my_table"
    assert _tbl("123name") == "t_123name"
    assert _tbl("##$") == "t_"


def test_build_duckdb_and_summary_cards_csv(tmp_path: Path):
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("a,b\n1,2\n3,4")
    db_path = tmp_path / "db.duckdb"

    cards = build_duckdb_and_summary_cards(tmp_path, db_path)
    assert len(cards) == 1

    card = cards[0]
    assert card.metadata["source_type"] == "table_summary"
    assert card.metadata["db_path"] == str(db_path)
    assert card.metadata["table"] == "data"
    assert "TABLE CARD" in card.page_content
    assert "a:BIGINT" in card.page_content
