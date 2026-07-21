# CodexRelay

[简体中文](README.md) | English

[![CI](https://github.com/Lortzing/CodexRelay/actions/workflows/ci.yml/badge.svg)](https://github.com/Lortzing/CodexRelay/actions/workflows/ci.yml)
[![GitHub Release](https://img.shields.io/github/v/release/Lortzing/CodexRelay)](https://github.com/Lortzing/CodexRelay/releases)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/github/license/Lortzing/CodexRelay)](LICENSE)

CodexRelay is a multi-account and multi-API profile manager for the OpenAI Codex CLI. It supports `auth.json` logins, OpenAI-compatible APIs, status and usage checks, manual switching, and automatic failover.

Each profile stores a complete `auth.json` and `config.toml`. Before activation, CodexRelay backs up the current files, acquires a process lock, and atomically replaces the active Codex configuration.

## Features

- Import and manage multiple ChatGPT/Codex `auth.json` profiles.
- Manage OpenAI-compatible profiles using an API key, base URL, and model.
- Automatically import the active Codex configuration on installation or first use.
- Switch profiles manually with backup, validation, and rollback.
- Display ChatGPT plan, rate-limit windows, and credits.
- Check third-party APIs through Responses, Models, or custom endpoints.
- Fail over by priority and recover automatically when a preferred profile becomes healthy.
- Show profile, health, latency, usage, and balance data as a table or JSON.
- Install silent completion for Bash, Zsh, and Fish.
- Self-update and uninstall with an option to preserve profile data.

## Requirements

- Python 3.11 or newer.
- `uv` is recommended for installation and lifecycle commands.
- The `codex` executable is required for actual Codex use.
- Network access is required for health and usage checks.

## Installation

```bash
git clone https://github.com/Lortzing/CodexRelay.git
cd CodexRelay
./install.sh
```

The installer registers:

```bash
cxr --help
codex-relay --help
```

`cxr` is the recommended short command. The installer silently configures shell completion and imports the active `$CODEX_HOME/auth.json` and `config.toml` when the profile library is empty.

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
│       └── config.toml    # Complete Codex configuration
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

When no managed profile exists, CodexRelay automatically imports the active Codex configuration. It detects ChatGPT-token or API-key authentication and extracts non-secret metadata such as email, plan, model, provider id, and base URL.

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

Import a ChatGPT/Codex `auth.json`:

```bash
cxr add-auth official ~/.codex/auth.json
```

Optionally specify a base configuration and model:

```bash
cxr add-auth official ./auth.json \
  --config ~/.codex/config.toml \
  --model gpt-5.6
```

Add an API-key profile:

```bash
cxr add-api backup \
  --url https://gateway.example.com/v1 \
  --model gpt-5.6 \
  --api-key 'sk-...'
```

To avoid placing the API key in shell history, read it from standard input:

```bash
printf '%s' "$GATEWAY_API_KEY" | cxr add-api backup \
  --url https://gateway.example.com/v1 \
  --model gpt-5.6 \
  --api-key-stdin
```

Without an API-key option, CodexRelay prompts for the key using hidden input.

## API health checks

Responses checks send a minimal request and may consume a small number of tokens:

```bash
cxr add-api backup \
  --url https://gateway.example.com/v1 \
  --model gpt-5.6 \
  --health-mode responses
```

Models API check:

```bash
cxr add-api backup \
  --url https://gateway.example.com/v1 \
  --model gpt-5.6 \
  --health-mode models
```

Custom endpoint:

```bash
cxr add-api backup \
  --url https://gateway.example.com/v1 \
  --model gpt-5.6 \
  --health-mode custom \
  --health-endpoint https://gateway.example.com/health \
  --expected-text ok
```

API providers do not share a universal balance protocol. Configure a provider-specific endpoint and JSON path when available:

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

The status view combines active state, profile metadata, model, endpoint, health, latency, ChatGPT usage, optional API balance, and diagnostics.

Before a switch, active files are backed up. Replacement uses a process lock and atomic writes; validation failure restores the previous configuration. Existing Codex processes may cache authentication, so restart them after a manual switch.

## Automatic switching

Evaluate once in priority order:

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
3. A higher-priority profile is restored after the configured consecutive-recovery threshold.
4. Recovery respects cooldown; emergency failover does not.
5. If every candidate is unhealthy, active files remain unchanged.

Select a healthy profile and launch a fresh Codex process:

```bash
cxr launch -p official -p backup -- exec "say hello"
```

Everything after `--` is passed to `codex`.

## Update and uninstall

Update from the GitHub `main` branch while preserving profiles and active Codex files:

```bash
cxr update
cxr update --yes
```

Interactive uninstall asks whether profiles, backups, and state should be preserved:

```bash
cxr uninstall
```

Skip confirmation and preserve managed data by default:

```bash
cxr uninstall --yes
```

Permanently delete all CodexRelay-managed data:

```bash
cxr uninstall --purge
cxr uninstall --purge --yes
```

Uninstall never removes the active `~/.codex/auth.json` or `~/.codex/config.toml`.

## Background monitoring

systemd user service:

```bash
mkdir -p ~/.config/systemd/user
cp examples/codex-relay.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now codex-relay.service
journalctl --user -u codex-relay.service -f
```

macOS launchd: edit the absolute executable path in `examples/com.codex-relay.auto.plist`, then run:

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

This is an unstable implementation endpoint, not a guaranteed public API. Use `cxr status --no-probe` to skip network probes.

## Security

- Profile directories use restrictive permissions where supported.
- Credential and state files use mode `0600` where supported.
- API keys and access tokens are not printed in status tables or JSON output.
- Prefer `--api-key-stdin` to avoid shell history.
- Custom health and balance endpoints receive the configured API key as a Bearer token.
- Backups contain credentials and must be protected.

## CI and releases

The repository includes two GitHub Actions workflows:

- `CI` tests Python 3.11, 3.12, and 3.13 across Linux, macOS, and Windows on pushes and pull requests.
- `Release` validates the version tag, runs tests, builds a wheel and source distribution, performs installation smoke tests, and creates a GitHub Release when a `v*` tag is pushed.

To publish a release:

```bash
# Update the version in pyproject.toml and src/codex_relay/__init__.py first.

git tag v0.6.0
git push origin v0.6.0
```

The GitHub Release includes:

```text
codex_relay-<version>-py3-none-any.whl
codex_relay-<version>.tar.gz
```

Optional PyPI publishing is disabled by default. After configuring a PyPI Trusted Publisher, creating a GitHub Environment named `pypi`, and setting the repository variable `PUBLISH_TO_PYPI` to `true`, the same tag workflow runs `uv publish` automatically.

## Diagnostics and development

```bash
cxr doctor
cxr doctor --json

uv sync --extra dev
uv run pytest
uv build --no-sources
```
