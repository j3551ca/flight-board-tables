# Put a flight board in your own repository

For the short version, use the **[quick-start guide](quick-start.md)**. This page covers the full setup and troubleshooting.

Choose **A** if you want a new repository containing the renderer and examples. Choose **B** if you already have a repository and only want to add a board to its README.

## A. Create a repository from the template

1. Open [flightboard_template](https://github.com/j3551ca/flightboard_template).
2. Click **Use this template → Create a new repository**.
3. Select **your account or organization** as the owner, enter a repository name, and choose its visibility. A public Action can render boards in either public or private consumer repositories.
4. In your new repository, edit `board.csv` with your own rows.
5. Edit `flight-board.yml` with your title and team name. Match each `columns[].field` to a CSV header exactly. Remove the `buttons` section if you do not want navigation signs.
6. Commit those changes to `main`. In **Actions**, open **Update flight board** and wait for its run to finish. You can also select **Run workflow** to generate it manually.
7. Return to the README. The workflow will have committed your generated board and optional signs.

If your repository's default branch is not `main`, update `branches` in `.github/workflows/update-board.yml`. If you rename your data or configuration file, update both `flight-board.yml` and the workflow's `paths` filters.

Replace the template README's explanatory text with your own introduction if desired. Keep the `flight-board:start` and `flight-board:end` markers where you want the board to appear. Only the content between those markers is regenerated.

## B. Add the reusable Action to an existing repository

You do **not** need to copy the Python scripts, install fonts, or create a separate board repository. Add the following files to the repository whose README should display the board.

### 1. Add `board.csv`

```csv
Pipeline,Status,Next run
Sample processing,Running,Daily 06:00 UTC
Model training,Queued,Monday 10:00 UTC
Release build,Passed,On release
```

You can later switch to JSON or a Markdown table. The renderer displays whatever values you supply; it does not infer dates, convert time zones, or poll pipeline systems automatically.

### 2. Add `flight-board.yml`

```yaml
source: board.csv
team: Your Organization / Team
# Optional: change the default heading.
title: DEPARTURES → PIPELINE STATUS
columns:
  - field: Pipeline
    width: 20
  - field: Status
    width: 12
  - field: Next run
    label: SCHEDULE / UTC
    width: 20
    animate: false
```

This example has no buttons. For the smallest possible configuration, use only `source` and `team`; columns will be inferred. To add signs, see [the sign configuration](configuration.md#airport-signs).

### 3. Choose where the board goes in `README.md`

Add these markers, with an empty line before and after them:

```html
<!-- flight-board:start -->
<!-- flight-board:end -->
```

You can put other content above and below them. If you omit the markers, the Action appends the board at the bottom of the README. The board links to your source table by default.

### 4. Add `.github/workflows/flight-board.yml`

```yaml
name: Update flight board

on:
  push:
    branches: [main]
    paths:
      - board.csv
      - flight-board.yml
      - .github/workflows/flight-board.yml
  workflow_dispatch:

permissions:
  contents: write

concurrency:
  group: flight-board-${{ github.ref }}
  cancel-in-progress: false

jobs:
  render:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: j3551ca/flightboard_template@v1
        id: board
        with:
          config: flight-board.yml
      - name: Save the updated board
        env:
          ASSETS: ${{ steps.board.outputs.assets-dir }}
          README: ${{ steps.board.outputs.readme }}
        run: |
          git config user.name 'github-actions[bot]'
          git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
          git add -- "$ASSETS"
          if [ -n "$README" ]; then git add -- "$README"; fi
          if ! git diff --cached --quiet; then
            git commit -m 'Refresh flight board'
            git push
          fi
```

Replace `main` if necessary. For an immutable Action version, replace `@v1` with a verified release commit SHA. The [standalone workflow file](../examples/use-action.yml) is also ready to copy.

### 5. Commit and check the result

Commit the CSV, configuration, README markers, and workflow. Open **Actions → Update flight board**. After a successful run, you should see:

- `assets/flight-board/board.gif` and `board.png` in your repository.
- The board in your README, with a link to the still PNG.
- A bot commit titled **Refresh flight board**, unless nothing changed.

To test manually, select **Run workflow** after the workflow file is on your default branch.

## Updating your board

Change the source table and commit it. The workflow regenerates the entire board, including any changed values in every displayed column. Change `flight-board.yml` to update headings, columns, labels, widths, buttons, colors, or animation. The workflow also reruns for configuration changes.

Changing unrelated files does not rerender the board. Update the workflow's `paths` filters whenever you move or rename inputs. Keep generated assets out of those filters. No special secrets or personal access token are needed for ordinary rendering and committing in the same repository.

To monitor actual workflow runs, follow [Monitor real workflows](monitoring.md). That optional adapter populates the data from GitHub's API before rendering. You can connect other pipeline systems by having them write a CSV or JSON summary first.

## Common setup problems

| Problem | What to check |
| --- | --- |
| Nothing runs | Workflow is on the default branch, Actions is enabled, and the changed file matches the branch and path filters. Use **Run workflow** to test. |
| The Action is blocked | Your organization's Actions policy must allow `j3551ca/flightboard_template` and its official checkout/setup-python dependencies. |
| The bot cannot push | Check repository **Settings → Actions → General → Workflow permissions**, organization restrictions, and branch protection. The example needs `contents: write`. For protected branches, use your organization's normal pull-request workflow to save the generated files instead. |
| A source field is missing | `columns[].field` must exactly match the CSV header or JSON/Markdown field name, including case. |
| The board still shows example data | Confirm `source` points to your file and your latest workflow succeeded. Refresh the page if GitHub's image cache is stale. |
| Signs look crowded | Use fewer signs or shorter labels. Omit `buttons` entirely for a clean board-only layout. |
| The board is too large | Reduce displayed columns, their widths, rows, font size, or animation rounds. A concise summary can link to the full source table. |
| The Action ran but nothing is saved | Rendering and committing are separate steps. Include the commit step from the example, or your own artifact/PR publishing step. |

See the [full configuration reference](configuration.md) for every setting and CLI override.
