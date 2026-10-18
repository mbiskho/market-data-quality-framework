from __future__ import annotations

import io
import unittest
from pathlib import Path

from mdq import validate_csv

ROOT = Path(__file__).resolve().parents[1]


class ValidationTests(unittest.TestCase):
    def test_sample_covers_gaps_duplicates_missing_and_ohlc_errors(self) -> None:
        report = validate_csv(ROOT / "data" / "sample_ohlcv.csv")
        codes = {issue.code for issue in report.issues}
        self.assertEqual(report.record_count, 13)
        self.assertEqual(report.parsed_count, 12)
        self.assertEqual(report.complete_row_count, 12)
        self.assertIn("timestamp_gap", codes)
        self.assertIn("duplicate_timestamp", codes)
        self.assertIn("missing_value", codes)
        self.assertIn("ohlc_inconsistent", codes)
        self.assertLess(report.quality_score, 100)

    def test_valid_aware_and_naive_timestamps_are_normalized_to_utc(self) -> None:
        csv_data = io.StringIO(
            "timestamp,open,high,low,close,volume\n"
            "2026-01-01T09:30:00,10,11,9,10.5,100\n"
            "2026-01-01T09:31:00+00:00,10.5,11,10,10.8,120\n"
        )
        report = validate_csv(csv_data)
        self.assertEqual(report.valid_row_count, 2)
        self.assertEqual(report.bars[0].timestamp.tzinfo, report.bars[1].timestamp.tzinfo)
        self.assertEqual(report.completeness_pct, 100)
        self.assertEqual(report.quality_score, 100)

    def test_malformed_values_and_negative_volume_are_findings(self) -> None:
        csv_data = io.StringIO(
            "timestamp,open,high,low,close,volume\n"
            "not-a-date,10,11,9,10,100\n"
            "2026-01-01T09:30:00Z,10,11,9,10,-1\n"
        )
        report = validate_csv(csv_data)
        codes = [issue.code for issue in report.issues]
        self.assertIn("invalid_timestamp", codes)
        self.assertIn("negative_volume", codes)
        self.assertEqual(report.valid_row_count, 0)

    def test_missing_columns_and_non_finite_values_are_reported(self) -> None:
        csv_data = io.StringIO("timestamp,open,close\n2026-01-01T00:00:00Z,inf,1\n")
        report = validate_csv(csv_data)
        codes = {issue.code for issue in report.issues}
        self.assertIn("missing_column", codes)
        self.assertIn("non_finite_number", codes)

    def test_interval_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            validate_csv(io.StringIO("timestamp,open,high,low,close,volume\n"), 0)


if __name__ == "__main__":
    unittest.main()
