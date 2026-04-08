from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ExpenseInput(BaseModel):
    date: str = Field(description="Expense date in YYYY-MM-DD format")
    description: str
    amount: float
    category: str
    invoice_reference: str | None = None


class ValidationResponse(BaseModel):
    expense: ExpenseInput
    status: Literal["approved", "rejected"]
    reasons: list[str] | None = None


class ParsedCsv(BaseModel):
    """
    Output from ReadCsvTool. This is intentionally simple JSON so Claude can
    reason over it easily.
    """

    filename: str
    headers: list[str]
    rows: list[dict[str, str]]
