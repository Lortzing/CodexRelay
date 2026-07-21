from pathlib import Path

from coder_relay import lifecycle
from coder_relay.lifecycle import cleanup_relay


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


def test_update_prefers_uv_tool(monkeypatch) -> None:
    monkeypatch.setattr(lifecycle.shutil, "which", lambda name: "/usr/bin/uv" if name == "uv" else None)
    commands: list[list[str]] = []

    def fake_run(command: list[str]):
        commands.append(command)
        return lifecycle.subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(lifecycle, "_run", fake_run)
    manager = lifecycle._update_distribution("git+https://example.invalid/repo.git")
    assert manager == "uv tool"
    assert commands == [["/usr/bin/uv", "tool", "install", "--force", "git+https://example.invalid/repo.git"]]


def test_find_windows_uninstaller_prefers_inno_setup_file(tmp_path: Path) -> None:
    executable = tmp_path / "cdy.exe"
    executable.write_bytes(b"exe")
    (tmp_path / "unins001.exe").write_bytes(b"newer")
    expected = tmp_path / "unins000.exe"
    expected.write_bytes(b"uninstaller")
    assert lifecycle._find_windows_uninstaller(executable) == expected


def test_find_windows_uninstaller_returns_none(tmp_path: Path) -> None:
    assert lifecycle._find_windows_uninstaller(tmp_path / "cdy.exe") is None
