"""Core value objects for market data validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class MarketBar:
    """One parsed OHLCV observation with a timezone-aware timestamp."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class QualityIssue:
    """A single validation finding tied to a source row where possible."""

    code: str
    severity: str
    message: str
    row: int | None = None


@dataclass(frozen=True)
class QualityReport:
    """Summary metrics and findings for one CSV validation run."""

    source: str
    record_count: int
    parsed_count: int
    valid_row_count: int
    complete_row_count: int
    complete_cells: int
    total_cells: int
    unique_timestamp_count: int
    issues: tuple[QualityIssue, ...]
    bars: tuple[MarketBar, ...]
    expected_interval_minutes: int

    @property
    def completeness_pct(self) -> float:
        return _percentage(self.complete_cells, self.total_cells)

    @property
    def validity_pct(self) -> float:
        return _percentage(self.valid_row_count, self.record_count)

    @property
    def uniqueness_pct(self) -> float:
        return _percentage(self.unique_timestamp_count, self.record_count)

    @property
    def quality_score(self) -> float:
        return (
            0.4 * self.completeness_pct
            + 0.4 * self.validity_pct
            + 0.2 * self.uniqueness_pct
        )

    @property
    def error_count(self) -> int:
        return sum(issue.severity == "error" for issue in self.issues)

    @property
    def warning_count(self) -> int:
        return sum(issue.severity == "warning" for issue in self.issues)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable report without raw observations."""
        return {
            "source": self.source,
            "expected_interval_minutes": self.expected_interval_minutes,
            "metrics": {
                "record_count": self.record_count,
                "parsed_count": self.parsed_count,
                "valid_row_count": self.valid_row_count,
                "complete_row_count": self.complete_row_count,
                "completeness_pct": round(self.completeness_pct, 2),
                "validity_pct": round(self.validity_pct, 2),
                "uniqueness_pct": round(self.uniqueness_pct, 2),
                "quality_score": round(self.quality_score, 2),
                "error_count": self.error_count,
                "warning_count": self.warning_count,
            },
            "issues": [asdict(issue) for issue in self.issues],
        }


def _percentage(numerator: int, denominator: int) -> float:
    return 100.0 * numerator / denominator if denominator else 100.0
