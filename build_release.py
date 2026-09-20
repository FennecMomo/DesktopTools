"""Build the Windows executable and its matching GitHub update index."""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "overlay_window.pyw"
EXECUTABLE = ROOT / "dist" / "DesktopTools.exe"
MANIFEST = ROOT / "dist" / "update.json"


def version_from_source() -> str:
    for statement in ast.parse(SOURCE.read_text(encoding="utf-8")).body:
        if isinstance(statement, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "APP_VERSION"
            for target in statement.targets
        ):
            return ast.literal_eval(statement.value)
    raise RuntimeError("overlay_window.pyw 缺少 APP_VERSION")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
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
            "--name",
            "DesktopTools",
            "--distpath",
            str(ROOT / "dist"),
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
        "sha256": sha256(EXECUTABLE),
        "size": EXECUTABLE.stat().st_size,
    }
    MANIFEST.write_text(
        json.dumps(package, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"DesktopTools v{version}: {EXECUTABLE} ({package['size']} bytes)")
    print(f"SHA-256: {package['sha256']}")


if __name__ == "__main__":
    main()
