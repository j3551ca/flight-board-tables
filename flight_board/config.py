"""Typed configuration, validation, and workspace-relative path handling."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, TypeVar
from urllib.parse import urlsplit

import yaml
from PIL import ImageColor


@dataclass(frozen=True)
class Column:
    """A source field, its display label, width in characters, and animation policy."""

    field: str
    label: str = ""
    width: int = 16
    animate: bool = True


@dataclass(frozen=True)
class Button:
    """An optional linked airport sign; URLs are relative to the README."""

    label: str
    url: str
    icon: str = "◆"
    arrow: str = "↗"


@dataclass(frozen=True)
class Animation:
    """Deterministic animation timing and limits, expressed in milliseconds."""

    enabled: bool = True
    rounds: int = 3
    max_cells: int = 4
    min_rotations: int = 3
    max_rotations: int = 6
    frames_per_flip: int = 6
    frame_ms: int = 60
    pause_ms: int = 4000
    seed: int = 27


@dataclass(frozen=True)
class Theme:
    """Board palette and typography; the bundled font makes rendering portable."""

    font_size: int = 22
    background: str = "#111921"
    panel: str = "#1b2732"
    card: str = "#293946"
    edge: str = "#3d4c58"
    text: str = "#f5edda"
    accent: str = "#f0c66a"
    muted: str = "#c1ced8"


@dataclass(frozen=True)
class Config:
    """Board settings. All filesystem paths are relative to the workspace root."""

    source: str = "board.csv"
    title: str = "DEPARTURES → PIPELINE STATUS"
    team: str = ""
    subtitle: str = ""
    footer: str = ""
    output_dir: str = "assets/flight-board"
    readme: str = "README.md"
    board_link: str = ""
    table_index: int = 0
    uppercase: bool = True
    columns: tuple[Column, ...] = ()
    buttons: tuple[Button, ...] = ()
    animation: Animation = field(default_factory=Animation)
    theme: Theme = field(default_factory=Theme)


T = TypeVar("T", Config, Column, Button, Animation, Theme)


def _construct(cls: type[T], data: Any) -> T:
    """Reject misspelled keys instead of silently ignoring configuration errors."""
    if not isinstance(data, dict):
        raise ValueError(f"{cls.__name__} must be a mapping.")
    unknown = set(data) - {item.name for item in fields(cls)}
    if unknown:
        raise ValueError(f"Unknown {cls.__name__} setting(s): {', '.join(sorted(unknown))}")
    try:
        return cls(**data)
    except TypeError as exc:
        raise ValueError(f"Invalid {cls.__name__}: {exc}") from exc


def load_config(path: Path | None) -> Config:
    """Load optional safe YAML, supplying defaults for every optional setting."""
    data = {} if path is None else yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("Configuration must be a YAML mapping.")
    for key in ("columns", "buttons"):
        if key in data and not isinstance(data[key], list):
            raise ValueError(f"{key} must be a list.")
    if "columns" in data:
        data["columns"] = tuple(_construct(Column, item) for item in data["columns"])
    if "buttons" in data:
        data["buttons"] = tuple(_construct(Button, item) for item in data["buttons"])
    if "animation" in data:
        data["animation"] = _construct(Animation, data["animation"])
    if "theme" in data:
        data["theme"] = _construct(Theme, data["theme"])
    config = _construct(Config, data)
    validate(config)
    return config


def _integer(name: str, value: int, minimum: int, maximum: int) -> None:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer from {minimum} to {maximum}.")


def validate_link(value: str) -> None:
    """Allow ordinary web links, relative paths and anchors, never executable URLs."""
    if not isinstance(value, str) or any(ord(char) < 32 for char in value):
        raise ValueError("Links must be text without control characters.")
    parsed = urlsplit(value)
    if parsed.scheme and parsed.scheme not in {"https", "http"}:
        raise ValueError("Links must use HTTPS/HTTP, a relative path, or an anchor.")
    if value.startswith("//"):
        raise ValueError("Use an explicit https:// URL instead of a protocol-relative link.")


def validate(config: Config) -> None:
    """Validate both YAML types and resource limits before rendering or writing files."""
    for key in (
        "source",
        "title",
        "team",
        "subtitle",
        "footer",
        "output_dir",
        "readme",
        "board_link",
    ):
        if not isinstance(getattr(config, key), str):
            raise ValueError(f"{key} must be text (quote YAML dates and numbers).")
    if not config.source or not config.output_dir:
        raise ValueError("source and output_dir cannot be empty.")
    if type(config.uppercase) is not bool or type(config.animation.enabled) is not bool:
        raise ValueError("uppercase and animation.enabled must be true or false.")
    _integer("table_index", config.table_index, 0, 100)
    _integer("theme.font_size", config.theme.font_size, 12, 40)
    for item in fields(Theme):
        if item.name != "font_size":
            try:
                ImageColor.getrgb(getattr(config.theme, item.name))
            except (ValueError, TypeError, AttributeError) as exc:
                raise ValueError(f"Invalid theme color: {item.name}") from exc
    for col in config.columns:
        if not isinstance(col.field, str) or not col.field:
            raise ValueError("Each column needs a nonempty field name.")
        if not isinstance(col.label, str) or type(col.animate) is not bool:
            raise ValueError("Column label must be text and animate must be true or false.")
        _integer("column.width", col.width, 4, 80)
    if len({col.field for col in config.columns}) != len(config.columns):
        raise ValueError("Column field names must be unique.")
    if len(config.buttons) > 6:
        raise ValueError("Use at most six navigation signs so they remain legible.")
    for button in config.buttons:
        if not all(
            isinstance(val, str) for val in (button.label, button.url, button.icon, button.arrow)
        ):
            raise ValueError("All button settings must be text.")
        if not button.label or not button.url:
            raise ValueError("Each button needs a label and URL.")
        if button.arrow not in {"↑", "↗", "→", "↘", "↓", "↙", "←", "↖"}:
            raise ValueError("Use a directional arrow glyph such as →, ↑, or ↗.")
        validate_link(button.url)
    validate_link(config.board_link)
    anim = config.animation
    for key, minimum, maximum in (
        ("rounds", 1, 8),
        ("max_cells", 1, 8),
        ("min_rotations", 1, 10),
        ("max_rotations", 1, 10),
        ("frames_per_flip", 4, 12),
        ("frame_ms", 20, 500),
        ("pause_ms", 500, 60000),
        ("seed", 0, 2**32 - 1),
    ):
        _integer(f"animation.{key}", getattr(anim, key), minimum, maximum)
    if anim.min_rotations > anim.max_rotations:
        raise ValueError("min_rotations cannot exceed max_rotations.")


def workspace_path(root: Path, value: str) -> Path:
    """Resolve a path inside the caller's workspace, including symlink checks."""
    if any(ord(char) < 32 for char in value):
        raise ValueError("Paths cannot contain control characters.")
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Path must stay inside the workspace: {value}")
    return path
