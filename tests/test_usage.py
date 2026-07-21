from coder_relay.usage import parse_auth_json, parse_usage_payload


def test_parse_chatgpt_auth(chatgpt_auth):
    info = parse_auth_json(chatgpt_auth)
    assert info["kind"] == "chatgpt"
    assert info["account_id"] == "acct_123"
    assert info["email"] == "test@example.com"
    assert info["plan"] == "plus"


def test_parse_usage_payload():
    parsed = parse_usage_payload(
        {
            "plan_type": "plus",
            "rate_limit": {
                "primary_window": {
                    "used_percent": 25,
                    "limit_window_seconds": 18000,
                    "reset_at": 2_000_000_000,
                }
            },
            "credits": {"has_credits": True, "unlimited": False, "balance": "12.5"},
        }
    )
    assert parsed["primary"]["used_percent"] == 25.0
    assert parsed["primary"]["window_minutes"] == 300
    assert parsed["credits"]["balance"] == "12.5"


def test_fetch_chatgpt_usage_headers(chatgpt_auth):
    import httpx
    from coder_relay.usage import fetch_chatgpt_usage

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer access-token"
        assert request.headers["chatgpt-account-id"] == "acct_123"
        return httpx.Response(
            200,
            json={
                "plan_type": "plus",
                "rate_limit": {"primary_window": {"used_percent": 10}},
            },
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        usage, code = fetch_chatgpt_usage(chatgpt_auth, client=client)
    assert code == 200
    assert usage["plan_type"] == "plus"
    assert usage["primary"]["used_percent"] == 10.0
