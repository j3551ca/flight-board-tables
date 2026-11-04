"""Plain dictionary defaults, validation, and workspace-relative path handling."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml
from PIL import ImageColor

# Settings contain strings, numbers, booleans, and nested dictionaries/lists.
Settings = dict[str, Any]


def default_config() -> Settings:
    """Return fresh defaults so changing one board cannot affect another."""
    return {
        "source": "board.csv",
        "title": "DEPARTURES → PIPELINE STATUS",
        "team": "",
        "subtitle": "",
        "footer": "",
        "output_dir": "assets/flight-board",
        "readme": "README.md",
        "board_link": "",
        "table_index": 0,
        "uppercase": True,
        "columns": [],
        "buttons": [],
        "animation": {
            "enabled": True,
            "rounds": 3,
            "max_cells": 4,
            "min_rotations": 3,
            "max_rotations": 6,
            "frames_per_flip": 6,
            "frame_ms": 60,
            "pause_ms": 4000,
            "seed": 27,
        },
        "theme": {
            "font_size": 22,
            "background": "#111921",
            "panel": "#1b2732",
            "card": "#293946",
            "edge": "#3d4c58",
            "text": "#f5edda",
            "accent": "#f0c66a",
            "muted": "#c1ced8",
        },
    }


def merge_settings(defaults: Settings, values: object, name: str) -> Settings:
    """Fill missing keys and reject unknown keys or incorrect value types."""
    if not isinstance(values, dict):
        raise ValueError(f"{name} must be a mapping.")
    for key, value in values.items():
        if key not in defaults:
            raise ValueError(f"Unknown setting: {name}.{key}")
        expected = type(defaults[key])
        if type(value) is not expected:
            raise ValueError(f"{name}.{key} must be {expected.__name__}.")
    return {**defaults, **values}


def make_config(values: object = None) -> Settings:
    """Build a validated dictionary from partial settings, including nested defaults."""
    defaults = default_config()
    config = merge_settings(defaults, {} if values is None else values, "config")
    for key in ("animation", "theme"):
        config[key] = merge_settings(defaults[key], config[key], key)
    config["columns"] = [
        merge_settings({"field": "", "label": "", "width": 16, "animate": True}, item, "column")
        for item in config["columns"]
    ]
    config["buttons"] = [
        merge_settings({"label": "", "url": "", "icon": "◆", "arrow": "↗"}, item, "button")
        for item in config["buttons"]
    ]
    validate(config)
    return config


def load_config(path: Path | None) -> Settings:
    """Read optional YAML and fill unspecified settings with the documented defaults."""
    data = None if path is None else yaml.safe_load(path.read_text(encoding="utf-8"))
    return make_config(data)


def validate(config: Settings) -> None:
    """Check rendering bounds and links after make_config has checked value types."""
    if not config["source"] or not config["output_dir"]:
        raise ValueError("source and output_dir cannot be empty.")
    limits = [
        ("table_index", config["table_index"], 0, 100),
        ("font_size", config["theme"]["font_size"], 12, 40),
    ]
    limits += [("column.width", col["width"], 4, 80) for col in config["columns"]]
    limits += [
        (key, config["animation"][key], low, high)
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
    for name, value in config["theme"].items():
        if name != "font_size":
            ImageColor.getrgb(value)
    if any(not col["field"] for col in config["columns"]):
        raise ValueError("Each column needs a nonempty field name.")
    if len({col["field"] for col in config["columns"]}) != len(config["columns"]):
        raise ValueError("Column field names must be unique.")
    if len(config["buttons"]) > 6:
        raise ValueError("Use at most six navigation signs so they remain legible.")
    for button in config["buttons"]:
        if (
            not button["label"]
            or not button["url"]
            or len(button["arrow"]) != 1
            or button["arrow"] not in "↑↗→↘↓↙←↖"
        ):
            raise ValueError("Each button needs a label, URL, and a directional arrow such as ↗.")
    for link in (config["board_link"], *(button["url"] for button in config["buttons"])):
        if (
            any(ord(char) < 32 for char in link)
            or link.startswith("//")
            or urlsplit(link).scheme not in ("", "http", "https")
        ):
            raise ValueError(
                "Use an HTTPS/HTTP link, relative path, or anchor without control characters."
            )
    if config["animation"]["min_rotations"] > config["animation"]["max_rotations"]:
        raise ValueError("min_rotations cannot exceed max_rotations.")


def workspace_path(root: Path, value: str) -> Path:
    """Resolve a path inside the caller's workspace, including symlink checks."""
    if any(ord(char) < 32 for char in value):
        raise ValueError("Paths cannot contain control characters.")
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Path must stay inside the workspace: {value}")
    return path
