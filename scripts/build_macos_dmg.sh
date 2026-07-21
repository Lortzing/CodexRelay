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

signing_enabled="${MACOS_SIGNING_ENABLED:-false}"
if [[ "$signing_enabled" == "true" ]]; then
  : "${MACOS_APPLICATION_IDENTITY:?MACOS_APPLICATION_IDENTITY is required}"
  : "${MACOS_INSTALLER_IDENTITY:?MACOS_INSTALLER_IDENTITY is required}"
  : "${APPLE_ID:?APPLE_ID is required}"
  : "${APPLE_TEAM_ID:?APPLE_TEAM_ID is required}"
  : "${APPLE_APP_PASSWORD:?APPLE_APP_PASSWORD is required}"
  suffix=""
else
  suffix="-unsigned"
fi

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
pkg_args=(
  --root "$package_root"
  --identifier "com.lortzing.codexrelay"
  --version "$version"
  --install-location "/"
)
if [[ "$signing_enabled" == "true" ]]; then
  pkg_args+=(--sign "$MACOS_INSTALLER_IDENTITY")
fi
pkgbuild "${pkg_args[@]}" "$pkg_path"

if [[ "$signing_enabled" == "true" ]]; then
  pkgutil --check-signature "$pkg_path"
  xcrun notarytool submit "$pkg_path" \
    --apple-id "$APPLE_ID" \
    --team-id "$APPLE_TEAM_ID" \
    --password "$APPLE_APP_PASSWORD" \
    --wait
  xcrun stapler staple "$pkg_path"
  xcrun stapler validate "$pkg_path"
fi

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

dmg_path="$output_dir/CodexRelay-${version}-macOS-${architecture}${suffix}.dmg"
hdiutil create \
  -volname "CodexRelay ${version}" \
  -srcfolder "$dmg_root" \
  -ov \
  -format UDZO \
  "$dmg_path"

if [[ "$signing_enabled" == "true" ]]; then
  codesign --force --timestamp --sign "$MACOS_APPLICATION_IDENTITY" "$dmg_path"
  codesign --verify --verbose=2 "$dmg_path"
  xcrun notarytool submit "$dmg_path" \
    --apple-id "$APPLE_ID" \
    --team-id "$APPLE_TEAM_ID" \
    --password "$APPLE_APP_PASSWORD" \
    --wait
  xcrun stapler staple "$dmg_path"
  xcrun stapler validate "$dmg_path"
fi

printf '%s\n' "$dmg_path"
