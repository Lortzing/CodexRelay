from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from .completion import uninstall_completion
from .errors import RelayError

CURRENT_DISTRIBUTION = "coder-relay"
DEFAULT_UPDATE_SOURCE = "git+https://github.com/Lortzing/CoderRelay.git"
RELEASES_URL = "https://github.com/Lortzing/CoderRelay/releases/latest"


def is_frozen_executable() -> bool:
    """Return whether CoderRelay is running from a standalone frozen executable."""
    return bool(getattr(sys, "frozen", False))


def _find_windows_uninstaller(executable: Path) -> Path | None:
    """Return the Inno Setup uninstaller next to a packaged cdy.exe, if present."""
    candidates = sorted(executable.parent.glob("unins*.exe"))
    return candidates[0] if candidates else None


def _remove_frozen_executable_and_exit() -> NoReturn:
    executable = Path(sys.executable).resolve()
    if os.name != "nt":
        try:
            executable.unlink()
            os.write(1, f"Removed standalone executable: {executable}\n".encode())
            os._exit(0)
        except PermissionError:
            os.write(
                2,
                (
                    f"Error: {executable} is not writable. "
                    "Run the command with elevated privileges or remove the installed package "
                    "with the system package manager.\n"
                ).encode(),
            )
            os._exit(1)
        except OSError as exc:
            os.write(2, f"Error: could not remove {executable}: {exc}\n".encode())
            os._exit(1)

    uninstaller = _find_windows_uninstaller(executable)
    if uninstaller is not None:
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        try:
            subprocess.Popen([str(uninstaller)], close_fds=True, creationflags=creationflags)
            os.write(1, f"Started the CoderRelay uninstaller: {uninstaller}\n".encode())
            os._exit(0)
        except OSError as exc:
            os.write(2, f"Error: could not start {uninstaller}: {exc}\n".encode())
            os._exit(1)

    script = Path(tempfile.gettempdir()) / f"coder-relay-uninstall-{os.getpid()}.cmd"
    script.write_text(
        "@echo off\r\n"
        ":retry\r\n"
        f'del /f /q "{executable}" >nul 2>&1\r\n'
        f'if exist "{executable}" (\r\n'
        "  ping 127.0.0.1 -n 2 >nul\r\n"
        "  goto retry\r\n"
        ")\r\n"
        'del /f /q "%~f0" >nul 2>&1\r\n',
        encoding="utf-8",
    )
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(
        subprocess, "DETACHED_PROCESS", 0
    )
    try:
        subprocess.Popen(
            ["cmd.exe", "/d", "/c", str(script)],
            close_fds=True,
            creationflags=creationflags,
        )
        os.write(1, f"Scheduled removal of standalone executable: {executable}\n".encode())
        os._exit(0)
    except OSError as exc:
        script.unlink(missing_ok=True)
        os.write(2, f"Error: could not schedule removal of {executable}: {exc}\n".encode())
        os._exit(1)


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
    raise RelayError(detail or "Could not update CoderRelay with uv, pipx, or pip.")


def cleanup_relay(*, app_home: Path, purge: bool, user_home: Path | None = None) -> CleanupResult:
    """Remove completion artifacts and optionally all managed data before package removal."""
    removed = uninstall_completion(app_home=app_home, home=user_home)
    data_removed = False
    if purge and app_home.exists():
        shutil.rmtree(app_home)
        data_removed = True
    return CleanupResult(completion_files_removed=len(removed), data_removed=data_removed)


def uninstall_and_exit() -> NoReturn:
    """Uninstall the package or remove the standalone executable, then terminate."""
    if is_frozen_executable():
        _remove_frozen_executable_and_exit()
    try:
        manager = _uninstall_distribution(CURRENT_DISTRIBUTION)
        os.write(1, f"Uninstalled {CURRENT_DISTRIBUTION} using {manager}.\n".encode())
        os._exit(0)
    except RelayError as exc:
        os.write(2, f"Error: {exc}\n".encode())
        os._exit(1)


def update_and_exit(*, source: str = DEFAULT_UPDATE_SOURCE) -> NoReturn:
    """Replace a package-managed installation and terminate."""
    if is_frozen_executable():
        os.write(
            2,
            (
                "Standalone executables are updated from GitHub Releases. "
                f"Download the matching asset from {RELEASES_URL}.\n"
            ).encode(),
        )
        os._exit(2)
    try:
        manager = _update_distribution(source)
        os.write(1, f"Updated {CURRENT_DISTRIBUTION} using {manager}.\n".encode())
        os._exit(0)
    except RelayError as exc:
        os.write(2, f"Error: {exc}\n".encode())
        os._exit(1)
