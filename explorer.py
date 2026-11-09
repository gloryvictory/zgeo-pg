"""Открытие файлов в проводнике Windows."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Iterable, List


def reveal_files(paths: Iterable[Path]) -> List[str]:
    """Показать файлы в проводнике; вернуть список ошибок."""
    errors: List[str] = []
    for path in paths:
        path = Path(path)
        if not path.exists():
            errors.append(str(path))
            continue
        try:
            if os.name == "nt":
                subprocess.Popen(["explorer", "/select,", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except OSError as error:
            errors.append(str(error))
    return errors