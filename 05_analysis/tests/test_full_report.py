"""Integration and reporting contracts for the restored full report."""
import hashlib
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import paper_analysis as audit
from paper_full_analysis import extended_results, tex


class FullReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = audit.default_root()
        cls.result = extended_results(cls.root)

    def test_known_question_collision_is_explicit(self):
        mismatches = self.result["question_mismatches"]
        self.assertEqual(len(mismatches), 3)
        self.assertEqual({row["model"] for row in mismatches}, {"Qwen2.5-14B"})
        self.assertEqual({row["event"] for row in mismatches}, {"T1"})
        self.assertEqual({row["condition"] for row in mismatches}, set("ABC"))
        self.assertNotIn("T1", self.result["aligned_events"])
        self.assertEqual(len(self.result["aligned_events"]), 29)

    def test_no_stored_event_rows_are_deleted(self):
        self.assertEqual(len(self.result["catalog"]), 30)
        self.assertEqual(len(self.result["units"]), 4)
        for units in self.result["units"].values():
            self.assertEqual(len(units), 90)
            self.assertIn("T1/B", units)

    def test_confidence_bins_partition_aligned_events(self):
        for bins in self.result["modal_calibration_bins"].values():
            self.assertEqual(sum(row["count"] for row in bins), 29)
            for row in bins:
                if row["count"]:
                    self.assertLessEqual(row["lower"], row["mean_confidence"])
                    self.assertLessEqual(row["mean_confidence"], row["upper"])
                    self.assertLessEqual(0, row["tie_aware_accuracy"])
                    self.assertLessEqual(row["tie_aware_accuracy"], 1)

    def test_source_bytes_are_unchanged_by_reanalysis(self):
        for name, digest in self.result["input_sha256"].items():
            self.assertEqual(hashlib.sha256((self.root / name).read_bytes()).hexdigest(), digest)

    def test_tex_escaping_and_punctuation(self):
        self.assertEqual(tex("A&B_1 – 2%"), r"A\&B\_1 -- 2\%")


if __name__ == "__main__":
    unittest.main()

