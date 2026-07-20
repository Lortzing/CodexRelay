from pathlib import Path

from typer.testing import CliRunner

from codex_relay.entrypoint import app
from codex_relay.completion import install_completion, uninstall_completion

runner = CliRunner()


def test_completion_options_are_hidden() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--install-completion" not in result.stdout
    assert "--show-completion" not in result.stdout


def test_zsh_completion_installs_for_public_commands(tmp_path: Path) -> None:
    home = tmp_path / "home"
    app_home = tmp_path / "app"
    home.mkdir()

    files = install_completion(app, shell="zsh", app_home=app_home, home=home)

    source = (app_home / "completions" / "codex-relay.zsh").read_text()
    zshrc = (home / ".zshrc").read_text()
    assert "#compdef cxr" in source
    assert "#compdef codex-relay" in source
    assert "_CXR_COMPLETE=complete_zsh" in source
    assert "_CODEX_RELAY_COMPLETE=complete_zsh" in source
    assert "codex-relay completion" in zshrc
    assert files

    install_completion(app, shell="zsh", app_home=app_home, home=home)
    assert (home / ".zshrc").read_text().count("# >>> codex-relay completion >>>") == 1


def test_fish_completion_installs_for_public_commands(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    files = install_completion(app, shell="fish", app_home=tmp_path / "app", home=home)
    assert {path.name for path in files} == {"cxr.fish", "codex-relay.fish"}
    assert "complete --command cxr --no-files" in (
        home / ".config/fish/completions/cxr.fish"
    ).read_text()


def test_uninstall_completion_removes_current_artifacts(tmp_path: Path) -> None:
    home = tmp_path / "home"
    app_home = tmp_path / "app"
    home.mkdir()
    install_completion(app, shell="zsh", app_home=app_home, home=home)

    removed = uninstall_completion(app_home=app_home, home=home)

    assert removed
    assert "codex-relay completion" not in (home / ".zshrc").read_text()
    assert not (app_home / "completion.json").exists()
