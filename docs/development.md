# Local use and development

## Run locally

Requires Python 3.11 or later.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
flight-board
```

With no arguments, the CLI reads `flight-board.yml` when present, otherwise `board.csv`, and writes to `assets/flight-board/`. No configuration file is required to get started.

```bash
flight-board --config examples/json-config.yml --team 'Research Engineering'
flight-board --no-animation             # Show the still PNG instead of the GIF
flight-board --validate-only            # Validate data and layout without writing files
flight-board --help
```

The sample configuration explicitly selects CSV fields. When changing formats or field names, update its `columns` section too, or use a new configuration with no explicit columns. All filesystem paths are relative to the selected workspace, not the configuration file's directory.

## How the animation works

Pillow renders a board of character cards. Each animation round selects a few eligible **cells**, starts all their letters together, and lets each letter settle after a seeded random number of rotations. Each rotation compresses the outgoing top half and expands the incoming bottom half with shading. Frames are encoded into a looping GIF; the original values are restored between rounds and at the loop boundary.

Animation never changes the data. Mark any column `animate: false` to keep its values visible. A linked still image is always available, and you can disable animation entirely. GitHub cannot pause a GIF based on the viewer's reduced-motion preference. The board image links to the source table; individual GIF cells cannot carry independent links. Navigation signs are separate linked images.

## Development

```bash
python -m pip install -e '.[dev]'
ruff check .
ruff format --check .
mypy flight_board scripts
pytest -q
```

The implementation separates input parsing, validated configuration, board rendering, README updates, and Action integration. Tests cover changed field names, wrapping, protected columns, GIF settling, optional signs, deterministic rendering, and use from a separate consumer checkout. The bundled DejaVu font avoids dependence on system fonts. Its supported glyphs include Latin, Greek, and Cyrillic, but it is not a universal CJK or emoji font.

MIT licensed. The bundled font retains its [own license](../flight_board/fonts/LICENSE.txt).
