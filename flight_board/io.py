"""Read source tables, draw optional signs, and update the managed README block."""

from __future__ import annotations

import csv
import html
import json
import os
import re
from pathlib import Path
from urllib.parse import quote

from markdown_it import MarkdownIt
from markdown_it.token import Token
from PIL import Image, ImageDraw

from .config import Button, Config, Table, Theme
from .render import font, wrap


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


START = "<!-- flight-board:start -->"
END = "<!-- flight-board:end -->"


def sign(button: Button, theme: Theme) -> Image.Image:
    """Draw a borderless sign with real typographic arrows and a customizable icon."""
    width, height = 720, 150
    image = Image.new("RGB", (width, height), theme.background)
    draw = ImageDraw.Draw(image)
    draw.ellipse((24, 42, 90, 108), fill=theme.accent)
    draw.text((57, 75), button.icon, font=font(32), fill=theme.background, anchor="mm")
    size = 34
    while size > 14 and len(wrap(button.label, int(480 / font(size).getlength("M")))) > 2:
        size -= 2
    lines = wrap(button.label, int(480 / font(size).getlength("M")))
    if len(lines) > 2:
        raise ValueError("Button label is too long. Use a short navigation label.")
    for index, line in enumerate(lines):
        draw.text(
            (116, 75 + (index - (len(lines) - 1) / 2) * (size + 8)),
            line,
            font=font(size),
            fill=theme.text,
            anchor="lm",
        )
    draw.text((660, 75), button.arrow, font=font(62), fill=theme.accent, anchor="mm")
    return image


def relative_url(path: Path, parent: Path) -> str:
    """Create a URL-escaped repository link relative to a README's directory."""
    return quote(Path(os.path.relpath(path, parent)).as_posix(), safe="/")


def readme_block(config: Config, output: Path, readme: Path, source: Path) -> str:
    """Generate linked signs and the board; the full source remains accessible."""
    lines = [START]
    if config.buttons:
        lines.append('<p align="center">')
        percent = (100 - 2 * (len(config.buttons) - 1)) / len(config.buttons)
        for index, button in enumerate(config.buttons):
            src = relative_url(output / f"sign-{index + 1}.png", readme.parent)
            lines.append(
                f'  <a href="{html.escape(button.url, quote=True)}">'
                f'<img src="{src}" width="{percent:g}%" '
                f'alt="{html.escape(button.label, quote=True)}"></a>'
            )
        lines.extend(["</p>", ""])
    image_path = output / ("board.gif" if config.animation.enabled else "board.png")
    destination = config.board_link or relative_url(source, readme.parent)
    lines.extend(
        [
            f'<a href="{html.escape(destination, quote=True)}">'
            f'<img src="{relative_url(image_path, readme.parent)}" width="100%" '
            f'alt="{html.escape(config.title, quote=True)} — open source table"></a>',
            "",
            f"[Static board]({relative_url(output / 'board.png', readme.parent)})",
            END,
        ]
    )
    return "\n".join(lines)


def updated_readme(original: str, block: str) -> str:
    """Replace exactly one managed block; refuse ambiguous markers without losing prose."""
    starts, ends = original.count(START), original.count(END)
    if not starts and not ends:
        return original.rstrip() + "\n\n" + block + "\n"
    if starts != 1 or ends != 1 or original.index(START) > original.index(END):
        raise ValueError("README needs exactly one correctly ordered flight-board marker pair.")
    return original[: original.index(START)] + block + original[original.index(END) + len(END) :]
