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
  echo "Usage: $0 --binary PATH --architecture x86_64|arm64 --version VERSION [--output-dir DIR]" >&2
  exit 2
fi
if [[ "$architecture" != "x86_64" && "$architecture" != "arm64" ]]; then
  echo "Unsupported architecture: $architecture" >&2
  exit 2
fi
if [[ ! -f "$binary" ]]; then
  echo "Binary not found: $binary" >&2
  exit 1
fi

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output_dir="$(mkdir -p "$output_dir" && cd "$output_dir" && pwd)"
work_dir="$(mktemp -d "${TMPDIR:-/tmp}/codex-relay-macos.XXXXXX")"
trap 'rm -rf "$work_dir"' EXIT

package_root="$work_dir/pkgroot"
install -d "$package_root/usr/local/bin"
install -m 0755 "$binary" "$package_root/usr/local/bin/cxr"
install -d "$package_root/usr/local/share/doc/codex-relay"
for name in README.md README.en.md LICENSE; do
  if [[ -f "$root_dir/$name" ]]; then
    install -m 0644 "$root_dir/$name" "$package_root/usr/local/share/doc/codex-relay/$name"
  fi
done

pkg_path="$work_dir/CodexRelay-${version}-macOS-${architecture}.pkg"
pkgbuild \
  --root "$package_root" \
  --identifier "com.lortzing.codexrelay" \
  --version "$version" \
  --install-location "/" \
  "$pkg_path"

dmg_root="$work_dir/dmgroot"
mkdir -p "$dmg_root"
cp "$pkg_path" "$dmg_root/CodexRelay-${version}.pkg"
for name in README.md README.en.md LICENSE; do
  if [[ -f "$root_dir/$name" ]]; then
    cp "$root_dir/$name" "$dmg_root/$name"
  fi
done
cat > "$dmg_root/INSTALL.txt" <<TXT
CodexRelay macOS installer

Double-click CodexRelay-${version}.pkg and follow the Installer prompts.
The package installs cxr to /usr/local/bin/cxr.

After installation, open Terminal and run:
  cxr status
TXT

dmg_path="$output_dir/CodexRelay-${version}-macOS-${architecture}.dmg"
hdiutil create \
  -volname "CodexRelay ${version}" \
  -srcfolder "$dmg_root" \
  -ov \
  -format UDZO \
  "$dmg_path"

printf '%s\n' "$dmg_path"
