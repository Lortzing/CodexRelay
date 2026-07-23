#!/usr/bin/env bash
set -euo pipefail

bundle=""
architecture=""
version=""
output_dir="release-assets"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bundle) bundle="$2"; shift 2 ;;
    --binary) bundle="$2"; shift 2 ;; # Backward-compatible internal alias.
    --architecture) architecture="$2"; shift 2 ;;
    --version) version="$2"; shift 2 ;;
    --output-dir) output_dir="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

[[ -n "$bundle" && -n "$architecture" && -n "$version" ]] || {
  echo "Missing arguments" >&2
  exit 2
}
[[ "$architecture" == "x86_64" || "$architecture" == "arm64" ]] || {
  echo "Unsupported architecture" >&2
  exit 2
}
[[ -d "$bundle" ]] || {
  echo "PyInstaller onedir bundle not found: $bundle" >&2
  exit 1
}
[[ -x "$bundle/cdy" ]] || {
  echo "Bundle entry point is missing or not executable: $bundle/cdy" >&2
  exit 1
}

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
bundle="$(cd "$bundle" && pwd)"
output_dir="$(mkdir -p "$output_dir" && cd "$output_dir" && pwd)"
work_dir="$(mktemp -d "${TMPDIR:-/tmp}/coder-relay-macos.XXXXXX")"
trap 'rm -rf "$work_dir"' EXIT

package_root="$work_dir/pkgroot"
runtime_root="$package_root/usr/local/lib/coder-relay"
launcher_root="$package_root/usr/local/bin"
docs_root="$package_root/usr/local/share/doc/coder-relay"

install -d "$runtime_root" "$launcher_root" "$docs_root"
ditto "$bundle" "$runtime_root"
chmod 0755 "$runtime_root/cdy"
ln -s ../lib/coder-relay/cdy "$launcher_root/cdy"

for name in README.md README.en.md LICENSE; do
  [[ -f "$root_dir/$name" ]] && install -m 0644 "$root_dir/$name" "$docs_root/$name"
done

pkg_path="$work_dir/CoderRelay-${version}-macOS-${architecture}.pkg"
pkgbuild \
  --root "$package_root" \
  --identifier "com.lortzing.coderrelay" \
  --version "$version" \
  --install-location / \
  "$pkg_path"

dmg_root="$work_dir/dmgroot"
mkdir -p "$dmg_root"
cp "$pkg_path" "$dmg_root/CoderRelay-${version}.pkg"
for name in README.md README.en.md LICENSE; do
  [[ -f "$root_dir/$name" ]] && cp "$root_dir/$name" "$dmg_root/$name"
done
cat > "$dmg_root/INSTALL.txt" <<TXT
CoderRelay macOS installer

Double-click CoderRelay-${version}.pkg and follow the Installer prompts.
The package installs the persistent runtime to:
  /usr/local/lib/coder-relay

The command remains available at:
  /usr/local/bin/cdy

The directory-based runtime avoids extracting the application on every command,
so commands such as 'cdy --help' start substantially faster than the old one-file build.

After installation, open Terminal and run:
  cdy --help
  cdy status --no-probe
TXT

dmg_path="$output_dir/CoderRelay-${version}-macOS-${architecture}.dmg"
hdiutil create \
  -volname "CoderRelay ${version}" \
  -srcfolder "$dmg_root" \
  -ov \
  -format UDZO \
  "$dmg_path"
printf '%s\n' "$dmg_path"
