from __future__ import annotations

import contextlib
import io
import json
import unittest
from pathlib import Path

from mdq.cli import main

ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def test_json_output_contains_metrics_and_findings(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main([str(ROOT / "data" / "sample_ohlcv.csv"), "--format", "json"])
        report = json.loads(output.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(report["metrics"]["record_count"], 13)
        self.assertGreater(report["metrics"]["error_count"], 0)

    def test_strict_mode_returns_nonzero_for_errors(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            result = main([str(ROOT / "data" / "sample_ohlcv.csv"), "--strict"])
        self.assertEqual(result, 1)


if __name__ == "__main__":
    unittest.main()
