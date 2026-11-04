# Quick start

**Use the Action from your own repository. No AI agent, separate board repository, or Python setup is needed.**

1. Copy these files:

   | Copy | Save as |
   | --- | --- |
   | [Table](../starter/board.csv) | `board.csv` |
   | [Configuration](../starter/flight-board-config.yml) | `flight-board-config.yml` |
   | [Workflow](../starter/flight-board-workflow.yml) | `.github/workflows/flight-board.yml` |

2. Edit your table and set `team` in `flight-board-config.yml`. All columns display automatically. See [configuration](configuration.md) to choose columns, protect dates from animation, or add navigation signs.
3. Commit to `main`. Open **Actions → Update flight board** to follow progress, then view your README.

The workflow adds the board at the bottom of your README. To choose its position, insert:

```html
<!-- flight-board:start -->
<!-- flight-board:end -->
```

After setup, commit table or configuration changes to refresh the board. You can also select **Actions → Update flight board → Run workflow**.

**Using a subfolder?** Keep the workflow in `.github/workflows/`. Set its `config` input to your configuration's path, and set `source` and any output paths relative to the repository root—not the configuration folder. Update the workflow's `paths` filters too. [Subfolder example](configuration.md#using-a-subfolder).

**Different branch?** Update the workflow's `branches` filter.

**Nothing runs?** Check that Actions is enabled and your organization permits this Action.

**The bot cannot save changes?** It needs `contents: write`. Protected branches may require your organization's pull-request process instead of a direct push.

**Need live statuses?** The board normally reflects your table. Add the optional [workflow monitor](monitoring.md) to populate it automatically.
