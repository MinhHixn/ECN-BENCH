"""Numerical and data-contract regression checks for the paper reanalysis."""
import unittest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from paper_analysis import brier, ensemble, hit, interval, near_uniform, validate_row


def record(probabilities, truth="yes", evidence="same"):
    return {
        "event_id": "test", "condition": "B", "ground_truth": truth,
        "probabilities": probabilities, "evidence_text": evidence,
        "question": "A fixed question", "options": list(probabilities),
    }


class PaperAnalysisTests(unittest.TestCase):
    def test_uniform_can_outscore_confident_error(self):
        uniform = record({"yes": 0.5, "no": 0.5})
        wrong = record({"yes": 0.0, "no": 1.0})
        self.assertEqual(brier(uniform), 0.5)
        self.assertEqual(brier(wrong), 2.0)
        self.assertEqual(hit(uniform), 0.5)
        self.assertTrue(near_uniform(uniform))

    def test_ensembling_identity(self):
        rows = [record({"yes": 0.9, "no": 0.1}), record({"yes": 0.3, "no": 0.7})]
        combined = ensemble(rows)
        spread = sum(sum((row["probabilities"][option] - combined["probabilities"][option]) ** 2
                         for option in combined["probabilities"]) for row in rows) / len(rows)
        self.assertAlmostEqual(sum(brier(row) for row in rows) / len(rows),
                               brier(combined) + spread)

    def test_repeating_campaign_measurements_does_not_narrow_event_interval(self):
        events = {"one": [0.1, 0.3], "two": [-0.3, 0.1], "three": [0.8, 1.0]}
        copied = {event: values * 8 for event, values in events.items()}
        self.assertEqual(interval(events, draws=5000), interval(copied, draws=5000))

    def test_equal_event_estimand_survives_unequal_cluster_sizes(self):
        events = {"one": [1.0], "two": [1.0], "three": [-1.0]}
        result = interval(events, {"one": "shared", "two": "shared"}, draws=5000)
        self.assertAlmostEqual(result["mean"], 1.0 / 3)
        self.assertEqual(result["n_clusters"], 2)
        self.assertEqual(result["n_events"], 3)

    def test_evidence_mismatch_prevents_averaging(self):
        with self.assertRaisesRegex(ValueError, "different evidence"):
            ensemble([record({"yes": 0.5, "no": 0.5}),
                      record({"yes": 0.6, "no": 0.4}, evidence="changed")])

    def test_invalid_vectors_fail_before_scoring(self):
        for probabilities in ({"yes": float("nan"), "no": 0.5},
                              {"yes": 0.3, "no": 0.3},
                              {"yes": -0.1, "no": 1.1}):
            with self.subTest(probabilities=probabilities):
                with self.assertRaises(ValueError):
                    validate_row(record(probabilities))

    def test_tie_excluding_truth_is_zero(self):
        self.assertEqual(hit(record({"yes": 0.2, "one": 0.4, "two": 0.4})), 0.0)


if __name__ == "__main__":
    unittest.main()

