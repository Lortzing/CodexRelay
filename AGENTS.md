# Project Agent Rules

- Work from the project root and read this file before modifying the project.
- Use the project-local `uv` environment for Python commands.
- Keep credentials out of source control, output, and logs.
- Store runtime secrets with restrictive permissions.
- After code changes, run the full test suite, CLI smoke tests, and `uv build`.
- Update this file when architecture, commands, or storage paths change.

## Architecture

- `src/codex_relay/cli.py`: Typer/Rich command-line interface.
- `src/codex_relay/completion.py`: silent Bash/Zsh/Fish completion installation and cleanup for `cr` and `codex-relay`.
- `src/codex_relay/lifecycle.py`: self-uninstallation and package-manager detection.
- `src/codex_relay/manager.py`: profile lifecycle, first-run import, switching, automatic failover, and diagnostics.
- `src/codex_relay/health.py`: ChatGPT and OpenAI-compatible API probes.
- `src/codex_relay/usage.py`: auth parsing and ChatGPT usage queries.
- `src/codex_relay/config.py`: Codex TOML generation with comment-preserving edits.
- `src/codex_relay/storage.py`: paths, legacy-data migration, atomic writes, process locks, and backups.
- `src/codex_relay/models.py`: persisted schemas and probe results.
- `install.sh`: installs the uv tool, removes the legacy distribution, configures completion, migrates data, and bootstraps the current Codex profile.

## Main Commands

```bash
uv sync --extra dev
uv run pytest
uv run cr --help
uv run codex-relay --help
uv run cr import-current --help
uv run cr uninstall --help
uv build
```

When no profiles exist, installation or the first business command automatically imports the active `$CODEX_HOME/auth.json` and `config.toml`. `status` is the unified profile/status command; `list` is a hidden compatibility alias.

## Runtime Data

- Default application home: `~/.config/codex-relay`.
- Legacy application home: `~/.config/codex-switchboard`, migrated once when the new home is absent.
- Default Codex home: `~/.codex` or `$CODEX_HOME`.
- Each profile owns a complete `auth.json` and `config.toml`.
- API keys and ChatGPT tokens must never be printed or committed.

## CLI Entry Points

- Public: `cr` and `codex-relay`.
- Deprecated compatibility: `csw`.
- Completion flags are intentionally hidden; completion is installed silently on the first interactive invocation.
- `cr uninstall` preserves managed data by default; `--purge` removes it. Active files under `~/.codex` are never removed.
