# Quick start

**No AI agent or API key required.** The board runs with Python and GitHub Actions.

## New repository

1. Open [flightboard_template](https://github.com/j3551ca/flightboard_template) and select **Use this template → Create a new repository**.
2. Edit `board.csv` with your rows and `flight-board.yml` with your heading, team, and columns.
3. Commit to `main`. Open **Actions → Update flight board** to see progress, then view your README.

## Existing repository

1. Copy these three files into your repository:

   | Copy from this template | Save in your repository as |
   | --- | --- |
   | [board.csv](../board.csv) | `board.csv` |
   | [flight-board.yml](../flight-board.yml) | `flight-board.yml` |
   | [Example workflow](../examples/use-action.yml) | `.github/workflows/board.yml` |

2. Replace the example data and team name. Match `columns[].field` to your table headers. Remove `buttons` unless you want navigation signs, and replace example links with your own.
3. Commit to `main`. The workflow adds the board to your README and saves the images automatically.

To choose its position, add these markers to your README before running:

```html
<!-- flight-board:start -->
<!-- flight-board:end -->
```

Otherwise, the board is appended at the bottom.

## After setup

Edit your table or configuration and commit; the board refreshes. You can also run it from **Actions → Update flight board → Run workflow**.

If you use a different branch or filenames, update the workflow's `branches` and `paths`. The bot needs permission to push; protected branches may require your organization's pull-request process.

**Want live pipeline statuses?** Add the optional [workflow monitor](monitoring.md). Otherwise, the board reflects your maintained table.

[Full setup and troubleshooting](getting-started.md) · [All settings](configuration.md) · [Run locally](development.md)
