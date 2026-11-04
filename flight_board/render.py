"""Portable Pillow rendering for complete boards and independently settling flaps."""

from __future__ import annotations

import math
import random
import textwrap
from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from .config import Settings

FONT_PATH = Path(__file__).parent / "fonts" / "DejaVuSansMono.ttf"
MAX_FRAME_PIXELS = 6_000_000
MAX_ANIMATION_PIXELS = 220_000_000
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


@lru_cache(maxsize=32)
def font(size: int) -> ImageFont.FreeTypeFont:
    """Load the redistributable bundled font, independent of host fonts."""
    return ImageFont.truetype(str(FONT_PATH), size=size)


def wrap(value: str, width: int) -> list[str]:
    """Preserve explicit line breaks and wrap long tokens without dropping content."""
    return [
        part
        for line in value.expandtabs(4).split("\n")
        for part in (
            textwrap.wrap(line, width, break_long_words=True, break_on_hyphens=False) or [""]
        )
    ]


def create_cards(theme: Settings) -> dict[str, Any]:
    """Create card dimensions and an empty image cache for one board."""
    width = math.ceil(font(theme["font_size"]).getlength("M")) + 4
    height = math.ceil(theme["font_size"] * 1.6)
    return {
        "theme": theme,
        "width": width,
        "height": height,
        "step": width + 2,
        "line_step": height + 4,
        "cache": {},
    }


def render_card(cards: dict[str, Any], character: str) -> Image.Image:
    """Return a static card with its text centered on the horizontal hinge."""
    theme = cards["theme"]
    width, height = cards["width"], cards["height"]
    cache: dict[str, Image.Image] = cards["cache"]
    if character not in cache:
        image = Image.new("RGB", (width, height), theme["background"])
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle(
            (0, 0, width - 1, height - 1),
            radius=2,
            fill=theme["card"],
            outline=theme["edge"],
        )
        draw.text(
            (width / 2, height / 2),
            character,
            font=font(theme["font_size"]),
            anchor="mm",
            fill=theme["text"],
        )
        draw.line(
            (0, height // 2, width, height // 2),
            fill=theme["background"],
        )
        cache[character] = image
    return cache[character]


def render_flap(cards: dict[str, Any], old: str, new: str, phase: int, phases: int) -> Image.Image:
    """Compress the old top, then expand the new bottom with directional shading."""
    theme = cards["theme"]
    width, card_height = cards["width"], cards["height"]
    progress = phase / (phases - 1)
    before, after = render_card(cards, old), render_card(cards, new)
    middle = card_height // 2
    result = before.copy()
    result.paste(after.crop((0, 0, width, middle)), (0, 0))
    if progress < 0.5:
        height = max(1, round(middle * math.cos(progress * math.pi)))
        moving = before.crop((0, 0, width, middle)).resize(
            (width, height), Image.Resampling.LANCZOS
        )
        moving = ImageEnhance.Brightness(moving).enhance(1 - 0.8 * progress)
        result.paste(moving, (0, middle - height))
    else:
        height = max(1, round((card_height - middle) * math.sin((progress - 0.5) * math.pi)))
        moving = after.crop((0, middle, width, card_height)).resize(
            (width, height), Image.Resampling.LANCZOS
        )
        moving = ImageEnhance.Brightness(moving).enhance(0.6 + 0.8 * (progress - 0.5))
        result.paste(moving, (0, middle))
    ImageDraw.Draw(result).line((0, middle, width, middle), fill=theme["background"])
    return result


def selected_columns(config: Settings, table: dict[str, Any]) -> list[Settings]:
    """Use explicitly ordered columns or infer sensible widths from the source."""
    columns = config["columns"] or [
        {
            "field": name,
            "label": "",
            "width": max(8, min(24, max(len(name), *(len(row[name]) for row in table["rows"])))),
            "animate": True,
        }
        for name in table["fields"]
    ]
    missing = {col["field"] for col in columns} - set(table["fields"])
    if missing:
        raise ValueError(f"Fields missing from source: {', '.join(sorted(missing))}")
    return columns


def render_board(config: Settings, table: dict[str, Any]) -> dict[str, Any]:
    """Return the image, cell positions, and card cache needed for animation."""
    columns = selected_columns(config, table)
    theme = config["theme"]
    cards = create_cards(theme)
    margin, column_gap, row_padding, row_gap = 24, 20, 12, 8
    widths = [col["width"] * cards["step"] - 2 for col in columns]
    content_width = sum(widths) + column_gap * (len(columns) - 1)
    # Small one-column boards still leave room for a readable heading.
    width = max(640, content_width + margin * 2)
    if width > 4000:
        raise ValueError("Board exceeds 4,000 pixels wide. Reduce column widths or font_size.")

    def display(value: str) -> str:
        return value.upper() if config["uppercase"] else value

    heading_blocks: list[tuple[list[str], int, str]] = []
    for text, size, color in (
        (config["title"], theme["font_size"] + 6, theme["accent"]),
        (config["team"], theme["font_size"] + 14, theme["text"]),
        (config["subtitle"], theme["font_size"] - 2, theme["muted"]),
    ):
        if text:
            chars = max(1, int((width - margin * 2) / font(size).getlength("M")))
            heading_blocks.append((wrap(text, chars), size, color))
    labels = [wrap(display(col["label"] or col["field"]), col["width"]) for col in columns]
    label_step = theme["font_size"] + 6
    heading_height = sum(len(lines) * (size + 10) + 8 for lines, size, _ in heading_blocks)
    top = margin + heading_height + max(map(len, labels)) * label_step + 12
    values = [
        [wrap(display(row[col["field"]]), col["width"]) for col in columns] for row in table["rows"]
    ]
    heights = [max(map(len, row)) * cards["line_step"] + row_padding * 2 for row in values]
    footer_size = theme["font_size"] - 3
    footer_lines = (
        wrap(config["footer"], max(1, int((width - margin * 2) / font(footer_size).getlength("M"))))
        if config["footer"]
        else []
    )
    height = top + sum(heights) + row_gap * (len(values) - 1) + margin
    height += len(footer_lines) * (footer_size + 8) + (12 if footer_lines else 0)
    if width * height > MAX_FRAME_PIXELS:
        raise ValueError("Board exceeds six megapixels. Reduce rows, widths, or font_size.")
    image = Image.new("RGB", (width, height), theme["background"])
    draw = ImageDraw.Draw(image)
    y = margin
    for lines, size, color in heading_blocks:
        for line in lines:
            draw.text((margin, y), line, font=font(size), fill=color)
            y += size + 10
        y += 8
    x = margin
    for lines, column_width in zip(labels, widths, strict=True):
        for index, line in enumerate(lines):
            draw.text(
                (x, y + index * label_step),
                line,
                font=font(theme["font_size"]),
                fill=theme["accent"],
            )
        x += column_width + column_gap
    cells: list[dict[str, Any]] = []
    y = top
    for row_index, (row, row_height) in enumerate(zip(values, heights, strict=True)):
        draw.rounded_rectangle(
            (margin - 10, y, width - margin + 10, y + row_height),
            radius=5,
            fill=theme["panel"],
        )
        line_count = max(map(len, row))
        for line_index in range(line_count):
            hinge = y + row_padding + line_index * cards["line_step"] + cards["height"] // 2
            draw.line((margin - 10, hinge, width - margin + 10, hinge), fill=theme["background"])
        x = margin
        for col, lines, column_width in zip(columns, row, widths, strict=True):
            slots: list[dict[str, Any]] = []
            for line_index in range(line_count):
                line = lines[line_index] if line_index < len(lines) else ""
                for char_index, character in enumerate(line.ljust(col["width"])):
                    position = (
                        x + char_index * cards["step"],
                        y + row_padding + line_index * cards["line_step"],
                    )
                    image.paste(render_card(cards, character), position)
                    if not character.isspace():
                        slots.append({"position": position, "character": character})
            cells.append(
                {
                    "row": row_index,
                    "field": col["field"],
                    "animate": col["animate"],
                    "bounds": (x, y, x + column_width, y + row_height),
                    "slots": slots,
                }
            )
            x += column_width + column_gap
        y += row_height + row_gap
    for line in footer_lines:
        draw.text((margin, y + 8), line, font=font(footer_size), fill=theme["muted"])
        y += footer_size + 8
    return {"image": image, "cells": cells, "cards": cards}


def choose_cells(
    board: dict[str, Any], animation: Settings, rng: random.Random
) -> list[dict[str, Any]]:
    """Select dispersed whole values while respecting protected columns."""
    candidates = [cell for cell in board["cells"] if cell["animate"] and cell["slots"]]
    if not candidates:
        return []
    return rng.sample(candidates, rng.randint(1, min(animation["max_cells"], len(candidates))))


def validate_animation(board: dict[str, Any], animation: Settings) -> bool:
    """Check the memory budget and return whether there are eligible animated cells."""
    can_animate = animation["enabled"] and any(
        cell["animate"] and cell["slots"] for cell in board["cells"]
    )
    frame_count = (
        1 + animation["rounds"] * (animation["max_rotations"] * animation["frames_per_flip"] + 1)
        if can_animate
        else 1
    )
    if board["image"].width * board["image"].height * frame_count > MAX_ANIMATION_PIXELS:
        raise ValueError(
            "Animation is too large. Reduce rounds, rotations, font_size or rows, "
            "or set animation.enabled to false in the configuration."
        )
    return can_animate


def animation_frames(
    board: dict[str, Any], animation: Settings
) -> tuple[list[Image.Image], list[int]]:
    """Build palette frames, starting every letter together and settling independently."""
    can_animate = validate_animation(board, animation)
    palette = board["image"].quantize(colors=128)

    def quantize(image: Image.Image) -> Image.Image:
        return image.quantize(palette=palette, dither=Image.Dither.NONE)

    frames, durations = [quantize(board["image"])], [animation["pause_ms"]]
    if not can_animate:
        return frames, durations
    rng = random.Random(animation["seed"])
    for _ in range(animation["rounds"]):
        changes: list[tuple[dict[str, Any], list[str]]] = []
        for cell in choose_cells(board, animation, rng):
            for slot in cell["slots"]:
                rotations = rng.randint(animation["min_rotations"], animation["max_rotations"])
                sequence = [slot["character"]]
                sequence.extend(rng.choice(ALPHABET) for _ in range(rotations - 1))
                sequence.append(slot["character"])
                changes.append((slot, sequence))
        for index in range(animation["max_rotations"] * animation["frames_per_flip"]):
            frame = board["image"].copy()
            rotation, phase = divmod(index, animation["frames_per_flip"])
            for slot, sequence in changes:
                if rotation < len(sequence) - 1:
                    frame.paste(
                        render_flap(
                            board["cards"],
                            sequence[rotation],
                            sequence[rotation + 1],
                            phase,
                            animation["frames_per_flip"],
                        ),
                        slot["position"],
                    )
            frames.append(quantize(frame))
            durations.append(animation["frame_ms"])
        frames.append(quantize(board["image"]))
        durations.append(animation["pause_ms"])
    return frames, durations


def save_animation(frames: list[Image.Image], durations: list[int], path: Path) -> None:
    """Encode palette frames as a looping GIF, retaining stable still pauses."""
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        disposal=1,
        optimize=True,
    )
