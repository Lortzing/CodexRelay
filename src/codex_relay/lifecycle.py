from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from .completion import uninstall_completion
from .errors import RelayError

CURRENT_DISTRIBUTION = "codex-relay"
DEFAULT_UPDATE_SOURCE = "git+https://github.com/Lortzing/CodexRelay.git"


@dataclass(slots=True)
class CleanupResult:
    completion_files_removed: int
    data_removed: bool


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=False)


def _uninstall_distribution(package: str) -> str:
    uv = shutil.which("uv")
    if uv:
        result = _run([uv, "tool", "uninstall", package])
        if result.returncode == 0:
            return "uv tool"
        combined = (result.stdout + result.stderr).lower()
        if "not installed" not in combined and "no tool" not in combined:
            raise RelayError((result.stderr or result.stdout).strip() or f"uv could not uninstall {package}")

    pipx = shutil.which("pipx")
    if pipx:
        result = _run([pipx, "uninstall", package])
        if result.returncode == 0:
            return "pipx"

    result = _run([sys.executable, "-m", "pip", "uninstall", "-y", package])
    if result.returncode == 0 and "successfully uninstalled" in (result.stdout + result.stderr).lower():
        return "pip"

    raise RelayError(
        f"Could not find an installed {package} tool. Remove it with the package manager used to install it."
    )


def _update_distribution(source: str) -> str:
    uv = shutil.which("uv")
    if uv:
        result = _run([uv, "tool", "install", "--force", source])
        if result.returncode == 0:
            return "uv tool"
        uv_error = (result.stderr or result.stdout).strip()
    else:
        uv_error = ""

    pipx = shutil.which("pipx")
    if pipx:
        result = _run([pipx, "install", "--force", source])
        if result.returncode == 0:
            return "pipx"

    result = _run([sys.executable, "-m", "pip", "install", "--upgrade", source])
    if result.returncode == 0:
        return "pip"

    detail = (result.stderr or result.stdout).strip() or uv_error
    raise RelayError(detail or "Could not update CodexRelay with uv, pipx, or pip.")


def cleanup_relay(
    *,
    app_home: Path,
    purge: bool,
    user_home: Path | None = None,
) -> CleanupResult:
    """Remove completion artifacts and optionally all managed data before package removal."""
    removed = uninstall_completion(app_home=app_home, home=user_home)
    data_removed = False
    if purge and app_home.exists():
        shutil.rmtree(app_home)
        data_removed = True
    return CleanupResult(
        completion_files_removed=len(removed),
        data_removed=data_removed,
    )


def uninstall_and_exit() -> NoReturn:
    """Uninstall the package and terminate without returning into removed dependencies."""
    try:
        manager = _uninstall_distribution(CURRENT_DISTRIBUTION)
        os.write(1, f"Uninstalled {CURRENT_DISTRIBUTION} using {manager}.\n".encode())
        os._exit(0)
    except RelayError as exc:
        os.write(2, f"Error: {exc}\n".encode())
        os._exit(1)


def update_and_exit(*, source: str = DEFAULT_UPDATE_SOURCE) -> NoReturn:
    """Replace the installed package and exit before importing replaced dependencies again."""
    try:
        manager = _update_distribution(source)
        os.write(1, f"Updated {CURRENT_DISTRIBUTION} using {manager}.\n".encode())
        os._exit(0)
    except RelayError as exc:
        os.write(2, f"Error: {exc}\n".encode())
        os._exit(1)
