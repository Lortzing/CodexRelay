# CodexRelay

[简体中文](README.md) | English

[![CI](https://github.com/Lortzing/CodexRelay/actions/workflows/ci.yml/badge.svg)](https://github.com/Lortzing/CodexRelay/actions/workflows/ci.yml)
[![GitHub Release](https://img.shields.io/github/v/release/Lortzing/CodexRelay)](https://github.com/Lortzing/CodexRelay/releases)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/github/license/Lortzing/CodexRelay)](LICENSE)

CodexRelay is a multi-account and multi-API profile manager for the OpenAI Codex CLI. It supports `auth.json` logins, OpenAI-compatible APIs, status and usage checks, manual switching, and automatic failover.

Each profile stores a complete `auth.json` and `config.toml`. Before activation, CodexRelay backs up the active files and updates them using a process lock and atomic replacement.

## Features

- Manage multiple ChatGPT/Codex login profiles.
- Manage OpenAI-compatible profiles using an API key, base URL, and model.
- Import the active Codex configuration automatically on installation or first use.
- Switch profiles with backup, validation, and rollback.
- Display ChatGPT plan, rate-limit windows, credits, API balance, and latency.
- Probe Responses, Models, or custom health endpoints.
- Fail over by priority and recover automatically when preferred profiles become healthy.
- Install completion for Bash, Zsh, and Fish.
- Update and uninstall while optionally preserving managed profile data.

## Installation

### Standalone executables

Download the archive matching your operating system and processor from [Releases](https://github.com/Lortzing/CodexRelay/releases). Standalone builds do not require a preinstalled Python interpreter.

| OS | Architecture | Release asset |
|---|---|---|
| Windows | 32-bit x86 | `codex-relay-<version>-windows-x86.zip` |
| Windows | x86_64 / x64 | `codex-relay-<version>-windows-x86_64.zip` |
| Windows | ARM64 | `codex-relay-<version>-windows-arm64.zip` |
| macOS | Intel x86_64 | `codex-relay-<version>-macos-x86_64.tar.gz` |
| macOS | Apple Silicon ARM64 | `codex-relay-<version>-macos-arm64.tar.gz` |
| Linux | x86_64 / AMD64 | `codex-relay-<version>-linux-x86_64.tar.gz` |
| Linux | ARM64 / AArch64 | `codex-relay-<version>-linux-aarch64.tar.gz` |

Linux/macOS:

```bash
mkdir -p ~/.local/bin
tar -xzf codex-relay-<version>-<platform>.tar.gz
install -m 0755 codex-relay-<version>-<platform>/cxr ~/.local/bin/cxr
cxr --help
```

Windows: extract `cxr.exe`, place it in a directory on `PATH`, and run:

```powershell
cxr.exe --help
```

Every release contains `SHA256SUMS.txt`:

```bash
sha256sum -c SHA256SUMS.txt
```

The current executables are not commercially code-signed. macOS or Windows may display a security warning. Verify that the file came from this repository and check its SHA-256 digest before running it.

### Install from source with uv

```bash
git clone https://github.com/Lortzing/CodexRelay.git
cd CodexRelay
./install.sh
```

Or install directly from GitHub:

```bash
uv tool install --force git+https://github.com/Lortzing/CodexRelay.git
cxr status --no-probe
```

The public commands are:

```bash
cxr --help
codex-relay --help
```

`cxr` is the recommended short command.

## Automatic first-run import

When no managed profile exists, installation or the first business command imports:

```text
$CODEX_HOME/auth.json
$CODEX_HOME/config.toml
```

Without `CODEX_HOME`, CodexRelay uses:

```text
~/.codex/auth.json
~/.codex/config.toml
```

Explicit import remains available:

```bash
cxr import-current
cxr import-current official
```

## Add profiles

Import a ChatGPT/Codex login:

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

## Status and manual switching

```bash
cxr status
cxr status --no-probe
cxr status --watch --interval 30
cxr status --json
cxr use official
```

Existing Codex processes may cache authentication. Restart Codex after switching profiles.

## Automatic failover

Run one evaluation:

```bash
cxr auto official backup
```

Monitor continuously:

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
2. The active profile fails over after the consecutive-failure threshold.
3. A preferred profile is restored after the consecutive-recovery threshold.
4. Recovery respects cooldown; emergency failover does not.
5. If every candidate is unhealthy, the active files remain unchanged.

Select a healthy profile and launch a new Codex process:

```bash
cxr launch -p official -p backup -- exec "say hello"
```

Arguments after `--` are passed directly to `codex`.

## Update

For installations managed by `uv tool`, `pipx`, or source tooling:

```bash
cxr update
cxr update --yes
```

Standalone executables are updated by downloading the matching asset from GitHub Releases and replacing the old executable. The standalone build does not silently overwrite itself.

## Uninstall

Interactively choose whether profiles, backups, and state are preserved:

```bash
cxr uninstall
```

Skip confirmation and preserve data:

```bash
cxr uninstall --yes
```

Remove all CodexRelay-managed data:

```bash
cxr uninstall --purge
cxr uninstall --purge --yes
```

Standalone builds also remove their executable; on Windows this happens after the running process exits. No uninstall mode removes the active `~/.codex/auth.json` or `~/.codex/config.toml`.

## Storage

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

Override paths with `CODEX_RELAY_HOME`, `CODEX_HOME`, `--home`, and `--codex-home`.

## Automated releases

Push a tag matching the project version:

```bash
git tag -a v0.6.0 -m "CodexRelay v0.6.0"
git push origin v0.6.0
```

The release workflow:

1. Verifies that the tag matches `pyproject.toml`.
2. Runs the complete test suite.
3. Builds standalone executables on native OS and CPU runners.
4. Smoke-tests every executable with `--help`.
5. Packages seven platform assets and generates `SHA256SUMS.txt`.
6. Creates or updates the GitHub Release.

This project does not publish to PyPI or GitHub Packages.

## Security

- Profiles and backups contain credentials and must be protected.
- Credential files use mode `0600` where supported.
- API keys and access tokens are not printed in status tables or JSON output.
- Responses API health checks may consume a small number of tokens.
- The ChatGPT usage endpoint is not a guaranteed public API and may change upstream.

## Development

```bash
uv sync --extra dev
uv run pytest
uv build --no-sources
```
