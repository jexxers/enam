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
                "mcp__expense_tools__sum_expenses",
            ],
            system_prompt="""
You are an expense report processing agent.
For each CSV file I provide, you must:
- Read the CSV via the provided tool.
- For each row, normalize into the API schema fields:
  date (YYYY-MM-DD), description (non-empty), amount (number),
  category (exact match from allowed_categories), invoice_reference (string or empty).
- Prefer the deterministic_normalized values when present; only deviate when needs_llm is true or values are clearly wrong.
- Call the validation API tool ONCE per expense.
- After you have validated all expenses, compute `Total Approved Amount` by calling the `sum_expenses` tool
  with the list of APPROVED expenses (each must include an `amount` field). Use the returned `total` as $<amount>.
- Produce a Markdown report matching this exact structure:
  # Expense Report: <source.csv>
  
  **Processed:** <YYYY-MM-DD HH:MM:SS>
  **Source file:** <source.csv>
  
  ## Summary
  
  | Metric | Value |
  |--------|-------|
  | Total Expenses | <n> |
  | Approved | <n> |
  | Rejected | <n> |
  | Total Approved Amount | $<amount> |
  
  ## Expense Details
  
  | # | Date | Description | Amount | Category | Invoice | Status |
  |---|------|-------------|--------|----------|---------|--------|
  
  ## Issues
  
  - If none rejected: `No issues found. All expenses were approved.`
  - Otherwise: `- **#<i> - <desc> ($<amt>):** <reason1>; <reason2>`
  
  Use `Approved`/`Rejected` status values in the table.
- Write the markdown report using the provided tool.
Do not skip expenses.
""".strip(),
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
