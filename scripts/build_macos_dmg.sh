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
[[ "$architecture" == "x86_64" || "$architecture" == "arm64" ]] || { echo "Unsupported architecture" >&2; exit 2; }
[[ -f "$binary" ]] || { echo "Binary not found: $binary" >&2; exit 1; }
root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output_dir="$(mkdir -p "$output_dir" && cd "$output_dir" && pwd)"
work_dir="$(mktemp -d "${TMPDIR:-/tmp}/coder-relay-macos.XXXXXX")"
trap 'rm -rf "$work_dir"' EXIT
package_root="$work_dir/pkgroot"
install -d "$package_root/usr/local/bin"
install -m 0755 "$binary" "$package_root/usr/local/bin/cdy"
install -d "$package_root/usr/local/share/doc/coder-relay"
for name in README.md README.en.md LICENSE; do
  [[ -f "$root_dir/$name" ]] && install -m 0644 "$root_dir/$name" "$package_root/usr/local/share/doc/coder-relay/$name"
done
pkg_path="$work_dir/CoderRelay-${version}-macOS-${architecture}.pkg"
pkgbuild --root "$package_root" --identifier "com.lortzing.coderrelay" --version "$version" --install-location "/" "$pkg_path"
dmg_root="$work_dir/dmgroot"; mkdir -p "$dmg_root"
cp "$pkg_path" "$dmg_root/CoderRelay-${version}.pkg"
for name in README.md README.en.md LICENSE; do [[ -f "$root_dir/$name" ]] && cp "$root_dir/$name" "$dmg_root/$name"; done
cat > "$dmg_root/INSTALL.txt" <<TXT
CoderRelay macOS installer

Double-click CoderRelay-${version}.pkg and follow the Installer prompts.
The package installs cdy to /usr/local/bin/cdy.

After installation, open Terminal and run:
  cdy status
TXT
dmg_path="$output_dir/CoderRelay-${version}-macOS-${architecture}.dmg"
hdiutil create -volname "CoderRelay ${version}" -srcfolder "$dmg_root" -ov -format UDZO "$dmg_path"
printf '%s\n' "$dmg_path"
