import json
from pathlib import Path

from typer.testing import CliRunner

from codex_relay.cli import app

runner = CliRunner()


def test_status_first_run_imports_current_profile(tmp_path: Path, chatgpt_auth: Path) -> None:
    app_home = tmp_path / "app"
    codex_home = tmp_path / "codex"
    codex_home.mkdir()
    (codex_home / "auth.json").write_bytes(chatgpt_auth.read_bytes())
    (codex_home / "config.toml").write_text(
        'model = "gpt-5.6"\nmodel_provider = "openai"\n',
        encoding="utf-8",
    )

    args = [
        "--home",
        str(app_home),
        "--codex-home",
        str(codex_home),
        "status",
        "--no-probe",
        "--json",
    ]
    first = runner.invoke(app, args)
    second = runner.invoke(app, args)

    assert first.exit_code == 0, first.stdout
    assert second.exit_code == 0, second.stdout
    first_payload = json.loads(first.stdout)
    second_payload = json.loads(second.stdout)
    assert first_payload["active_profile"] == "test"
    assert [item["name"] for item in first_payload["profiles"]] == ["test"]
    assert [item["name"] for item in second_payload["profiles"]] == ["test"]


def test_list_is_hidden_but_remains_compatible(tmp_path: Path) -> None:
    help_result = runner.invoke(app, ["--help"])
    assert help_result.exit_code == 0
    assert "list" not in help_result.stdout

    result = runner.invoke(
        app,
        ["--home", str(tmp_path / "app"), "--codex-home", str(tmp_path / "codex"), "list", "--json"],
    )
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["profiles"] == []
    assert payload["results"] == []
