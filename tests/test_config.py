from codex_relay.config import build_api_config, build_chatgpt_config


def test_build_chatgpt_config_preserves_other_settings():
    result = build_chatgpt_config('approval_policy = "on-request"\nmodel_provider = "old"\n')
    assert 'approval_policy = "on-request"' in result
    assert 'model_provider = "openai"' in result


def test_build_api_config_adds_provider():
    result, provider = build_api_config(
        'approval_policy = "on-request"\n',
        profile_name="backup",
        base_url="https://gateway.example/v1/",
        model="gpt-test",
    )
    assert provider == "relay-backup"
    assert 'model = "gpt-test"' in result
    assert 'model_provider = "relay-backup"' in result
    assert 'base_url = "https://gateway.example/v1"' in result
    assert "requires_openai_auth = true" in result
