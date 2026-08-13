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
]


def run(database_path: Path = DEFAULT_DATABASE) -> None:
    if not database_path.exists():
        load(database_path)
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        for filename in QUERY_FILES:
            rows = connection.execute((SQL / filename).read_text()).fetchall()
            output = OUTPUTS / filename.replace(".sql", ".csv")
            with output.open("w", newline="", encoding="utf-8") as handle:
                if rows:
                    writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
                    writer.writeheader()
                    writer.writerows(dict(row) for row in rows)
            print(f"{filename}: {len(rows)} rows -> {output.relative_to(ROOT)}")


if __name__ == "__main__":
    run()
