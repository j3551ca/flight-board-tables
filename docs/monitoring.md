# Populate the board from real pipelines

The renderer turns a local table into images. It does not query pipeline systems by itself. Keep your data producer separate from the renderer so you can use GitHub Actions, Nextflow, a release tracker, a laboratory information system, or another source.

## GitHub Actions example

For a repository created from this template:

1. Copy `examples/github-workflows-config.yml` to `flight-board.yml` and set your team name.
2. Copy `examples/github-workflows.yml` to `.github/workflows/monitor.yml`.
3. Run **Actions → Monitor pipelines → Run workflow**.
4. In `update-board.yml`, change the source path filter from `board.csv` to `board.json` if you also want manual JSON edits to refresh the board.

The collector reads the latest run of each active workflow, including its status, branch, update time, and run link. It writes `board.json`, then the normal renderer builds the board. Workflows with no runs show “Not run.” API failures fail the job instead of publishing false statuses. The monitor excludes itself and the rendering workflow by name.

The example schedule checks every six hours. GitHub may delay scheduled workflows, so treat the board as a snapshot, not a real-time alerting system. Optionally enable the commented `workflow_run` trigger with your actual workflow names to refresh after those runs complete. Do not include the monitor's own name or consume code/artifacts from untrusted pull requests in a privileged monitoring workflow.

```bash
python scripts/collect_workflows.py \
  --repository YOUR-ORG/YOUR-REPO \
  --branch main \
  --exclude 'Monitor pipelines' \
  --output board.json
```

`--repository` defaults to `GITHUB_REPOSITORY`. `GH_TOKEN` is optional for public API reads but is needed for private repositories and appropriate rate limits. In Actions, use `${{ github.token }}` with `actions: read`; `contents: write` is only needed by the later commit step. The example collector targets github.com; GitHub Enterprise Server users should adapt the API endpoint before use.

For an existing repository consuming the reusable Action, copy the collector script too (or use your own data producer), and replace `uses: ./` with `uses: j3551ca/flightboard_template@v1` in the monitoring example.

## Other pipeline systems

Have your existing workflow write a CSV or JSON summary before invoking Flight Board:

```json
[
  {"Pipeline": "Sample QC", "Status": "Passed", "Updated": "2026-11-04 14:00 UTC"},
  {"Pipeline": "Assembly", "Status": "Running", "Updated": "2026-11-04 14:02 UTC"}
]
```

Keep detailed logs in their original system. Use a `Run URL` field in the linked source or a navigation sign pointing to the dashboard. Each image is a single hyperlink; GIF frames cannot contain independently clickable cells.

The default update workflow triggers only when its listed source/config/code paths change or when manually run. If you rename files, add additional data sources, or change the default branch, update those filters. Generated assets are excluded to avoid a render/commit loop. Scheduled monitoring is opt-in, not enabled in the template by default.
