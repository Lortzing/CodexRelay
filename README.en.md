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
- Verified automatic updates from the latest stable GitHub Release.
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

Open the DMG and run the included PKG. The current package uses a persistent PyInstaller directory runtime instead of extracting a one-file executable on every command.

The runtime is installed under:

```text
/usr/local/lib/coder-relay/
```

The command remains available at:

```text
/usr/local/bin/cdy
```

Install the new PKG again when upgrading from the earlier macOS one-file build. The existing executable does not become faster until it is replaced.

```bash
time cdy --help
cdy status --no-probe
```

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
uv tool install --force git+https://github.com/Lortzing/CoderRelay.git@v0.8.0
```

## Quick start

```bash
cdy status
cdy status --no-probe
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

Override it with `CODER_RELAY_HOME`. Active Codex files remain under `~/.codex`; updates and uninstall never delete them.

## Automatic updates and uninstall

Starting with v0.8.0, every installation type supports:

```bash
cdy update
cdy update -y
cdy update --force
```

The updater:

1. Queries the latest stable GitHub Release instead of tracking `main`.
2. Selects the exact asset for the operating system, CPU architecture, and installation type.
3. Downloads the asset and `SHA256SUMS.txt`.
4. Verifies size, the SHA-256 manifest, and the GitHub asset digest when available.
5. Installs or replaces the application using the native platform mechanism.

Platform behavior:

- Windows Setup runs the verified installer after the current process exits.
- Windows Portable replaces `cdy.exe` after the current process exits.
- macOS mounts the DMG and runs the system PKG installer; an administrator password may be requested.
- Linux DEB/RPM uses the system package manager.
- Linux TAR.GZ replaces the current executable in place.
- `uv`, `pipx`, and `pip` install the fixed tag for the latest stable release rather than `main`.

v0.7.0 and earlier do not contain the downloader, so they require one manual installation of v0.8.0. Later stable releases can then be installed with `cdy update`.

```bash
cdy uninstall
cdy uninstall --purge
```

The macOS PKG installs under `/usr/local`, so remove it with administrator privileges:

```bash
sudo cdy uninstall --yes
```

## Release

Create a tag matching `pyproject.toml`:

```bash
git tag -a v0.8.0 -m "CoderRelay v0.8.0"
git push origin v0.8.0
```

The Release workflow builds native Windows installers, macOS DMG/PKG installers, Linux TAR/DEB/RPM packages, and `SHA256SUMS.txt`. macOS uses a PyInstaller directory runtime to reduce repeated startup latency. These artifacts are unsigned and may trigger Windows SmartScreen or macOS Gatekeeper warnings.

## Development

```bash
uv sync --extra dev
uv run pytest
uv run cdy --help
uv build --no-sources
```

## License

MIT
