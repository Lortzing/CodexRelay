# Implementation references

The project is independently implemented, while the following sources were consulted for compatibility.

## OpenAI Codex

- Custom provider implementation and fields such as `base_url`, `wire_api`, and `requires_openai_auth`:
  - https://github.com/openai/codex/blob/main/codex-rs/model-provider-info/src/lib.rs
- Codex `auth.json` structure, including `OPENAI_API_KEY` and token fields:
  - https://github.com/openai/codex/blob/main/codex-rs/login/src/auth/storage.rs
- API-key login test showing Bearer authentication on a Responses request:
  - https://github.com/openai/codex/blob/main/sdk/python/tests/test_app_server_login.py

## codex-auth

- Usage endpoint behavior and response parsing:
  - https://github.com/Loongphy/codex-auth/blob/main/src/api/usage.zig
- Request headers used for ChatGPT usage lookup:
  - https://github.com/Loongphy/codex-auth/blob/main/src/api/http_curl.zig
- Project disclaimer and endpoint declaration:
  - https://github.com/Loongphy/codex-auth/blob/main/README.md

The ChatGPT `wham/usage` endpoint is treated as an unstable implementation detail rather than a guaranteed public API.
