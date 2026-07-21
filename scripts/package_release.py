from __future__ import annotations

import argparse
import shutil
import stat
import tarfile
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_TARGETS = {
    "windows-x86_64": ".zip",
    "macos-x86_64": ".tar.gz",
    "macos-arm64": ".tar.gz",
    "linux-x86_64": ".tar.gz",
}


def normalize_version(value: str) -> str:
    version = value.strip()
    if version.startswith("v"):
        version = version[1:]
    if not version:
        raise ValueError("Version cannot be empty.")
    return version


def installation_text(target: str) -> str:
    if target.startswith("windows-"):
        return """CodexRelay portable package\n\n1. Move cxr.exe to a permanent directory.\n2. Add that directory to PATH.\n3. Open a new terminal and run: cxr status\n\nThe executable is unsigned. Windows SmartScreen may show a warning.\n"""
    return """CodexRelay portable package\n\n1. Make the executable runnable: chmod +x cxr\n2. Move it to a directory on PATH, for example: mkdir -p ~/.local/bin && mv cxr ~/.local/bin/cxr\n3. Open a new terminal and run: cxr status\n"""


def _tar_filter(member: tarfile.TarInfo) -> tarfile.TarInfo:
    if member.isfile() and member.name.endswith("/cxr"):
        member.mode |= 0o111
    return member


def build_archive(*, binary: Path, target: str, version: str, output_dir: Path) -> Path:
    if target not in SUPPORTED_TARGETS:
        supported = ", ".join(sorted(SUPPORTED_TARGETS))
        raise ValueError(f"Unsupported target {target!r}. Expected one of: {supported}")
    if not binary.is_file():
        raise FileNotFoundError(f"Binary does not exist: {binary}")

    version = normalize_version(version)
    output_dir.mkdir(parents=True, exist_ok=True)
    package_name = f"codex-relay-{version}-{target}"

    with tempfile.TemporaryDirectory(prefix="codex-relay-release-") as temporary:
        stage = Path(temporary) / package_name
        stage.mkdir()
        executable_name = "cxr.exe" if target.startswith("windows-") else "cxr"
        executable = stage / executable_name
        shutil.copy2(binary, executable)
        if not target.startswith("windows-"):
            executable.chmod(executable.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        for name in ("README.md", "README.en.md", "LICENSE"):
            source = ROOT / name
            if source.is_file():
                shutil.copy2(source, stage / name)
        (stage / "INSTALL.txt").write_text(installation_text(target), encoding="utf-8")

        if target.startswith("windows-"):
            archive = output_dir / f"{package_name}.zip"
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
                for path in sorted(stage.rglob("*")):
                    if path.is_file():
                        handle.write(path, Path(package_name) / path.relative_to(stage))
        else:
            archive = output_dir / f"{package_name}.tar.gz"
            with tarfile.open(archive, "w:gz") as handle:
                handle.add(stage, arcname=package_name, filter=_tar_filter)

    return archive


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a CodexRelay standalone release archive.")
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--target", choices=sorted(SUPPORTED_TARGETS), required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("release-assets"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    archive = build_archive(
        binary=args.binary,
        target=args.target,
        version=args.version,
        output_dir=args.output_dir,
    )
    print(archive)


if __name__ == "__main__":
    main()
