"""Regression tests for the reproducible dashboard pipeline."""

from __future__ import annotations

import csv
import sqlite3
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import sys

sys.path.insert(0, str(ROOT / "scripts"))

from build_database import load  # noqa: E402


class DashboardPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.database = Path(cls.temp_dir.name) / "test.db"
        load(cls.database)
        cls.connection = sqlite3.connect(cls.database)
        cls.connection.row_factory = sqlite3.Row

    @classmethod
    def tearDownClass(cls) -> None:
        cls.connection.close()
        cls.temp_dir.cleanup()

    def test_expected_table_grain(self) -> None:
        students = self.connection.execute(
            "SELECT COUNT(*) FROM dim_student"
        ).fetchone()[0]
        student_months = self.connection.execute(
            "SELECT COUNT(*) FROM fact_engagement_monthly"
        ).fetchone()[0]
        months_per_student = self.connection.execute(
            """
            SELECT MIN(n), MAX(n)
            FROM (
                SELECT student_id, COUNT(*) AS n
                FROM fact_engagement_monthly
                GROUP BY student_id
            )
            """
        ).fetchone()
        self.assertEqual(students, 3200)
        self.assertEqual(student_months, 28800)
        self.assertEqual(tuple(months_per_student), (9, 9))

    def test_foreign_keys_are_valid(self) -> None:
        failures = self.connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()
        self.assertEqual(failures, [])

    def test_kpis_reconcile_to_student_summary(self) -> None:
        query = (ROOT / "sql" / "02_dashboard_kpis.sql").read_text()
        kpi = self.connection.execute(query).fetchone()
        self.assertEqual(kpi["eligible_students"], 3200)
        self.assertEqual(kpi["activated_students"], 2946)
        self.assertAlmostEqual(kpi["activation_rate"], 0.9206)
        self.assertGreater(kpi["avg_score_change"], 0)
        self.assertLessEqual(kpi["followup_completion_rate"], 1)

    def test_priority_ranking_has_actionable_variation(self) -> None:
        query = (ROOT / "sql" / "06_implementation_risk.sql").read_text()
        rows = self.connection.execute(query).fetchall()
        self.assertEqual(len(rows), 32)
        self.assertEqual(rows[0]["intervention_priority"], 1)
        self.assertIn(rows[0]["risk_band"], {"Critical", "High"})
        self.assertGreater(rows[0]["risk_score"], rows[-1]["risk_score"])

    def test_committed_quality_output_passes(self) -> None:
        with (ROOT / "outputs" / "07_data_quality.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 7)
        self.assertTrue(all(row["status"] == "PASS" for row in rows))
        self.assertTrue(all(int(row["failing_records"]) == 0 for row in rows))


if __name__ == "__main__":
    unittest.main()
