from __future__ import annotations

import unittest

from agent.agent.models import ExpenseInput, ValidationResponse
from agent.agent.report_md import ReportRow, render_report_markdown


class TestReportMarkdown(unittest.TestCase):
    def test_render_report_contains_tables(self) -> None:
        exp1 = ExpenseInput(
            date="2025-03-01",
            description="Office chair",
            amount=249.99,
            category="equipment",
            invoice_reference="INV-2025-001",
        )
        val1 = ValidationResponse(expense=exp1, status="approved", reasons=None)
        md = render_report_markdown(
            source_filename="simple-report.csv",
            rows=[ReportRow(index=1, expense=exp1, validation=val1)],
        )
        self.assertIn("# Expense Report: simple-report.csv", md)
        self.assertIn("## Summary", md)
        self.assertIn("## Expense Details", md)
        self.assertIn(
            "| # | Date | Description | Amount | Category | Invoice | Status |", md
        )


if __name__ == "__main__":
    unittest.main()
