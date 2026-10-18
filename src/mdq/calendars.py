"""Lightweight US market-day calendars using only the Python standard library.

The returned weekday states are a reference aid, not an exchange-authoritative
calendar. Intraday sessions, one-off local closures, and instrument-specific
publication schedules require a separately maintained source.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from functools import lru_cache
from types import MappingProxyType
from typing import Mapping

OPEN, CLOSED, UNCERTAIN = "open", "closed", "uncertain"
CALENDARS = ("NYSE", "FED", "SIFMA", "NYMEX")

_NATIONAL_MOURNING = ("2007-01-02", "2012-10-29", "2012-10-30", "2018-12-05", "2025-01-09")
_FEDERAL_EXTRA = ("2018-12-05", "2018-12-24", "2020-12-24")
_SIFMA_EXTRA = ("2012-10-29", "2012-10-30", "2018-12-05")


def _nth_weekday(year: int, month: int, weekday: int, occurrence: int) -> date:
    first = date(year, month, 1)
    return first + timedelta(days=(weekday - first.weekday()) % 7 + (occurrence - 1) * 7)


def _last_weekday(year: int, month: int, weekday: int) -> date:
    last = date(year, month, monthrange(year, month)[1])
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def _observed_nearest(day: date) -> date:
    if day.weekday() == 5:
        return day - timedelta(days=1)
    if day.weekday() == 6:
        return day + timedelta(days=1)
    return day


def _observed_sunday_only(day: date) -> date:
    return day + timedelta(days=1) if day.weekday() == 6 else day


def _easter_sunday(year: int) -> date:
    """Gregorian Easter date, used to identify Good Friday."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return date(year, month, day)


def _federal_holidays(year: int, *, saturday_observance: bool = True) -> set[date]:
    observe = _observed_nearest if saturday_observance else _observed_sunday_only
    holidays = {
        observe(date(year, 1, 1)),
        _nth_weekday(year, 1, 0, 3),
        _nth_weekday(year, 2, 0, 3),
        _last_weekday(year, 5, 0),
        _nth_weekday(year, 9, 0, 1),
        _nth_weekday(year, 11, 3, 4),
        observe(date(year, 12, 25)),
    }
    if year >= 2022:
        holidays.add(_observed_nearest(date(year, 6, 19)))
    holidays.add(_observed_nearest(date(year, 7, 4)))
    return holidays


def _inauguration_dates(year: int) -> set[date]:
    if (year - 1937) % 4:
        return set()
    day = date(year, 1, 20)
    return {day} if day.weekday() < 5 else set()


def _half_days(year: int) -> set[date]:
    dates = {_nth_weekday(year, 11, 3, 4) + timedelta(days=1)}
    for month, day_number in ((7, 3), (7, 5), (12, 24), (12, 26), (12, 31)):
        day = date(year, month, day_number)
        if day.weekday() < 5:
            dates.add(day)
    return dates


def _date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


@lru_cache(maxsize=32)
def _cached_calendar(name: str, start: date, end: date) -> Mapping[date, str]:
    if name not in CALENDARS:
        raise ValueError(f"unknown calendar {name!r}; choose one of {', '.join(CALENDARS)}")
    if end < start:
        raise ValueError("end must be on or after start")

    states = {
        start + timedelta(days=offset): OPEN
        for offset in range((end - start).days + 1)
        if (start + timedelta(days=offset)).weekday() < 5
    }
    for year in range(start.year, end.year + 1):
        closings = _federal_holidays(year, saturday_observance=name == "FED")
        if name == "NYSE":
            # NYSE does not close on Friday 31 December when New Year's Day is Saturday.
            if date(year, 1, 1).weekday() == 5:
                closings.discard(date(year - 1, 12, 31))
            closings.update(
                date.fromisoformat(value)
                for value in _NATIONAL_MOURNING
                if date.fromisoformat(value).year == year
            )
            closings.update(date(year, 9, day) for day in (11, 12, 13, 14) if year == 2001)
            if year == 2004:
                closings.add(date(2004, 6, 11))
            _close_dates(states, closings)
        elif name == "FED":
            closings.update(_inauguration_dates(year))
            closings.update(_dates_in_year(_FEDERAL_EXTRA, year))
            _close_dates(states, closings)
            if year == 2021:
                _mark_uncertain(states, {date(2021, 6, 18)})
        elif name == "SIFMA":
            # SIFMA treats Good Friday as uncertain rather than uniformly closed.
            closings.discard(_easter_sunday(year) - timedelta(days=2))
            closings.update(_dates_in_year(_SIFMA_EXTRA, year))
            _close_dates(states, closings)
            _mark_uncertain(states, {_easter_sunday(year) - timedelta(days=2)})
            if year == 2021:
                _mark_uncertain(states, {date(2021, 6, 18)})
        else:
            closings.update(
                date.fromisoformat(value)
                for value in _NATIONAL_MOURNING
                if date.fromisoformat(value).year == year
            )
            _close_dates(states, closings)
            _mark_uncertain(states, _half_days(year))

    return MappingProxyType(states)


def _dates_in_year(values: tuple[str, ...], year: int) -> set[date]:
    return {parsed for value in values if (parsed := date.fromisoformat(value)).year == year}


def _close_dates(states: dict[date, str], dates: set[date]) -> None:
    for day in dates:
        if day in states:
            states[day] = CLOSED


def _mark_uncertain(states: dict[date, str], dates: set[date]) -> None:
    for day in dates:
        if states.get(day) == OPEN:
            states[day] = UNCERTAIN


def calendar(name: str, start: str | date, end: str | date) -> Mapping[date, str]:
    """Return weekday states for an inclusive date range.

    Keys are ``datetime.date`` values; weekends are omitted. For example,
    ``calendar("NYSE", "2026-01-01", "2026-01-05")`` maps each weekday to
    ``"open"`` or ``"closed"``. NYMEX early-close dates and SIFMA Good Friday
    are ``"uncertain"`` because this day-level utility cannot express sessions.
    """
    return _cached_calendar(name.upper(), _date(start), _date(end))
