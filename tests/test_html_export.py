"""HTML-отчёт: экранирование, структура и разделы."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from .support import load_package

load_package()

from zgeo_pg.html_export import (  # noqa: E402
    write_html_report,
    write_html_sections,
    write_html_table,
)


class HtmlExportTest(unittest.TestCase):
    """Страницы пишутся без внешних зависимостей и без XSS."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.root = Path(self._dir.name)

    def test_table_page_contains_headers_and_rows(self) -> None:
        path = write_html_table(
            self.root / "table.html",
            ["Таблица", "Строк"],
            [["roads", 10], ["buildings", 20]],
            title="Таблицы",
        )
        text = path.read_text(encoding="utf-8")
        self.assertIn("<!DOCTYPE html>", text)
        self.assertIn("Таблица", text)
        self.assertIn("roads", text)
        self.assertIn("buildings", text)
        self.assertIn("Таблицы", text)

    def test_html_special_characters_are_escaped(self) -> None:
        path = write_html_table(
            self.root / "escape.html",
            ["value"],
            [['<script>alert("x")</script>']],
            title="t",
        )
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("<script>alert", text)
        self.assertIn("&lt;script&gt;", text)

    def test_numbers_are_formatted_with_separators(self) -> None:
        path = write_html_table(
            self.root / "numbers.html",
            ["Строк"],
            [[1234567]],
            title="t",
        )
        text = path.read_text(encoding="utf-8")
        self.assertIn("1", text)
        self.assertIn("234", text)

    def test_sections_page_keeps_every_section(self) -> None:
        path = write_html_sections(
            self.root / "sections.html",
            [
                ("Совпало", ["Значение"], [["Москва"]]),
                ("Расхождения", ["Значение"], [["Тверь"]]),
            ],
            title="Сверка НСИ",
        )
        text = path.read_text(encoding="utf-8")
        for expected in ("Совпало", "Расхождения", "Москва", "Тверь", "Сверка НСИ"):
            self.assertIn(expected, text)

    def test_report_page_has_info_stats_and_sections(self) -> None:
        path = write_html_report(
            self.root / "report.html",
            "Отчёт",
            [["Соединение", "local"], ["Таблица", "roads"]],
            [["Совпало", 10], ["Нет в правой", 2]],
            [("Значения", ["Значение"], [["Москва"]])],
            footer="ZGeo-PG",
        )
        text = path.read_text(encoding="utf-8")
        for expected in (
            "Отчёт",
            "Соединение",
            "local",
            "Совпало",
            "Значения",
            "Москва",
            "ZGeo-PG",
        ):
            self.assertIn(expected, text)

    def test_extension_is_added_when_missing(self) -> None:
        path = write_html_table(self.root / "noext", ["a"], [[1]])
        self.assertEqual(path.suffix, ".html")
        self.assertTrue(path.exists())

    def test_language_attribute_is_written(self) -> None:
        path = write_html_table(self.root / "lang.html", ["a"], [[1]], lang="en")
        self.assertIn('lang="en"', path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
