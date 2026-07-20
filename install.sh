#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v uv >/dev/null 2>&1; then
  printf 'Error: uv is required to install CodexRelay.\n' >&2
  exit 1
fi

# The pre-rename distribution used a different uv-tool package name and may
# export conflicting executables. Removing it does not delete profile data.
uv tool uninstall codex-switchboard >/dev/null 2>&1 || true
uv tool install --force "$ROOT_DIR"

BIN_DIR="$(uv tool dir --bin)"
if [[ -x "$BIN_DIR/cr" ]]; then
  # Configure completion, migrate legacy data, and bootstrap the active Codex
  # configuration. Missing/invalid active files must not fail installation.
  "$BIN_DIR/cr" --help >/dev/null
  "$BIN_DIR/cr" status --no-probe --json >/dev/null 2>&1 || true
fi

printf 'Installed CodexRelay. Use: cr status\n'
