#!/usr/bin/env bash
set -euo pipefail

binary=""
architecture=""
version=""
output_dir="release-assets"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --binary) binary="$2"; shift 2 ;;
    --architecture) architecture="$2"; shift 2 ;;
    --version) version="$2"; shift 2 ;;
    --output-dir) output_dir="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$binary" || -z "$architecture" || -z "$version" ]]; then
  echo "Usage: $0 --binary PATH --architecture x86_64|aarch64 --version VERSION [--output-dir DIR]" >&2
  exit 2
fi
if [[ "$architecture" != "x86_64" && "$architecture" != "aarch64" ]]; then
  echo "Unsupported architecture: $architecture" >&2
  exit 2
fi
if [[ ! -f "$binary" ]]; then
  echo "Binary not found: $binary" >&2
  exit 1
fi
if ! command -v nfpm >/dev/null 2>&1; then
  echo "nfpm is required to build DEB and RPM packages." >&2
  exit 1
fi

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output_dir="$(mkdir -p "$output_dir" && cd "$output_dir" && pwd)"
work_dir="$(mktemp -d "${TMPDIR:-/tmp}/codex-relay-linux.XXXXXX")"
trap 'rm -rf "$work_dir"' EXIT

if [[ "$architecture" == "x86_64" ]]; then
  nfpm_arch="amd64"
  deb_arch="amd64"
  rpm_arch="x86_64"
else
  nfpm_arch="arm64"
  deb_arch="arm64"
  rpm_arch="aarch64"
fi

python "$root_dir/scripts/package_release.py" \
  --binary "$binary" \
  --target "linux-$architecture" \
  --version "$version" \
  --output-dir "$output_dir"

config="$work_dir/nfpm.yaml"
cat > "$config" <<YAML
name: codex-relay
arch: $nfpm_arch
platform: linux
version: $version
release: "1"
section: utils
priority: optional
maintainer: Lortzing <noreply@github.com>
description: Multi-account and multi-API profile manager for OpenAI Codex CLI.
vendor: Lortzing
homepage: https://github.com/Lortzing/CodexRelay
license: MIT
contents:
  - src: $binary
    dst: /usr/bin/cxr
    file_info:
      mode: 0755
  - src: $root_dir/README.md
    dst: /usr/share/doc/codex-relay/README.md
    file_info:
      mode: 0644
  - src: $root_dir/README.en.md
    dst: /usr/share/doc/codex-relay/README.en.md
    file_info:
      mode: 0644
  - src: $root_dir/LICENSE
    dst: /usr/share/doc/codex-relay/LICENSE
    file_info:
      mode: 0644
YAML

nfpm package \
  --config "$config" \
  --packager deb \
  --target "$output_dir/codex-relay_${version}_${deb_arch}.deb"

nfpm package \
  --config "$config" \
  --packager rpm \
  --target "$output_dir/codex-relay-${version}-1.${rpm_arch}.rpm"

printf '%s\n' \
  "$output_dir/codex-relay-${version}-linux-${architecture}.tar.gz" \
  "$output_dir/codex-relay_${version}_${deb_arch}.deb" \
  "$output_dir/codex-relay-${version}-1.${rpm_arch}.rpm"
