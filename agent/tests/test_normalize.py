from __future__ import annotations

import unittest

from agent.agent.normalize import parse_amount, parse_date_iso, normalize_category


class TestNormalize(unittest.TestCase):
    def test_parse_amount_basic(self) -> None:
        self.assertEqual(parse_amount("249.99"), 249.99)
        self.assertEqual(parse_amount("  $62.50 "), 62.5)

    def test_parse_date_iso_common(self) -> None:
        self.assertEqual(parse_date_iso("2025-03-01"), "2025-03-01")
        self.assertEqual(parse_date_iso("03/15/2025"), "2025-03-15")
        self.assertEqual(parse_date_iso("20250324"), "2025-03-24")
        self.assertEqual(parse_date_iso("March 17 2025"), "2025-03-17")

    def test_normalize_category_aliases(self) -> None:
        allowed = [
            "travel",
            "meals",
            "office_supplies",
            "software",
            "equipment",
            "training",
            "other",
        ]
        self.assertEqual(normalize_category(" Meals ", allowed), "meals")
        self.assertEqual(normalize_category("equip", allowed), "equipment")
        self.assertEqual(
            normalize_category("Office Supplies", allowed), "office_supplies"
        )


if __name__ == "__main__":
    unittest.main()
