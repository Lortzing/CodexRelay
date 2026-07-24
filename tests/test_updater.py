from __future__ import annotations

import hashlib
from pathlib import Path

import httpx
import pytest

from coder_relay.errors import RelayError
from coder_relay.updater import (
    ReleaseAsset,
    fetch_latest_release,
    parse_checksums,
    select_update_target,
    verify_asset,
    version_key,
)


def test_version_key_accepts_release_tags() -> None:
    assert version_key("v1.2.3") == (1, 2, 3)
    assert version_key("1.2.3") == (1, 2, 3)
    assert version_key("1.2.3+build") == (1, 2, 3)


def test_version_key_rejects_non_semver() -> None:
    with pytest.raises(RelayError):
        version_key("latest")


def test_fetch_latest_release_uses_browser_download_assets() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).endswith("/releases/latest")
        return httpx.Response(
            200,
            json={
                "tag_name": "v0.8.0",
                "assets": [
                    {
                        "name": "SHA256SUMS.txt",
                        "browser_download_url": "https://example.invalid/SHA256SUMS.txt",
                        "size": 123,
                        "digest": "sha256:" + "a" * 64,
                    }
                ],
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        release = fetch_latest_release(client)
    assert release.tag == "v0.8.0"
    assert release.version == "0.8.0"
    assert release.assets["SHA256SUMS.txt"].size == 123


@pytest.mark.parametrize(
    ("kwargs", "installation", "asset_name"),
    [
        (
            {"system": "windows", "architecture": "x86_64", "windows_setup": True},
            "windows-setup",
            "CoderRelay-Setup-0.8.0-windows-x86_64.exe",
        ),
        (
            {"system": "windows", "architecture": "arm64", "windows_setup": False},
            "windows-portable",
            "CoderRelay-Portable-0.8.0-windows-arm64.zip",
        ),
        (
            {"system": "macos", "architecture": "arm64"},
            "macos-pkg",
            "CoderRelay-0.8.0-macOS-arm64.dmg",
        ),
        (
            {"system": "linux", "architecture": "x86_64", "linux_package_kind": "deb"},
            "linux-deb",
            "coder-relay_0.8.0_amd64.deb",
        ),
        (
            {"system": "linux", "architecture": "aarch64", "linux_package_kind": "rpm"},
            "linux-rpm",
            "coder-relay-0.8.0-1.aarch64.rpm",
        ),
        (
            {"system": "linux", "architecture": "aarch64", "linux_package_kind": ""},
            "linux-tar",
            "coder-relay-0.8.0-linux-aarch64.tar.gz",
        ),
    ],
)
def test_select_update_target(kwargs: dict[str, object], installation: str, asset_name: str) -> None:
    target = select_update_target("0.8.0", executable=Path("/tmp/cdy"), **kwargs)
    assert target.installation == installation
    assert target.asset_name == asset_name


def test_verify_asset_requires_and_checks_sha256(tmp_path: Path) -> None:
    path = tmp_path / "asset.zip"
    path.write_bytes(b"verified release asset")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    asset = ReleaseAsset(path.name, "https://example.invalid/asset.zip", digest=f"sha256:{digest}")
    verify_asset(path, asset, parse_checksums(f"{digest}  {path.name}\n"))

    with pytest.raises(RelayError, match="SHA-256"):
        verify_asset(path, asset, {path.name: "0" * 64})


def test_parse_checksums_supports_binary_marker() -> None:
    value = "f" * 64
    assert parse_checksums(f"{value} *CoderRelay.dmg\n") == {"CoderRelay.dmg": value}
