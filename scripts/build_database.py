"""Load generated CSV tables into a deterministic SQLite database."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "build" / "generated"
SQL = ROOT / "sql"
DEFAULT_DATABASE = ROOT / "build" / "student_success.db"

TABLE_FILES = {
    "dim_district": "dim_district.csv",
    "dim_school": "dim_school.csv",
    "dim_student": "dim_student.csv",
    "fact_engagement_monthly": "fact_engagement_monthly.csv",
    "fact_assessment": "fact_assessment.csv",
    "fact_support_ticket": "fact_support_ticket.csv",
    "fact_implementation": "fact_implementation.csv",
}


def load(database_path: Path = DEFAULT_DATABASE) -> Path:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    if database_path.exists():
        database_path.unlink()

    with sqlite3.connect(database_path) as connection:
        connection.executescript((SQL / "00_schema.sql").read_text())
        for table, filename in TABLE_FILES.items():
            with (DATA / filename).open(newline="", encoding="utf-8") as handle:
                reader = csv.reader(handle)
                headers = next(reader)
                placeholders = ", ".join("?" for _ in headers)
                columns = ", ".join(headers)
                connection.executemany(
                    f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
                    reader,
                )
        connection.executescript((SQL / "01_metric_views.sql").read_text())
        connection.commit()
    return database_path


if __name__ == "__main__":
    path = load()
    print(f"Built {path.relative_to(ROOT)}")
