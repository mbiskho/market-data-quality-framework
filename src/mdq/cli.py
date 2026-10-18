"""Command-line interface for market data quality reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .charts import render_reports
from .validation import validate_csv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mdq",
        description="Validate an OHLCV CSV and produce an auditable quality summary.",
    )
    parser.add_argument("input", type=Path, help="CSV with timestamp, open, high, low, close, volume columns")
    parser.add_argument("--interval-minutes", type=int, default=1, help="Expected bar interval (default: 1)")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Report format")
    parser.add_argument("--write-reports", type=Path, metavar="DIR", help="Write overview and flow charts as SVG and PNG")
    parser.add_argument("--strict", action="store_true", help="Exit with status 1 when validation errors are found")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = validate_csv(args.input, args.interval_minutes)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"mdq: {error}")
        return 2

    if args.format == "json":
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(
            f"Market data quality report: {report.source}\n"
            f"  Records:       {report.record_count}\n"
            f"  Parsed bars:   {report.parsed_count}\n"
            f"  Valid rows:    {report.valid_row_count}\n"
            f"  Completeness:  {report.completeness_pct:.1f}%\n"
            f"  Validity:      {report.validity_pct:.1f}%\n"
            f"  Uniqueness:    {report.uniqueness_pct:.1f}%\n"
            f"  Quality score: {report.quality_score:.1f}/100\n"
            f"  Findings:      {report.error_count} error(s), {report.warning_count} warning(s)"
        )
        for issue in report.issues:
            location = f"row {issue.row}" if issue.row is not None else "dataset"
            print(f"  [{issue.severity.upper()}] {issue.code} ({location}): {issue.message}")

    if args.write_reports:
        outputs = render_reports(report, args.write_reports)
        print(f"Wrote {len(outputs)} charts to {args.write_reports}")
    return 1 if args.strict and report.error_count else 0
