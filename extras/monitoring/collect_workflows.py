"""Optional adapter: summarize the latest GitHub Actions run for each workflow."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def github_get(path: str, token: str) -> dict[str, Any]:
    """Read JSON from GitHub's REST API using a token scoped to the caller's repository."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "repo-flight-board",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"https://api.github.com/{path}", headers=headers)
    with urlopen(request, timeout=30) as response:
        result: dict[str, Any] = json.load(response)
    return result


def collect(repository: str, token: str, branch: str, excluded: set[str]) -> list[dict[str, str]]:
    """Collect active workflows and their latest run, explicitly handling never-run workflows."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("repository must have the form owner/repository.")
    workflows: list[dict[str, Any]] = []
    page = 1
    while True:
        batch = github_get(f"repos/{repository}/actions/workflows?per_page=100&page={page}", token)
        items = batch["workflows"]
        workflows.extend(items)
        if len(items) < 100:
            break
        page += 1
    rows: list[dict[str, str]] = []
    for workflow in workflows:
        if workflow["state"] != "active" or workflow["name"] in excluded:
            continue
        query = urlencode({"per_page": 1, **({"branch": branch} if branch else {})})
        runs = github_get(
            f"repos/{repository}/actions/workflows/{workflow['id']}/runs?{query}", token
        )
        latest = runs["workflow_runs"][0] if runs["workflow_runs"] else None
        rows.append(
            {
                "Workflow": workflow["name"],
                "Status": (latest["conclusion"] or latest["status"]) if latest else "Not run",
                "Branch": latest["head_branch"] or "—" if latest else "—",
                "Updated / UTC": latest["updated_at"].replace("T", "\n").removesuffix("Z")
                if latest
                else "—",
                "Run URL": latest["html_url"] if latest else workflow["html_url"],
            }
        )
    if not rows:
        raise ValueError("No active workflows matched. Check the repository and exclusions.")
    return rows


def main() -> int:
    """Write a snapshot only after all API requests succeed; retain old data on failure."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--output", type=Path, default=Path("board.json"))
    parser.add_argument("--branch", default="", help="Only inspect runs on this branch.")
    parser.add_argument(
        "--exclude", action="append", default=[], help="Workflow name to omit; repeatable."
    )
    args = parser.parse_args()
    try:
        rows = collect(
            args.repository, os.environ.get("GH_TOKEN", ""), args.branch, set(args.exclude)
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(
            json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        temporary.replace(args.output)
    except (ValueError, OSError, URLError, KeyError) as exc:
        print(f"collect-workflows: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
