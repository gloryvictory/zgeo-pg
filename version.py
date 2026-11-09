"""Версия плагина ZGeo-PG из metadata.txt."""

from __future__ import annotations

from pathlib import Path

from .i18n import tr

METADATA_PATH = Path(__file__).with_name("metadata.txt")


def get_plugin_version() -> str:
    """Вернуть версию из metadata.txt или «неизвестна»."""

    try:
        content = METADATA_PATH.read_text(encoding="utf-8")
    except OSError:
        return tr("неизвестна")

    for line in content.splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() == "version":
            version = value.strip()
            if version:
                return version
    return tr("неизвестна")
