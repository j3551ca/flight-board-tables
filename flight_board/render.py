"""Portable Pillow rendering for complete boards and independently settling flaps."""

from __future__ import annotations

import math
import random
import textwrap
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from .config import Animation, Column, Config, Table, Theme

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


@dataclass(frozen=True)
class Slot:
    """One nonblank character and its pixel position."""

    position: tuple[int, int]
    character: str


@dataclass(frozen=True)
class Cell:
    """One row/column value; animation selects whole cells, never individual letters."""

    row: int
    field: str
    animate: bool
    bounds: tuple[int, int, int, int]
    slots: tuple[Slot, ...]


@dataclass(frozen=True)
class Board:
    """The still board and locations needed to animate only selected cells."""

    image: Image.Image
    cells: tuple[Cell, ...]
    cards: Cards


class Cards:
    """Cache individual card images and simulate a rotating top/bottom flap."""

    def __init__(self, theme: Theme) -> None:
        self.theme = theme
        self.width = math.ceil(font(theme.font_size).getlength("M")) + 4
        self.height = math.ceil(theme.font_size * 1.6)
        self.step = self.width + 2
        self.line_step = self.height + 4
        self._cards: dict[str, Image.Image] = {}

    def card(self, character: str) -> Image.Image:
        """Return a static card with its text centered on the horizontal hinge."""
        if character not in self._cards:
            image = Image.new("RGB", (self.width, self.height), self.theme.background)
            draw = ImageDraw.Draw(image)
            draw.rounded_rectangle(
                (0, 0, self.width - 1, self.height - 1),
                radius=2,
                fill=self.theme.card,
                outline=self.theme.edge,
            )
            draw.text(
                (self.width / 2, self.height / 2),
                character,
                font=font(self.theme.font_size),
                anchor="mm",
                fill=self.theme.text,
            )
            draw.line(
                (0, self.height // 2, self.width, self.height // 2), fill=self.theme.background
            )
            self._cards[character] = image
        return self._cards[character]

    def flap(self, old: str, new: str, phase: int, phases: int) -> Image.Image:
        """Compress the old top, then expand the new bottom with directional shading."""
        progress = phase / (phases - 1)
        before, after = self.card(old), self.card(new)
        middle = self.height // 2
        result = before.copy()
        result.paste(after.crop((0, 0, self.width, middle)), (0, 0))
        if progress < 0.5:
            height = max(1, round(middle * math.cos(progress * math.pi)))
            moving = before.crop((0, 0, self.width, middle)).resize(
                (self.width, height), Image.Resampling.LANCZOS
            )
            moving = ImageEnhance.Brightness(moving).enhance(1 - 0.8 * progress)
            result.paste(moving, (0, middle - height))
        else:
            height = max(1, round((self.height - middle) * math.sin((progress - 0.5) * math.pi)))
            moving = after.crop((0, middle, self.width, self.height)).resize(
                (self.width, height), Image.Resampling.LANCZOS
            )
            moving = ImageEnhance.Brightness(moving).enhance(0.6 + 0.8 * (progress - 0.5))
            result.paste(moving, (0, middle))
        ImageDraw.Draw(result).line((0, middle, self.width, middle), fill=self.theme.background)
        return result


def selected_columns(config: Config, table: Table) -> tuple[Column, ...]:
    """Use explicitly ordered columns or infer sensible widths from the source."""
    columns = config.columns or tuple(
        Column(name, width=max(8, min(24, max(len(name), *(len(row[name]) for row in table.rows)))))
        for name in table.fields
    )
    missing = {col.field for col in columns} - set(table.fields)
    if missing:
        raise ValueError(f"Fields missing from source: {', '.join(sorted(missing))}")
    return columns


def render_board(config: Config, table: Table) -> Board:
    """Lay out any selected columns and variable-height rows without clipping cells."""
    columns = selected_columns(config, table)
    cards = Cards(config.theme)
    margin, column_gap, row_padding, row_gap = 24, 20, 12, 8
    widths = [col.width * cards.step - 2 for col in columns]
    content_width = sum(widths) + column_gap * (len(columns) - 1)
    # Small one-column boards still leave room for a readable heading.
    width = max(640, content_width + margin * 2)
    if width > 4000:
        raise ValueError("Board exceeds 4,000 pixels wide. Reduce column widths or font_size.")

    def display(value: str) -> str:
        return value.upper() if config.uppercase else value

    heading_blocks: list[tuple[list[str], int, str]] = []
    for text, size, color in (
        (config.title, config.theme.font_size + 6, config.theme.accent),
        (config.team, config.theme.font_size + 14, config.theme.text),
        (config.subtitle, config.theme.font_size - 2, config.theme.muted),
    ):
        if text:
            chars = max(1, int((width - margin * 2) / font(size).getlength("M")))
            heading_blocks.append((wrap(text, chars), size, color))
    labels = [wrap(display(col.label or col.field), col.width) for col in columns]
    label_step = config.theme.font_size + 6
    heading_height = sum(len(lines) * (size + 10) + 8 for lines, size, _ in heading_blocks)
    top = margin + heading_height + max(map(len, labels)) * label_step + 12
    values = [[wrap(display(row[col.field]), col.width) for col in columns] for row in table.rows]
    heights = [max(map(len, row)) * cards.line_step + row_padding * 2 for row in values]
    footer_size = config.theme.font_size - 3
    footer_lines = (
        wrap(config.footer, max(1, int((width - margin * 2) / font(footer_size).getlength("M"))))
        if config.footer
        else []
    )
    height = top + sum(heights) + row_gap * (len(values) - 1) + margin
    height += len(footer_lines) * (footer_size + 8) + (12 if footer_lines else 0)
    if width * height > MAX_FRAME_PIXELS:
        raise ValueError("Board exceeds six megapixels. Reduce rows, widths, or font_size.")
    image = Image.new("RGB", (width, height), config.theme.background)
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
                font=font(config.theme.font_size),
                fill=config.theme.accent,
            )
        x += column_width + column_gap
    cells: list[Cell] = []
    y = top
    for row_index, (row, row_height) in enumerate(zip(values, heights, strict=True)):
        draw.rounded_rectangle(
            (margin - 10, y, width - margin + 10, y + row_height), radius=5, fill=config.theme.panel
        )
        line_count = max(map(len, row))
        for line_index in range(line_count):
            hinge = y + row_padding + line_index * cards.line_step + cards.height // 2
            draw.line(
                (margin - 10, hinge, width - margin + 10, hinge), fill=config.theme.background
            )
        x = margin
        for col, lines, column_width in zip(columns, row, widths, strict=True):
            slots: list[Slot] = []
            for line_index in range(line_count):
                line = lines[line_index] if line_index < len(lines) else ""
                for char_index, character in enumerate(line.ljust(col.width)):
                    position = (
                        x + char_index * cards.step,
                        y + row_padding + line_index * cards.line_step,
                    )
                    image.paste(cards.card(character), position)
                    if not character.isspace():
                        slots.append(Slot(position, character))
            cells.append(
                Cell(
                    row_index,
                    col.field,
                    col.animate,
                    (x, y, x + column_width, y + row_height),
                    tuple(slots),
                )
            )
            x += column_width + column_gap
        y += row_height + row_gap
    for line in footer_lines:
        draw.text((margin, y + 8), line, font=font(footer_size), fill=config.theme.muted)
        y += footer_size + 8
    return Board(image, tuple(cells), cards)


def choose_cells(board: Board, animation: Animation, rng: random.Random) -> list[Cell]:
    """Select dispersed whole values while respecting protected columns."""
    candidates = [cell for cell in board.cells if cell.animate and cell.slots]
    if not candidates:
        return []
    return rng.sample(candidates, rng.randint(1, min(animation.max_cells, len(candidates))))


def validate_animation(board: Board, animation: Animation) -> bool:
    """Check the memory budget and return whether there are eligible animated cells."""
    can_animate = animation.enabled and any(cell.animate and cell.slots for cell in board.cells)
    frame_count = (
        1 + animation.rounds * (animation.max_rotations * animation.frames_per_flip + 1)
        if can_animate
        else 1
    )
    if board.image.width * board.image.height * frame_count > MAX_ANIMATION_PIXELS:
        raise ValueError(
            "Animation is too large. Reduce rounds, rotations, font_size or rows, "
            "or use --no-animation for a static board."
        )
    return can_animate


def animation_frames(board: Board, animation: Animation) -> tuple[list[Image.Image], list[int]]:
    """Build palette frames, starting every letter together and settling independently."""
    can_animate = validate_animation(board, animation)
    palette = board.image.quantize(colors=128)

    def quantize(image: Image.Image) -> Image.Image:
        return image.quantize(palette=palette, dither=Image.Dither.NONE)

    frames, durations = [quantize(board.image)], [animation.pause_ms]
    if not can_animate:
        return frames, durations
    rng = random.Random(animation.seed)
    for _ in range(animation.rounds):
        changes: list[tuple[Slot, list[str]]] = []
        for cell in choose_cells(board, animation, rng):
            for slot in cell.slots:
                rotations = rng.randint(animation.min_rotations, animation.max_rotations)
                sequence = [slot.character]
                sequence.extend(rng.choice(ALPHABET) for _ in range(rotations - 1))
                sequence.append(slot.character)
                changes.append((slot, sequence))
        for index in range(animation.max_rotations * animation.frames_per_flip):
            frame = board.image.copy()
            rotation, phase = divmod(index, animation.frames_per_flip)
            for slot, sequence in changes:
                if rotation < len(sequence) - 1:
                    frame.paste(
                        board.cards.flap(
                            sequence[rotation],
                            sequence[rotation + 1],
                            phase,
                            animation.frames_per_flip,
                        ),
                        slot.position,
                    )
            frames.append(quantize(frame))
            durations.append(animation.frame_ms)
        frames.append(quantize(board.image))
        durations.append(animation.pause_ms)
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
