"""Verified update downloads and staged installation, independent of Tk."""
from __future__ import annotations
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from .state import _default_settings_path

UPDATE_MANIFEST_URL = (
    "https://raw.githubusercontent.com/FennecMomo/DesktopTools/"
    "main/dist/update.json"
)
UPDATE_PACKAGE_URL = (
    "https://raw.githubusercontent.com/FennecMomo/DesktopTools/"
    "main/dist/DesktopTools.exe"
)
MAX_UPDATE_BYTES = 100 * 1024 * 1024

class UpdateError(Exception):
    pass


def _version_numbers(value: str) -> tuple[int, int, int]:
    if not isinstance(value, str) or re.fullmatch(r"\d+\.\d+\.\d+", value) is None:
        raise UpdateError("版本号格式无效")
    return tuple(int(part) for part in value.split("."))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class UpdateClient:
    """Read the public GitHub package index and verify a staged executable."""

    def __init__(
        self,
        directory: Path | None = None,
        *,
        manifest_url: str = UPDATE_MANIFEST_URL,
        package_url: str = UPDATE_PACKAGE_URL,
        opener: Callable | None = None,
        app_version: str = "",
    ) -> None:
        self.directory = (
            Path(directory)
            if directory is not None
            else _default_settings_path().parent / "updates"
        )
        self.manifest_url = manifest_url
        self.app_version = app_version
        self.package_url = package_url
        self._open = opener or urllib.request.urlopen

    def _request(self, url: str) -> urllib.request.Request:
        return urllib.request.Request(
            url,
            headers={
                "User-Agent": f"DesktopTools/{self.app_version}",
                "Cache-Control": "no-cache",
            },
        )

    def latest(self) -> dict[str, str | int] | None:
        try:
            with self._open(self._request(self.manifest_url), timeout=15) as response:
                contents = response.read(64 * 1024 + 1)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            raise UpdateError(f"GitHub 返回 HTTP {error.code}") from error
        except (OSError, urllib.error.URLError) as error:
            raise UpdateError(f"无法连接 GitHub：{error}") from error
        if len(contents) > 64 * 1024:
            raise UpdateError("版本索引过大")
        try:
            raw = json.loads(contents)
        except (ValueError, UnicodeError) as error:
            raise UpdateError("版本索引不是有效 JSON") from error
        if not isinstance(raw, dict):
            raise UpdateError("版本索引格式无效")
        version = raw.get("version")
        digest = raw.get("sha256")
        size = raw.get("size")
        _version_numbers(version)
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-fA-F]{64}", digest) is None:
            raise UpdateError("版本索引缺少有效的 SHA-256")
        if type(size) is not int or not 0 < size <= MAX_UPDATE_BYTES:
            raise UpdateError("版本索引包含无效的文件大小")
        return {"version": version, "sha256": digest.lower(), "size": size}

    def download(self, latest: dict[str, str | int]) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        destination = self.directory / (
            f"DesktopTools-{latest['version']}-{latest['sha256'][:12]}.exe"
        )
        if (
            destination.is_file()
            and destination.stat().st_size == latest["size"]
            and _sha256_file(destination) == latest["sha256"]
        ):
            return destination

        descriptor, temporary_name = tempfile.mkstemp(
            prefix="download-",
            suffix=".tmp",
            dir=self.directory,
        )
        temporary_path = Path(temporary_name)
        try:
            digest = hashlib.sha256()
            downloaded = 0
            try:
                with os.fdopen(descriptor, "wb") as file:
                    with self._open(
                        self._request(self.package_url), timeout=30
                    ) as response:
                        while True:
                            chunk = response.read(1024 * 1024)
                            if not chunk:
                                break
                            if downloaded == 0 and not chunk.startswith(b"MZ"):
                                raise UpdateError("下载内容不是 Windows EXE")
                            downloaded += len(chunk)
                            if downloaded > latest["size"]:
                                raise UpdateError("下载文件大小与版本索引不符")
                            digest.update(chunk)
                            file.write(chunk)
                    file.flush()
                    os.fsync(file.fileno())
            except (OSError, urllib.error.URLError) as error:
                raise UpdateError(f"下载更新失败：{error}") from error
            if downloaded != latest["size"] or digest.hexdigest() != latest["sha256"]:
                raise UpdateError("下载文件校验失败，未安装更新")
            os.replace(temporary_path, destination)
            return destination
        finally:
            temporary_path.unlink(missing_ok=True)


def _apply_staged_update(arguments: list[str]) -> int:
    logger = logging.getLogger("desktoptools")
    try:
        result = _install_staged_update(arguments)
    except Exception:
        logger.exception("Update installation failed unexpectedly")
        result = 4
    if result:
        logger.error("Update installation failed, exit code %s", result)
    else:
        logger.info("Update installation completed")
    return result


def _install_staged_update(arguments: list[str]) -> int:
    """Run from the verified new EXE after the old process has exited."""
    if (
        len(arguments) != 3
        or arguments[2] not in ("restart", "no-restart")
        or not getattr(sys, "frozen", False)
    ):
        return 2
    target = Path(arguments[0]).resolve()
    expected_sha256 = arguments[1].lower()
    restart = arguments[2] == "restart"
    staged = Path(sys.executable).resolve()
    try:
        staged_sha256 = _sha256_file(staged)
    except OSError:
        logging.getLogger("desktoptools").exception("Cannot read staged executable")
        return 3
    if (
        target == staged
        or target.suffix.lower() != ".exe"
        or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None
        or staged_sha256 != expected_sha256
    ):
        return 3

    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".DesktopTools-update-",
            suffix=".tmp",
            dir=target.parent,
        )
    except OSError:
        logging.getLogger("desktoptools").exception("Cannot prepare update in target directory")
        return 4
    temporary_path = Path(temporary_name)
    try:
        with staged.open("rb") as source, os.fdopen(descriptor, "wb") as destination:
            shutil.copyfileobj(source, destination, length=1024 * 1024)
            destination.flush()
            os.fsync(destination.fileno())
        deadline = time.monotonic() + 120
        while True:
            try:
                os.replace(temporary_path, target)
                break
            except OSError as error:
                if getattr(error, "winerror", None) not in (5, 32, 33):
                    raise
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.25)
        if restart:
            subprocess.Popen([str(target)], cwd=target.parent)
        return 0
    except OSError:
        logging.getLogger("desktoptools").exception("Cannot replace or restart updated executable")
        return 4
    finally:
        temporary_path.unlink(missing_ok=True)
