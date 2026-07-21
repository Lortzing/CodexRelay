from pathlib import Path

from coder_relay.manager import RelayManager
from coder_relay.models import ProbeResult


def test_add_and_switch_profiles(paths, chatgpt_auth):
    manager = RelayManager(paths)
    paths.active_config.write_text('approval_policy = "on-request"\n', encoding="utf-8")
    manager.add_auth_profile("official", chatgpt_auth)
    manager.add_api_profile(
        "backup",
        base_url="https://api.example/v1",
        api_key="secret",
        model="gpt-test",
    )

    manager.switch("official")
    active, state = manager.current_profile()
    assert active == "official"
    assert state == "managed"

    manager.switch("backup")
    active, state = manager.current_profile()
    assert active == "backup"
    assert state == "managed"
    assert "secret" in paths.active_auth.read_text(encoding="utf-8")
    assert 'model_provider = "relay-backup"' in paths.active_config.read_text(encoding="utf-8")


def test_auto_failover(paths, chatgpt_auth, monkeypatch):
    manager = RelayManager(paths)
    manager.add_auth_profile("official", chatgpt_auth)
    manager.add_api_profile(
        "backup",
        base_url="https://api.example/v1",
        api_key="secret",
        model="gpt-test",
    )
    manager.switch("official")

    def fake_probe_many(names, workers=4):
        return [
            ProbeResult(profile="official", healthy=False, status="provider_error"),
            ProbeResult(profile="backup", healthy=True, status="healthy"),
        ]

    monkeypatch.setattr(manager, "probe_many", fake_probe_many)
    result = manager.auto_once(["official", "backup"], fail_threshold=1)
    assert result["action"] == "switch"
    assert result["target"] == "backup"
    assert manager.current_profile()[0] == "backup"


def test_detects_external_modification(paths, chatgpt_auth):
    manager = RelayManager(paths)
    manager.add_auth_profile("official", chatgpt_auth)
    manager.switch("official")
    paths.active_config.write_text('model_provider = "changed"\n', encoding="utf-8")
    active, state = manager.current_profile()
    assert active == "official"
    assert "modified" in state


def test_auto_recovery_threshold(paths, chatgpt_auth, monkeypatch):
    manager = RelayManager(paths)
    manager.add_auth_profile("official", chatgpt_auth)
    manager.add_api_profile(
        "backup",
        base_url="https://api.example/v1",
        api_key="secret",
        model="gpt-test",
    )
    manager.switch("backup")

    def both_healthy(names, workers=4):
        return [
            ProbeResult(profile="official", healthy=True, status="healthy"),
            ProbeResult(profile="backup", healthy=True, status="healthy"),
        ]

    monkeypatch.setattr(manager, "probe_many", both_healthy)
    first = manager.auto_once(
        ["official", "backup"], cooldown_seconds=0, recover_threshold=2
    )
    assert first["action"] == "keep"
    second = manager.auto_once(
        ["official", "backup"], cooldown_seconds=0, recover_threshold=2
    )
    assert second["action"] == "switch"
    assert second["target"] == "official"


def test_import_current_chatgpt_profile(paths, chatgpt_auth):
    manager = RelayManager(paths)
    paths.codex_home.mkdir(parents=True, exist_ok=True)
    paths.active_auth.write_bytes(chatgpt_auth.read_bytes())
    config_text = (
        'model = "gpt-5.6"\n'
        'model_provider = "openai"\n'
        'approval_policy = "on-request"\n'
    )
    paths.active_config.write_text(config_text, encoding="utf-8")

    profile = manager.import_current_profile()

    assert profile.kind == "chatgpt"
    assert profile.name == "test"
    assert profile.model == "gpt-5.6"
    assert manager.current_profile() == ("test", "managed")
    assert manager._profile_paths("test")[3].read_text(encoding="utf-8") == config_text


def test_import_current_api_profile(paths):
    manager = RelayManager(paths)
    paths.codex_home.mkdir(parents=True, exist_ok=True)
    paths.active_auth.write_text(
        '{"auth_mode":"apikey","OPENAI_API_KEY":"secret"}',
        encoding="utf-8",
    )
    config_text = (
        'model = "gpt-test"\n'
        'model_provider = "gateway"\n\n'
        '[model_providers.gateway]\n'
        'name = "Gateway"\n'
        'base_url = "https://gateway.example/v1/"\n'
        'wire_api = "responses"\n'
        'requires_openai_auth = true\n'
    )
    paths.active_config.write_text(config_text, encoding="utf-8")

    profile = manager.import_current_profile()

    assert profile.name == "gateway"
    assert profile.kind == "api"
    assert profile.model == "gpt-test"
    assert profile.provider_id == "gateway"
    assert profile.base_url == "https://gateway.example/v1"
    assert profile.health.mode == "responses"
    assert manager.current_profile() == ("gateway", "managed")


def test_import_current_openai_api_uses_default_url(paths):
    manager = RelayManager(paths)
    paths.codex_home.mkdir(parents=True, exist_ok=True)
    paths.active_auth.write_text(
        '{"auth_mode":"apikey","OPENAI_API_KEY":"secret"}',
        encoding="utf-8",
    )
    paths.active_config.write_text(
        'model_provider = "openai"\n',
        encoding="utf-8",
    )

    profile = manager.import_current_profile()

    assert profile.name == "openai-api"
    assert profile.base_url == "https://api.openai.com/v1"
    assert profile.health.mode == "models"


def test_bootstrap_current_profile_is_idempotent(paths, chatgpt_auth):
    manager = RelayManager(paths)
    paths.active_auth.write_bytes(chatgpt_auth.read_bytes())
    paths.active_config.write_text(
        'model = "gpt-5.6"\nmodel_provider = "openai"\n',
        encoding="utf-8",
    )

    imported = manager.bootstrap_current_profile()
    repeated = manager.bootstrap_current_profile()

    assert imported is not None
    assert imported.name == "test"
    assert repeated is None
    assert [profile.name for profile in manager.list_profiles()] == ["test"]
    assert manager.current_profile() == ("test", "managed")


def test_bootstrap_skips_when_current_files_are_missing(paths):
    manager = RelayManager(paths)

    assert manager.bootstrap_current_profile() is None
    assert manager.list_profiles() == []
