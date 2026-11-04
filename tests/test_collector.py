"""Exercise live-data adaptation without making external API requests."""

from __future__ import annotations

from typing import Any

import pytest

from extras.monitoring import collect_workflows


def test_collector_preserves_status_links_and_never_run_workflows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_get(path: str, token: str) -> dict[str, Any]:
        calls.append(path)
        assert token == "test-token"
        if "/runs?" not in path:
            return {
                "workflows": [
                    {
                        "name": "Build",
                        "state": "active",
                        "id": 1,
                        "html_url": "https://example.org/1",
                    },
                    {
                        "name": "New",
                        "state": "active",
                        "id": 2,
                        "html_url": "https://example.org/2",
                    },
                    {"name": "Monitor", "state": "active", "id": 3},
                    {"name": "Old", "state": "disabled_manually", "id": 4},
                ]
            }
        if "/1/runs?" in path:
            return {
                "workflow_runs": [
                    {
                        "conclusion": "success",
                        "status": "completed",
                        "head_branch": "main",
                        "updated_at": "2026-11-04T12:00:00Z",
                        "html_url": "https://example.org/run/1",
                    }
                ]
            }
        return {"workflow_runs": []}

    monkeypatch.setattr(collect_workflows, "github_get", fake_get)
    rows = collect_workflows.collect("team/repo", "test-token", "main", {"Monitor"})
    assert len(rows) == 2
    assert rows[0]["Status"] == "success"
    assert rows[0]["Updated / UTC"] == "2026-11-04\n12:00:00"
    assert rows[0]["Run URL"] == "https://example.org/run/1"
    assert rows[1]["Status"] == "Not run"
    assert len(calls) == 3 and "branch=main" in calls[1]


def test_collector_rejects_api_path_injection() -> None:
    with pytest.raises(ValueError, match="owner/repository"):
        collect_workflows.collect("org/repo?anything=else", "", "", set())


def test_collector_propagates_api_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(path: str, token: str) -> dict[str, Any]:
        raise OSError("API unavailable")

    monkeypatch.setattr(collect_workflows, "github_get", fail)
    with pytest.raises(OSError, match="API unavailable"):
        collect_workflows.collect("team/repo", "", "", set())
