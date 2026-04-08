from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CsvReadResult:
    filename: str
    headers: list[str]
    rows: list[dict[str, str]]


def glob_csv_files(drop_zone_dir: Path) -> list[Path]:
    return sorted([p for p in drop_zone_dir.glob("*.csv") if p.is_file()])


def read_csv_file(path: Path) -> CsvReadResult:
    raw = path.read_text(encoding="utf-8", errors="replace")
    sample = raw[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[",", "\t", ";", "|"])
    except csv.Error:
        dialect = csv.excel
        dialect.delimiter = ","

    lines = raw.splitlines()
    reader = csv.reader(lines, dialect=dialect)

    try:
        headers = next(reader)
    except StopIteration:
        return CsvReadResult(filename=path.name, headers=[], rows=[])

    headers = [h.strip() for h in headers]
    rows: list[dict[str, str]] = []
    for values in reader:
        # pad/trim to headers length
        if len(values) < len(headers):
            values = [*values, *[""] * (len(headers) - len(values))]
        elif len(values) > len(headers):
            values = values[: len(headers)]
        row = {
            headers[i]: (values[i] if values[i] is not None else "")
            for i in range(len(headers))
        }
        rows.append(row)

    return CsvReadResult(filename=path.name, headers=headers, rows=rows)
