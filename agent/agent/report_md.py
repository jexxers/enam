from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .models import ExpenseInput, ValidationResponse


def _money(amount: float) -> str:
    return f"${amount:.2f}"


@dataclass(frozen=True)
class ReportRow:
    index: int
    expense: ExpenseInput
    validation: ValidationResponse | None


def render_report_markdown(*, source_filename: str, rows: list[ReportRow]) -> str:
    processed = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    approved = [r for r in rows if r.validation and r.validation.status == "approved"]
    rejected = [r for r in rows if r.validation and r.validation.status == "rejected"]
    approved_total = sum((r.expense.amount for r in approved), 0.0)

    lines: list[str] = []
    lines.append(f"# Expense Report: {source_filename}")
    lines.append("")
    lines.append(f"**Processed:** {processed}")
    lines.append(f"**Source file:** {source_filename}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total Expenses | {len(rows)} |")
    lines.append(f"| Approved | {len(approved)} |")
    lines.append(f"| Rejected | {len(rejected)} |")
    lines.append(f"| Total Approved Amount | {_money(approved_total)} |")
    lines.append("")
    lines.append("## Expense Details")
    lines.append("")
    lines.append("| # | Date | Description | Amount | Category | Invoice | Status |")
    lines.append("|---|------|-------------|--------|----------|---------|--------|")

    for r in rows:
        exp = r.expense
        status = "-"
        if r.validation:
            status = "Approved" if r.validation.status == "approved" else "Rejected"
        invoice = exp.invoice_reference or "-"
        lines.append(
            f"| {r.index} | {exp.date} | {exp.description} | {_money(exp.amount)} | {exp.category} | {invoice} | {status} |"
        )

    lines.append("")
    lines.append("## Issues")
    lines.append("")

    if not rejected:
        lines.append("No issues found. All expenses were approved.")
        return "\n".join(lines) + "\n"

    for r in rejected:
        reasons = r.validation.reasons if r.validation else None
        reasons_text = "; ".join(reasons or ["unknown rejection reason"])
        lines.append(
            f"- **#{r.index} - {r.expense.description} ({_money(r.expense.amount)}):** {reasons_text}"
        )

    return "\n".join(lines) + "\n"
