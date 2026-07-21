#!/usr/bin/env bash
set -euo pipefail
binary=""; architecture=""; version=""; output_dir="release-assets"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --binary) binary="$2"; shift 2 ;;
    --architecture) architecture="$2"; shift 2 ;;
    --version) version="$2"; shift 2 ;;
    --output-dir) output_dir="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done
[[ -n "$binary" && -n "$architecture" && -n "$version" ]] || { echo "Missing arguments" >&2; exit 2; }
[[ "$architecture" == "x86_64" || "$architecture" == "aarch64" ]] || { echo "Unsupported architecture" >&2; exit 2; }
[[ -f "$binary" ]] || { echo "Binary not found: $binary" >&2; exit 1; }
command -v nfpm >/dev/null 2>&1 || { echo "nfpm is required" >&2; exit 1; }
root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output_dir="$(mkdir -p "$output_dir" && cd "$output_dir" && pwd)"
work_dir="$(mktemp -d "${TMPDIR:-/tmp}/coder-relay-linux.XXXXXX")"
trap 'rm -rf "$work_dir"' EXIT
if [[ "$architecture" == "x86_64" ]]; then nfpm_arch="amd64"; deb_arch="amd64"; rpm_arch="x86_64"; else nfpm_arch="arm64"; deb_arch="arm64"; rpm_arch="aarch64"; fi
python "$root_dir/scripts/package_release.py" --binary "$binary" --target "linux-$architecture" --version "$version" --output-dir "$output_dir"
config="$work_dir/nfpm.yaml"
cat > "$config" <<YAML
name: coder-relay
arch: $nfpm_arch
platform: linux
version: $version
release: "1"
section: utils
priority: optional
maintainer: Lortzing <noreply@github.com>
description: Profile and API routing manager for coding agents; currently supports OpenAI Codex CLI.
vendor: Lortzing
homepage: https://github.com/Lortzing/CoderRelay
license: MIT
contents:
  - src: $binary
    dst: /usr/bin/cdy
    file_info: { mode: 0755 }
  - src: $root_dir/README.md
    dst: /usr/share/doc/coder-relay/README.md
    file_info: { mode: 0644 }
  - src: $root_dir/README.en.md
    dst: /usr/share/doc/coder-relay/README.en.md
    file_info: { mode: 0644 }
  - src: $root_dir/LICENSE
    dst: /usr/share/doc/coder-relay/LICENSE
    file_info: { mode: 0644 }
YAML
nfpm package --config "$config" --packager deb --target "$output_dir/coder-relay_${version}_${deb_arch}.deb"
nfpm package --config "$config" --packager rpm --target "$output_dir/coder-relay-${version}-1.${rpm_arch}.rpm"
printf '%s\n' "$output_dir/coder-relay-${version}-linux-${architecture}.tar.gz" "$output_dir/coder-relay_${version}_${deb_arch}.deb" "$output_dir/coder-relay-${version}-1.${rpm_arch}.rpm"
