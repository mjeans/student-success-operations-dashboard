"""Protect the legacy risk ranking and test the action queue's decision rules."""

from __future__ import annotations

import csv
import io
import sqlite3
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_database import load  # noqa: E402
from run_queries import QUERY_FILES, export_query  # noqa: E402

RISK_SQL = (ROOT / "sql/06_implementation_risk.sql").read_text(encoding="utf-8")
QUEUE_SQL = (ROOT / "sql/08_intervention_action_queue.sql").read_text(encoding="utf-8")
VIEWS_SQL = (ROOT / "sql/01_risk_views.sql").read_text(encoding="utf-8")
FLAGS = (
    "missed_activation_target", "missed_dosage_target", "missed_followup_target",
    "missed_support_sla_target", "missed_fidelity_target", "stale_data_flag",
)
CODES = ("ACTIVATION", "DOSAGE", "FOLLOWUP", "SUPPORT_SLA", "FIDELITY", "DATA_FRESHNESS")
OWNERS = ("School-success lead", "Implementation lead", "Assessment lead",
          "Support operations", "Implementation lead", "Data operations")


def csv_text(rows: list[sqlite3.Row], headers: list[str]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(headers)
    writer.writerows([[row[column] for column in headers] for row in rows])
    return stream.getvalue()


class RiskDriverIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.database = Path(cls.temp_dir.name) / "risk.db"
        load(cls.database)
        cls.connection = sqlite3.connect(cls.database)
        cls.connection.row_factory = sqlite3.Row
        cls.risk = cls.connection.execute(RISK_SQL).fetchall()
        cls.queue = cls.connection.execute(QUEUE_SQL).fetchall()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.connection.close()
        cls.temp_dir.cleanup()

    def test_all_legacy_columns_match_frozen_baseline(self) -> None:
        # Frozen from main at 00f662d; do not regenerate this fixture with new logic.
        reference = ROOT / "tests/fixtures/implementation_risk_baseline.csv"
        with reference.open(newline="", encoding="utf-8") as handle:
            expected = handle.read()
        headers = next(csv.reader(io.StringIO(expected)))
        self.assertEqual(len(self.risk), 32)
        self.assertEqual(csv_text(self.risk, headers), expected)

    def test_six_flags_and_queue_counts_reconcile_for_every_school(self) -> None:
        counts = Counter(row["school_id"] for row in self.queue)
        for row in self.risk:
            with self.subTest(school=row["school_id"]):
                self.assertTrue(all(row[flag] in (0, 1) for flag in FLAGS))
                self.assertEqual(sum(row[flag] for flag in FLAGS), row["risk_score"])
                self.assertEqual(counts[row["school_id"]], row["risk_score"])
                actual = {x["driver_code"] for x in self.queue if x["school_id"] == row["school_id"]}
                expected = {code for flag, code in zip(FLAGS, CODES) if row[flag]}
                self.assertEqual(actual, expected)

    def test_dashboard_high_risk_count_uses_the_same_school_score(self) -> None:
        query = (ROOT / "sql/02_dashboard_kpis.sql").read_text(encoding="utf-8")
        kpi = self.connection.execute(query).fetchone()
        self.assertEqual(kpi["high_risk_schools"], 5)
        self.assertEqual(kpi["high_risk_schools"], sum(r["risk_score"] >= 3 for r in self.risk))

    def test_highest_risk_school_has_five_correctly_routed_actions(self) -> None:
        rows = [row for row in self.queue if row["school_id"] == "S0064"]
        self.assertEqual([row["driver_code"] for row in rows], list(CODES[1:]))
        for row in rows:
            self.assertEqual(row["intervention_priority"], 1)
            self.assertEqual(row["risk_score"], 5)
            self.assertEqual(row["risk_band"], "Critical")
            self.assertEqual(row["students"], 100)
            self.assertEqual(row["training_rate"], 0.5)
            self.assertEqual(row["training_support_needed"], 1)
            self.assertEqual(row["stale_data_flag"], 1)
            self.assertEqual(row["suggested_owner"], dict(zip(CODES, OWNERS))[row["driver_code"]])
            self.assertEqual(row["suggested_review_cadence"], "Twice weekly")

    def test_queue_is_deterministic_and_has_unique_school_driver_keys(self) -> None:
        again = self.connection.execute(QUEUE_SQL).fetchall()
        self.assertEqual([tuple(row) for row in self.queue], [tuple(row) for row in again])
        order = [(r["intervention_priority"], r["school_id"], r["driver_order"]) for r in self.queue]
        self.assertEqual(order, sorted(order))
        keys = [(r["school_id"], r["driver_code"]) for r in self.queue]
        self.assertEqual(len(keys), len(set(keys)))

    def test_each_action_is_explainable_and_actually_misses_its_target(self) -> None:
        for row in self.queue:
            with self.subTest(school=row["school_id"], driver=row["driver_code"]):
                for field in ("driver_label", "recommended_first_action", "suggested_owner", "suggested_review_cadence"):
                    self.assertTrue(row[field])
                self.assertGreater(row["students"], 0)
                self.assertIn(row["metric_unit"], {"proportion", "score", "days"})
                if row["failure_operator"] == "<":
                    self.assertLess(row["observed_value"], row["target_value"])
                else:
                    self.assertEqual(row["failure_operator"], ">")
                    self.assertGreater(row["observed_value"], row["target_value"])

    def test_saved_outputs_match_fresh_queries_byte_for_byte(self) -> None:
        for name, rows in (("06_implementation_risk", self.risk), ("08_intervention_action_queue", self.queue)):
            with self.subTest(output=name):
                actual = csv_text(rows, list(rows[0].keys())).encode("utf-8")
                self.assertEqual(actual, (ROOT / "outputs" / f"{name}.csv").read_bytes())
        self.assertIn("08_intervention_action_queue.sql", QUERY_FILES)


class RiskDriverBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        # Isolate risk logic from the stochastic fixture generator and upstream joins.
        self.connection = sqlite3.connect(":memory:")
        self.addCleanup(self.connection.close)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("""
            CREATE TABLE v_school_operating_metrics (
                school_id TEXT PRIMARY KEY, school_name TEXT, district_id TEXT,
                students INTEGER, activation_rate REAL, dosage_rate REAL,
                followup_rate REAL, support_sla_rate REAL, training_rate REAL,
                fidelity_score REAL, data_refresh_days INTEGER
            )
        """)
        self.connection.executescript(VIEWS_SQL)

    def insert_school(self, school_id: str = "S001", **changes: float) -> None:
        row = dict(school_id=school_id, school_name=f"Test {school_id}", district_id="D001",
                   students=100, activation_rate=0.75, dosage_rate=0.60,
                   followup_rate=0.80, support_sla_rate=0.80, training_rate=0.80,
                   fidelity_score=70.0, data_refresh_days=14)
        row.update(changes)
        self.connection.execute(
            f"INSERT INTO v_school_operating_metrics ({', '.join(row)}) VALUES ({', '.join('?' for _ in row)})",
            tuple(row.values()),
        )

    def test_exact_thresholds_pass_and_empty_queue_keeps_headers(self) -> None:
        self.insert_school()
        row = self.connection.execute(RISK_SQL).fetchone()
        self.assertEqual(row["risk_score"], 0)
        self.assertEqual(row["training_support_needed"], 0)
        self.assertEqual(self.connection.execute(QUEUE_SQL).fetchall(), [])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "queue.csv"
            self.assertEqual(export_query(self.connection, QUEUE_SQL, output), 0)
            with output.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                self.assertIn("driver_code", reader.fieldnames)
                self.assertIn("suggested_owner", reader.fieldnames)
                self.assertEqual(list(reader), [])

    def test_all_six_just_failed_boundaries_keep_unrounded_values(self) -> None:
        self.insert_school(activation_rate=0.749999, dosage_rate=0.599999,
                           followup_rate=0.799999, support_sla_rate=0.799999,
                           fidelity_score=69.999999, data_refresh_days=15)
        risk = self.connection.execute(RISK_SQL).fetchone()
        queue = self.connection.execute(QUEUE_SQL).fetchall()
        self.assertEqual(risk["risk_score"], 6)
        self.assertEqual(risk["risk_band"], "Critical")
        self.assertEqual([r["driver_code"] for r in queue], list(CODES))
        self.assertEqual([r["suggested_owner"] for r in queue], list(OWNERS))
        self.assertEqual([r["target_value"] for r in queue], [0.75, 0.60, 0.80, 0.80, 70, 14])
        self.assertEqual(queue[0]["observed_value"], 0.749999)
        self.assertEqual(risk["activation_rate"], 0.75)  # Rounded display must not affect flags.

    def test_training_only_is_context_not_a_seventh_driver(self) -> None:
        self.insert_school(training_rate=0.50)
        risk = self.connection.execute(RISK_SQL).fetchone()
        self.assertEqual(risk["training_support_needed"], 1)
        self.assertEqual(risk["risk_score"], 0)
        self.assertEqual(risk["risk_band"], "Stable")
        self.assertEqual(self.connection.execute(QUEUE_SQL).fetchall(), [])

    def test_risk_bands_and_suggested_cadences(self) -> None:
        cases = (
            ({"activation_rate": 0.50}, "Stable", "Monthly"),
            ({"activation_rate": 0.50, "dosage_rate": 0.50}, "Watch", "Every two weeks"),
            ({"activation_rate": 0.50, "dosage_rate": 0.50, "followup_rate": 0.50}, "High", "Weekly"),
            ({"activation_rate": 0.50, "dosage_rate": 0.50, "followup_rate": 0.50, "fidelity_score": 60}, "Critical", "Twice weekly"),
        )
        for number, (changes, band, cadence) in enumerate(cases, 1):
            school = f"S00{number}"
            self.insert_school(school, **changes)
            row = self.connection.execute("SELECT * FROM v_school_implementation_risk WHERE school_id = ?", (school,)).fetchone()
            self.assertEqual(row["risk_score"], number)
            self.assertEqual(row["risk_band"], band)
            actions = [r for r in self.connection.execute(QUEUE_SQL) if r["school_id"] == school]
            self.assertTrue(all(r["suggested_review_cadence"] == cadence for r in actions))

    def test_equal_scores_use_activation_then_school_id_for_ranking(self) -> None:
        self.insert_school("S003", dosage_rate=0.50, activation_rate=0.90)
        self.insert_school("S002", dosage_rate=0.50, activation_rate=0.80)
        self.insert_school("S001", dosage_rate=0.50, activation_rate=0.80)
        rows = self.connection.execute(RISK_SQL).fetchall()
        self.assertEqual([r["school_id"] for r in rows], ["S001", "S002", "S003"])
        self.assertEqual([r["intervention_priority"] for r in rows], [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
