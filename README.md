# Expense Report Processing Agent

Build an AI-powered agent that processes expense report spreadsheets, validates each expense against a provided API, and generates a summary report.

**Time:** ~60 minutes

## What You'll Build

An agent that:

1. Scans the `drop-zone/` directory for CSV files containing expense data
2. Reads and extracts expense line items from each file
3. Submits each expense to the validation API for approval/rejection
4. Generates a Markdown summary report in the `output/` directory

The validation API is intentionally strict about data formats. Your agent should leverage Claude to handle messy, real-world data — normalizing dates, cleaning up categories, and dealing with formatting inconsistencies before submitting to the API.

## Getting Started

### Prerequisites

- Docker and Docker Compose
- An Anthropic API key (included in the email with this challenge)

### Setup

1. Clone this repository
2. Create your `.env` file:
   ```bash
   cp .env.example .env
   # Edit .env and add your Anthropic API key
   ```
3. Start the API server:
   ```bash
   docker compose up api-server
   ```
4. Verify the server is running:
   ```bash
   curl http://localhost:8080/api/health
   # {"status":"ok"}
   ```
5. Copy a sample file into the drop zone:
   ```bash
   cp sample-data/simple-report.csv drop-zone/
   ```

### Running Your Solution

Build your agent in the `agent/` directory. You must provide a `Dockerfile` so it can run via Docker Compose:

```bash
docker compose up
```

Your agent container will have:
- `ANTHROPIC_API_KEY` — your API key, from the `.env` file
- `API_SERVER_URL` — the API server URL (`http://api-server:8080`)
- `/app/drop-zone` — mounted from `./drop-zone/` on your host
- `/app/output` — mounted from `./output/` on your host

## API Reference

The validation API runs on port 8080 and exposes three endpoints.

### GET /api/health

Health check.

```bash
curl http://localhost:8080/api/health
```

```json
{"status": "ok"}
```

### GET /api/categories

Returns the list of allowed expense categories.

```bash
curl http://localhost:8080/api/categories
```

```json
{
  "categories": [
    "travel", "meals", "office_supplies", "software",
    "equipment", "training", "other"
  ]
}
```

### POST /api/expenses/validate

Validates a single expense. Submit each expense individually.

```bash
curl -X POST http://localhost:8080/api/expenses/validate \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2025-03-01",
    "description": "Office chair",
    "amount": 249.99,
    "category": "equipment",
    "invoice_reference": "INV-2025-001"
  }'
```

**Approved response:**
```json
{
  "expense": {
    "date": "2025-03-01",
    "description": "Office chair",
    "amount": 249.99,
    "category": "equipment",
    "invoice_reference": "INV-2025-001"
  },
  "status": "approved",
  "reasons": null
}
```

**Rejected response:**
```json
{
  "expense": { ... },
  "status": "rejected",
  "reasons": [
    "invoice_reference is required for amounts over $50.00",
    "invalid category 'conferences'; must be one of: travel, meals, office_supplies, software, equipment, training, other"
  ]
}
```

### Validation Rules

The API enforces these rules strictly. All must pass for an expense to be approved:

| Rule | Requirement |
|------|-------------|
| **amount** | Must be a positive number |
| **date** | Must be a valid date in `YYYY-MM-DD` format |
| **date** | Must not be in the future |
| **category** | Must be an exact lowercase match from the allowed list |
| **description** | Must be non-empty |
| **invoice_reference** | Required when amount is over $50.00 |

Multiple validation errors are returned at once — not just the first failure.

## Sample Data

Three CSV files are provided in `sample-data/`, each progressively more challenging:

### `simple-report.csv`
5 clean, well-formatted expenses. All should be approved by the API. Start here.

### `mixed-report.csv`
8 expenses with a mix of valid and invalid data. Some have missing invoice references, invalid categories, or negative amounts. Your agent should submit them all and report the results accurately.

### `messy-report.csv`
10 expenses with real-world data quality issues:
- Inconsistent date formats (`MM/DD/YYYY`, `March 17 2025`, `YYYYMMDD`, etc.)
- Leading/trailing whitespace in fields
- Currency symbols in amounts (`$62.50`)
- Abbreviated or misspelled categories (`equip`, `sw`, `Office Supplies`)
- Missing fields

This is where your AI agent adds the most value. A naive CSV parser will fail on this data. Your agent should clean and normalize the data before submitting to the API.

## Expected Output

For each CSV file processed, your agent should produce a Markdown report in `output/` named `<input-filename>-report.md`.

For example, processing `simple-report.csv` should produce `output/simple-report-report.md`:

```markdown
# Expense Report: simple-report.csv

**Processed:** 2025-03-27 14:30:00
**Source file:** simple-report.csv

## Summary

| Metric | Value |
|--------|-------|
| Total Expenses | 5 |
| Approved | 5 |
| Rejected | 0 |
| Total Approved Amount | $839.49 |

## Expense Details

| # | Date | Description | Amount | Category | Invoice | Status |
|---|------|-------------|--------|----------|---------|--------|
| 1 | 2025-03-01 | Office chair | $249.99 | equipment | INV-2025-001 | Approved |
| 2 | 2025-03-03 | Team lunch | $42.50 | meals | - | Approved |
| 3 | 2025-03-05 | Flight to NYC | $389.00 | travel | INV-2025-002 | Approved |
| 4 | 2025-03-10 | Notion subscription | $8.00 | software | - | Approved |
| 5 | 2025-03-12 | Python training course | $150.00 | training | INV-2025-003 | Approved |

## Issues

No issues found. All expenses were approved.
```

For rejected expenses, the Issues section should list each rejection with reasons:

```markdown
## Issues

- **#3 - Standing desk ($599.99):** invoice_reference is required for amounts over $50.00
- **#6 - Conference tickets ($800.00):** invalid category 'conferences'; must be one of: travel, meals, office_supplies, software, equipment, training, other
- **#8 - Ergonomic keyboard (-$45.00):** amount must be a positive number
```

## Requirements

- **Must use Claude** (via the Anthropic API) as the AI backbone of your agent
- **Must call the validation API** for each expense — do not re-implement validation logic locally
- **Must produce Markdown reports** in the `output/` directory
- **Must include a Dockerfile** in the `agent/` directory so it runs via `docker compose up`
- **Language-agnostic** — use whatever language you prefer for the agent
- File-watching the drop zone is ideal, but a one-shot script that processes all files currently in `drop-zone/` is also acceptable

## Resources

- [Claude Agent SDK documentation](https://platform.claude.com/docs/en/agent-sdk/overview) — reference for building agents with Claude

## Expectations

We expect production-ready code. This means:

- Clean, readable architecture with appropriate separation of concerns
- Meaningful error handling — not just happy-path code
- Test coverage that gives confidence the solution works correctly
- Code you'd be comfortable shipping and maintaining in a real codebase

## Hints

- Use `GET /api/categories` to fetch the allowed categories — this can help your agent map messy category names to valid ones
- Start with `simple-report.csv` to get your end-to-end flow working, then tackle the harder files
- Think about how your agent can interpret ambiguous dates, abbreviated categories, and noisy formatting
- The API returns all validation failures at once — use this to give good feedback in your report
