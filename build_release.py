"""Build the Windows executable and its matching GitHub update index."""

from __future__ import annotations

import ast
import argparse
import hashlib
import importlib.metadata
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "overlay_window.pyw"


def version_from_source(source: Path = SOURCE) -> str:
    for statement in ast.parse(source.read_text(encoding="utf-8")).body:
        if isinstance(statement, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "APP_VERSION"
            for target in statement.targets
        ):
            version = ast.literal_eval(statement.value)
            if not isinstance(version, str) or re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version) is None:
                raise ValueError("APP_VERSION 必须为 A.B.C")
            return version
    raise RuntimeError("overlay_window.pyw 缺少 APP_VERSION")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_release(directory: Path, *, source: Path = SOURCE, tag: str | None = None) -> dict:
    package = json.loads((directory / "update.json").read_text(encoding="utf-8"))
    executable = directory / "DesktopTools.exe"
    version = version_from_source(source)
    if package.get("version") != version:
        raise ValueError("源码 APP_VERSION 与更新索引版本不一致")
    if tag is not None and tag != "v" + version:
        raise ValueError("发布标签与源码版本不一致")
    if executable.stat().st_size != package.get("size"):
        raise ValueError("EXE 大小与更新索引不一致")
    if sha256(executable) != package.get("sha256"):
        raise ValueError("EXE SHA-256 与更新索引不一致")
    return package


def check_build_dependencies() -> None:
    if sys.platform != "win32":
        raise RuntimeError("请在 Windows 上打包 DesktopTools")
    for requirements in (ROOT / "requirements.txt", ROOT / "requirements-build.txt"):
        for line in requirements.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith(("#", "-")):
                continue
            name, expected = line.split("==", 1)
            try:
                actual = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                actual = None
            if actual != expected:
                raise RuntimeError(
                    f"构建需要 {name}=={expected}，当前为 {actual}；"
                    "请运行 python -m pip install -r requirements-build.txt"
                )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--tag", help="校验发布标签，例如 v2.2.1")
    args = parser.parse_args()
    directory = args.dist_dir.resolve()
    if args.verify_only:
        package = verify_release(directory, tag=args.tag)
        print(f"Release verified: v{package['version']}, {package['size']} bytes")
        return
    check_build_dependencies()
    version = version_from_source()
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            "--windowed",
            "--icon",
            str(ROOT / "assets" / "DesktopTools.ico"),
            "--add-data",
            str(ROOT / "assets") + ";assets",
            "--collect-submodules",
            "tkwry",
            "--name",
            "DesktopTools",
            "--distpath",
            str(directory),
            "--workpath",
            str(ROOT / "build" / "pyinstaller"),
            "--specpath",
            str(ROOT / "build"),
            str(SOURCE),
        ],
        check=True,
        cwd=ROOT,
    )
    package = {
        "version": version,
        "sha256": sha256(directory / "DesktopTools.exe"),
        "size": (directory / "DesktopTools.exe").stat().st_size,
    }
    (directory / "update.json").write_text(
        json.dumps(package, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    verify_release(directory, tag=args.tag)
    print(f"DesktopTools v{version}: {directory / 'DesktopTools.exe'} ({package['size']} bytes)")
    print(f"SHA-256: {package['sha256']}")


if __name__ == "__main__":
    main()
