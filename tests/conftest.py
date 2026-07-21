from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from coder_relay.storage import Paths


def jwt(payload: dict) -> str:
    def enc(value: dict) -> str:
        raw = json.dumps(value, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    return f"{enc({'alg': 'none'})}.{enc(payload)}.sig"


@pytest.fixture
def chatgpt_auth(tmp_path: Path) -> Path:
    path = tmp_path / "chatgpt-auth.json"
    path.write_text(
        json.dumps(
            {
                "auth_mode": "chatgpt",
                "OPENAI_API_KEY": None,
                "tokens": {
                    "id_token": jwt(
                        {
                            "email": "test@example.com",
                            "https://api.openai.com/auth": {
                                "chatgpt_account_id": "acct_123",
                                "chatgpt_user_id": "user_123",
                                "chatgpt_plan_type": "plus",
                            },
                        }
                    ),
                    "access_token": "access-token",
                    "refresh_token": "refresh-token",
                    "account_id": "acct_123",
                },
            }
        ),
        encoding="utf-8",
    )
    return path


@pytest.fixture
def paths(tmp_path: Path) -> Paths:
    return Paths(tmp_path / "app", tmp_path / "codex")
