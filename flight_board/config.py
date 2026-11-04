"""Typed configuration, validation, and workspace-relative path handling."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, TypeVar, get_type_hints
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


@dataclass(frozen=True)
class Table:
    """Ordered field names and string-valued rows ready for presentation."""

    fields: tuple[str, ...]
    rows: tuple[dict[str, str], ...]


T = TypeVar("T", Config, Column, Button, Animation, Theme)


def _construct(cls: type[T], data: Any) -> T:
    """Build a settings object, rejecting unknown keys and non-mapping values."""
    if not isinstance(data, dict):
        raise ValueError(f"{cls.__name__} must be a mapping.")
    try:
        return cls(**data)
    except TypeError as exc:
        raise ValueError(str(exc)) from exc


def load_config(path: Path | None) -> Config:
    """Read optional YAML and fill unspecified settings with the documented defaults."""
    data = {} if path is None else yaml.safe_load(path.read_text(encoding="utf-8"))
    data = {} if data is None else data
    if not isinstance(data, dict):
        raise ValueError("Configuration must be a YAML mapping.")
    for key in ("columns", "buttons"):
        if key in data and not isinstance(data[key], list):
            raise ValueError(f"{key} must be a list.")
    data["columns"] = tuple(_construct(Column, item) for item in data.get("columns", []))
    data["buttons"] = tuple(_construct(Button, item) for item in data.get("buttons", []))
    data["animation"] = _construct(Animation, data.get("animation", {}))
    data["theme"] = _construct(Theme, data.get("theme", {}))
    config = _construct(Config, data)
    validate(config)
    return config


def validate(config: Config) -> None:
    """Check declared scalar types, useful rendering bounds, and safe links."""
    models: tuple[Config | Animation | Theme | Column | Button, ...] = (
        config,
        config.animation,
        config.theme,
        *config.columns,
        *config.buttons,
    )
    for model in models:
        hints = get_type_hints(type(model))
        for item in fields(model):
            expected = hints[item.name]
            if expected in (str, int, bool) and type(getattr(model, item.name)) is not expected:
                raise ValueError(f"{type(model).__name__}.{item.name} must be {expected.__name__}.")
    if not config.source or not config.output_dir:
        raise ValueError("source and output_dir cannot be empty.")
    limits = [
        ("table_index", config.table_index, 0, 100),
        ("font_size", config.theme.font_size, 12, 40),
    ]
    limits += [("column.width", col.width, 4, 80) for col in config.columns]
    limits += [
        (key, getattr(config.animation, key), low, high)
        for key, low, high in (
            ("rounds", 1, 8),
            ("max_cells", 1, 8),
            ("min_rotations", 1, 10),
            ("max_rotations", 1, 10),
            ("frames_per_flip", 4, 12),
            ("frame_ms", 20, 500),
            ("pause_ms", 500, 60000),
            ("seed", 0, 2**32 - 1),
        )
    ]
    for name, value, low, high in limits:
        if not low <= value <= high:
            raise ValueError(f"{name} must be between {low} and {high}.")
    for item in fields(Theme):
        if item.name != "font_size":
            ImageColor.getrgb(getattr(config.theme, item.name))
    if any(not col.field for col in config.columns):
        raise ValueError("Each column needs a nonempty field name.")
    if len({col.field for col in config.columns}) != len(config.columns):
        raise ValueError("Column field names must be unique.")
    if len(config.buttons) > 6:
        raise ValueError("Use at most six navigation signs so they remain legible.")
    for button in config.buttons:
        if (
            not button.label
            or not button.url
            or len(button.arrow) != 1
            or button.arrow not in "↑↗→↘↓↙←↖"
        ):
            raise ValueError("Each button needs a label, URL, and a directional arrow such as ↗.")
    for link in (config.board_link, *(button.url for button in config.buttons)):
        if (
            any(ord(char) < 32 for char in link)
            or link.startswith("//")
            or urlsplit(link).scheme not in ("", "http", "https")
        ):
            raise ValueError(
                "Use an HTTPS/HTTP link, relative path, or anchor without control characters."
            )
    if config.animation.min_rotations > config.animation.max_rotations:
        raise ValueError("min_rotations cannot exceed max_rotations.")


def workspace_path(root: Path, value: str) -> Path:
    """Resolve a path inside the caller's workspace, including symlink checks."""
    if any(ord(char) < 32 for char in value):
        raise ValueError("Paths cannot contain control characters.")
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Path must stay inside the workspace: {value}")
    return path
