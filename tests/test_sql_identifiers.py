"""Экранирование идентификаторов: единственный путь имени в текст запроса."""

from __future__ import annotations

import unittest

from .support import load_package

load_package()

from zgeo_pg.i18n import set_language  # noqa: E402
from zgeo_pg.sql_identifiers import quote_ident, render_sql  # noqa: E402


class QuoteIdentTest(unittest.TestCase):
    """Кавычки и очистка имени объекта."""

    def test_plain_name_is_quoted(self) -> None:
        self.assertEqual(quote_ident("roads"), '"roads"')

    def test_schema_qualified_parts_are_quoted_separately(self) -> None:
        self.assertEqual(
            quote_ident("public") + "." + quote_ident("roads"),
            '"public"."roads"',
        )

    def test_embedded_quotes_are_doubled(self) -> None:
        self.assertEqual(quote_ident('we"ird'), '"we""ird"')

    def test_attempted_escape_stays_inside_identifier(self) -> None:
        injected = quote_ident('roads"; DROP TABLE users; --')
        self.assertTrue(injected.startswith('"'))
        self.assertTrue(injected.endswith('"'))
        self.assertEqual(injected.count('"'), 4)
        self.assertEqual(
            injected,
            '"roads""; DROP TABLE users; --"',
        )

    def test_control_characters_are_dropped(self) -> None:
        self.assertEqual(quote_ident("ro\tads\n"), '"roads"')

    def test_non_latin_names_survive(self) -> None:
        self.assertEqual(quote_ident("Дороги"), '"Дороги"')

    def test_empty_name_raises(self) -> None:
        for value in ("", "\x00\x01\x1f"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    quote_ident(value)

    def test_whitespace_name_is_quoted_not_rejected(self) -> None:
        """Пробелы printable: имя из пробелов не пустое, но и не ломает запрос."""

        self.assertEqual(quote_ident("   "), '"   "')

    def test_error_text_follows_language(self) -> None:
        set_language("en")
        try:
            with self.assertRaises(ValueError) as caught:
                quote_ident("")
            self.assertEqual(str(caught.exception), "Empty object name")
        finally:
            set_language("ru")

    def test_numbers_are_quoted_as_text(self) -> None:
        self.assertEqual(quote_ident(42), '"42"')


class RenderSqlTest(unittest.TestCase):
    """Подстановка в шаблон запроса."""

    def test_named_placeholders(self) -> None:
        sql = render_sql(
            "CREATE INDEX ON {table} USING gist ({column})",
            table='"public"."roads"',
            column='"geom"',
        )
        self.assertEqual(
            sql, 'CREATE INDEX ON "public"."roads" USING gist ("geom")'
        )

    def test_positional_placeholders(self) -> None:
        self.assertEqual(render_sql("SELECT {0} FROM {1}", "a", "b"), "SELECT a FROM b")

    def test_template_without_placeholders_is_unchanged(self) -> None:
        template = "SELECT count(*) FROM roads"
        self.assertEqual(render_sql(template), template)


if __name__ == "__main__":
    unittest.main()
