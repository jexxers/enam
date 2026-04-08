from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from .models import ExpenseInput, ValidationResponse


@dataclass(frozen=True)
class ExpenseApiClient:
    base_url: str

    async def health(self) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
            r = await client.get("/api/health")
            r.raise_for_status()
            return r.json()

    async def get_categories(self) -> list[str]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
            r = await client.get("/api/categories")
            r.raise_for_status()
            data = r.json()
            cats = data.get("categories", [])
            if not isinstance(cats, list):
                return []
            return [str(c) for c in cats]

    async def validate_expense(self, expense: ExpenseInput) -> ValidationResponse:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=20.0) as client:
            r = await client.post(
                "/api/expenses/validate", json=expense.model_dump(mode="json")
            )
            r.raise_for_status()
            return ValidationResponse.model_validate(r.json())
