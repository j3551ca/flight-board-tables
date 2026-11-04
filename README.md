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

**[Quick start →](docs/quick-start.md)** · [Full setup guide](docs/getting-started.md) · [Configuration](docs/configuration.md)

No AI agent, model, or API key is needed. Python renders the images; GitHub Actions runs it automatically when your data or configuration changes. You can also run it locally.

## Use this template

1. Click **Use this template → Create a new repository**.
2. Edit [board.csv](board.csv) and [flight-board.yml](flight-board.yml) with your data, heading, and team.
3. Commit to `main`. The workflow updates the board in your README.

## Add to an existing repository

Copy [board.csv](board.csv), [flight-board.yml](flight-board.yml), and the [example workflow](examples/use-action.yml) into your repository. Save the workflow as `.github/workflows/board.yml`, customize your data/configuration, and commit to `main`.

The workflow uses `j3551ca/flightboard_template@v1` and commits the generated board. [Quick start](docs/quick-start.md#existing-repository) covers placement and permissions.

## Customize

- Supply CSV, JSON, or a Markdown table.
- Choose your columns, labels, widths, heading, team, and colors.
- Omit `buttons` to hide the airport signs.
- Set a column's `animate: false` to keep important values still.

[All settings](docs/configuration.md) · [Monitor real workflows](docs/monitoring.md) · [Local use and development](docs/development.md)

MIT licensed. The bundled font retains its [own license](flight_board/fonts/LICENSE.txt).
