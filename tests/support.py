"""Общая загрузка пакета плагина для тестов.

Каталог плагина называется ``zgeo-pg``, а имя пакета в QGIS — ``zgeo_pg``
(дефис недопустим в идентификаторе Python). Поэтому тесты регистрируют пакет
вручную, и дальше работает обычный ``from zgeo_pg import ...``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PACKAGE = "zgeo_pg"
ROOT = Path(__file__).resolve().parent.parent


def load_package() -> "object":
    """Зарегистрировать пакет плагина в ``sys.modules`` и вернуть его."""

    if PACKAGE in sys.modules:
        return sys.modules[PACKAGE]

    spec = importlib.util.spec_from_file_location(
        PACKAGE,
        ROOT / "__init__.py",
        submodule_search_locations=[str(ROOT)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load package from {}".format(ROOT))
    module = importlib.util.module_from_spec(spec)
    sys.modules[PACKAGE] = module
    spec.loader.exec_module(module)
    return module


def plugin_files() -> "list[Path]":
    """Все модули плагина в корне каталога."""

    return sorted(ROOT.glob("*.py"))


load_package()
