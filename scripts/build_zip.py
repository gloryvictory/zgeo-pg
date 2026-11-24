"""Сборка ZIP-архива плагина ZGeo-PG (кроссплатформенная).

Тот же результат, что и у ``scripts/build_zip.ps1``, но без PowerShell: скрипт
используется в CI и на любой ОС. В архиве лежит одна корневая папка
``zgeo_pg`` — имя папки должно быть корректным идентификатором Python, иначе
QGIS не сможет импортировать плагин из ZIP. Служебные файлы разработки
(``img``, ``tests``, ``scripts``, ``dist``, кэши, инструкции для агентов) в
архив не попадают.

Запуск::

    python scripts/build_zip.py                  # dist/zgeo-pg-<version>.zip
    python scripts/build_zip.py --output-dir out # другой каталог
"""

from __future__ import annotations

import argparse
import configparser
import pathlib
import re
import shutil
import sys
import tempfile
import zipfile
from typing import Iterable, Optional, Set

# Имена, которые не попадают в архив: тесты, сборка, кэши и локальные файлы.
EXCLUDED_NAMES: Set[str] = {
    "__pycache__",
    "dist",
    "scripts",
    "tests",
    "img",
    ".git",
    ".github",
    ".gitignore",
    ".idea",
    ".vscode",
    ".empryo",
    ".pytest_cache",
    ".ruff_cache",
    "ruff.toml",
    "AGENTS.md",
    "agents.md",
}

PLUGIN_NAME = "zgeo-pg"
PACKAGE_NAME = "zgeo_pg"


def package_name(folder_name: str) -> str:
    """Имя корневой папки архива: корректный идентификатор Python."""

    name = re.sub(r"[^0-9A-Za-z_]", "_", folder_name)
    if name[:1].isdigit():
        name = "_" + name
    if not re.match(r"^[A-Za-z_][0-9A-Za-z_]*$", name):
        raise ValueError("package name is not a valid Python identifier: " + name)
    return name


def read_version(root: pathlib.Path) -> str:
    """Версия плагина из ``metadata.txt``."""

    metadata = root / "metadata.txt"
    if not metadata.exists():
        raise FileNotFoundError("metadata.txt not found: {}".format(metadata))
    config = configparser.ConfigParser()
    config.read(metadata, encoding="utf-8")
    version = config.get("general", "version", fallback="").strip()
    if not version:
        raise ValueError("version is not defined in metadata.txt")
    return version


def collect_files(root: pathlib.Path, excluded: Optional[Iterable[str]] = None) -> list:
    """Файлы плагина, которые попадут в архив (относительные posix-пути)."""

    skip = EXCLUDED_NAMES if excluded is None else set(excluded)
    collected = []
    for item in sorted(root.iterdir()):
        if item.name in skip:
            continue
        if item.is_dir():
            for path in sorted(item.rglob("*")):
                if path.is_dir():
                    continue
                if any(part in skip for part in path.relative_to(root).parts):
                    continue
                collected.append(path.relative_to(root).as_posix())
        else:
            collected.append(item.name)
    return collected


def build(
    root: Optional[pathlib.Path] = None,
    output_dir: Optional[pathlib.Path] = None,
    version: Optional[str] = None,
) -> pathlib.Path:
    """Собрать архив и вернуть путь к нему."""

    root = pathlib.Path(root) if root else pathlib.Path(__file__).resolve().parent.parent
    version = version or read_version(root)
    output_dir = pathlib.Path(output_dir) if output_dir else root / "dist"
    output_dir.mkdir(parents=True, exist_ok=True)

    archive_name = "{}-{}.zip".format(PLUGIN_NAME, version)
    zip_path = output_dir / archive_name
    prefix = package_name(root.name if root.name else PACKAGE_NAME)

    staging = pathlib.Path(tempfile.mkdtemp(prefix="zgeo-pg-build-"))
    staging_plugin = staging / prefix
    staging_plugin.mkdir(parents=True, exist_ok=True)
    try:
        for relative in collect_files(root):
            target = staging_plugin / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / relative, target)

        if zip_path.exists():
            zip_path.unlink()

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(staging_plugin.rglob("*")):
                if path.is_dir():
                    continue
                relative = path.relative_to(staging_plugin).as_posix()
                archive.write(path, "{}/{}".format(prefix, relative))
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    # В каталоге сборки остаётся только последний вариант.
    for stale in output_dir.glob("{}-*.zip".format(PLUGIN_NAME)):
        if stale != zip_path:
            stale.unlink()
            print("Removed stale build: {}".format(stale.name))

    print("Created: {} (root folder: {})".format(zip_path, prefix))
    return zip_path


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Build the ZGeo-PG plugin zip.")
    parser.add_argument("--output-dir", default=None, help="каталог для архива")
    parser.add_argument("--version", default=None, help="версия вместо metadata.txt")
    args = parser.parse_args(argv)

    try:
        path = build(output_dir=args.output_dir, version=args.version)
    except (FileNotFoundError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    print(
        "Install in QGIS: Plugins > Manage and Install Plugins > Install from ZIP"
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
