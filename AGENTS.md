# Project Agent Rules

- Work from the project root and read this file before changes.
- Use the project-local `uv` environment for Python commands.
- Keep credentials out of source control and logs.
- After code changes, run the full test suite and update this file when architecture or commands change.

## Identity

- Product: `CoderRelay`.
- Distribution and full command: `coder-relay`.
- Recommended command: `cdy`.
- Python module: `coder_relay`.
- Application home: `~/.config/coder-relay` or `$CODER_RELAY_HOME`.
- Current backend: OpenAI Codex CLI. Claude Code support is planned but not yet implemented.
- Do not reintroduce `CodexRelay`, `codex-relay`, `codex_relay`, or `cxr` compatibility aliases.

## Architecture

- `src/coder_relay/cli.py`: Typer/Rich command definitions.
- `src/coder_relay/entrypoint.py`: public command surface and lifecycle commands.
- `src/coder_relay/completion.py`: Bash/Zsh/Fish completion for `cdy` and `coder-relay`.
- `src/coder_relay/lifecycle.py`: updates, installer-aware uninstall, and cleanup.
- `src/coder_relay/manager.py`: profile import, switching, failover, and diagnostics.
- `src/coder_relay/health.py`: ChatGPT and OpenAI-compatible API probes.
- `src/coder_relay/usage.py`: auth parsing and ChatGPT usage queries.
- `src/coder_relay/config.py`: Codex TOML generation.
- `src/coder_relay/storage.py`: paths, atomic writes, locks, and backups.
- `scripts/cdy_launcher.py`: PyInstaller entry point.
- `scripts/package_release.py`: portable archive builder.
- `scripts/build_windows_installer.ps1`: Windows Setup EXE and ZIP.
- `installers/windows/CoderRelay.iss`: Inno Setup definition.
- `scripts/build_macos_dmg.sh`: macOS PKG/DMG packaging.
- `scripts/build_linux_packages.sh`: Linux TAR/DEB/RPM packaging.

## Commands

```bash
uv sync --extra dev
uv run pytest
uv run cdy --help
uv run coder-relay --help
uv build --no-sources
```

## Release policy

- Release tags use semantic versions prefixed with `v` and must match `pyproject.toml`.
- Native builds run on target runners.
- Windows publishes Setup EXE and ZIP for x86, x86_64, and ARM64.
- macOS publishes DMG images containing PKG installers for Intel and Apple Silicon.
- Linux publishes TAR.GZ, DEB, and RPM for x86_64 and AArch64.
- Release assets include `SHA256SUMS.txt`.
- Release artifacts are unsigned.
