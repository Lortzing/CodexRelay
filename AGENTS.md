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
- `src/codex_relay/lifecycle.py`: package-managed update, standalone-aware uninstall, completion cleanup, and optional data purge.
- `src/codex_relay/manager.py`: profile lifecycle, first-run import, switching, failover, and diagnostics.
- `src/codex_relay/health.py`: ChatGPT and OpenAI-compatible API probes.
- `src/codex_relay/usage.py`: auth parsing and ChatGPT usage queries.
- `src/codex_relay/config.py`: Codex TOML generation with comment-preserving edits.
- `src/codex_relay/storage.py`: paths, atomic writes, process locks, and backups.
- `src/codex_relay/models.py`: persisted schemas and probe results.
- `scripts/cxr_launcher.py`: PyInstaller entry point for standalone executables.
- `scripts/package_release.py`: creates platform-specific ZIP/TAR.GZ release archives.
- `install.sh`: installs the uv tool, configures completion, and bootstraps the active Codex configuration.
- `README.md`: default Simplified Chinese documentation.
- `README.en.md`: English documentation.
- `.github/workflows/ci.yml`: cross-platform tests and Linux standalone smoke build.
- `.github/workflows/release.yml`: tag-driven native standalone builds and GitHub Release publishing.

## Main Commands

```bash
uv sync --extra dev
uv run pytest
uv run cxr --help
uv run codex-relay --help
uv build --no-sources
```

When no profiles exist, installation or the first business command automatically imports the active `$CODEX_HOME/auth.json` and `config.toml`. `status` is the single profile/status command.

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

- Releases use semantic version tags prefixed with `v`.
- The tag must match `[project].version` in `pyproject.toml`.
- Releases are published only through GitHub Releases; there is no PyPI or GitHub Packages publishing.
- PyInstaller builds run natively on the target OS and CPU architecture.
- Release targets: Windows x86/x86_64/ARM64, macOS x86_64/ARM64, Linux x86_64/AArch64.
- Every executable must pass a CLI smoke test before publication.
- Release assets include a SHA-256 checksum manifest.

## Uninstall and Update

- Package-managed installations use `cxr update`.
- Standalone executables are updated by replacing them with a newer GitHub Release asset.
- `cxr uninstall` asks whether profile data should be preserved.
- `cxr uninstall --purge` deletes all managed data after confirmation.
- Standalone uninstall removes the executable; Windows schedules deletion after process exit.
- No uninstall mode deletes active files under `~/.codex`.
