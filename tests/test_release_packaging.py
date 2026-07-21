from __future__ import annotations

import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path


def test_package_release_creates_windows_zip(tmp_path: Path) -> None:
    binary = tmp_path / "cdy.exe"
    binary.write_bytes(b"fake executable")
    output = tmp_path / "out"
    subprocess.run([
        sys.executable, "scripts/package_release.py", "--binary", str(binary),
        "--target", "windows-x86_64", "--version", "v1.2.3", "--output-dir", str(output),
    ], check=True)
    archive = output / "coder-relay-1.2.3-windows-x86_64.zip"
    assert archive.is_file()
    with zipfile.ZipFile(archive) as handle:
        names = set(handle.namelist())
    root = "coder-relay-1.2.3-windows-x86_64"
    assert f"{root}/cdy.exe" in names
    assert f"{root}/INSTALL.txt" in names
    assert f"{root}/README.md" in names
    assert f"{root}/README.en.md" in names


def test_package_release_creates_unix_tarball(tmp_path: Path) -> None:
    binary = tmp_path / "cdy"
    binary.write_bytes(b"fake executable")
    output = tmp_path / "out"
    subprocess.run([
        sys.executable, "scripts/package_release.py", "--binary", str(binary),
        "--target", "macos-arm64", "--version", "1.2.3", "--output-dir", str(output),
    ], check=True)
    archive = output / "coder-relay-1.2.3-macos-arm64.tar.gz"
    assert archive.is_file()
    with tarfile.open(archive, "r:gz") as handle:
        members = {member.name: member for member in handle.getmembers()}
    root = "coder-relay-1.2.3-macos-arm64"
    assert f"{root}/cdy" in members
    assert members[f"{root}/cdy"].mode & 0o111
    assert f"{root}/INSTALL.txt" in members
    assert f"{root}/README.en.md" in members
