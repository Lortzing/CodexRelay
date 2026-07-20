# CodexRelay

CodexRelay is a profile manager and automatic failover tool for the OpenAI Codex CLI. It supports:

- ChatGPT/Codex login profiles imported from `auth.json`.
- OpenAI-compatible API profiles configured with an API key, base URL, and model.
- Manual switching, health checks, automatic failover, and recovery.
- ChatGPT plan, rate-limit window, and credit display.
- Optional provider-specific API balance endpoints.
- Human-readable status tables and JSON output.

Profiles are stored independently and activated by atomically replacing the active Codex `auth.json` and `config.toml`.

## Requirements

- Python 3.11 or newer.
- `uv` for the recommended installation and lifecycle commands.
- Codex CLI available as `codex` for actual Codex use.
- Network access for health and usage checks.

## Installation

```bash
git clone https://github.com/Lortzing/CodexRelay.git
cd CodexRelay
./install.sh
```

The installer registers both commands:

```bash
cxr --help
codex-relay --help
```

`cxr` is the recommended short command. Shell completion is installed silently; completion-management flags are not exposed. When the profile library is empty, installation or the first business command automatically imports the active `$CODEX_HOME/auth.json` and `config.toml`.

Direct installation is also supported:

```bash
uv tool install --force git+https://github.com/Lortzing/CodexRelay.git
cxr status --no-probe
```

## Storage

```text
~/.config/codex-relay/
├── profiles/
│   └── <name>/
│       ├── profile.json   # Non-secret metadata
│       ├── auth.json      # Credentials; mode 0600
│       └── config.toml    # Complete Codex config for this profile
├── backups/
├── state.json
└── switch.lock
```

Active Codex files are written to:

```text
~/.codex/auth.json
~/.codex/config.toml
```

Override locations with `CODEX_RELAY_HOME`, `CODEX_HOME`, or the global `--home` and `--codex-home` options.

## Automatic first-run import

When no managed profile exists, CodexRelay imports the active Codex configuration automatically. The importer detects ChatGPT-token or API-key login, preserves both files exactly, and extracts non-secret metadata such as email, plan, model, provider id, and base URL.

Explicit import remains available:

```bash
cxr import-current
cxr import-current official
```

Optional API probe and balance overrides:

```bash
cxr import-current gateway \
  --health-mode responses \
  --balance-url https://gateway.example.com/account/credits \
  --balance-path data.balance
```

## Add profiles

Import a ChatGPT `auth.json`:

```bash
cxr add-auth official ~/.codex/auth.json
```

Optionally use a specific base configuration and model:

```bash
cxr add-auth official ./auth.json \
  --config ~/.codex/config.toml \
  --model gpt-5.6
```

Add an API key, URL, and model:

```bash
cxr add-api backup \
  --url https://gateway.example.com/v1 \
  --model gpt-5.6 \
  --api-key 'sk-...'
```

Avoid shell history by reading the key from standard input:

```bash
printf '%s' "$GATEWAY_API_KEY" | cxr add-api backup \
  --url https://gateway.example.com/v1 \
  --model gpt-5.6 \
  --api-key-stdin
```

Without either API-key option, CodexRelay prompts for the key with hidden input.

### API health modes

Responses probe, which may consume a small number of tokens:

```bash
cxr add-api backup \
  --url https://gateway.example.com/v1 \
  --model gpt-5.6 \
  --health-mode responses
```

Models-list probe:

```bash
cxr add-api backup \
  --url https://gateway.example.com/v1 \
  --model gpt-5.6 \
  --health-mode models
```

Custom probe:

```bash
cxr add-api backup \
  --url https://gateway.example.com/v1 \
  --model gpt-5.6 \
  --health-mode custom \
  --health-endpoint https://gateway.example.com/health \
  --expected-text ok
```

Optional provider-specific balance endpoint:

```bash
cxr add-api backup \
  --url https://gateway.example.com/v1 \
  --model gpt-5.6 \
  --balance-url https://gateway.example.com/account/credits \
  --balance-path data.balance
```

## Status and manual switching

```bash
cxr status --no-probe
cxr status
cxr status --watch --interval 30
cxr status --json
cxr use official
cxr use backup
```

The status table combines profile metadata, active state, health, latency, ChatGPT usage, optional API balance, and diagnostics.

Before a switch, current active files are backed up. Replacement uses a process lock and atomic writes; validation failure restores the previous active files. Existing Codex processes may cache authentication, so restart them after a manual switch.

## Automatic switching

One evaluation in priority order:

```bash
cxr auto official backup
```

Continuous monitoring:

```bash
cxr auto official backup \
  --watch \
  --interval 60 \
  --fail-threshold 2 \
  --recover-threshold 2 \
  --cooldown 300
```

Policy:

1. Earlier profiles have higher priority.
2. The active profile fails over after the configured consecutive-failure threshold.
3. A higher-priority profile is restored after the consecutive-recovery threshold.
4. Recovery respects cooldown; emergency failover does not.
5. If every candidate is unhealthy, active files remain unchanged.

Select a healthy profile and launch a fresh Codex process:

```bash
cxr launch -p official -p backup -- exec "say hello"
```

Everything after `--` is passed to `codex`.

## Update

Update from the GitHub `main` branch while preserving profiles and active Codex files:

```bash
cxr update
```

Skip confirmation:

```bash
cxr update --yes
```

## Uninstall

Interactive uninstall asks whether profiles, backups, and state should be preserved:

```bash
cxr uninstall
```

Non-interactive uninstall preserves managed data by default:

```bash
cxr uninstall --yes
```

Permanently delete all CodexRelay-managed data:

```bash
cxr uninstall --purge
cxr uninstall --purge --yes
```

Uninstall removes shell-completion artifacts but never removes active `~/.codex/auth.json` or `~/.codex/config.toml`.

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

Edit the absolute executable path in `examples/com.codex-relay.auto.plist`, then run:

```bash
mkdir -p ~/Library/LaunchAgents
cp examples/com.codex-relay.auto.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.codex-relay.auto.plist
```

## ChatGPT usage query

For ChatGPT profiles, CodexRelay reads the access token and account id from `auth.json`, then queries:

```text
GET https://chatgpt.com/backend-api/wham/usage
Authorization: Bearer <access token>
ChatGPT-Account-Id: <account id>
```

This is an unstable implementation endpoint, not a guaranteed public API. Use `cxr status --no-probe` to avoid network access.

## Security

- Profile directories use restrictive permissions where supported.
- Credential and state files use mode `0600` where supported.
- API keys and access tokens are not printed in status tables or JSON output.
- Prefer `--api-key-stdin` over a direct argument to avoid shell history.
- Custom health and balance endpoints receive the configured API key as a Bearer token.
- Backups contain credentials and must be protected.

## Diagnostics and development

```bash
cxr doctor
cxr doctor --json

uv sync --extra dev
uv run pytest
uv build
```
