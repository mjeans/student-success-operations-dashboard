"""Source reconciliation, accessibility, determinism and failure-path checks."""
from __future__ import annotations
import csv
import importlib.util
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from shutil import copytree

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("render_previews", ROOT / "scripts/render_previews.py")
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)


class TestPreviews(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        copytree(ROOT / "outputs", self.root / "outputs")
        copytree(ROOT / "powerbi", self.root / "powerbi")

    def edit(self, filename, change):
        path = self.root / "outputs" / filename
        with path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            fields, records = reader.fieldnames, list(reader)
        change(records)
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(records)

    def test_svg_is_parseable_and_accessible(self):
        for name, source in preview.render(self.root).items():
            with self.subTest(name=name):
                svg = ET.fromstring(source)
                self.assertEqual(svg.attrib["role"], "img")
                self.assertEqual(svg.attrib["viewBox"], "0 0 1600 1120")
                self.assertIsNotNone(svg.find("{http://www.w3.org/2000/svg}title"))
                self.assertIsNotNone(svg.find("{http://www.w3.org/2000/svg}desc"))
                self.assertNotIn("<script", source)
                self.assertNotIn("<foreignObject", source)

    def test_output_is_deterministic(self):
        self.assertEqual(preview.render(self.root), preview.render(self.root))

    def test_kpi_labels_follow_input(self):
        self.edit("02_dashboard_kpis.csv", lambda r: r[0].update(activation_rate="0.9123"))
        self.assertIn("91.2%", preview.render(self.root)["executive-dashboard.svg"])

    def test_plot_labels_follow_monthly_input(self):
        self.edit("03_monthly_engagement.csv", lambda r: r[-1].update(active_rate="0.831"))
        result = preview.render(self.root)
        self.assertIn("83.1%", result["executive-dashboard.svg"])
        self.assertIn("83.1%", result["outcomes-participation.svg"])

    def test_unknown_action_school_fails(self):
        self.edit("08_intervention_action_queue.csv", lambda r: r[0].update(school_id="UNKNOWN"))
        with self.assertRaisesRegex(ValueError, "unknown school"):
            preview.render(self.root)

    def test_duplicate_action_fails(self):
        self.edit("08_intervention_action_queue.csv", lambda r: r.append(dict(r[0])))
        with self.assertRaisesRegex(ValueError, "Duplicate school-driver"):
            preview.render(self.root)

    def test_risk_reconciliation_fails_closed(self):
        self.edit("06_implementation_risk.csv", lambda r: r[0].update(risk_score="6"))
        with self.assertRaisesRegex(ValueError, "Risk flags do not reconcile"):
            preview.render(self.root)

    def test_invalid_rate_fails(self):
        self.edit("03_monthly_engagement.csv", lambda r: r[0].update(active_rate="1.2"))
        with self.assertRaisesRegex(ValueError, "Rate outside"):
            preview.render(self.root)

    def test_text_is_escaped(self):
        self.edit("06_implementation_risk.csv", lambda r: r[0].update(school_name="A & B <School>"))
        source = preview.render(self.root)["implementation-monitor.svg"]
        self.assertIn("A &amp; B &lt;School&gt;", source)
        ET.fromstring(source)

    def test_empty_action_queue_is_supported(self):
        self.edit("08_intervention_action_queue.csv", lambda r: r.clear())
        def clear_risk(records):
            for row in records:
                row.update({flag: "0" for flag in preview.FLAGS})
                row.update(risk_score="0", risk_band="Stable")
        self.edit("06_implementation_risk.csv", clear_risk)
        self.edit("02_dashboard_kpis.csv", lambda r: r[0].update(high_risk_schools="0"))
        self.assertIn("No missed scored thresholds", preview.render(self.root)["implementation-monitor.svg"])

    def test_half_up_percentage_rounding(self):
        self.assertEqual(preview.pct("0.8525"), "85.3%")
        self.assertEqual(preview.pct("0.4255"), "42.6%")

    def test_check_mode_detects_missing_and_stale_previews(self):
        command = [sys.executable, str(ROOT / "scripts/render_previews.py"), "--root", str(self.root)]
        result = subprocess.run(command + ["--check"], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Stale previews", result.stderr)
        subprocess.run(command, check=True, capture_output=True)
        self.assertEqual(subprocess.run(command + ["--check"], capture_output=True).returncode, 0)
        path = self.root / "assets" / preview.NAMES[0]
        path.write_text("stale", encoding="utf-8")
        self.assertNotEqual(subprocess.run(command + ["--check"], capture_output=True).returncode, 0)


if __name__ == "__main__":
    unittest.main()
