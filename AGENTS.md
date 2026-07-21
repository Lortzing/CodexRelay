# Project Agent Rules

- Work from the project root and read this file before changes.
- Use the project-local `uv` environment for Python commands.
- Keep credentials out of source control and logs.
- Store runtime secrets with restrictive permissions.
- After code changes, run the full test suite and update this file when architecture or commands change.

## Architecture

- `src/codex_relay/cli.py`: core Typer/Rich command definitions.
- `src/codex_relay/entrypoint.py`: public command surface and lifecycle commands.
- `src/codex_relay/completion.py`: silent Bash/Zsh/Fish completion installation for `cxr` and `codex-relay`.
- `src/codex_relay/lifecycle.py`: package-managed update, installer-aware uninstall, completion cleanup, and optional data purge.
- `src/codex_relay/manager.py`: profile lifecycle, first-run import, switching, failover, and diagnostics.
- `src/codex_relay/health.py`: ChatGPT and OpenAI-compatible API probes.
- `src/codex_relay/usage.py`: auth parsing and ChatGPT usage queries.
- `src/codex_relay/config.py`: Codex TOML generation with comment-preserving edits.
- `src/codex_relay/storage.py`: paths, atomic writes, process locks, and backups.
- `src/codex_relay/models.py`: persisted schemas and probe results.
- `scripts/cxr_launcher.py`: PyInstaller entry point.
- `scripts/package_release.py`: portable ZIP/TAR.GZ archive builder.
- `scripts/build_windows_installer.ps1`: Windows Setup EXE and portable ZIP builder.
- `installers/windows/CodexRelay.iss`: Inno Setup installer definition and user-PATH management.
- `scripts/build_macos_dmg.sh`: macOS PKG/DMG builder.
- `scripts/build_linux_packages.sh`: Linux TAR.GZ, DEB, and RPM packaging through nFPM.
- `.github/workflows/ci.yml`: cross-platform tests and standalone smoke build.
- `.github/workflows/release.yml`: tag-driven native installers and GitHub Release publishing.

## Main Commands

```bash
uv sync --extra dev
uv run pytest
uv run cxr --help
uv run codex-relay --help
uv build --no-sources
```

When no profiles exist, installation or the first business command automatically imports the active `$CODEX_HOME/auth.json` and `config.toml`.

## Runtime Data

- Default application home: `~/.config/codex-relay`.
- Default Codex home: `~/.codex` or `$CODEX_HOME`.
- Each profile owns a complete `auth.json` and `config.toml`.
- API keys and ChatGPT tokens must never be printed or committed.

## CLI Entry Points

- `cxr` is the recommended short command.
- `codex-relay` is the full command.
- No historical command aliases or legacy-data migration are supported.
- Completion flags are hidden; completion is installed silently on the first interactive invocation.

## Release Policy

- Release tags use semantic versions prefixed with `v` and must match `pyproject.toml`.
- PyInstaller builds run on native target runners.
- Windows targets publish Setup EXE and portable ZIP for x86, x86_64, and ARM64.
- macOS targets publish DMG images containing PKG installers for Intel and Apple Silicon.
- Linux targets publish TAR.GZ, DEB, and RPM for x86_64 and AArch64.
- Every binary and installer receives a smoke or structural verification before publication.
- Release assets include `SHA256SUMS.txt`.

## Uninstall and Update

- `cxr update` updates source or `uv tool` installations.
- Standalone and installer builds are updated by replacing them with a newer GitHub Release asset.
- Windows Setup installations use the adjacent Inno Setup uninstaller when `cxr uninstall` is run.
- `cxr uninstall` asks whether profile data should be preserved.
- `cxr uninstall --purge` deletes all managed data after confirmation.
- No uninstall mode deletes active files under `~/.codex`.
