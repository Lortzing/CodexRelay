from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .errors import InvalidProfileError

_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def validate_name(name: str) -> str:
    if not _NAME_RE.fullmatch(name):
        raise InvalidProfileError(
            "Profile name must be 1-64 characters and contain only letters, numbers, '.', '_' or '-'."
        )
    return name


def default_app_home() -> Path:
    override = os.environ.get("CODEX_RELAY_HOME")
    if override:
        return Path(override).expanduser()
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg).expanduser() / "codex-relay"
    return Path.home() / ".config" / "codex-relay"


def legacy_app_homes() -> list[Path]:
    """Return legacy CodexSwitchboard data locations in priority order."""
    homes: list[Path] = []
    override = os.environ.get("CODEX_SWITCHBOARD_HOME")
    if override:
        homes.append(Path(override).expanduser())
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        homes.append(Path(xdg).expanduser() / "codex-switchboard")
    homes.append(Path.home() / ".config" / "codex-switchboard")
    unique: list[Path] = []
    for item in homes:
        if item not in unique:
            unique.append(item)
    return unique


def migrate_legacy_app_home(target: Path) -> Path | None:
    """Move legacy profile data into CodexRelay when the new home is absent."""
    target = target.expanduser()
    if target.exists():
        return None
    candidates = [target.parent / "codex-switchboard", *legacy_app_homes()]
    seen: list[Path] = []
    for source in candidates:
        if source in seen:
            continue
        seen.append(source)
        if not source.exists() or source.resolve() == target.resolve():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            source.replace(target)
        except OSError:
            shutil.copytree(source, target)
        return source
    return None


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser()


@dataclass(frozen=True, slots=True)
class Paths:
    app_home: Path
    codex_home: Path

    @classmethod
    def defaults(cls) -> "Paths":
        return cls(default_app_home(), default_codex_home())

    @property
    def profiles_dir(self) -> Path:
        return self.app_home / "profiles"

    @property
    def backups_dir(self) -> Path:
        return self.app_home / "backups"

    @property
    def state_file(self) -> Path:
        return self.app_home / "state.json"

    @property
    def lock_file(self) -> Path:
        return self.app_home / "switch.lock"

    @property
    def active_auth(self) -> Path:
        return self.codex_home / "auth.json"

    @property
    def active_config(self) -> Path:
        return self.codex_home / "config.toml"

    def profile_dir(self, name: str) -> Path:
        return self.profiles_dir / validate_name(name)

    def ensure(self) -> None:
        for directory in (self.app_home, self.profiles_dir, self.backups_dir, self.codex_home):
            directory.mkdir(parents=True, exist_ok=True)
        try:
            self.app_home.chmod(0o700)
            self.profiles_dir.chmod(0o700)
            self.backups_dir.chmod(0o700)
        except OSError:
            pass


def atomic_write(path: Path, content: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            temp_path.chmod(mode)
        except OSError:
            pass
        os.replace(temp_path, path)
        try:
            dir_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def write_text(path: Path, text: str, mode: int = 0o600) -> None:
    atomic_write(path, text.encode("utf-8"), mode)


def write_json(path: Path, data: Any, mode: int = 0o600) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n", mode)


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InvalidProfileError(f"Missing file: {path}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidProfileError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise InvalidProfileError(f"Expected a JSON object in {path}")
    return data


def copy_atomic(source: Path, target: Path, mode: int = 0o600) -> None:
    atomic_write(target, source.read_bytes(), mode)


def backup_active(paths: Paths) -> Path | None:
    existing = [p for p in (paths.active_auth, paths.active_config) if p.exists()]
    if not existing:
        return None
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    destination = paths.backups_dir / stamp
    destination.mkdir(parents=True, exist_ok=False)
    for source in existing:
        shutil.copy2(source, destination / source.name)
    try:
        destination.chmod(0o700)
        for item in destination.iterdir():
            item.chmod(0o600)
    except OSError:
        pass
    return destination


class FileLock(AbstractContextManager["FileLock"]):
    def __init__(self, path: Path):
        self.path = path
        self._handle = None

    def __enter__(self) -> "FileLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a+b")
        if os.name == "nt":
            import msvcrt

            if self.path.stat().st_size == 0:
                self._handle.write(b"0")
                self._handle.flush()
            self._handle.seek(0)
            msvcrt.locking(self._handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._handle is None:
            return
        try:
            if os.name == "nt":
                import msvcrt

                self._handle.seek(0)
                msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        finally:
            self._handle.close()
            self._handle = None
