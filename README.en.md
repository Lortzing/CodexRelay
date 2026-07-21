# CodexRelay

[简体中文](README.md) | English

[![CI](https://github.com/Lortzing/CodexRelay/actions/workflows/ci.yml/badge.svg)](https://github.com/Lortzing/CodexRelay/actions/workflows/ci.yml)
[![GitHub Release](https://img.shields.io/github/v/release/Lortzing/CodexRelay)](https://github.com/Lortzing/CodexRelay/releases)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/github/license/Lortzing/CodexRelay)](LICENSE)

CodexRelay is a multi-account and multi-API profile manager for the OpenAI Codex CLI. It supports `auth.json` logins, OpenAI-compatible APIs, status and usage checks, manual switching, and automatic failover.

Each profile stores a complete `auth.json` and `config.toml`. Before activation, CodexRelay backs up the active files, acquires a process lock, and atomically replaces the Codex configuration.

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

## Installation

### Standalone GitHub Release packages

Each release automatically contains four platform archives:

| Operating system | Architecture | Release asset |
|---|---|---|
| Windows | x86_64 | `codex-relay-<version>-windows-x86_64.zip` |
| macOS | Intel x86_64 | `codex-relay-<version>-macos-x86_64.tar.gz` |
| macOS | Apple Silicon arm64 | `codex-relay-<version>-macos-arm64.tar.gz` |
| Linux | x86_64 | `codex-relay-<version>-linux-x86_64.tar.gz` |

A `SHA256SUMS` file is included for download verification.

Windows:

```powershell
# Extract the archive, move cxr.exe to a permanent directory, and add it to PATH.
cxr.exe --help
```

macOS / Linux:

```bash
chmod +x cxr
mkdir -p ~/.local/bin
mv cxr ~/.local/bin/cxr
cxr --help
```

Standalone packages include the Python runtime and dependencies. No separate Python installation is required. Current artifacts are not commercially code-signed, so Windows SmartScreen or macOS Gatekeeper may display a warning.

### Install from source

Python 3.11+ and `uv` are required:

```bash
git clone https://github.com/Lortzing/CodexRelay.git
cd CodexRelay
./install.sh
```

Direct Git installation is also supported:

```bash
uv tool install --force git+https://github.com/Lortzing/CodexRelay.git
```

Available commands:

```bash
cxr --help
codex-relay --help
```

`cxr` is the recommended short command.

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

Active Codex files are stored at:

```text
~/.codex/auth.json
~/.codex/config.toml
```

Override locations with `CODEX_RELAY_HOME`, `CODEX_HOME`, or the global `--home` and `--codex-home` options.

## Automatic first-run import

When no managed profile exists, installation or the first business command imports the active Codex configuration. The importer detects ChatGPT-token or API-key authentication and extracts non-secret metadata such as email, plan, model, provider id, and base URL.

Explicit import remains available:

```bash
cxr import-current
cxr import-current official
```

## Add profiles

Import a ChatGPT/Codex `auth.json`:

```bash
cxr add-auth official ~/.codex/auth.json
```

Add an API profile:

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

## Health checks

Minimal Responses API request:

```bash
cxr add-api backup \
  --url https://gateway.example.com/v1 \
  --model gpt-5.6 \
  --health-mode responses
```

Models API:

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

## Status and manual switching

```bash
cxr status --no-probe
cxr status
cxr status --watch --interval 30
cxr status --json
cxr use official
```

Before a switch, active files are backed up. Replacement uses a process lock and atomic writes; validation failure restores the previous files. Existing Codex processes may cache authentication, so restart Codex after switching.

## Automatic switching

Profile order defines priority:

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

## Update and uninstall

Update a source installation:

```bash
cxr update
cxr update --yes
```

Interactive uninstall asks whether profiles, backups, and state should be preserved:

```bash
cxr uninstall
```

Preserve data without confirmation:

```bash
cxr uninstall --yes
```

Permanently delete all CodexRelay-managed data:

```bash
cxr uninstall --purge
cxr uninstall --purge --yes
```

Uninstall never removes active `~/.codex/auth.json` or `~/.codex/config.toml` files.

## Release workflow

Push a tag that matches the version in `pyproject.toml`:

```bash
git tag -a v0.6.0 -m "CodexRelay v0.6.0"
git push origin v0.6.0
```

The Release workflow automatically:

1. Verifies that the Git tag matches the project version.
2. Runs tests in all four target environments.
3. Builds four standalone executables with PyInstaller.
4. Smoke-tests every executable with `cxr --help`.
5. Creates ZIP or TAR.GZ platform archives.
6. Generates `SHA256SUMS`.
7. Creates or updates the GitHub Release and uploads all artifacts.

## Security

- Profile directories and credential files use restrictive permissions.
- API keys and access tokens are not printed in status tables or JSON output.
- Prefer `--api-key-stdin` to avoid shell history.
- Custom health and balance endpoints receive the configured Bearer token.
- Backups may contain credentials and must be protected.
- ChatGPT usage checks rely on an unstable implementation endpoint and may break after upstream changes.

## Development

```bash
uv sync --extra dev
uv run pytest
uv run cxr --help
uv build --no-sources
```
