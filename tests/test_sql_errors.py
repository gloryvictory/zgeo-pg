"""Тексты ошибок SQL: права доступа и служебные префиксы."""

from __future__ import annotations

import unittest

from .support import load_package

load_package()

from zgeo_pg.i18n import set_language  # noqa: E402
from zgeo_pg.sql_errors import (  # noqa: E402
    PERMISSION_MARK,
    permission_error,
    query_error,
    readable_error,
)


class FakeError:
    """Подмена ``QSqlError``: только то, что читает ``query_error``."""

    def __init__(self, text: str = "", code: str = "", database_text: str = "") -> None:
        self._text = text
        self._code = code
        self._database_text = database_text

    def databaseText(self) -> str:
        return self._database_text

    def text(self) -> str:
        return self._text

    def nativeErrorCode(self) -> str:
        return self._code


class FakeQuery:
    """Подмена ``QSqlQuery`` с заданной ошибкой."""

    def __init__(self, error: FakeError) -> None:
        self._error = error

    def lastError(self) -> FakeError:
        return self._error


class PermissionMarkTest(unittest.TestCase):
    """Пометка прав доступа переводится в момент показа."""

    def tearDown(self) -> None:
        set_language("ru")

    def test_mark_contains_table_name(self) -> None:
        marked = permission_error("public.roads")
        self.assertTrue(marked.startswith(PERMISSION_MARK))
        self.assertIn("public.roads", marked)

    def test_readable_text_in_russian(self) -> None:
        set_language("ru")
        self.assertEqual(
            readable_error(permission_error("public.roads")),
            "Нет доступа к таблице: public.roads",
        )

    def test_readable_text_in_english(self) -> None:
        set_language("en")
        try:
            self.assertEqual(
                readable_error(permission_error("public.roads")),
                "No access to the table: public.roads",
            )
        finally:
            set_language("ru")

    def test_mark_without_table(self) -> None:
        self.assertEqual(readable_error(permission_error()), "Нет доступа к таблице")

    def test_plain_message_passes_through(self) -> None:
        self.assertEqual(readable_error("relation does not exist"), "relation does not exist")


class QueryErrorTest(unittest.TestCase):
    """Ошибки запросов превращаются в понятный текст."""

    def test_permission_denied_by_code(self) -> None:
        query = FakeQuery(FakeError(text="permission denied for table roads", code="42501"))
        self.assertTrue(query_error(query, "public.roads").startswith(PERMISSION_MARK))

    def test_permission_denied_by_text(self) -> None:
        query = FakeQuery(FakeError(text="ERROR: permission denied for relation roads"))
        self.assertTrue(query_error(query, "public.roads").startswith(PERMISSION_MARK))

    def test_permission_denied_in_russian_locale(self) -> None:
        """Клиент PostgreSQL может отдать ошибку по-русски."""

        query = FakeQuery(FakeError(text="ОШИБКА: нет доступа к таблице roads"))
        self.assertTrue(query_error(query, "public.roads").startswith(PERMISSION_MARK))

    def test_error_prefix_is_stripped(self) -> None:
        query = FakeQuery(FakeError(database_text='ОШИБКА:  relation "roads" does not exist'))
        self.assertEqual(
            query_error(query, "public.roads"),
            'relation "roads" does not exist',
        )

    def test_english_error_prefix_is_stripped(self) -> None:
        query = FakeQuery(FakeError(text="ERROR: syntax error at end of input"))
        self.assertEqual(query_error(query, ""), "syntax error at end of input")

    def test_database_text_wins_over_text(self) -> None:
        query = FakeQuery(
            FakeError(text="generic", database_text="ОШИБКА: detailed message")
        )
        self.assertEqual(query_error(query), "detailed message")

    def test_empty_error_falls_back_to_translated_text(self) -> None:
        query = FakeQuery(FakeError())
        self.assertEqual(query_error(query), "Ошибка запроса")

    def test_empty_error_uses_current_language(self) -> None:
        set_language("en")
        try:
            self.assertEqual(query_error(FakeQuery(FakeError())), "Query failed")
        finally:
            set_language("ru")


if __name__ == "__main__":
    unittest.main()
