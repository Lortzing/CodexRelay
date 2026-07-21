from __future__ import annotations

import json
import os
import shlex
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from typer.completion import get_completion_script

from .storage import default_app_home

if TYPE_CHECKING:
    import typer

_COMPLETION_SCHEMA_VERSION = 3
_BLOCK_BEGIN = "# >>> coder-relay completion >>>"
_BLOCK_END = "# <<< coder-relay completion <<<"
_SUPPORTED_SHELLS = {"bash", "zsh", "fish"}
_PROGRAMS = ("cdy", "coder-relay")


def _completion_var(program: str) -> str:
    return f"_{program.upper().replace('-', '_')}_COMPLETE"


def _completion_source(app: "typer.Typer", shell: str, program: str) -> str:
    del app
    return (
        get_completion_script(
            prog_name=program,
            complete_var=_completion_var(program),
            shell=shell,
        ).rstrip()
        + "\n"
    )


def _managed_block(source_file: Path, shell: str) -> str:
    quoted = shlex.quote(str(source_file))
    if shell == "zsh":
        body = (
            f"if [[ -r {quoted} ]]; then\n"
            "  autoload -Uz compinit\n"
            "  (( $+functions[compdef] )) || compinit\n"
            f"  source {quoted}\n"
            "fi"
        )
    elif shell == "bash":
        body = f"if [[ -r {quoted} ]]; then\n  source {quoted}\nfi"
    else:
        raise ValueError(f"Managed rc blocks are not used for {shell}")
    return f"{_BLOCK_BEGIN}\n{body}\n{_BLOCK_END}"


def _remove_block(text: str, begin: str, end: str) -> str:
    while True:
        start = text.find(begin)
        finish = text.find(end, start + len(begin)) if start >= 0 else -1
        if start < 0 or finish < 0:
            break
        finish += len(end)
        before = text[:start].rstrip()
        after = text[finish:].lstrip("\r\n")
        text = before + (("\n\n" + after) if before and after else after)
    return text.rstrip() + ("\n" if text.strip() else "")


def _upsert_managed_block(path: Path, block: str) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    existing = _remove_block(existing, _BLOCK_BEGIN, _BLOCK_END)
    separator = "" if not existing else ("" if existing.endswith("\n\n") else "\n")
    updated = existing + separator + block + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(updated, encoding="utf-8")


def _install_zsh_or_bash(app: "typer.Typer", shell: str, app_home: Path, home: Path) -> list[Path]:
    completion_dir = app_home / "completions"
    completion_dir.mkdir(parents=True, exist_ok=True)
    source_file = completion_dir / f"coder-relay.{shell}"
    combined = "\n".join(_completion_source(app, shell, program) for program in _PROGRAMS)
    source_file.write_text(combined, encoding="utf-8")
    try:
        source_file.chmod(0o644)
    except OSError:
        pass

    rc_file = home / (".zshrc" if shell == "zsh" else ".bashrc")
    _upsert_managed_block(rc_file, _managed_block(source_file, shell))
    return [source_file, rc_file]


def _install_fish(app: "typer.Typer", home: Path) -> list[Path]:
    completion_dir = home / ".config" / "fish" / "completions"
    completion_dir.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    for program in _PROGRAMS:
        path = completion_dir / f"{program}.fish"
        path.write_text(_completion_source(app, "fish", program), encoding="utf-8")
        try:
            path.chmod(0o644)
        except OSError:
            pass
        files.append(path)
    return files


def install_completion(
    app: "typer.Typer",
    *,
    shell: str,
    app_home: Path | None = None,
    home: Path | None = None,
) -> list[Path]:
    """Install completion files for the public executable names without output."""
    normalized_shell = Path(shell).name.lower()
    if normalized_shell not in _SUPPORTED_SHELLS:
        return []
    resolved_home = (home or Path.home()).expanduser()
    resolved_app_home = (app_home or default_app_home()).expanduser()
    resolved_app_home.mkdir(parents=True, exist_ok=True)
    if normalized_shell == "fish":
        files = _install_fish(app, resolved_home)
    else:
        files = _install_zsh_or_bash(app, normalized_shell, resolved_app_home, resolved_home)

    marker = resolved_app_home / "completion.json"
    marker.write_text(
        json.dumps(
            {
                "schema_version": _COMPLETION_SCHEMA_VERSION,
                "shell": normalized_shell,
                "programs": list(_PROGRAMS),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    try:
        marker.chmod(0o600)
    except OSError:
        pass
    return files


def uninstall_completion(*, app_home: Path | None = None, home: Path | None = None) -> list[Path]:
    """Remove CoderRelay completion artifacts."""
    resolved_home = (home or Path.home()).expanduser()
    resolved_app_home = (app_home or default_app_home()).expanduser()
    changed: list[Path] = []

    for rc_file in (resolved_home / ".zshrc", resolved_home / ".bashrc"):
        if not rc_file.exists():
            continue
        original = rc_file.read_text(encoding="utf-8")
        updated = _remove_block(original, _BLOCK_BEGIN, _BLOCK_END)
        if updated != original:
            rc_file.write_text(updated, encoding="utf-8")
            changed.append(rc_file)

    fish_dir = resolved_home / ".config" / "fish" / "completions"
    for program in _PROGRAMS:
        path = fish_dir / f"{program}.fish"
        if path.exists():
            path.unlink()
            changed.append(path)

    for candidate in (
        resolved_app_home / "completion.json",
        resolved_app_home / "completions" / "coder-relay.zsh",
        resolved_app_home / "completions" / "coder-relay.bash",
    ):
        if candidate.exists():
            candidate.unlink()
            changed.append(candidate)
    completions_dir = resolved_app_home / "completions"
    if completions_dir.exists() and not any(completions_dir.iterdir()):
        completions_dir.rmdir()
    return changed


def _completion_request_in_progress() -> bool:
    return any(os.environ.get(_completion_var(program)) for program in _PROGRAMS)


def ensure_completion(app: "typer.Typer") -> None:
    """Silently install completion on the first interactive CLI invocation."""
    if os.environ.get("CODER_RELAY_DISABLE_COMPLETION") == "1":
        return
    if _completion_request_in_progress():
        return
    if not (sys.stdin.isatty() or sys.stdout.isatty()):
        return

    shell = Path(os.environ.get("SHELL", "")).name.lower()
    if shell not in _SUPPORTED_SHELLS:
        return

    app_home = default_app_home().expanduser()
    marker = app_home / "completion.json"
    try:
        if marker.exists():
            data = json.loads(marker.read_text(encoding="utf-8"))
            if (
                data.get("schema_version") == _COMPLETION_SCHEMA_VERSION
                and data.get("shell") == shell
                and data.get("programs") == list(_PROGRAMS)
            ):
                return
        install_completion(app, shell=shell, app_home=app_home)
    except (OSError, ValueError, json.JSONDecodeError):
        return
