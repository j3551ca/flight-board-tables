"""GitHub Action adapter: translate environment inputs into the shared CLI settings."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

from .cli import generate, parser, resolve_config


def run() -> int:
    """Render in the caller's checkout and publish paths without committing anything."""
    try:
        root = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
        argv = ["--workspace", str(root)]
        for key in ("config", "source", "title", "team", "output-dir", "readme"):
            value = os.environ.get("FB_" + key.upper().replace("-", "_"), "")
            if value:
                argv.extend([f"--{key}", value])
        for key in ("no-animation", "no-buttons", "no-readme"):
            value = os.environ.get("FB_" + key.upper().replace("-", "_"), "false")
            if value not in {"true", "false"}:
                raise ValueError(f"{key} must be 'true' or 'false'.")
            if value == "true":
                argv.append(f"--{key}")
        config = resolve_config(parser().parse_args(argv), root)
        generate(config, root)
        output = (root / config.output_dir).resolve().relative_to(root).as_posix()
        readme = (
            (root / config.readme).resolve().relative_to(root).as_posix() if config.readme else ""
        )
        image = f"{output}/board.{'gif' if config.animation.enabled else 'png'}"
        with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as stream:
            for name, value in (("assets-dir", output), ("readme", readme), ("image", image)):
                stream.write(f"{name}={value}\n")
    except (ValueError, OSError, KeyError, yaml.YAMLError) as exc:
        print(f"flight-board: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
