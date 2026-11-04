"""Command-line entry point; configuration paths belong to the consuming workspace."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import yaml

from .config import Config, load_config, validate, workspace_path
from .data import read_table
from .publish import readme_block, sign, updated_readme
from .render import animation_frames, render_board, save_animation, validate_animation


def parser() -> argparse.ArgumentParser:
    """Build the public CLI with a small default invocation and explicit overrides."""
    result = argparse.ArgumentParser(description="Render a configurable split-flap README board.")
    result.add_argument(
        "--workspace",
        type=Path,
        default=Path.cwd(),
        help="Consumer repository root (default: current directory).",
    )
    result.add_argument(
        "--config", default=None, help="YAML config (default: flight-board.yml if present)."
    )
    for name, help_text in (
        ("source", "CSV, JSON or Markdown source (default: board.csv)."),
        ("output-dir", "Generated assets directory (default: assets/flight-board)."),
        ("title", "Board heading."),
        ("team", "Organization or team name."),
        ("subtitle", "Optional subtitle."),
        ("footer", "Optional footer."),
        ("readme", "README to update (default: README.md)."),
        ("board-link", "Destination when the board is clicked (default: source file)."),
    ):
        result.add_argument(f"--{name}", help=help_text)
    result.add_argument("--table-index", type=int, help="Markdown table index, starting at 0.")
    result.add_argument("--font-size", type=int, help="Font size in pixels (default: 22).")
    result.add_argument("--seed", type=int, help="Deterministic animation seed (default: 27).")
    result.add_argument("--no-animation", action="store_true", help="Show the PNG in the README.")
    result.add_argument("--no-buttons", action="store_true", help="Omit configured signs.")
    result.add_argument("--no-readme", action="store_true", help="Generate assets only.")
    result.add_argument(
        "--validate-only", action="store_true", help="Check input/layout; write nothing."
    )
    return result


def resolve_config(args: argparse.Namespace, root: Path) -> Config:
    """Apply CLI overrides after YAML defaults, without mutating the source config."""
    path = workspace_path(root, args.config or "flight-board.yml")
    if args.config and not path.is_file():
        raise ValueError(f"Configuration not found: {args.config}")
    config = load_config(path if path.is_file() else None)
    overrides = {
        name: getattr(args, name)
        for name in (
            "source",
            "output_dir",
            "title",
            "team",
            "subtitle",
            "footer",
            "readme",
            "board_link",
            "table_index",
        )
        if getattr(args, name) is not None
    }
    config = replace(config, **overrides)
    if args.no_buttons:
        config = replace(config, buttons=())
    if args.no_readme:
        config = replace(config, readme="")
    if args.no_animation:
        config = replace(config, animation=replace(config.animation, enabled=False))
    if args.seed is not None:
        config = replace(config, animation=replace(config.animation, seed=args.seed))
    if args.font_size is not None:
        config = replace(config, theme=replace(config.theme, font_size=args.font_size))
    validate(config)
    return config


def generate(config: Config, root: Path, validate_only: bool = False) -> list[Path]:
    """Validate first, render to staging, then atomically replace each generated file."""
    source = workspace_path(root, config.source)
    output = workspace_path(root, config.output_dir)
    readme = workspace_path(root, config.readme) if config.readme else None
    # Dedicated assets keep the workflow's explicit git add from staging arbitrary sources.
    if (
        output == root
        or source.is_relative_to(output)
        or (readme and readme.is_relative_to(output))
    ):
        raise ValueError(
            "output_dir must be a dedicated directory outside source and README paths."
        )
    generated = [output / "board.png", output / "board.gif"]
    generated += [output / f"sign-{i + 1}.png" for i in range(len(config.buttons))]
    for path in generated:
        if path.is_symlink():
            raise ValueError(f"Generated file cannot be a symlink: {path.name}")
    board = render_board(config, read_table(source, config.table_index))
    buttons = [sign(button, config.theme) for button in config.buttons]
    content = None
    if readme:
        if readme == source:
            raise ValueError("Keep source data separate from the managed README.")
        original = readme.read_text(encoding="utf-8") if readme.exists() else "# Flight board\n"
        content = updated_readme(original, readme_block(config, output, readme, source))
    validate_animation(board, config.animation)
    if validate_only:
        print(
            f"Valid: {len(board.cells)} cells, {board.image.width} × {board.image.height} pixels."
        )
        return []
    frames, durations = animation_frames(board, config.animation)
    with tempfile.TemporaryDirectory(prefix="flight-board-") as temporary:
        stage = Path(temporary)
        board.image.save(stage / "board.png")
        save_animation(frames, durations, stage / "board.gif")
        for index, image in enumerate(buttons, 1):
            image.save(stage / f"sign-{index}.png")
        output.mkdir(parents=True, exist_ok=True)
        for path in generated:
            _replace_file(stage / path.name, path)
        # Remove only generated sign filenames, never unrelated assets.
        for index in range(len(buttons) + 1, 7):
            obsolete = output / f"sign-{index}.png"
            if obsolete.is_file() or obsolete.is_symlink():
                obsolete.unlink()
        if readme and content is not None:
            (stage / "readme").write_text(content, encoding="utf-8")
            _replace_file(stage / "readme", readme)
            generated.append(readme)
    print(f"Rendered {board.image.width} × {board.image.height} board in {output}.")
    return generated


def _replace_file(source: Path, destination: Path) -> None:
    """Use a same-directory temporary file for atomic replacement across filesystems."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".flight-board-", dir=destination.parent)
    try:
        with os.fdopen(fd, "wb") as stream, source.open("rb") as original:
            shutil.copyfileobj(original, stream)
        os.chmod(temporary, 0o644)
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    """Run the CLI, returning concise actionable errors without a traceback."""
    args = parser().parse_args(argv)
    root = args.workspace.resolve()
    try:
        config = resolve_config(args, root)
        generate(config, root, args.validate_only)
    except (ValueError, OSError, yaml.YAMLError) as exc:
        print(f"flight-board: {exc}", file=sys.stderr)
        return 2
    return 0
