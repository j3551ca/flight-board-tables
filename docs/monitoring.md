# Monitor real GitHub workflows

The Action renders a table. This optional collector fills that table from GitHub's API so it reflects real workflow runs.

Copy these files into **your** repository instead of the ordinary starter files:

| Copy | Save as |
| --- | --- |
| [Collector](../extras/monitoring/collect_workflows.py) | `collect_workflows.py` |
| [Configuration](../extras/monitoring/flight-board-config.yml) | `flight-board-config.yml` |
| [Workflow](../extras/monitoring/flight-board-workflow.yml) | `.github/workflows/flight-board.yml` |

Set your team name, commit, and run **Actions → Monitor pipelines → Run workflow**. The workflow fetches statuses, writes `board.json`, runs the Action, and commits the table and images. It also checks every six hours. Do not install the ordinary starter workflow alongside this one.

Lifecycle labels such as “Development” and “Production” describe your pipeline and should come from your own table or data producer. This collector reports execution results such as “Running” and “Success,” not deployment environments.

The collector shows the latest run per active workflow, including status, branch, UTC update time, and a run link. Workflows with no runs show “Not run.” API failures fail the job without replacing the previous snapshot with false statuses.

GitHub supplies the token automatically. The workflow requests `actions: read` for collecting and `contents: write` for saving. GitHub may delay scheduled jobs, so this is a status snapshot, not real-time alerting.

To refresh after specific workflows finish, enable the commented `workflow_run` trigger and enter their names. Exclude the monitor itself to avoid a loop. Never consume untrusted pull-request code or artifacts in a privileged monitoring workflow.

For other pipeline systems, have your own producer write CSV or JSON before invoking the Action. The included collector targets github.com, not GitHub Enterprise Server.
