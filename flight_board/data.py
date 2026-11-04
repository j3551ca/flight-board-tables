"""Read scalar rows from CSV, JSON, and GitHub-style Markdown tables."""

from __future__ import annotations

import csv
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path

from markdown_it import MarkdownIt
from markdown_it.token import Token


@dataclass(frozen=True)
class Table:
    """Ordered field names and string-valued rows ready for presentation."""

    fields: tuple[str, ...]
    rows: tuple[dict[str, str], ...]


def _inline_text(tokens: list[Token]) -> str:
    """Keep link labels and code, turn explicit breaks into lines, discard markup."""
    parts: list[str] = []
    for token in tokens:
        if token.type in {"text", "code_inline"}:
            parts.append(token.content)
        elif token.type in {"softbreak", "hardbreak"}:
            parts.append("\n")
        elif token.type == "html_inline" and re.fullmatch(r"<br\s*/?>", token.content, re.I):
            parts.append("\n")
        elif token.type == "image":
            parts.append(token.content)
    return html.unescape("".join(parts))


def _markdown(path: Path, table_index: int) -> list[list[str]]:
    parser = MarkdownIt("commonmark", {"html": True}).enable("table")
    index = -1
    rows: list[list[str]] = []
    row: list[str] = []
    for token in parser.parse(path.read_text(encoding="utf-8")):
        if token.type == "table_open":
            index += 1
        if index != table_index:
            continue
        if token.type == "tr_open":
            row = []
        elif token.type == "inline":
            row.append(_inline_text(token.children or []))
        elif token.type == "tr_close":
            rows.append(row)
        elif token.type == "table_close":
            return rows
    raise ValueError(f"Markdown table {table_index} not found in {path.name}.")


def _scalar(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    raise ValueError("JSON cells must be strings, numbers, booleans, or null, not objects/lists.")


def read_table(path: Path, table_index: int = 0) -> Table:
    """Read a table without changing its source or performing domain-specific rewrites."""
    if path.stat().st_size > 5_000_000:
        raise ValueError("Input exceeds 5 MB. Provide a summary table for the board.")
    suffix = path.suffix.lower()
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list) or not data or not all(isinstance(r, dict) for r in data):
            raise ValueError("JSON input must be a nonempty array of objects.")
        headers = list(data[0])
        if any(set(row) != set(headers) for row in data):
            raise ValueError("Every JSON row must have the same field names.")
        values = [[_scalar(row[key]) for key in headers] for row in data]
    else:
        if suffix == ".csv":
            with path.open(encoding="utf-8-sig", newline="") as stream:
                matrix = list(csv.reader(stream))
        elif suffix in {".md", ".markdown"}:
            matrix = _markdown(path, table_index)
        else:
            raise ValueError("Supported source formats: .csv, .json, .md, .markdown.")
        if len(matrix) < 2:
            raise ValueError("The table needs a header and at least one data row.")
        headers, *values = matrix
    if not headers or any(not name.strip() for name in headers):
        raise ValueError("Column names cannot be empty.")
    if len(set(headers)) != len(headers):
        raise ValueError("Column names must be unique.")
    if len(values) > 100:
        raise ValueError("Use at most 100 rows; split large tables into separate boards.")
    if any(len(row) != len(headers) for row in values):
        raise ValueError("Every row must have the same number of cells as the header.")
    if any(len(value) > 2000 for row in values for value in row):
        raise ValueError("A cell exceeds 2,000 characters. Use a concise display field.")
    return Table(tuple(headers), tuple(dict(zip(headers, row, strict=True)) for row in values))
