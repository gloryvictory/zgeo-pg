"""Открытие файлов и папок в системном проводнике.

Внешние команды не запускаются: для показа папки достаточно средства рабочего
стола Qt, поэтому плагин не зависит от того, какие программы есть в системе.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

try:
    from qgis.PyQt.QtGui import QDesktopServices
except ImportError:  # Qt 5 / старые сборки QGIS
    from qgis.PyQt.QtWidgets import QDesktopServices
from qgis.PyQt.QtCore import QUrl


def reveal_files(paths: Iterable[Path]) -> List[str]:
    """Открыть папку с файлами в системном проводнике; вернуть список ошибок.

    Используется штатное средство рабочего стола QGIS, поэтому внешние
    процессы не запускаются и команда не зависит от того, что установлено в
    системе.
    """

    errors: List[str] = []
    opened: List[Path] = []
    for path in paths:
        path = Path(path)
        if not path.exists():
            errors.append(str(path))
            continue
        folder = path if path.is_dir() else path.parent
        if folder in opened:
            continue
        opened.append(folder)
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder))):
            errors.append(str(folder))
    return errors