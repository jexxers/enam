from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

from .logger import configure_logging, get_logger
from .config import get_settings
from .csv_ingest import glob_csv_files
from .tools import build_tools_server

logger = get_logger(__name__)

DROP_ZONE_DIR = Path("/app/drop-zone")


system_prompt = """You are an expense report processing agent."

For each CSV file I provide, you must:
- Read the CSV via the provided tool.
- For each row, normalize into the API schema fields: date (YYYY-MM-DD), description (non-empty), amount (number),category (exact match from allowed_categories), invoice_reference (string or empty).
- Prefer the deterministic_normalized values when present; only deviate when needs_llm is true or values are clearly wrong.
- Call the validation API tool ONCE per expense.
- Produce a Markdown report matching the README example exactly (sections, tables, Issues formatting).
- Write the markdown report using the provided tool.

Do not skip expenses.
"""


def main() -> None:
    configure_logging(service_name="agent")

    settings = get_settings()
    logger.info("agent starting")
    logger.info("settings loaded")

    csv_files = glob_csv_files(DROP_ZONE_DIR)
    if not csv_files:
        logger.info("no csv files found in drop-zone; exiting")
        return

    async def run() -> None:
        server = build_tools_server(api_server_url=str(settings.api_server_url))

        options = ClaudeAgentOptions(
            mcp_servers={"expense_tools": server},
            allowed_tools=[
                "mcp__expense_tools__read_expense_csv",
                "mcp__expense_tools__expense_api",
                "mcp__expense_tools__write_markdown_report",
            ],
            system_prompt=(
                "You are an expense report processing agent.\n"
                "For each CSV file I provide, you must:\n"
                "- Read the CSV via the provided tool.\n"
                "- For each row, normalize into the API schema fields:\n"
                "  date (YYYY-MM-DD), description (non-empty), amount (number),\n"
                "  category (exact match from allowed_categories), invoice_reference (string or empty).\n"
                "- Prefer the deterministic_normalized values when present; only deviate when needs_llm is true or values are clearly wrong.\n"
                "- Call the validation API tool ONCE per expense.\n"
                "- Produce a Markdown report matching this exact structure:\n"
                "  # Expense Report: <source.csv>\n"
                "  \n"
                "  **Processed:** <YYYY-MM-DD HH:MM:SS>\n"
                "  **Source file:** <source.csv>\n"
                "  \n"
                "  ## Summary\n"
                "  \n"
                "  | Metric | Value |\n"
                "  |--------|-------|\n"
                "  | Total Expenses | <n> |\n"
                "  | Approved | <n> |\n"
                "  | Rejected | <n> |\n"
                "  | Total Approved Amount | $<amount> |\n"
                "  \n"
                "  ## Expense Details\n"
                "  \n"
                "  | # | Date | Description | Amount | Category | Invoice | Status |\n"
                "  |---|------|-------------|--------|----------|---------|--------|\n"
                "  \n"
                "  ## Issues\n"
                "  \n"
                "  - If none rejected: `No issues found. All expenses were approved.`\n"
                "  - Otherwise: `- **#<i> - <desc> ($<amt>):** <reason1>; <reason2>`\n"
                "  \n"
                "  Use `Approved`/`Rejected` status values in the table.\n"
                "- Write the markdown report using the provided tool.\n"
                "Do not skip expenses.\n"
            ),
        )

        for csv_path in csv_files:
            out_filename = f"{csv_path.stem}-report.md"
            processed_ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            prompt = (
                f"Process the CSV at path: {csv_path}\n"
                f"Write report filename: {out_filename}\n"
                f"Processed timestamp (use exactly this): {processed_ts}\n"
                "Important: the report title must be `# Expense Report: <source filename>`.\n"
            )
            logger.info(
                "processing file", extra={"file": str(csv_path), "out": out_filename}
            )

            async for message in query(prompt=prompt, options=options):
                if isinstance(message, ResultMessage):
                    if message.subtype == "success":
                        logger.info("completed file", extra={"file": str(csv_path)})
                    else:
                        logger.info(
                            "file processing failed",
                            extra={"file": str(csv_path), "result": message.subtype},
                        )

    asyncio.run(run())


if __name__ == "__main__":
    main()
