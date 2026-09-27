"""Regression against preserved real MCP responses, including isError=false rejection."""
import json
import unittest
from pathlib import Path
from result_status import execution_failure

ROOT = Path(__file__).resolve().parents[2]


class ExecutionReceiptTests(unittest.TestCase):
    def test_real_safe_mode_rejection_is_not_success(self):
        receipt = json.loads((ROOT / "docs/p08/golden/recovery/mpfb-setup-mcp.json").read_text(encoding="utf-8-sig"))
        self.assertFalse(receipt["result"]["isError"])
        self.assertIsNotNone(execution_failure(receipt["result"], receipt["tool"]))

    def test_real_successful_export_remains_success(self):
        receipt = json.loads((ROOT / "docs/p08/golden/apex/creation-final-mcp.json").read_text(encoding="utf-8-sig"))
        self.assertIsNone(execution_failure(receipt["result"], receipt["tool"]))


if __name__ == "__main__":
    unittest.main()
