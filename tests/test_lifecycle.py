from pathlib import Path

from codex_relay import lifecycle
from codex_relay.lifecycle import cleanup_relay


def test_cleanup_preserves_data_by_default(tmp_path: Path, monkeypatch) -> None:
    app_home = tmp_path / "app"
    (app_home / "profiles" / "official").mkdir(parents=True)
    monkeypatch.setattr(lifecycle, "uninstall_completion", lambda **kwargs: [tmp_path / "completion"])

    result = cleanup_relay(app_home=app_home, purge=False)

    assert app_home.exists()
    assert result.completion_files_removed == 1
    assert not result.data_removed


def test_cleanup_purge_removes_data(tmp_path: Path, monkeypatch) -> None:
    app_home = tmp_path / "app"
    (app_home / "profiles" / "official").mkdir(parents=True)
    monkeypatch.setattr(lifecycle, "uninstall_completion", lambda **kwargs: [])

    result = cleanup_relay(app_home=app_home, purge=True)

    assert not app_home.exists()
    assert result.data_removed


def test_update_prefers_uv_tool(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(lifecycle.shutil, "which", lambda name: "/usr/bin/uv" if name == "uv" else None)
    commands: list[list[str]] = []

    def fake_run(command: list[str]):
        commands.append(command)
        return lifecycle.subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(lifecycle, "_run", fake_run)

    manager = lifecycle._update_distribution("git+https://example.invalid/repo.git")

    assert manager == "uv tool"
    assert commands == [["/usr/bin/uv", "tool", "install", "--force", "git+https://example.invalid/repo.git"]]


def test_frozen_executable_detection(monkeypatch) -> None:
    monkeypatch.setattr(lifecycle.sys, "frozen", True, raising=False)
    assert lifecycle.is_frozen_executable()


def test_frozen_uninstall_removes_unix_executable(tmp_path: Path, monkeypatch) -> None:
    executable = tmp_path / "cxr"
    executable.write_bytes(b"binary")
    monkeypatch.setattr(lifecycle.os, "name", "posix")
    monkeypatch.setattr(lifecycle.sys, "executable", str(executable))

    def fake_exit(code: int) -> None:
        raise SystemExit(code)

    monkeypatch.setattr(lifecycle.os, "_exit", fake_exit)

    try:
        lifecycle._remove_frozen_executable_and_exit()
    except SystemExit as exc:
        assert exc.code == 0
    else:
        raise AssertionError("expected frozen uninstall to terminate")

    assert not executable.exists()
