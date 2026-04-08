from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from .api_client import ExpenseApiClient
from .csv_ingest import read_csv_file
from .models import ExpenseInput
from .normalize import deterministic_normalize_row


def build_tools_server(*, api_server_url: str) -> Any:
    """
    Returns an in-process MCP server exposing the three project tools:
    - read_csv_file
    - expense_api
    - write_markdown_report
    """

    api = ExpenseApiClient(base_url=api_server_url)

    @tool(
        "read_expense_csv",
        "Read an expense CSV from /app/drop-zone and return headers and rows (strings).",
        {"path": str},
    )
    async def read_expense_csv(args: dict[str, Any]) -> dict[str, Any]:
        path = Path(args["path"])
        res = read_csv_file(path)
        categories = await api.get_categories()
        deterministic = [
            deterministic_normalize_row(r, allowed_categories=categories).__dict__
            for r in res.rows
        ]
        payload = {
            "filename": res.filename,
            "headers": res.headers,
            "rows": res.rows,
            "allowed_categories": categories,
            "deterministic_normalized": deterministic,
        }
        return {"content": [{"type": "text", "text": json.dumps(payload)}]}

    @tool(
        "expense_api",
        "Call the expense validation API. Use operation=get_categories or operation=validate_expense.",
        {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "get_categories or validate_expense",
                },
                "expense": {
                    "type": "object",
                    "description": "Expense payload for validate_expense operation",
                },
            },
            "required": ["operation"],
        },
    )
    async def expense_api(args: dict[str, Any]) -> dict[str, Any]:
        op = args.get("operation")
        if op == "get_categories":
            cats = await api.get_categories()
            return {
                "content": [{"type": "text", "text": json.dumps({"categories": cats})}]
            }
        if op == "validate_expense":
            exp = args.get("expense") or {}
            # Let API be the validator; we just pass through.
            expense = ExpenseInput.model_validate(exp)
            resp = await api.validate_expense(expense=expense)
            return {
                "content": [
                    {"type": "text", "text": json.dumps(resp.model_dump(mode="json"))}
                ]
            }
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Unknown operation: {op}. Use get_categories or validate_expense.",
                }
            ]
        }

    @tool(
        "write_markdown_report",
        "Write a markdown report to /app/output. Provide filename (e.g. simple-report-report.md) and markdown content.",
        {"filename": str, "content": str},
    )
    async def write_markdown_report(args: dict[str, Any]) -> dict[str, Any]:
        out_dir = Path("/app/output")
        out_dir.mkdir(parents=True, exist_ok=True)
        filename = Path(args["filename"]).name
        content = args["content"]
        (out_dir / filename).write_text(content, encoding="utf-8")
        return {"content": [{"type": "text", "text": f"Wrote /app/output/{filename}"}]}

    return create_sdk_mcp_server(
        name="expense-tools",
        version="1.0.0",
        tools=[read_expense_csv, expense_api, write_markdown_report],
    )
