# Local use and development

Ordinary users only need the [three starter files](quick-start.md). Clone this repository when you want to run or modify the Python implementation yourself.

## Run locally

With Python 3.11 or later, from this repository:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
flight-board --config demo/flight-board-config.yml
```

Both the Action and local use run the **same entry point**: `python -m flight_board`. Use `--workspace /path/to/your/repository` to render another local repository. Paths in the configuration are relative to that workspace.

```bash
flight-board --config demo/flight-board-config.yml --validate-only
flight-board --help
```

All board settings—including animation, buttons, titles, and output paths—belong in `flight-board-config.yml`. The CLI only selects the config/workspace and optionally validates without writing.

## Follow the code

| File | Responsibility |
| --- | --- |
| `flight_board/__main__.py` | Read arguments, load inputs, render, save images, update README. |
| `flight_board/config.py` | Typed defaults and validation. |
| `flight_board/io.py` | Read tables and prepare the README/signs. |
| `flight_board/render.py` | Board layout and split-flap animation. |

Pillow creates each frame. All letters in a selected cell begin together, rotate several times, and settle independently. A fixed seed makes animation repeatable. Protected columns never animate, and each round returns to the real values.

## Check changes

```bash
python -m pip install -e '.[dev]'
ruff check .
ruff format --check .
mypy flight_board extras
pytest -q
```

Tests cover inputs, layout, protected columns, GIF settling, optional signs, README preservation, and Action outputs. The bundled DejaVu font avoids dependence on system fonts; it supports Latin, Greek, and Cyrillic but not every script or emoji.
