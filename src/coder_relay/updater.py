from __future__ import annotations

import hashlib
import os
import platform
import re
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

import httpx

from . import __version__
from .errors import RelayError

RELEASE_API_URL = "https://api.github.com/repos/Lortzing/CoderRelay/releases/latest"
RELEASES_URL = "https://github.com/Lortzing/CoderRelay/releases/latest"
CHECKSUM_ASSET = "SHA256SUMS.txt"
HTTP_TIMEOUT_SECONDS = 60.0


@dataclass(frozen=True, slots=True)
class ReleaseAsset:
    name: str
    download_url: str
    size: int | None = None
    digest: str | None = None


@dataclass(frozen=True, slots=True)
class ReleaseInfo:
    tag: str
    version: str
    assets: dict[str, ReleaseAsset]


@dataclass(frozen=True, slots=True)
class UpdateTarget:
    system: str
    architecture: str
    installation: str
    asset_name: str


def version_key(value: str) -> tuple[int, int, int]:
    """Return a comparable semantic-version core for stable CoderRelay releases."""
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?", value.strip())
    if not match:
        raise RelayError(f"Unsupported release version: {value}")
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def _github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"CoderRelay/{__version__}",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_latest_release(client: httpx.Client | None = None) -> ReleaseInfo:
    """Read the latest published stable release and its downloadable assets."""
    owns_client = client is None
    if client is None:
        client = httpx.Client(
            headers=_github_headers(),
            timeout=HTTP_TIMEOUT_SECONDS,
            follow_redirects=True,
        )
    try:
        response = client.get(RELEASE_API_URL)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise RelayError(f"Could not query the latest CoderRelay release: {exc}") from exc
    finally:
        if owns_client:
            client.close()

    if not isinstance(payload, dict):
        raise RelayError("GitHub returned an invalid release response.")
    tag = payload.get("tag_name")
    raw_assets = payload.get("assets")
    if not isinstance(tag, str) or not isinstance(raw_assets, list):
        raise RelayError("GitHub release metadata is missing the tag or assets list.")

    version = tag.removeprefix("v")
    version_key(version)
    assets: dict[str, ReleaseAsset] = {}
    for item in raw_assets:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        download_url = item.get("browser_download_url")
        if not isinstance(name, str) or not isinstance(download_url, str):
            continue
        size = item.get("size") if isinstance(item.get("size"), int) else None
        digest = item.get("digest") if isinstance(item.get("digest"), str) else None
        assets[name] = ReleaseAsset(name, download_url, size=size, digest=digest)
    return ReleaseInfo(tag=tag, version=version, assets=assets)


def normalized_system() -> str:
    if os.name == "nt":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    if sys.platform.startswith("linux"):
        return "linux"
    raise RelayError(f"Automatic updates are not supported on {sys.platform}.")


def normalized_architecture(system: str | None = None) -> str:
    system = system or normalized_system()
    machine = platform.machine().lower()
    if system == "windows" and struct.calcsize("P") == 4:
        return "x86"
    if machine in {"amd64", "x86_64"}:
        return "x86_64"
    if machine in {"i386", "i486", "i586", "i686", "x86"}:
        return "x86"
    if machine in {"arm64", "aarch64"}:
        return "arm64" if system in {"windows", "macos"} else "aarch64"
    raise RelayError(f"Unsupported {system} architecture: {machine or 'unknown'}")


def _run_quiet(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=False)


def _windows_has_setup_uninstaller(executable: Path) -> bool:
    return any(executable.parent.glob("unins*.exe"))


def _linux_package_kind() -> str | None:
    dpkg_query = shutil.which("dpkg-query")
    if dpkg_query:
        result = _run_quiet([dpkg_query, "-W", "-f=${db:Status-Status}", "coder-relay"])
        if result.returncode == 0 and result.stdout.strip() == "installed":
            return "deb"
    rpm = shutil.which("rpm")
    if rpm and _run_quiet([rpm, "-q", "coder-relay"]).returncode == 0:
        return "rpm"
    return None


def select_update_target(
    version: str,
    *,
    executable: Path | None = None,
    system: str | None = None,
    architecture: str | None = None,
    linux_package_kind: str | None = None,
    windows_setup: bool | None = None,
) -> UpdateTarget:
    """Resolve the exact release asset for this installation."""
    system = system or normalized_system()
    architecture = architecture or normalized_architecture(system)
    executable = executable or Path(sys.executable).resolve()

    if system == "windows":
        if architecture not in {"x86", "x86_64", "arm64"}:
            raise RelayError(f"Unsupported Windows architecture: {architecture}")
        setup = _windows_has_setup_uninstaller(executable) if windows_setup is None else windows_setup
        installation = "windows-setup" if setup else "windows-portable"
        kind = "Setup" if setup else "Portable"
        extension = "exe" if setup else "zip"
        name = f"CoderRelay-{kind}-{version}-windows-{architecture}.{extension}"
        return UpdateTarget(system, architecture, installation, name)

    if system == "macos":
        if architecture not in {"x86_64", "arm64"}:
            raise RelayError(f"Unsupported macOS architecture: {architecture}")
        name = f"CoderRelay-{version}-macOS-{architecture}.dmg"
        return UpdateTarget(system, architecture, "macos-pkg", name)

    if system == "linux":
        if architecture not in {"x86_64", "aarch64"}:
            raise RelayError(f"Unsupported Linux architecture: {architecture}")
        package_kind = linux_package_kind if linux_package_kind is not None else _linux_package_kind()
        if package_kind == "deb":
            deb_arch = "amd64" if architecture == "x86_64" else "arm64"
            return UpdateTarget(system, architecture, "linux-deb", f"coder-relay_{version}_{deb_arch}.deb")
        if package_kind == "rpm":
            rpm_arch = "x86_64" if architecture == "x86_64" else "aarch64"
            return UpdateTarget(system, architecture, "linux-rpm", f"coder-relay-{version}-1.{rpm_arch}.rpm")
        return UpdateTarget(
            system,
            architecture,
            "linux-tar",
            f"coder-relay-{version}-linux-{architecture}.tar.gz",
        )

    raise RelayError(f"Automatic updates are not supported on {system}.")


def _download_asset(client: httpx.Client, asset: ReleaseAsset, destination: Path) -> None:
    try:
        with client.stream("GET", asset.download_url) as response:
            response.raise_for_status()
            with destination.open("wb") as handle:
                for chunk in response.iter_bytes():
                    handle.write(chunk)
    except (httpx.HTTPError, OSError) as exc:
        raise RelayError(f"Could not download {asset.name}: {exc}") from exc
    if asset.size is not None and destination.stat().st_size != asset.size:
        raise RelayError(
            f"Downloaded size mismatch for {asset.name}: expected {asset.size}, "
            f"got {destination.stat().st_size}."
        )


def parse_checksums(text: str) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?(.+)", line)
        if match:
            checksums[match.group(2)] = match.group(1).lower()
    return checksums


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_github_digest(path: Path, asset: ReleaseAsset) -> None:
    if not asset.digest:
        return
    algorithm, separator, value = asset.digest.partition(":")
    if not separator or algorithm.lower() != "sha256":
        return
    if sha256_file(path) != value.lower():
        raise RelayError(f"GitHub asset digest verification failed for {asset.name}.")


def verify_asset(path: Path, asset: ReleaseAsset, checksums: dict[str, str]) -> None:
    expected = checksums.get(asset.name)
    if not expected:
        raise RelayError(f"{CHECKSUM_ASSET} does not contain {asset.name}.")
    actual = sha256_file(path)
    if actual != expected:
        raise RelayError(f"SHA-256 verification failed for {asset.name}.")
    verify_github_digest(path, asset)


def _require_asset(release: ReleaseInfo, name: str) -> ReleaseAsset:
    asset = release.assets.get(name)
    if asset is None:
        raise RelayError(f"Release {release.tag} does not contain the required asset: {name}")
    return asset


def _download_verified_update(release: ReleaseInfo, target: UpdateTarget) -> tuple[Path, Path]:
    asset = _require_asset(release, target.asset_name)
    checksum_asset = _require_asset(release, CHECKSUM_ASSET)
    work_dir = Path(tempfile.mkdtemp(prefix="coder-relay-update-"))
    asset_path = work_dir / asset.name
    checksum_path = work_dir / CHECKSUM_ASSET
    client = httpx.Client(
        headers=_github_headers(),
        timeout=HTTP_TIMEOUT_SECONDS,
        follow_redirects=True,
    )
    try:
        _download_asset(client, checksum_asset, checksum_path)
        verify_github_digest(checksum_path, checksum_asset)
        _download_asset(client, asset, asset_path)
        checksums = parse_checksums(checksum_path.read_text(encoding="utf-8"))
        verify_asset(asset_path, asset, checksums)
    except Exception:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise
    finally:
        client.close()
    return work_dir, asset_path


def _quote_cmd(value: Path | str) -> str:
    return '"' + str(value).replace('"', '""') + '"'


def _launch_windows_helper(script: Path) -> None:
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(
        subprocess, "DETACHED_PROCESS", 0
    )
    try:
        subprocess.Popen(
            ["cmd.exe", "/d", "/c", str(script)],
            close_fds=True,
            creationflags=creationflags,
        )
    except OSError as exc:
        raise RelayError(f"Could not start the Windows update helper: {exc}") from exc


def _schedule_windows_setup(work_dir: Path, installer: Path) -> str:
    helper = Path(tempfile.gettempdir()) / f"coder-relay-update-{os.getpid()}.cmd"
    helper.write_text(
        "@echo off\r\n"
        "setlocal\r\n"
        ":wait_for_cdy\r\n"
        f'tasklist /FI "PID eq {os.getpid()}" /NH | find "{os.getpid()}" >nul\r\n'
        "if not errorlevel 1 (\r\n"
        "  timeout /t 1 /nobreak >nul\r\n"
        "  goto wait_for_cdy\r\n"
        ")\r\n"
        f'start /wait "" {_quote_cmd(installer)} /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-\r\n'
        "set update_code=%errorlevel%\r\n"
        f'rmdir /s /q {_quote_cmd(work_dir)}\r\n'
        'del /f /q "%~f0" >nul 2>&1\r\n'
        "exit /b %update_code%\r\n",
        encoding="utf-8",
    )
    _launch_windows_helper(helper)
    return "The verified Windows installer will run after CoderRelay exits."


def _portable_executable_from_zip(archive: Path, destination: Path) -> None:
    try:
        with zipfile.ZipFile(archive) as handle:
            candidates = [
                name for name in handle.namelist()
                if name.replace("\\", "/").rstrip("/").endswith("/cdy.exe") or name == "cdy.exe"
            ]
            if len(candidates) != 1:
                raise RelayError("The Windows portable archive does not contain exactly one cdy.exe.")
            with handle.open(candidates[0]) as source, destination.open("wb") as target:
                shutil.copyfileobj(source, target)
    except (OSError, zipfile.BadZipFile) as exc:
        raise RelayError(f"Could not unpack the Windows portable update: {exc}") from exc


def _schedule_windows_portable(work_dir: Path, archive: Path, executable: Path) -> str:
    if not os.access(executable.parent, os.W_OK):
        raise RelayError(
            f"The portable executable directory is not writable: {executable.parent}. "
            "Run CoderRelay from an administrator terminal or reinstall with Setup."
        )
    replacement = work_dir / "cdy-new.exe"
    _portable_executable_from_zip(archive, replacement)
    helper = Path(tempfile.gettempdir()) / f"coder-relay-update-{os.getpid()}.cmd"
    helper.write_text(
        "@echo off\r\n"
        "setlocal\r\n"
        ":wait_for_cdy\r\n"
        f'tasklist /FI "PID eq {os.getpid()}" /NH | find "{os.getpid()}" >nul\r\n'
        "if not errorlevel 1 (\r\n"
        "  timeout /t 1 /nobreak >nul\r\n"
        "  goto wait_for_cdy\r\n"
        ")\r\n"
        f'move /y {_quote_cmd(replacement)} {_quote_cmd(executable)} >nul\r\n'
        "set update_code=%errorlevel%\r\n"
        f'rmdir /s /q {_quote_cmd(work_dir)}\r\n'
        'del /f /q "%~f0" >nul 2>&1\r\n'
        "exit /b %update_code%\r\n",
        encoding="utf-8",
    )
    _launch_windows_helper(helper)
    return "The verified portable executable will replace cdy.exe after CoderRelay exits."


def _elevated(command: list[str]) -> list[str]:
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        return command
    sudo = shutil.which("sudo")
    if not sudo:
        raise RelayError("Administrator privileges are required, but sudo was not found.")
    return [sudo, *command]


def _run_visible(command: list[str], *, description: str) -> None:
    try:
        result = subprocess.run(command, check=False)
    except OSError as exc:
        raise RelayError(f"Could not start {description}: {exc}") from exc
    if result.returncode != 0:
        raise RelayError(f"{description} failed with exit code {result.returncode}.")


def _install_macos_dmg(work_dir: Path, dmg: Path) -> str:
    hdiutil = shutil.which("hdiutil")
    installer = shutil.which("installer") or "/usr/sbin/installer"
    if not hdiutil:
        raise RelayError("hdiutil was not found on this macOS system.")
    mount_point = work_dir / "mounted"
    mount_point.mkdir()
    try:
        attach = _run_quiet([
            hdiutil,
            "attach",
            "-nobrowse",
            "-readonly",
            "-mountpoint",
            str(mount_point),
            str(dmg),
        ])
        if attach.returncode != 0:
            raise RelayError((attach.stderr or attach.stdout).strip() or "Could not mount the update DMG.")
        packages = list(mount_point.glob("*.pkg"))
        if len(packages) != 1:
            raise RelayError("The update DMG does not contain exactly one PKG installer.")
        _run_visible(
            _elevated([installer, "-pkg", str(packages[0]), "-target", "/"]),
            description="macOS package installation",
        )
    finally:
        if mount_point.exists():
            subprocess.run([hdiutil, "detach", str(mount_point), "-force"], check=False, capture_output=True)
        shutil.rmtree(work_dir, ignore_errors=True)
    return "CoderRelay was updated with the verified macOS package."


def _install_linux_package(work_dir: Path, package: Path, kind: str) -> str:
    try:
        if kind == "linux-deb":
            apt_get = shutil.which("apt-get")
            if apt_get:
                command = _elevated([apt_get, "install", "-y", str(package)])
            else:
                dpkg = shutil.which("dpkg")
                if not dpkg:
                    raise RelayError("Neither apt-get nor dpkg was found.")
                command = _elevated([dpkg, "-i", str(package)])
        else:
            dnf = shutil.which("dnf")
            yum = shutil.which("yum")
            rpm = shutil.which("rpm")
            if dnf:
                command = _elevated([dnf, "install", "-y", str(package)])
            elif yum:
                command = _elevated([yum, "install", "-y", str(package)])
            elif rpm:
                command = _elevated([rpm, "-U", str(package)])
            else:
                raise RelayError("No RPM package manager was found.")
        _run_visible(command, description=f"{kind.removeprefix('linux-').upper()} package installation")
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
    return f"CoderRelay was updated with the verified {kind.removeprefix('linux-').upper()} package."


def _extract_linux_binary(archive: Path, destination: Path) -> None:
    try:
        with tarfile.open(archive, "r:gz") as handle:
            candidates = [
                member for member in handle.getmembers()
                if member.isfile() and (member.name.rstrip("/").endswith("/cdy") or member.name == "cdy")
            ]
            if len(candidates) != 1:
                raise RelayError("The Linux archive does not contain exactly one cdy executable.")
            source = handle.extractfile(candidates[0])
            if source is None:
                raise RelayError("Could not read cdy from the Linux archive.")
            with source, destination.open("wb") as target:
                shutil.copyfileobj(source, target)
            destination.chmod(0o755)
    except (OSError, tarfile.TarError) as exc:
        raise RelayError(f"Could not unpack the Linux update: {exc}") from exc


def _replace_linux_tar(work_dir: Path, archive: Path, executable: Path) -> str:
    replacement = work_dir / "cdy-new"
    _extract_linux_binary(archive, replacement)
    try:
        if os.access(executable.parent, os.W_OK):
            staged = executable.with_name(f".{executable.name}.coder-relay-update")
            shutil.copy2(replacement, staged)
            staged.chmod(0o755)
            os.replace(staged, executable)
        else:
            staged = executable.with_name(f".{executable.name}.coder-relay-update")
            _run_visible(
                _elevated(["install", "-m", "0755", str(replacement), str(staged)]),
                description="staging the Linux executable",
            )
            _run_visible(
                _elevated(["mv", "-f", str(staged), str(executable)]),
                description="replacing the Linux executable",
            )
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
    return f"CoderRelay was updated in place at {executable}."


def install_frozen_update(
    release: ReleaseInfo,
    *,
    executable: Path | None = None,
    force: bool = False,
) -> str:
    """Download, verify, and apply the latest release to a frozen installation."""
    if version_key(release.version) <= version_key(__version__) and not force:
        return f"CoderRelay {__version__} is already up to date."
    executable = (executable or Path(sys.executable)).resolve()
    target = select_update_target(release.version, executable=executable)
    print(f"Downloading {target.asset_name} from {release.tag}...", flush=True)
    work_dir, asset_path = _download_verified_update(release, target)
    print("SHA-256 verification passed.", flush=True)

    if target.installation == "windows-setup":
        return _schedule_windows_setup(work_dir, asset_path)
    if target.installation == "windows-portable":
        return _schedule_windows_portable(work_dir, asset_path, executable)
    if target.installation == "macos-pkg":
        return _install_macos_dmg(work_dir, asset_path)
    if target.installation in {"linux-deb", "linux-rpm"}:
        return _install_linux_package(work_dir, asset_path, target.installation)
    if target.installation == "linux-tar":
        return _replace_linux_tar(work_dir, asset_path, executable)

    shutil.rmtree(work_dir, ignore_errors=True)
    raise RelayError(f"Unsupported installation type: {target.installation}")


def latest_tagged_source(release: ReleaseInfo) -> str:
    return f"git+https://github.com/Lortzing/CoderRelay.git@{release.tag}"
