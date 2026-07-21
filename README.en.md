# CoderRelay

[简体中文](README.md) | English

[![CI](https://github.com/Lortzing/CoderRelay/actions/workflows/ci.yml/badge.svg)](https://github.com/Lortzing/CoderRelay/actions/workflows/ci.yml)
[![GitHub Release](https://img.shields.io/github/v/release/Lortzing/CoderRelay)](https://github.com/Lortzing/CoderRelay/releases)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/github/license/Lortzing/CoderRelay)](LICENSE)

CoderRelay manages accounts, profiles, and API routes for coding-agent CLIs. The current release fully supports OpenAI Codex CLI. The product identity and architecture are vendor-neutral so Claude Code can be added next.

Current capabilities:

- Multiple ChatGPT/Codex login profiles.
- OpenAI-compatible API profiles using an API key, base URL, and model.
- Automatic import of the active Codex configuration on first use.
- Manual switching, health checks, failover, and preferred-profile recovery.
- ChatGPT plan, rate-limit windows, credits, provider balance, and latency display.
- Safe activation using backups, process locks, and atomic writes.
- Bash, Zsh, and Fish completion.

> Claude Code support is planned. This release does not modify Claude Code configuration.

## Commands

```bash
cdy --help          # recommended
coder-relay --help  # full command
```

## Installation

### Windows

| Architecture | Installer | Portable |
|---|---|---|
| x86 32-bit | `CoderRelay-Setup-<version>-windows-x86.exe` | `CoderRelay-Portable-<version>-windows-x86.zip` |
| x86_64 / x64 | `CoderRelay-Setup-<version>-windows-x86_64.exe` | `CoderRelay-Portable-<version>-windows-x86_64.zip` |
| ARM64 | `CoderRelay-Setup-<version>-windows-arm64.exe` | `CoderRelay-Portable-<version>-windows-arm64.zip` |

### macOS

| Architecture | Disk image |
|---|---|
| Intel x86_64 | `CoderRelay-<version>-macOS-x86_64.dmg` |
| Apple Silicon ARM64 | `CoderRelay-<version>-macOS-arm64.dmg` |

The included PKG installs `cdy` to `/usr/local/bin/cdy`.

### Linux

| Architecture | Portable | Debian/Ubuntu | Fedora/RHEL |
|---|---|---|---|
| x86_64 | `coder-relay-<version>-linux-x86_64.tar.gz` | `coder-relay_<version>_amd64.deb` | `coder-relay-<version>-1.x86_64.rpm` |
| ARM64/AArch64 | `coder-relay-<version>-linux-aarch64.tar.gz` | `coder-relay_<version>_arm64.deb` | `coder-relay-<version>-1.aarch64.rpm` |

### Source installation

```bash
git clone https://github.com/Lortzing/CoderRelay.git
cd CoderRelay
./install.sh
```

Or install a fixed tag:

```bash
uv tool install --force git+https://github.com/Lortzing/CoderRelay.git@v0.7.0
```

## Quick start

```bash
cdy status
cdy add-auth official ~/.codex/auth.json
cdy add-api backup --url https://gateway.example.com/v1 --model gpt-5.6 --api-key-stdin
cdy use official
cdy auto official backup --watch
cdy launch -p official -p backup --
```

## Storage

```text
~/.config/coder-relay/
├── profiles/
├── backups/
├── state.json
└── switch.lock
```

Override it with `CODER_RELAY_HOME`. Active Codex files remain under `~/.codex`; uninstall never deletes them.

## Release

A matching `v*` tag builds native Windows installers, macOS DMG/PKG installers, Linux TAR/DEB/RPM packages, and `SHA256SUMS.txt`. These artifacts are unsigned and may trigger Windows SmartScreen or macOS Gatekeeper warnings.

## Development

```bash
uv sync --extra dev
uv run pytest
uv run cdy --help
uv build --no-sources
```

## License

MIT
