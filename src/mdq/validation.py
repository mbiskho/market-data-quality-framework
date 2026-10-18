"""CSV loading and deterministic market-data quality checks."""

from __future__ import annotations

import csv
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TextIO

from .models import MarketBar, QualityIssue, QualityReport

REQUIRED_COLUMNS = ("timestamp", "open", "high", "low", "close", "volume")
PRICE_COLUMNS = ("open", "high", "low", "close")


def validate_csv(
    source: str | Path | TextIO,
    expected_interval_minutes: int = 1,
) -> QualityReport:
    """Read and validate a CSV containing timestamp, OHLC, and volume fields.

    Timestamps must be ISO-8601. Naive timestamps are interpreted as UTC;
    timezone-aware values are normalized to UTC. A row is valid only when all
    required cells parse and all numeric and OHLC constraints pass.
    """
    if expected_interval_minutes <= 0:
        raise ValueError("expected_interval_minutes must be positive")

    close_after_read = False
    if hasattr(source, "read"):
        stream = source
        source_name = getattr(source, "name", "<stream>")
    else:
        path = Path(source)
        stream = path.open("r", newline="", encoding="utf-8-sig")
        close_after_read = True
        source_name = str(path)

    issues: list[QualityIssue] = []
    bars: list[MarketBar] = []
    row_issue_counts: dict[int, int] = {}
    complete_cells = 0
    complete_row_count = 0
    record_count = 0
    seen_timestamps: set[datetime] = set()
    previous_timestamp: datetime | None = None

    try:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        missing_columns = [column for column in REQUIRED_COLUMNS if column not in headers]
        if missing_columns:
            issues.append(
                QualityIssue(
                    "missing_column",
                    "error",
                    "Required columns missing: " + ", ".join(missing_columns),
                )
            )

        for row_number, values in enumerate(reader, start=2):
            record_count += 1
            row_had_error = False

            def issue(code: str, message: str, severity: str = "error") -> None:
                nonlocal row_had_error
                issues.append(QualityIssue(code, severity, message, row_number))
                if severity == "error":
                    row_had_error = True
                    row_issue_counts[row_number] = row_issue_counts.get(row_number, 0) + 1

            cells = [values.get(column) or "" for column in REQUIRED_COLUMNS]
            complete_cells += sum(cell.strip() != "" for cell in cells)
            complete_row_count += all(cell.strip() != "" for cell in cells)

            if missing_columns:
                issue("missing_column", "Row cannot be evaluated because required columns are absent.")

            missing_values = [column for column in REQUIRED_COLUMNS if not (values.get(column) or "").strip()]
            for column in missing_values:
                issue("missing_value", f"Required value '{column}' is blank.")

            timestamp: datetime | None = None
            raw_timestamp = (values.get("timestamp") or "").strip()
            if raw_timestamp:
                try:
                    timestamp = datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=timezone.utc)
                    timestamp = timestamp.astimezone(timezone.utc)
                except ValueError:
                    issue("invalid_timestamp", f"'{raw_timestamp}' is not a valid ISO-8601 timestamp.")

            numbers: dict[str, float] = {}
            for column in REQUIRED_COLUMNS[1:]:
                raw_value = (values.get(column) or "").strip()
                if not raw_value:
                    continue
                try:
                    number = float(raw_value)
                except ValueError:
                    issue("invalid_number", f"'{column}' value '{raw_value}' is not numeric.")
                    continue
                if not math.isfinite(number):
                    issue("non_finite_number", f"'{column}' must be finite.")
                    continue
                numbers[column] = number

            if timestamp is not None:
                if timestamp in seen_timestamps:
                    issue("duplicate_timestamp", f"Timestamp {timestamp.isoformat()} appears more than once.")
                else:
                    seen_timestamps.add(timestamp)
                if previous_timestamp is not None:
                    if timestamp < previous_timestamp:
                        issue("out_of_order", "Timestamp is earlier than the preceding source row.", "warning")
                    elif timestamp - previous_timestamp > timedelta(minutes=expected_interval_minutes):
                        gap = timestamp - previous_timestamp
                        missing_bars = max(
                            1,
                            int(gap.total_seconds() // (expected_interval_minutes * 60)) - 1,
                        )
                        issue(
                            "timestamp_gap",
                            f"Gap implies {missing_bars} missing interval(s) before this row.",
                            "warning",
                        )
                previous_timestamp = timestamp

            for column, number in numbers.items():
                if column in PRICE_COLUMNS and number <= 0:
                    issue("non_positive_price", f"'{column}' must be greater than zero.")
                if column == "volume" and number < 0:
                    issue("negative_volume", "'volume' must be zero or greater.")

            if all(column in numbers for column in PRICE_COLUMNS):
                if numbers["high"] < max(numbers["open"], numbers["close"], numbers["low"]):
                    issue("ohlc_inconsistent", "'high' must be at least open, close, and low.")
                if numbers["low"] > min(numbers["open"], numbers["close"], numbers["high"]):
                    issue("ohlc_inconsistent", "'low' must be at most open, close, and high.")

            if timestamp is not None and all(column in numbers for column in REQUIRED_COLUMNS[1:]):
                bars.append(MarketBar(timestamp=timestamp, **numbers))

            # Out-of-order and gap findings are warnings and do not invalidate a row.
            if not row_had_error:
                row_issue_counts.setdefault(row_number, 0)
    finally:
        if close_after_read:
            stream.close()

    valid_row_count = sum(count == 0 for count in row_issue_counts.values())
    if record_count == 0 and not missing_columns:
        issues.append(QualityIssue("empty_dataset", "warning", "CSV contains no data rows."))

    return QualityReport(
        source=str(source_name),
        record_count=record_count,
        parsed_count=len(bars),
        valid_row_count=valid_row_count,
        complete_row_count=complete_row_count,
        complete_cells=complete_cells,
        total_cells=record_count * len(REQUIRED_COLUMNS),
        unique_timestamp_count=len(seen_timestamps),
        issues=tuple(issues),
        bars=tuple(bars),
        expected_interval_minutes=expected_interval_minutes,
    )
