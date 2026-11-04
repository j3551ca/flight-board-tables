# Flight Board

A GitHub Action that turns your table into an animated flight board in your README. No AI agent or AI API key required.

<!-- flight-board:start -->
<p align="center">
  <a href="demo/board.csv"><img src="assets/flight-board/sign-1.png" width="32%" alt="Pipelines"></a>
  <a href="docs/configuration.md"><img src="assets/flight-board/sign-2.png" width="32%" alt="Configuration"></a>
  <a href="#quick-start"><img src="assets/flight-board/sign-3.png" width="32%" alt="Quick start"></a>
</p>

<a href="demo/board.csv"><img src="assets/flight-board/board.gif" width="100%" alt="DEPARTURES → PIPELINE STATUS — open source table"></a>

[Static board](assets/flight-board/board.png)
<!-- flight-board:end -->

## Quick start

Copy **three files** into your own repository:

| File to copy | Destination in your repository |
| --- | --- |
| [Table](starter/board.csv) | `board.csv` |
| [Configuration](starter/flight-board.yml) | `flight-board.yml` |
| [Workflow](starter/flight-board-workflow.yml) | `.github/workflows/flight-board.yml` |

Edit the table and team name, then commit to `main`. The workflow generates the board and adds it to your README. **You do not need to clone this repository or copy its Python code.**

[Setup details and troubleshooting](docs/quick-start.md) · [Optional settings](docs/configuration.md)

## How it works

Your workflow calls `j3551ca/flightboard_template@v2`. The Action reads **your** table and configuration, generates images in **your** repository, and updates **your** README. The workflow commits those changes.

The board above is just this repository's demo. Your data and images stay in your repository.

## What lives here

- `flight_board/` — the Python implementation, supplied by the Action.
- `starter/` — the three files users copy.
- `demo/` — data for the demonstration above.
- `extras/monitoring/` — optional collection of real GitHub workflow statuses.

[Automatic pipeline monitoring](docs/monitoring.md) · [Local use and development](docs/development.md)

MIT licensed. The bundled font retains its [own license](flight_board/fonts/LICENSE.txt).
