#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v uv >/dev/null 2>&1; then
  printf 'Error: uv is required to install CodexRelay.\n' >&2
  exit 1
fi

uv tool install --force "$ROOT_DIR"

BIN_DIR="$(uv tool dir --bin)"
if [[ -x "$BIN_DIR/cxr" ]]; then
  # Configure completion and bootstrap the active Codex configuration.
  # Missing or invalid active files must not fail installation.
  "$BIN_DIR/cxr" --help >/dev/null
  "$BIN_DIR/cxr" status --no-probe --json >/dev/null 2>&1 || true
fi

printf 'Installed CodexRelay. Use: cxr status\n'
