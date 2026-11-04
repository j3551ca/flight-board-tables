"""Optional airport signs and idempotent updates to a delimited README block."""

from __future__ import annotations

import html
import os
from pathlib import Path
from urllib.parse import quote

from PIL import Image, ImageDraw

from .config import Button, Config, Theme
from .render import font, wrap

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
