# Flight Board

A split-flap status board for your repository. Bring your own table, choose your columns, and give your team's pipelines a departure board.

<!-- flight-board:start -->
<p align="center">
  <a href="board.csv"><img src="assets/flight-board/sign-1.png" width="32%" alt="Pipelines"></a>
  <a href="docs/configuration.md"><img src="assets/flight-board/sign-2.png" width="32%" alt="Configuration"></a>
  <a href="#use-this-template"><img src="assets/flight-board/sign-3.png" width="32%" alt="Quick start"></a>
</p>

<a href="board.csv"><img src="assets/flight-board/board.gif" width="100%" alt="DEPARTURES → PIPELINE STATUS — open source table"></a>

[Static board](assets/flight-board/board.png)
<!-- flight-board:end -->

## Use this template

1. Choose **Use this template → Create a new repository** on GitHub.
2. Edit [board.csv](board.csv) and [flight-board.yml](flight-board.yml). Set your heading, team, columns, and optional navigation signs.
3. Push to `main`, or run **Actions → Update flight board → Run workflow**.

The workflow renders a PNG and an animated GIF, updates only the marked section of this README, and commits the generated files. Your other README content stays in place. Change the workflow's branch and `paths` filters if you rename the source or configuration.

The example above contains fictional data. No account name, organization, dates, time zones, or source-column names are built into the renderer.

## Add the Action to an existing repository

You only need your data, a configuration file, and a workflow. The Action supplies the Python code and font.

```yaml
steps:
  - uses: actions/checkout@v4
  - uses: j3551ca/flightboard_template@v1
    id: board
    with:
      config: flight-board.yml
```

Copy the [complete workflow](examples/use-action.yml), which also commits the result. Use a release commit SHA instead of `v1` if your organization requires immutable dependencies. Organizations may need to allow this Action in their Actions policy.

The Action itself **does not commit, push, create repositories, or require a token**. The example workflow grants `contents: write` only so its separate commit step can save the generated images. A repository with protected branches may require a pull request instead of a direct push.

## Configure only what you need

```yaml
source: board.csv
title: DEPARTURES → RELEASE STATUS
team: Platform Engineering
columns:
  - field: Pipeline
    width: 22
  - field: Status
    width: 12
  - field: Deadline
    width: 18
    animate: false
```

Omit `columns` to show all source fields. Omit `buttons` for a board with no signs. CSV, JSON arrays of objects, and Markdown tables are supported. Use `buttons: []` or `--no-buttons` to hide signs from an existing configuration.

- [Configuration reference](docs/configuration.md) — headings, columns, colors, timing, signs, CLI, and Action inputs.
- [Monitor real workflows](docs/monitoring.md) — feed the board from GitHub Actions or another pipeline system.
- [Markdown example](examples/pipelines.md) and [JSON example](examples/pipelines.json).

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

MIT licensed. The bundled font retains its [own license](flight_board/fonts/LICENSE.txt).
