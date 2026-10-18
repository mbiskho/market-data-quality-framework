from __future__ import annotations

import unittest
from datetime import date

from mdq.calendars import CLOSED, OPEN, UNCERTAIN, calendar


class CalendarTests(unittest.TestCase):
    def test_calendar_marks_weekdays_and_omits_weekends(self) -> None:
        states = calendar("NYSE", "2026-01-01", "2026-01-05")
        self.assertEqual(states[date(2026, 1, 1)], CLOSED)
        self.assertEqual(states[date(2026, 1, 2)], OPEN)
        self.assertNotIn(date(2026, 1, 3), states)

    def test_good_friday_is_uncertain_for_sifma(self) -> None:
        states = calendar("SIFMA", "2026-04-03", "2026-04-03")
        self.assertEqual(states[date(2026, 4, 3)], UNCERTAIN)

    def test_unknown_calendar_and_reversed_range_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            calendar("UNKNOWN", "2026-01-01", "2026-01-02")
        with self.assertRaises(ValueError):
            calendar("NYSE", "2026-01-02", "2026-01-01")


if __name__ == "__main__":
    unittest.main()
