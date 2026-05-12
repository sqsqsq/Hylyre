"""Progress store + CLI."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from hylyre.cli.__main__ import app
from hylyre.progress import store

runner = CliRunner()


def _mini_repo(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "hylyre"\n', encoding="utf-8"
    )
    (tmp_path / "docs").mkdir()
    return tmp_path


def test_find_hylyre_repo_root(tmp_path: Path) -> None:
    _mini_repo(tmp_path)
    sub = tmp_path / "nested" / "deep"
    sub.mkdir(parents=True)
    assert store.find_hylyre_repo_root(sub) == tmp_path.resolve()


def test_append_progress_section(tmp_path: Path) -> None:
    _mini_repo(tmp_path)
    p = tmp_path / "docs" / "progress.md"
    store.append_progress_section("line one", path=p, title="## Custom")
    assert "## Custom" in p.read_text(encoding="utf-8")
    assert "line one" in p.read_text(encoding="utf-8")


def test_progress_path_cli(tmp_path: Path, monkeypatch) -> None:
    _mini_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    r = runner.invoke(app, ["progress", "path"])
    assert r.exit_code == 0, r.stderr
    expect = str((tmp_path / "docs" / "progress.md").resolve())
    assert expect in r.stdout or expect.replace("\\", "/") in r.stdout.replace("\\", "/")


def test_progress_append_cli(tmp_path: Path, monkeypatch) -> None:
    _mini_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    r = runner.invoke(
        app,
        ["progress", "append", "-m", "authored by test"],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    text = (tmp_path / "docs" / "progress.md").read_text(encoding="utf-8")
    assert "authored by test" in text


def test_spec_list_cli_fallback(tmp_path: Path, monkeypatch) -> None:
    _mini_repo(tmp_path)
    (tmp_path / "openspec" / "specs" / "cli").mkdir(parents=True)
    (tmp_path / "openspec" / "specs" / "cli" / "spec.md").write_text("# x", encoding="utf-8")
    (tmp_path / "openspec" / "changes" / "draft").mkdir(parents=True)
    monkeypatch.setattr("hylyre.cli.commands.spec_cmd.shutil.which", lambda _: None)
    monkeypatch.chdir(tmp_path)
    r = runner.invoke(app, ["spec", "list"])
    assert r.exit_code == 0, r.stdout + r.stderr
    assert "cli" in r.stdout
