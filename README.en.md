# CodexRelay

[简体中文](README.md) | English

[![CI](https://github.com/Lortzing/CodexRelay/actions/workflows/ci.yml/badge.svg)](https://github.com/Lortzing/CodexRelay/actions/workflows/ci.yml)
[![GitHub Release](https://img.shields.io/github/v/release/Lortzing/CodexRelay)](https://github.com/Lortzing/CodexRelay/releases)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/github/license/Lortzing/CodexRelay)](LICENSE)

CodexRelay is a multi-account and multi-API profile manager for the OpenAI Codex CLI. It supports `auth.json` logins, OpenAI-compatible APIs, status and usage checks, manual switching, and automatic failover.

Each profile stores a complete `auth.json` and `config.toml`. Before activation, CodexRelay backs up the active files, acquires a process lock, and atomically replaces the Codex configuration.

## Features

- Manage multiple ChatGPT/Codex login profiles.
- Manage OpenAI-compatible API profiles using an API key, base URL, and model.
- Automatically import the active Codex configuration on first use.
- Manual switching, health checks, failover, and preferred-profile recovery.
- Display ChatGPT plan, rate-limit windows, credits, API balance, and latency.
- Bash, Zsh, and Fish completion.
- Self-update and uninstall with optional profile-data preservation.

## Installation

### Windows

| Architecture | Installer | Portable |
|---|---|---|
| x86 32-bit | `CodexRelay-Setup-<version>-windows-x86.exe` | `CodexRelay-Portable-<version>-windows-x86.zip` |
| x86_64 / x64 | `CodexRelay-Setup-<version>-windows-x86_64.exe` | `CodexRelay-Portable-<version>-windows-x86_64.zip` |
| ARM64 | `CodexRelay-Setup-<version>-windows-arm64.exe` | `CodexRelay-Portable-<version>-windows-arm64.zip` |

The Setup executable installs `cxr.exe` in the current user's application directory, adds it to the user `PATH`, and registers a standard uninstaller.

```powershell
cxr --help
```

Windows may display a security warning for installers downloaded from the internet.

### macOS

| Architecture | Disk image |
|---|---|
| Intel x86_64 | `CodexRelay-<version>-macOS-x86_64.dmg` |
| Apple Silicon ARM64 | `CodexRelay-<version>-macOS-arm64.dmg` |

Open the DMG and run the included `CodexRelay-<version>.pkg`. It installs:

```text
/usr/local/bin/cxr
```

macOS may display a security warning for disk images downloaded from the internet.

### Linux

| Architecture | Portable | Debian/Ubuntu | Fedora/RHEL |
|---|---|---|---|
| x86_64 | `codex-relay-<version>-linux-x86_64.tar.gz` | `codex-relay_<version>_amd64.deb` | `codex-relay-<version>-1.x86_64.rpm` |
| ARM64/AArch64 | `codex-relay-<version>-linux-aarch64.tar.gz` | `codex-relay_<version>_arm64.deb` | `codex-relay-<version>-1.aarch64.rpm` |

```bash
sudo apt install ./codex-relay_<version>_amd64.deb
# or
sudo rpm -Uvh ./codex-relay-<version>-1.x86_64.rpm
```

### Install from source

```bash
git clone https://github.com/Lortzing/CodexRelay.git
cd CodexRelay
./install.sh
```

Or install a fixed tag:

```bash
uv tool install --force git+https://github.com/Lortzing/CodexRelay.git@v0.6.0
```

## Verify downloads

Every release contains `SHA256SUMS.txt`:

```bash
sha256sum -c SHA256SUMS.txt
```

## Common commands

```bash
cxr status
cxr import-current
cxr add-auth official ~/.codex/auth.json
cxr add-api backup --url https://gateway.example.com/v1 --model gpt-5.6
cxr use official
cxr auto official backup --watch
cxr launch -p official -p backup --
cxr doctor
cxr update
cxr uninstall
```

## Automatic switching policy

1. Earlier profiles have higher priority.
2. The active profile fails over after the consecutive-failure threshold.
3. A preferred profile is restored after the consecutive-recovery threshold.
4. Recovery respects cooldown; emergency failover does not.
5. If all candidates are unhealthy, active files remain unchanged.

## Storage

```text
~/.config/codex-relay/
├── profiles/
├── backups/
├── state.json
└── switch.lock
```

Active Codex files remain at `~/.codex/auth.json` and `~/.codex/config.toml`; uninstall does not remove them.

## Release

Push a tag that matches `pyproject.toml`:

```bash
git tag -a v0.6.0 -m "CodexRelay v0.6.0"
git push origin v0.6.0
```

The Release workflow builds native Windows Setup executables, macOS DMG/PKG installers, and Linux TAR/DEB/RPM packages, smoke-tests them, generates `SHA256SUMS.txt`, and uploads the assets to GitHub Releases.

## Security

- Profiles and backups contain credentials and must be protected.
- API keys and access tokens are not printed in status output.
- Prefer `--api-key-stdin` to avoid shell history.
- Responses API health checks may consume a small number of tokens.
- ChatGPT usage checks rely on an unstable implementation endpoint.

## Development

```bash
uv sync --extra dev
uv run pytest
uv run cxr --help
uv build --no-sources
```
