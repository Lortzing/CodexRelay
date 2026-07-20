from pathlib import Path

from typer.testing import CliRunner

from codex_relay.cli import app
from codex_relay.completion import install_completion

runner = CliRunner()


def test_completion_options_are_hidden() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--install-completion" not in result.stdout
    assert "--show-completion" not in result.stdout


def test_zsh_completion_installs_for_both_commands(tmp_path: Path) -> None:
    home = tmp_path / "home"
    app_home = tmp_path / "app"
    home.mkdir()

    files = install_completion(app, shell="zsh", app_home=app_home, home=home)

    source = (app_home / "completions" / "codex-relay.zsh").read_text()
    zshrc = (home / ".zshrc").read_text()
    assert "#compdef cr" in source
    assert "#compdef codex-relay" in source
    assert "_CR_COMPLETE=complete_zsh" in source
    assert "_CODEX_RELAY_COMPLETE=complete_zsh" in source
    assert "codex-relay completion" in zshrc
    assert files

    install_completion(app, shell="zsh", app_home=app_home, home=home)
    assert (home / ".zshrc").read_text().count("# >>> codex-relay completion >>>") == 1


def test_fish_completion_installs_for_both_commands(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    files = install_completion(app, shell="fish", app_home=tmp_path / "app", home=home)
    assert {path.name for path in files} == {"cr.fish", "codex-relay.fish"}
    assert "complete --command cr --no-files" in (home / ".config/fish/completions/cr.fish").read_text()


def test_install_replaces_legacy_completion_block(tmp_path: Path) -> None:
    home = tmp_path / "home"
    app_home = tmp_path / "app"
    home.mkdir()
    (home / ".zshrc").write_text(
        "before\n# >>> codex-switchboard completion >>>\nlegacy\n"
        "# <<< codex-switchboard completion <<<\nafter\n"
    )

    install_completion(app, shell="zsh", app_home=app_home, home=home)

    source = (home / ".zshrc").read_text()
    assert "codex-switchboard completion" not in source
    assert source.count("# >>> codex-relay completion >>>") == 1
