# Project Agent Rules

- Work from the project root and read this file before changes.
- Use the project-local `uv` environment for Python commands.
- Keep credentials out of source control and logs.
- Store runtime secrets with restrictive permissions.
- After code changes, run the full test suite and update this file when architecture or commands change.

## Architecture

- `src/codex_relay/cli.py`: core Typer/Rich command definitions.
- `src/codex_relay/entrypoint.py`: public command surface and lifecycle commands.
- `src/codex_relay/completion.py`: silent first-run Bash/Zsh/Fish completion installation for `cxr` and `codex-relay`.
- `src/codex_relay/lifecycle.py`: self-update, uninstall, completion cleanup, and optional data purge.
- `src/codex_relay/manager.py`: profile lifecycle, idempotent first-run import, switching, automatic failover, and diagnostics.
- `src/codex_relay/health.py`: ChatGPT and OpenAI-compatible API probes.
- `src/codex_relay/usage.py`: auth parsing and ChatGPT usage queries.
- `src/codex_relay/config.py`: Codex TOML generation with comment-preserving edits.
- `src/codex_relay/storage.py`: paths, atomic writes, process locks, and backups.
- `src/codex_relay/models.py`: persisted schemas and probe results.
- `install.sh`: installs the uv tool, silently configures completion, and bootstraps the current Codex configuration.
- `README.md`: default Simplified Chinese documentation.
- `README.en.md`: English documentation linked from the default README.
- `.github/workflows/ci.yml`: cross-platform test, build, and distribution smoke tests.
- `.github/workflows/release.yml`: tag-driven GitHub Release packaging and optional PyPI Trusted Publishing.

## Main Commands

```bash
uv sync --extra dev
uv run pytest
uv run cxr --help
uv run codex-relay --help
uv run cxr import-current --help
uv build --no-sources
```

When no profiles exist, installation or the first business command automatically imports the active `$CODEX_HOME/auth.json` and `config.toml`. `import-current` remains available for explicit re-import. `status` is the single profile/status command.

## Runtime Data

- Default application home: `~/.config/codex-relay`.
- Default Codex home: `~/.codex` or `$CODEX_HOME`.
- Each profile owns a complete `auth.json` and `config.toml`.
- API keys and ChatGPT tokens must never be printed or committed.

## CLI Entry Points

- `cxr` is the recommended short command.
- `codex-relay` is the full command.
- No historical command aliases or automatic legacy-data migration are supported.
- Completion flags are intentionally hidden; completion is installed silently on the first interactive invocation.

## Release Policy

- Release tags use semantic versions prefixed with `v`, such as `v0.6.0`.
- The tag version must match `[project].version` in `pyproject.toml`.
- CI must pass before release work is considered complete.
- GitHub Releases contain both wheel and source distribution artifacts.
- PyPI publishing is optional and requires repository variable `PUBLISH_TO_PYPI=true`, GitHub Environment `pypi`, and a configured PyPI Trusted Publisher.

## Uninstall and Update

- `cxr update` updates from the repository main branch and preserves profile data.
- `cxr uninstall` asks whether profile data should be preserved.
- `cxr uninstall --purge` deletes all managed data after confirmation.
- Neither uninstall mode deletes active files under `~/.codex`.
