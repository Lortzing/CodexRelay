from pathlib import Path

from codex_relay import lifecycle
from codex_relay.lifecycle import cleanup_relay
from codex_relay.storage import migrate_legacy_app_home


def test_migrate_legacy_app_home(tmp_path: Path) -> None:
    home = tmp_path / "home"
    legacy = home / ".config" / "codex-switchboard"
    target = home / ".config" / "codex-relay"
    (legacy / "profiles" / "official").mkdir(parents=True)
    (legacy / "state.json").write_text("{}\n")

    migrated = migrate_legacy_app_home(target)

    assert migrated == legacy
    assert (target / "state.json").is_file()
    assert not legacy.exists()


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
