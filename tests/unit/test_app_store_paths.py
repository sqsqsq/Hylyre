"""App knowledge store path resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from hylyre.app_store.paths import resolve_read_dirs, resolve_write_dir


def test_resolve_read_dirs_order_cli_env_cwd_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.chdir(tmp_path)
    home_apps = fake_home / ".hylyre" / "apps"
    home_apps.mkdir(parents=True)
    cwd_apps = tmp_path / ".hylyre" / "apps"
    cwd_apps.mkdir(parents=True)
    cli = tmp_path / "cli_store"
    cli.mkdir()
    env_store = tmp_path / "env_store"
    env_store.mkdir()

    monkeypatch.delenv("HYLYRE_APP_STORE_DIR", raising=False)
    dirs = resolve_read_dirs(cli)
    assert dirs[0] == cli.resolve()
    assert cwd_apps.resolve() in dirs
    assert home_apps.resolve() in dirs
    assert dirs[-1] == home_apps.resolve()

    monkeypatch.setenv("HYLYRE_APP_STORE_DIR", str(env_store))
    dirs2 = resolve_read_dirs(cli)
    assert dirs2[0] == cli.resolve()
    assert env_store.resolve() == dirs2[1]


def test_resolve_write_dir_prefers_cli_over_env_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    cli = tmp_path / "w_cli"
    cli.mkdir()
    env_store = tmp_path / "w_env"
    env_store.mkdir()
    monkeypatch.setenv("HYLYRE_APP_STORE_DIR", str(env_store))

    assert resolve_write_dir(cli) == cli.resolve()
    monkeypatch.delenv("HYLYRE_APP_STORE_DIR", raising=False)
    assert resolve_write_dir(None) == (tmp_path / ".hylyre" / "apps").resolve()


def test_resolve_write_dir_succeeds_when_cwd_under_fake_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: user-home-shaped cwd still gets a writable project-local store."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    workspace = fake_home / "workspace"
    workspace.mkdir()
    monkeypatch.chdir(workspace)
    monkeypatch.delenv("HYLYRE_APP_STORE_DIR", raising=False)
    assert resolve_write_dir(None) == (workspace / ".hylyre" / "apps").resolve()

