from __future__ import annotations

import hashlib
import json
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from .config import (
    build_api_config,
    build_chatgpt_config,
    inspect_codex_config,
    read_base_config,
    validate_toml,
)
from .errors import InvalidProfileError, ProfileNotFoundError, SwitchError
from .health import probe_profile
from .models import (
    ActiveState,
    BalanceConfig,
    HealthConfig,
    ProbeResult,
    Profile,
    utc_now_iso,
)
from .storage import (
    FileLock,
    Paths,
    atomic_write,
    backup_active,
    read_json,
    validate_name,
    write_json,
    write_text,
)
from .usage import parse_auth_json


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).astimezone(UTC)
    except ValueError:
        return None


class RelayManager:
    def __init__(self, paths: Paths | None = None):
        self.paths = paths or Paths.defaults()
        self.paths.ensure()

    def _profile_paths(self, name: str) -> tuple[Path, Path, Path, Path]:
        directory = self.paths.profile_dir(name)
        return directory, directory / "profile.json", directory / "auth.json", directory / "config.toml"

    def bootstrap_current_profile(self) -> Profile | None:
        """Import the active Codex files once when no managed profiles exist."""
        if self.list_profiles():
            return None
        if not self.paths.active_auth.is_file() or not self.paths.active_config.is_file():
            return None

        with FileLock(self.paths.lock_file):
            # Another first-run process may have completed the import while this
            # process was waiting for the lock.
            if self.list_profiles():
                return None
            return self.import_current_profile()

    def _state(self) -> ActiveState:
        if not self.paths.state_file.exists():
            return ActiveState()
        return ActiveState.from_dict(read_json(self.paths.state_file))

    def _save_state(self, state: ActiveState) -> None:
        write_json(self.paths.state_file, state.to_dict(), 0o600)

    def _unique_import_name(self, suggested: str) -> str:
        candidate = "".join(
            char.lower() if char.isalnum() or char in {"-", "_"} else "-"
            for char in suggested
        ).strip("-_") or "current"
        candidate = candidate[:64]
        if not self.paths.profile_dir(candidate).exists():
            return candidate
        index = 2
        while self.paths.profile_dir(f"{candidate}-{index}").exists():
            index += 1
        return f"{candidate}-{index}"

    def import_current_profile(
        self,
        name: str | None = None,
        *,
        force: bool = False,
        health_mode: str | None = None,
        balance_url: str | None = None,
        balance_path: str | None = None,
        notes: str | None = None,
    ) -> Profile:
        """Import the active CODEX_HOME auth.json and config.toml as a managed profile."""
        auth_info = parse_auth_json(self.paths.active_auth)
        config_info = inspect_codex_config(
            self.paths.active_config,
            auth_kind=str(auth_info["kind"]),
        )

        if name is None:
            if auth_info["kind"] == "chatgpt":
                email = auth_info.get("email")
                suggested = email.split("@", 1)[0] if isinstance(email, str) and email else "chatgpt"
            else:
                provider = config_info.get("provider_id")
                suggested = "openai-api" if provider == "openai" else str(provider or "api")
            resolved_name = self._unique_import_name(suggested)
        else:
            validate_name(name)
            resolved_name = name

        directory, metadata_path, stored_auth, stored_config = self._profile_paths(resolved_name)
        if directory.exists() and not force:
            raise InvalidProfileError(
                f"Profile already exists: {resolved_name}. Use --force to replace it."
            )
        if directory.exists():
            shutil.rmtree(directory)

        now = utc_now_iso()
        if auth_info["kind"] == "chatgpt":
            profile = Profile(
                name=resolved_name,
                kind="chatgpt",
                created_at=now,
                updated_at=now,
                model=config_info.get("model"),
                account_email=auth_info.get("email"),
                account_plan=auth_info.get("plan"),
                health=HealthConfig(mode="chatgpt_usage"),
                notes=notes or "Imported from the active Codex configuration.",
            )
        else:
            resolved_health_mode = health_mode or (
                "responses" if config_info.get("model") else "models"
            )
            if resolved_health_mode not in {"responses", "models"}:
                raise InvalidProfileError(
                    "Imported API profiles support responses or models health mode."
                )
            profile = Profile(
                name=resolved_name,
                kind="api",
                created_at=now,
                updated_at=now,
                model=config_info.get("model"),
                base_url=config_info.get("base_url"),
                provider_id=config_info.get("provider_id"),
                health=HealthConfig(mode=resolved_health_mode),  # type: ignore[arg-type]
                balance=BalanceConfig(balance_url, balance_path) if balance_url else None,
                notes=notes or "Imported from the active Codex configuration.",
            )

        directory.mkdir(parents=True, exist_ok=True)
        try:
            directory.chmod(0o700)
        except OSError:
            pass
        atomic_write(stored_auth, self.paths.active_auth.read_bytes(), 0o600)
        atomic_write(stored_config, self.paths.active_config.read_bytes(), 0o600)
        write_json(metadata_path, profile.to_dict(), 0o600)

        state = self._state()
        state.active_profile = resolved_name
        state.last_switch_at = utc_now_iso()
        state.last_switch_reason = "imported active Codex configuration"
        self._save_state(state)
        return profile

    def add_auth_profile(
        self,
        name: str,
        auth_json: Path,
        *,
        config: Path | None = None,
        model: str | None = None,
        notes: str | None = None,
        force: bool = False,
    ) -> Profile:
        validate_name(name)
        auth_info = parse_auth_json(auth_json)
        if auth_info["kind"] != "chatgpt":
            raise InvalidProfileError(
                "The supplied auth.json contains an API key. Use add-api for API-key profiles."
            )
        directory, metadata_path, stored_auth, stored_config = self._profile_paths(name)
        if directory.exists() and not force:
            raise InvalidProfileError(f"Profile already exists: {name}. Use --force to replace it.")

        base = read_base_config(config, self.paths.active_config)
        config_text = build_chatgpt_config(base, model=model)
        now = utc_now_iso()
        profile = Profile(
            name=name,
            kind="chatgpt",
            created_at=now,
            updated_at=now,
            model=model,
            account_email=auth_info.get("email"),
            account_plan=auth_info.get("plan"),
            health=HealthConfig(mode="chatgpt_usage"),
            notes=notes,
        )
        directory.mkdir(parents=True, exist_ok=True)
        try:
            directory.chmod(0o700)
        except OSError:
            pass
        atomic_write(stored_auth, auth_json.read_bytes(), 0o600)
        write_text(stored_config, config_text, 0o600)
        write_json(metadata_path, profile.to_dict(), 0o600)
        return profile

    def add_api_profile(
        self,
        name: str,
        *,
        base_url: str,
        api_key: str,
        model: str,
        config: Path | None = None,
        provider_id: str | None = None,
        health_mode: str = "responses",
        health_endpoint: str | None = None,
        health_method: str = "GET",
        expected_text: str | None = None,
        timeout_seconds: float = 15.0,
        balance_url: str | None = None,
        balance_path: str | None = None,
        notes: str | None = None,
        force: bool = False,
    ) -> Profile:
        validate_name(name)
        if not api_key.strip():
            raise InvalidProfileError("API key cannot be empty.")
        if health_mode not in {"responses", "models", "custom"}:
            raise InvalidProfileError("health_mode must be responses, models, or custom.")
        if health_mode == "custom" and not health_endpoint:
            raise InvalidProfileError("Custom health mode requires --health-endpoint.")

        directory, metadata_path, stored_auth, stored_config = self._profile_paths(name)
        if directory.exists() and not force:
            raise InvalidProfileError(f"Profile already exists: {name}. Use --force to replace it.")
        base = read_base_config(config, self.paths.active_config)
        config_text, resolved_provider = build_api_config(
            base,
            profile_name=name,
            base_url=base_url,
            model=model,
            provider_id=provider_id,
        )
        auth_data = {"auth_mode": "apikey", "OPENAI_API_KEY": api_key.strip()}
        now = utc_now_iso()
        profile = Profile(
            name=name,
            kind="api",
            created_at=now,
            updated_at=now,
            model=model,
            base_url=base_url.rstrip("/"),
            provider_id=resolved_provider,
            health=HealthConfig(
                mode=health_mode,  # type: ignore[arg-type]
                timeout_seconds=timeout_seconds,
                endpoint=health_endpoint,
                method=health_method.upper(),
                expected_text=expected_text,
            ),
            balance=BalanceConfig(balance_url, balance_path) if balance_url else None,
            notes=notes,
        )
        directory.mkdir(parents=True, exist_ok=True)
        try:
            directory.chmod(0o700)
        except OSError:
            pass
        write_json(stored_auth, auth_data, 0o600)
        write_text(stored_config, config_text, 0o600)
        write_json(metadata_path, profile.to_dict(), 0o600)
        return profile

    def load_profile(self, name: str) -> Profile:
        _, metadata_path, auth_path, config_path = self._profile_paths(name)
        if not metadata_path.exists():
            raise ProfileNotFoundError(f"Profile not found: {name}")
        profile = Profile.from_dict(read_json(metadata_path))
        parse_auth_json(auth_path)
        try:
            validate_toml(config_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise InvalidProfileError(f"Profile is missing config.toml: {name}") from exc
        return profile

    def profile_auth_path(self, name: str) -> Path:
        return self._profile_paths(name)[2]

    def list_profiles(self) -> list[Profile]:
        profiles: list[Profile] = []
        if not self.paths.profiles_dir.exists():
            return profiles
        for directory in sorted(self.paths.profiles_dir.iterdir(), key=lambda p: p.name.lower()):
            if not directory.is_dir():
                continue
            try:
                profiles.append(self.load_profile(directory.name))
            except (InvalidProfileError, ProfileNotFoundError):
                continue
        return profiles

    def remove_profile(self, name: str, *, force_active: bool = False) -> None:
        directory, _, _, _ = self._profile_paths(name)
        if not directory.exists():
            raise ProfileNotFoundError(f"Profile not found: {name}")
        state = self._state()
        if state.active_profile == name and not force_active:
            raise InvalidProfileError("Cannot remove the active profile without --force-active.")
        shutil.rmtree(directory)
        if state.active_profile == name:
            state.active_profile = None
            state.last_switch_reason = "active profile removed"
            self._save_state(state)

    def _profile_matches_active(self, name: str) -> bool:
        _, _, auth_path, config_path = self._profile_paths(name)
        return (
            _sha256(auth_path) == _sha256(self.paths.active_auth)
            and _sha256(config_path) == _sha256(self.paths.active_config)
            and auth_path.exists()
            and config_path.exists()
        )

    def current_profile(self) -> tuple[str | None, str]:
        state = self._state()
        if state.active_profile:
            try:
                self.load_profile(state.active_profile)
            except (ProfileNotFoundError, InvalidProfileError):
                return None, "state points to a missing or invalid profile"
            if self._profile_matches_active(state.active_profile):
                return state.active_profile, "managed"
            return state.active_profile, "active files were modified outside CoderRelay"
        return None, "unmanaged"

    def switch(self, name: str, *, reason: str = "manual") -> Path | None:
        self.load_profile(name)
        _, _, source_auth, source_config = self._profile_paths(name)
        with FileLock(self.paths.lock_file):
            backup = backup_active(self.paths)
            old_auth = self.paths.active_auth.read_bytes() if self.paths.active_auth.exists() else None
            old_config = self.paths.active_config.read_bytes() if self.paths.active_config.exists() else None
            try:
                atomic_write(self.paths.active_auth, source_auth.read_bytes(), 0o600)
                atomic_write(self.paths.active_config, source_config.read_bytes(), 0o600)
                # Validate the files after replacement before committing state.
                parse_auth_json(self.paths.active_auth)
                validate_toml(self.paths.active_config.read_text(encoding="utf-8"))
                state = self._state()
                state.active_profile = name
                state.last_switch_at = utc_now_iso()
                state.last_switch_reason = reason
                self._save_state(state)
                return backup
            except Exception as exc:
                try:
                    if old_auth is None:
                        self.paths.active_auth.unlink(missing_ok=True)
                    else:
                        atomic_write(self.paths.active_auth, old_auth, 0o600)
                    if old_config is None:
                        self.paths.active_config.unlink(missing_ok=True)
                    else:
                        atomic_write(self.paths.active_config, old_config, 0o600)
                except OSError:
                    pass
                raise SwitchError(f"Failed to switch to {name}; active files were rolled back: {exc}") from exc

    def probe(self, name: str) -> ProbeResult:
        profile = self.load_profile(name)
        return probe_profile(profile, self.profile_auth_path(name))

    def probe_many(self, names: Iterable[str] | None = None, *, workers: int = 4) -> list[ProbeResult]:
        selected = list(names) if names else [profile.name for profile in self.list_profiles()]
        if not selected:
            return []
        results: dict[str, ProbeResult] = {}
        with ThreadPoolExecutor(max_workers=max(1, min(workers, len(selected)))) as executor:
            futures = {executor.submit(self.probe, name): name for name in selected}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    results[name] = future.result()
                except Exception as exc:
                    results[name] = ProbeResult(
                        profile=name,
                        healthy=False,
                        status="error",
                        message=str(exc),
                    )
        return [results[name] for name in selected]

    def auto_once(
        self,
        order: list[str],
        *,
        cooldown_seconds: int = 300,
        fail_threshold: int = 1,
        recover_threshold: int = 2,
    ) -> dict[str, Any]:
        if not order:
            order = [profile.name for profile in self.list_profiles()]
        if not order:
            raise InvalidProfileError("No profiles are configured.")
        for name in order:
            self.load_profile(name)

        results = self.probe_many(order)
        result_map = {result.profile: result for result in results}
        state = self._state()
        for result in results:
            counter = state.counters.setdefault(result.profile, {"success": 0, "failure": 0})
            if result.healthy:
                counter["success"] = int(counter.get("success", 0)) + 1
                counter["failure"] = 0
            else:
                counter["failure"] = int(counter.get("failure", 0)) + 1
                counter["success"] = 0

        active, active_state = self.current_profile()
        now = datetime.now(UTC)
        last_switch = _parse_time(state.last_switch_at)
        cooldown_elapsed = last_switch is None or (now - last_switch).total_seconds() >= cooldown_seconds
        action = "keep"
        reason = "current profile remains selected"
        target = active

        healthy_names = [name for name in order if result_map[name].healthy]
        if active not in order:
            target = healthy_names[0] if healthy_names else None
            action = "switch" if target else "none"
            reason = "no managed active profile" if target else "no healthy profile"
        else:
            active_result = result_map[active]
            active_counter = state.counters.get(active, {})
            if not active_result.healthy:
                if int(active_counter.get("failure", 0)) >= max(1, fail_threshold):
                    alternatives = [name for name in healthy_names if name != active]
                    target = alternatives[0] if alternatives else None
                    action = "switch" if target else "none"
                    reason = (
                        f"active profile failed {active_counter.get('failure', 0)} consecutive checks"
                        if target
                        else "active profile is unhealthy and no fallback is healthy"
                    )
                else:
                    reason = "failure threshold not reached"
            else:
                active_index = order.index(active)
                higher_priority = order[:active_index]
                recovered = [
                    name
                    for name in higher_priority
                    if result_map[name].healthy
                    and int(state.counters.get(name, {}).get("success", 0)) >= max(1, recover_threshold)
                ]
                if recovered and cooldown_elapsed:
                    target = recovered[0]
                    action = "switch"
                    reason = "higher-priority profile recovered"
                elif recovered:
                    reason = "higher-priority profile recovered but switch cooldown is active"
                elif active_state != "managed":
                    reason = active_state

        updated_counters = {
            name: state.counters.get(name, {"success": 0, "failure": 0}) for name in order
        }
        if action == "switch" and target:
            self.switch(target, reason=f"automatic: {reason}")
            state = self._state()  # reload timestamps written by switch()
        state.counters = updated_counters
        self._save_state(state)
        return {
            "action": action,
            "target": target,
            "reason": reason,
            "results": [result.to_dict() for result in results],
            "checked_at": utc_now_iso(),
        }

    def doctor(self) -> list[dict[str, Any]]:
        checks: list[dict[str, Any]] = []

        def add(name: str, ok: bool, detail: str) -> None:
            checks.append({"name": name, "ok": ok, "detail": detail})

        add("application home", self.paths.app_home.is_dir(), str(self.paths.app_home))
        add("Codex home", self.paths.codex_home.is_dir(), str(self.paths.codex_home))
        codex = shutil.which("codex")
        add("Codex executable", codex is not None, codex or "not found on PATH")
        profile_dirs = [
            item for item in self.paths.profiles_dir.iterdir() if item.is_dir()
        ] if self.paths.profiles_dir.exists() else []
        valid_count = 0
        for directory in sorted(profile_dirs, key=lambda item: item.name.lower()):
            try:
                profile = self.load_profile(directory.name)
                valid_count += 1
                add(f"profile:{profile.name}", True, f"{profile.kind} profile is valid")
            except Exception as exc:
                add(f"profile:{directory.name}", False, str(exc))
        add("profiles", valid_count > 0, f"{valid_count} valid profile(s), {len(profile_dirs) - valid_count} invalid")
        active, status = self.current_profile()
        add("active profile", active is not None, f"{active or 'none'} ({status})")
        return checks
