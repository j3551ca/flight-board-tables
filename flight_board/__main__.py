"""One command for local use and GitHub Actions: read → render → save."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

from .config import Settings, load_config, workspace_path
from .io import read_table, readme_block, sign, updated_readme
from .render import animation_frames, render_board, save_animation, validate_animation


def parser() -> argparse.ArgumentParser:
    """Select the workspace/configuration or validate without writing files."""
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "--workspace", type=Path, default=Path.cwd(), help="Consumer repository root."
    )
    result.add_argument(
        "--config", help="YAML file; defaults to flight-board-config.yml when present."
    )
    result.add_argument(
        "--validate-only",
        action="store_true",
        help="Check configuration and layout without writing files.",
    )
    return result


def resolve_config(args: argparse.Namespace, root: Path) -> Settings:
    """Load every board setting from YAML, using defaults for unspecified values."""
    path = workspace_path(root, args.config or "flight-board-config.yml")
    if args.config and not path.is_file():
        raise ValueError(f"Configuration not found: {args.config}")
    return load_config(path if path.is_file() else None)


def generate(config: Settings, root: Path, validate_only: bool = False) -> list[Path]:
    """Validate first, render to staging, then atomically replace each generated file."""
    source = workspace_path(root, config["source"])
    output = workspace_path(root, config["output_dir"])
    readme = workspace_path(root, config["readme"]) if config["readme"] else None
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
    generated += [output / f"sign-{i + 1}.png" for i in range(len(config["buttons"]))]
    for path in generated:
        if path.is_symlink():
            raise ValueError(f"Generated file cannot be a symlink: {path.name}")
    board = render_board(config, read_table(source, config["table_index"]))
    buttons = [sign(button, config["theme"]) for button in config["buttons"]]
    content = None
    if readme:
        if readme == source:
            raise ValueError("Keep source data separate from the managed README.")
        original = readme.read_text(encoding="utf-8") if readme.exists() else "# Flight board\n"
        content = updated_readme(original, readme_block(config, output, readme, source))
    validate_animation(board, config["animation"])
    if validate_only:
        print(
            f"Valid: {len(board['cells'])} cells, "
            f"{board['image'].width} × {board['image'].height} pixels."
        )
        return []
    frames, durations = animation_frames(board, config["animation"])
    with tempfile.TemporaryDirectory(prefix="flight-board-") as temporary:
        stage = Path(temporary)
        board["image"].save(stage / "board.png")
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
    print(f"Rendered {board['image'].width} × {board['image'].height} board in {output}.")
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
    """Run the pipeline, emitting file paths when invoked inside GitHub Actions."""
    args = parser().parse_args(argv)
    root = args.workspace.resolve()
    try:
        config = resolve_config(args, root)
        generate(config, root, args.validate_only)
        if not args.validate_only and os.environ.get("GITHUB_OUTPUT"):
            output = workspace_path(root, config["output_dir"]).relative_to(root).as_posix()
            readme = (
                workspace_path(root, config["readme"]).relative_to(root).as_posix()
                if config["readme"]
                else ""
            )
            with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as stream:
                stream.write(
                    f"assets-dir={output}\nreadme={readme}\n"
                    f"image={output}/board.{'gif' if config['animation']['enabled'] else 'png'}\n"
                )
    except (ValueError, OSError, yaml.YAMLError) as exc:
        print(f"flight-board: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
