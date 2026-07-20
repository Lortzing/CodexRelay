# CodexRelay

CodexRelay manages multiple authentication and API profiles for the OpenAI Codex CLI. It supports:

- ChatGPT/Codex accounts imported from `auth.json`.
- OpenAI-compatible APIs configured with an API key, base URL, and model.
- Manual switching and priority-based automatic failover/recovery.
- ChatGPT usage windows, credits, API health, latency, and optional provider balance display.
- Atomic activation, backups, process locking, automatic first-run import, and JSON output.

Profiles are stored independently and activated by replacing the active Codex `auth.json` and `config.toml` with validated, atomic writes.

## Requirements

- Python 3.11 or newer.
- `uv` for the recommended installation path.
- Codex CLI available as `codex` for actual Codex use.

## Installation

Clone the repository and run:

```bash
git clone https://github.com/Lortzing/CodexRelay.git
cd CodexRelay
./install.sh
```

The installer:

1. Removes the legacy `codex-switchboard` uv tool when present, without deleting its data.
2. Installs CodexRelay with `uv tool install`.
3. Installs shell completion silently for Zsh, Bash, or Fish.
4. Migrates legacy `~/.config/codex-switchboard` data when needed.
5. Imports the active `$CODEX_HOME/auth.json` and `config.toml` when no managed profile exists.

The public commands are:

```bash
cr --help
codex-relay --help
```

`cr` is the recommended short command. A deprecated `csw` entry point remains temporarily for compatibility, but it is not shown in documentation or completion.

Direct installation is also supported:

```bash
uv tool install git+https://github.com/Lortzing/CodexRelay.git
cr status --no-probe
```

## Upgrade from CodexSwitchboard

The old distribution and commands were:

```text
codex-switchboard
codex-switch
csw
```

Recommended upgrade:

```bash
git clone https://github.com/Lortzing/CodexRelay.git
cd CodexRelay
./install.sh
```

Manual uv-tool upgrade:

```bash
uv tool uninstall codex-switchboard
uv tool install --force git+https://github.com/Lortzing/CodexRelay.git
cr status --no-probe
```

For an old pip installation:

```bash
python -m pip uninstall codex-switchboard
python -m pip install --upgrade git+https://github.com/Lortzing/CodexRelay.git
```

On first use, CodexRelay migrates the old default data directory:

```text
~/.config/codex-switchboard  ->  ~/.config/codex-relay
```

This migration preserves profiles, backups, and state. It does not modify or delete the active files under `~/.codex`.

## Storage

Default application data:

```text
~/.config/codex-relay/
├── profiles/
│   └── <name>/
│       ├── profile.json
│       ├── auth.json
│       └── config.toml
├── backups/
├── state.json
└── switch.lock
```

Active Codex files:

```text
~/.codex/auth.json
~/.codex/config.toml
```

Override locations with `CODEX_RELAY_HOME`, `CODEX_HOME`, `--home`, or `--codex-home`.

## Automatic first-run import

When the profile library is empty, the installer or the first business command imports the current Codex configuration automatically:

```bash
cr status --no-probe
```

Explicit import remains available:

```bash
cr import-current
cr import-current official
```

The importer detects ChatGPT token login or API-key login and extracts non-secret metadata such as email, plan, model, provider id, and base URL. Tokens and keys are never printed.

## Add profiles

Import a ChatGPT `auth.json`:

```bash
cr add-auth official ~/.codex/auth.json
```

Add an API profile:

```bash
cr add-api backup \
  --url https://gateway.example.com/v1 \
  --model gpt-5.6 \
  --api-key-stdin
```

Without `--api-key` or `--api-key-stdin`, the CLI prompts for the key with hidden input.

API health modes:

```bash
# Minimal Responses API request; may consume a small number of tokens.
cr add-api backup --url https://gateway.example.com/v1 --model gpt-5.6 \
  --health-mode responses --api-key-stdin

# GET /models; usually cheaper.
cr add-api backup --url https://gateway.example.com/v1 --model gpt-5.6 \
  --health-mode models --api-key-stdin

# Provider-specific endpoint.
cr add-api backup --url https://gateway.example.com/v1 --model gpt-5.6 \
  --health-mode custom \
  --health-endpoint https://gateway.example.com/health \
  --expected-text ok \
  --api-key-stdin
```

Optional provider balance endpoint:

```bash
cr add-api backup \
  --url https://gateway.example.com/v1 \
  --model gpt-5.6 \
  --balance-url https://gateway.example.com/account/credits \
  --balance-path data.balance \
  --api-key-stdin
```

## Status and manual switching

`status` combines profile listing, current-state inspection, health checks, usage, and balance display:

```bash
cr status
cr status --no-probe
cr status --watch --interval 30
cr status --json
```

Activate a profile:

```bash
cr use official
cr use backup
```

Restart existing Codex CLI/App processes after switching because they may cache authentication. New processes read the activated files.

The former `list` command remains a hidden compatibility alias for `status --no-probe`.

## Automatic switching

One evaluation in priority order:

```bash
cr auto official backup
```

Continuous monitoring:

```bash
cr auto official backup \
  --watch \
  --interval 60 \
  --fail-threshold 2 \
  --recover-threshold 2 \
  --cooldown 300
```

Policy:

1. Earlier profile names have higher priority.
2. The active profile fails over after the configured number of consecutive failures.
3. A higher-priority profile is restored after consecutive successful checks.
4. Recovery respects the cooldown to reduce flapping.
5. Emergency failover is not blocked by cooldown.
6. If every profile is unhealthy, active files remain unchanged.

## Launch Codex with automatic selection

`launch` checks profiles, activates the first healthy one, and then starts a fresh Codex process:

```bash
cr launch -p official -p backup -- exec "say hello"
```

Everything after `--` is passed to `codex`.

## Uninstallation

Uninstall the program and shell completion while preserving profiles and backups:

```bash
cr uninstall
```

Skip confirmation:

```bash
cr uninstall --yes
```

Also remove all CodexRelay-managed profiles, backups, state, and metadata:

```bash
cr uninstall --purge
```

Also attempt to remove an installed legacy `codex-switchboard` package:

```bash
cr uninstall --legacy
```

Uninstallation never removes the active `~/.codex/auth.json` or `~/.codex/config.toml`.

Old versions without the `uninstall` command can be removed manually:

```bash
uv tool uninstall codex-switchboard
# or, for a pip installation:
python -m pip uninstall codex-switchboard
```

To delete old data as well:

```bash
rm -rf ~/.config/codex-switchboard
```

## Background monitoring

### systemd user service

```bash
mkdir -p ~/.config/systemd/user
cp examples/codex-relay.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now codex-relay.service
journalctl --user -u codex-relay.service -f
```

### macOS launchd

Edit the executable path in `examples/com.codex-relay.auto.plist`, then:

```bash
mkdir -p ~/Library/LaunchAgents
cp examples/com.codex-relay.auto.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.codex-relay.auto.plist
```

## Security notes

- Credential and state files use mode `0600` where supported.
- Profile and backup directories use restrictive permissions.
- API keys and access tokens are omitted from status and JSON output.
- Prefer `--api-key-stdin` because direct command-line arguments may remain in shell history.
- ChatGPT usage checks send the access token only to the configured OpenAI ChatGPT endpoint.
- Custom health and balance endpoints receive the API key as a Bearer token; use trusted HTTPS endpoints.
- Backups contain credentials and must be protected.

## Diagnostics and development

```bash
cr doctor
uv sync --extra dev
uv run pytest
uv build
```
