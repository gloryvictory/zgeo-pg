"""Тексты ошибок SQL-запросов, общие для модулей плагина.

QtSql возвращает текст ошибки базы как есть: для PostgreSQL это строка вида
«ОШИБКА: нет доступа к таблице ...». Здесь ошибка превращается в понятный
пользователю текст, а отсутствие прав доступа переводится отдельно и
переводится заново при смене языка интерфейса (служебная пометка
`PERMISSION_MARK` хранится в тексте ошибки до момента показа).
"""

from __future__ import annotations

from .i18n import tr

# Служебная пометка «нет прав на таблицу»: текст показывается уже переведённым
# на текущий язык интерфейса, поэтому в строке ошибки хранится только пометка
# с именем таблицы.
PERMISSION_MARK = "permission-mark::"


def permission_error(table_note: str = "") -> str:
    """Текст ошибки прав доступа с пометкой для повторного перевода."""

    return PERMISSION_MARK + table_note


def readable_error(message: str) -> str:
    """Перевести служебную пометку ошибки в текст на текущем языке."""

    if message.startswith(PERMISSION_MARK):
        note = message[len(PERMISSION_MARK):]
        text = tr("Нет доступа к таблице")
        return text + (": " + note if note else "")
    return message


def query_error(query, table_note: str = "") -> str:
    """Понятный текст ошибки запроса: права доступа переводятся отдельно."""

    error = query.lastError()
    text = (error.databaseText() or error.text() or "").strip()
    code = str(error.nativeErrorCode() or "")
    lowered = text.casefold()
    if code == "42501" or "permission denied" in lowered or "нет доступа" in lowered:
        return permission_error(table_note)
    for prefix in ("ОШИБКА:", "ERROR:", "ОШИБКА :"):
        if text.upper().startswith(prefix):
            text = text[len(prefix):].strip()
            break
    return text or tr("Ошибка запроса")
