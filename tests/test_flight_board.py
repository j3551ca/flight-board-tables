"""Functional contracts for portable input, layout, animation, and publication."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from random import Random

import pytest
from PIL import Image, ImageChops

from flight_board.action import run
from flight_board.cli import generate, main
from flight_board.config import (
    Animation,
    Button,
    Column,
    Config,
    Theme,
    load_config,
    workspace_path,
)
from flight_board.data import Table, read_table
from flight_board.publish import END, START, updated_readme
from flight_board.render import animation_frames, choose_cells, render_board, save_animation


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """An unrelated consumer checkout, separate from the Action's source code."""
    (tmp_path / "board.csv").write_text("Pipeline,Status\nAlpha,Ready\nBeta,Running\n")
    (tmp_path / "README.md").write_text(f"# My team\n\n{START}\nOld board\n{END}\n\nKeep me.\n")
    return tmp_path


def test_input_formats_and_escaped_markdown(tmp_path: Path) -> None:
    source = tmp_path / "input.md"
    source.write_text(
        "Intro\n\n| Name | Date |\n| --- | --- |\n"
        "| [A \\| B](https://example.org) | **Tuesday**<br>14:00 UTC |\n\n"
        "| Other |\n| --- |\n| Second |\n"
    )
    assert read_table(source).rows == ({"Name": "A | B", "Date": "Tuesday\n14:00 UTC"},)
    assert read_table(source, 1).rows == ({"Other": "Second"},)
    source = tmp_path / "input.json"
    source.write_text(json.dumps([{"name": "A", "count": 0}, {"count": None, "name": "B"}]))
    assert read_table(source).rows[1] == {"name": "B", "count": ""}
    source = tmp_path / "input.csv"
    source.write_text('name,description\nA,"Quoted, with\nline break"\n')
    assert read_table(source).rows[0]["description"] == "Quoted, with\nline break"


@pytest.mark.parametrize("contents", ["a,a\nx,y\n", "a,b\nx\n", "a,b\n", ",b\nx,y\n"])
def test_invalid_csv_is_rejected(tmp_path: Path, contents: str) -> None:
    path = tmp_path / "bad.csv"
    path.write_text(contents)
    with pytest.raises(ValueError):
        read_table(path)


@pytest.mark.parametrize(
    "contents",
    [
        "typo: true",
        "animation: {max_cells: 0}",
        "columns: {field: name}",
        "columns: [{field: x, animate: 'false'}]",
        "theme: {font_size: true}",
        "buttons: [{label: Bad, url: 'javascript:alert(1)'}]",
        "title: 123",
        "animation: {min_rotations: 6, max_rotations: 3}",
        "animation: {enabled: 'false'}",
    ],
)
def test_invalid_configuration_is_actionable(tmp_path: Path, contents: str) -> None:
    path = tmp_path / "config.yml"
    path.write_text(contents)
    with pytest.raises(ValueError):
        load_config(path)


def test_layout_has_no_fixed_rows_or_columns() -> None:
    table = Table(
        ("Task", "Notes"),
        (
            {"Task": "Alpha", "Notes": "A long value with many words and an explicit\nline break"},
            {"Task": "Beta", "Notes": "短い"},
            *({"Task": f"Task {i}", "Notes": "OK"} for i in range(12)),
        ),
    )
    config = Config(columns=(Column("Notes", width=12), Column("Task", width=10)))
    board = render_board(config, table)
    assert len(board.cells) == 28  # More than the original eleven hard-coded rows.
    assert board.cells[0].field == "Notes"
    assert board.cells[0].bounds[3] - board.cells[0].bounds[1] > (
        board.cells[2].bounds[3] - board.cells[2].bounds[1]
    )
    for cell in board.cells:
        for slot in cell.slots:
            x, y = slot.position
            assert 0 <= x < x + board.cards.width <= board.image.width
            assert 0 <= y < y + board.cards.height <= board.image.height


def test_missing_field_and_large_board_fail_before_writing(workspace: Path) -> None:
    config = Config(columns=(Column("Missing"),))
    with pytest.raises(ValueError, match="Fields missing"):
        generate(config, workspace)
    assert not (workspace / "assets").exists()
    with pytest.raises(ValueError, match="4,000"):
        render_board(
            Config(
                columns=(Column("Pipeline", width=80), Column("Status", width=80)),
                theme=Theme(font_size=40),
            ),
            read_table(workspace / "board.csv"),
        )


def test_flap_endpoints_and_settling(tmp_path: Path) -> None:
    config = Config(
        columns=(Column("Task", width=8), Column("Deadline", width=8, animate=False)),
        animation=Animation(rounds=1, min_rotations=2, max_rotations=3),
    )
    table = Table(("Task", "Deadline"), ({"Task": "Alpha", "Deadline": "12:00"},))
    board = render_board(config, table)
    cards = board.cards
    assert ImageChops.difference(cards.card("A"), cards.flap("A", "B", 0, 6)).getbbox() is None
    assert ImageChops.difference(cards.card("B"), cards.flap("A", "B", 5, 6)).getbbox() is None
    selected = choose_cells(board, config.animation, Random(2))
    assert all(cell.field != "Deadline" for cell in selected)
    assert len(selected) <= config.animation.max_cells
    frames, durations = animation_frames(board, config.animation)
    assert frames[0].tobytes() == frames[-1].tobytes()
    assert any(frame.tobytes() != frames[0].tobytes() for frame in frames)
    deadline = board.cells[1].bounds
    assert all(
        frame.crop(deadline).tobytes() == frames[0].crop(deadline).tobytes() for frame in frames
    )
    path = tmp_path / "board.gif"
    save_animation(frames, durations, path)
    with Image.open(path) as gif:
        first = gif.convert("RGB")
        assert gif.n_frames > 1
        for index in range(gif.n_frames):
            gif.seek(index)
            assert (
                ImageChops.difference(
                    first.crop(deadline), gif.convert("RGB").crop(deadline)
                ).getbbox()
                is None
            )
        assert ImageChops.difference(first, gif.convert("RGB")).getbbox() is None


@pytest.mark.parametrize("count", [0, 1, 3, 6])
def test_optional_signs_and_idempotent_readme(workspace: Path, count: int) -> None:
    config = Config(
        animation=Animation(enabled=False),
        buttons=tuple(Button(f"Guide {index}", f"docs/{index}.md") for index in range(count)),
    )
    generate(config, workspace)
    first = (workspace / "README.md").read_bytes()
    png = (workspace / config.output_dir / "board.png").read_bytes()
    generate(config, workspace)
    assert (workspace / "README.md").read_bytes() == first
    assert (workspace / config.output_dir / "board.png").read_bytes() == png
    text = first.decode()
    assert text.count(START) == text.count(END) == 1
    assert text.startswith("# My team") and text.endswith("Keep me.\n")
    assert text.count('alt="Guide') == count
    assert ('<p align="center">' in text) == bool(count)
    assert len(list((workspace / config.output_dir).glob("sign-*.png"))) == count
    generate(replace(config, buttons=()), workspace)
    assert not list((workspace / config.output_dir).glob("sign-*.png"))


def test_bad_markers_do_not_overwrite_files(workspace: Path) -> None:
    original = f"{START}\nUser text\n{START}"
    (workspace / "README.md").write_text(original)
    with pytest.raises(ValueError, match="marker pair"):
        generate(Config(), workspace)
    assert (workspace / "README.md").read_text() == original
    assert not (workspace / "assets").exists()


def test_readme_append_preserves_content() -> None:
    assert updated_readme("Hello\n", f"{START}\n{END}") == f"Hello\n\n{START}\n{END}\n"


def test_validate_only_and_no_readme(workspace: Path) -> None:
    original = (workspace / "README.md").read_bytes()
    assert main(["--workspace", str(workspace), "--validate-only"]) == 0
    assert not (workspace / "assets").exists()
    assert main(["--workspace", str(workspace), "--no-readme", "--no-animation"]) == 0
    assert (workspace / "README.md").read_bytes() == original


def test_action_targets_consumer_and_does_not_evaluate_input(
    workspace: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output = tmp_path / "action-output"
    monkeypatch.setenv("GITHUB_WORKSPACE", str(workspace))
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setenv("FB_NO_ANIMATION", "true")
    monkeypatch.setenv("FB_TITLE", "Literal $(touch SHOULD_NOT_EXIST)")
    monkeypatch.setenv("FB_TEAM", 'Team "R&D"')
    assert run() == 0
    assert "image=assets/flight-board/board.png" in output.read_text()
    assert (workspace / "assets/flight-board/board.png").exists()
    assert not (workspace / "SHOULD_NOT_EXIST").exists()


def test_path_escape_and_source_collision(workspace: Path, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="inside the workspace"):
        workspace_path(workspace, "../outside")
    with pytest.raises(ValueError, match="control"):
        workspace_path(workspace, "x\ny")
    with pytest.raises(ValueError, match="dedicated"):
        generate(Config(output_dir="."), workspace)
    (workspace / "escape").symlink_to(workspace.parent, target_is_directory=True)
    with pytest.raises(ValueError, match="inside the workspace"):
        workspace_path(workspace, "escape/out.png")


def test_default_config_and_unicode_text(workspace: Path) -> None:
    assert load_config(None) == Config()
    table = Table(("Name",), ({"Name": "Montréal → Zürich"},))
    board = render_board(Config(), table)
    assert "".join(slot.character for slot in board.cells[0].slots) == "MONTRÉAL→ZÜRICH"


def test_yaml_errors_are_concise(workspace: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (workspace / "flight-board.yml").write_text("title: [unclosed")
    assert main(["--workspace", str(workspace)]) == 2
    assert "Traceback" not in capsys.readouterr().err
