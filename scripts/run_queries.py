"""Run portfolio SQL and save stable CSV outputs for review."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from build_database import DEFAULT_DATABASE, ROOT, SQL, load

OUTPUTS = ROOT / "outputs"
QUERY_FILES = [
    "02_dashboard_kpis.sql",
    "03_monthly_engagement.sql",
    "04_district_performance.sql",
    "05_segment_outcomes.sql",
    "06_implementation_risk.sql",
    "07_data_quality.sql",
    "08_intervention_action_queue.sql",
]


def export_query(connection: sqlite3.Connection, query: str, output: Path) -> int:
    """Preserve headers even when a SELECT returns no action rows."""
    cursor = connection.execute(query)
    if cursor.description is None:
        raise ValueError("Expected a query that returns named columns.")
    headers = [column[0] for column in cursor.description]
    rows = cursor.fetchall()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)
    return len(rows)


def run(database_path: Path = DEFAULT_DATABASE) -> None:
    if not database_path.exists():
        load(database_path)
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        for filename in QUERY_FILES:
            output = OUTPUTS / filename.replace(".sql", ".csv")
            count = export_query(
                connection, (SQL / filename).read_text(encoding="utf-8"), output
            )
            print(f"{filename}: {count} rows -> {output.relative_to(ROOT)}")


if __name__ == "__main__":
    run()
