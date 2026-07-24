from __future__ import annotations

from pathlib import Path

import pytest

from coder_relay import lifecycle
from coder_relay.lifecycle import cleanup_relay
from coder_relay.updater import ReleaseInfo


class ExitCalled(Exception):
    def __init__(self, code: int):
        self.code = code


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
    manager = lifecycle._update_distribution("git+https://example.invalid/repo.git@v1.2.3")
    assert manager == "uv tool"
    assert commands == [["/usr/bin/uv", "tool", "install", "--force", "git+https://example.invalid/repo.git@v1.2.3"]]


def test_package_update_tracks_latest_stable_tag(monkeypatch) -> None:
    release = ReleaseInfo(tag="v0.9.0", version="0.9.0", assets={})
    sources: list[str] = []
    monkeypatch.setattr(lifecycle, "fetch_latest_release", lambda: release)
    monkeypatch.setattr(lifecycle, "is_frozen_executable", lambda: False)
    monkeypatch.setattr(lifecycle, "_update_distribution", lambda source: sources.append(source) or "uv tool")
    monkeypatch.setattr(lifecycle.os, "_exit", lambda code: (_ for _ in ()).throw(ExitCalled(code)))

    with pytest.raises(ExitCalled) as caught:
        lifecycle.update_and_exit()
    assert caught.value.code == 0
    assert sources == ["git+https://github.com/Lortzing/CoderRelay.git@v0.9.0"]


def test_frozen_update_uses_release_installer(monkeypatch) -> None:
    release = ReleaseInfo(tag="v0.9.0", version="0.9.0", assets={})
    calls: list[tuple[ReleaseInfo, bool]] = []
    monkeypatch.setattr(lifecycle, "fetch_latest_release", lambda: release)
    monkeypatch.setattr(lifecycle, "is_frozen_executable", lambda: True)
    monkeypatch.setattr(
        lifecycle,
        "install_frozen_update",
        lambda selected, force=False: calls.append((selected, force)) or "scheduled",
    )
    monkeypatch.setattr(lifecycle.os, "_exit", lambda code: (_ for _ in ()).throw(ExitCalled(code)))

    with pytest.raises(ExitCalled) as caught:
        lifecycle.update_and_exit(force=True)
    assert caught.value.code == 0
    assert calls == [(release, True)]


def test_find_windows_uninstaller_prefers_inno_setup_file(tmp_path: Path) -> None:
    executable = tmp_path / "cdy.exe"
    executable.write_bytes(b"exe")
    (tmp_path / "unins001.exe").write_bytes(b"newer")
    expected = tmp_path / "unins000.exe"
    expected.write_bytes(b"uninstaller")
    assert lifecycle._find_windows_uninstaller(executable) == expected


def test_find_windows_uninstaller_returns_none(tmp_path: Path) -> None:
    assert lifecycle._find_windows_uninstaller(tmp_path / "cdy.exe") is None


def test_macos_runtime_root_detects_packaged_entrypoint() -> None:
    executable = Path("/usr/local/lib/coder-relay/cdy")
    assert lifecycle._macos_runtime_root(executable) == Path("/usr/local/lib/coder-relay")


def test_macos_runtime_root_rejects_unrelated_executable(tmp_path: Path) -> None:
    assert lifecycle._macos_runtime_root(tmp_path / "cdy") is None
