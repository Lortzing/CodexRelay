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
LEGACY_DISTRIBUTION = "codex-switchboard"


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


def cleanup_relay(
    *,
    app_home: Path,
    purge: bool,
    user_home: Path | None = None,
) -> CleanupResult:
    """Remove completion artifacts and optionally managed data before package removal."""
    removed = uninstall_completion(app_home=app_home, home=user_home)
    data_removed = False
    if purge and app_home.exists():
        shutil.rmtree(app_home)
        data_removed = True
    return CleanupResult(
        completion_files_removed=len(removed),
        data_removed=data_removed,
    )


def uninstall_and_exit(*, include_legacy_package: bool = False) -> NoReturn:
    """Uninstall packages and terminate without returning into removed dependencies.

    A uv tool uninstall removes this process's virtual environment. Returning to
    Typer/Rich after that can trigger lazy imports from files that no longer
    exist, so the command exits through ``os._exit`` immediately afterward.
    """
    try:
        if include_legacy_package:
            try:
                _uninstall_distribution(LEGACY_DISTRIBUTION)
            except RelayError:
                pass
        manager = _uninstall_distribution(CURRENT_DISTRIBUTION)
        os.write(1, f"Uninstalled {CURRENT_DISTRIBUTION} using {manager}.\n".encode())
        os._exit(0)
    except RelayError as exc:
        os.write(2, f"Error: {exc}\n".encode())
        os._exit(1)
