"""Evidence failures must remain failures even when someone edits a status flag."""
import copy
import unittest

from content_ledger import build, inspect, safe_path


class ContentLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = build()

    def test_real_baseline_has_no_false_acceptance(self):
        report = inspect(self.ledger, scan=False)
        self.assertTrue(report["validation_passed"], report["errors"])
        self.assertFalse(report["content_acceptance_passed"])
        self.assertEqual(self.ledger["baseline"]["cinematics"]["unique_file_hashes"], 59)
        self.assertEqual(self.ledger["baseline"]["pcm_music"]["unique_file_hashes"], 14)
        self.assertIsNone(self.ledger["baseline"]["independent_family_semantics_count"])

    def test_accepted_flag_without_qa_does_not_close_reference(self):
        ledger = copy.deepcopy(self.ledger)
        row = next(r for r in ledger["entries"] if r["category"] == "cinematic")
        row["status"] = "accepted"
        report = inspect(ledger, scan=False)
        self.assertFalse(report["validation_passed"])
        self.assertTrue(any("Accepted row lacks" in error for error in report["errors"]))

    def test_removing_unmapped_family_is_detected(self):
        ledger = copy.deepcopy(self.ledger)
        row = next(r for r in ledger["entries"] if r["category"] == "family_catalog")
        ledger["entries"].remove(row)
        self.assertTrue(any("Baseline lost/duplicated" in e for e in inspect(ledger, scan=False)["errors"]))

    def test_duplicate_id_cannot_inflate_coverage(self):
        ledger = copy.deepcopy(self.ledger)
        ledger["entries"].append(copy.deepcopy(ledger["entries"][0]))
        self.assertIn("Duplicate semantic row IDs", inspect(ledger, scan=False)["errors"])

    def test_unrecognized_replacement_fails(self):
        ledger = copy.deepcopy(self.ledger)
        ledger["entries"][0]["replacement_ids"] = ["imaginary-new-asset"]
        self.assertTrue(any("Missing production mapping" in e for e in inspect(ledger, scan=False)["errors"]))

    def test_changed_bound_hash_is_rejected(self):
        ledger = copy.deepcopy(self.ledger)
        ledger["production_assets"][0]["production_paths"][0]["sha256"] = "0" * 64
        self.assertTrue(any("Missing/stale bound file" in e for e in inspect(ledger, scan=False)["errors"]))

    def test_source_hash_in_production_is_rejected(self):
        ledger = copy.deepcopy(self.ledger)
        ledger["production_assets"][0]["production_paths"][0]["sha256"] = ledger["reference_source_files"][0]["sha256"]
        self.assertTrue(any("Direct source byte copy" in e for e in inspect(ledger, scan=False)["errors"]))

    def test_3d_asset_requires_concept(self):
        ledger = copy.deepcopy(self.ledger)
        ledger["production_assets"][0]["concept_paths"] = []
        self.assertTrue(any("Missing concept" in e for e in inspect(ledger, scan=False)["errors"]))

    def test_path_traversal_rejected(self):
        with self.assertRaises(ValueError):
            safe_path("../../outside-source.wav")


if __name__ == "__main__":
    unittest.main()
