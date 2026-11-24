"""Запись XLSX: структура пакета, типы ячеек и экранирование."""

from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from .support import load_package

load_package()

from zgeo_pg.excel_export import write_xlsx_sheets  # noqa: E402


class WriteXlsxTest(unittest.TestCase):
    """Книга собирается как валидный ZIP-пакет Office Open XML."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.root = Path(self._dir.name)

    def _write(self, sheets):
        path = write_xlsx_sheets(self.root / "book.xlsx", sheets)
        with zipfile.ZipFile(path) as archive:
            return path, {name: archive.read(name) for name in archive.namelist()}

    def test_package_has_required_parts(self) -> None:
        _path, parts = self._write(
            [("Лист", ["Таблица"], [["roads"]])]
        )
        for required in (
            "[Content_Types].xml",
            "_rels/.rels",
            "xl/workbook.xml",
            "xl/_rels/workbook.xml.rels",
            "xl/worksheets/sheet1.xml",
        ):
            self.assertIn(required, parts)

    def test_every_sheet_gets_its_own_part(self) -> None:
        _path, parts = self._write(
            [
                ("Статистика", ["Формат"], [["Shapefile"]]),
                ("Совпало", ["Значение"], [["Москва"]]),
                ("Расхождения", ["Значение"], [["Тверь"]]),
            ]
        )
        sheets = [name for name in parts if name.startswith("xl/worksheets/sheet")]
        self.assertEqual(len(sheets), 3)
        workbook = parts["xl/workbook.xml"].decode("utf-8")
        self.assertIn("Статистика", workbook)
        self.assertIn("Расхождения", workbook)

    def test_numbers_stay_numbers_and_text_stays_text(self) -> None:
        _path, parts = self._write(
            [("Лист", ["n", "t"], [[42, "42"], [None, ""]])]
        )
        sheet = parts["xl/worksheets/sheet1.xml"].decode("utf-8")
        # Число записано числовой ячейкой, текст — inlineStr.
        self.assertIn('<c r="A2"><v>42</v></c>', sheet)
        self.assertIn('<c r="B2" t="inlineStr">', sheet)

    def test_xml_special_characters_are_escaped(self) -> None:
        _path, parts = self._write(
            [("Лист", ["value"], [['a & b < c > d " e']])]
        )
        sheet = parts["xl/worksheets/sheet1.xml"].decode("utf-8")
        self.assertIn("a &amp; b &lt; c &gt; d &quot; e", sheet)
        self.assertNotIn("a & b < c >", sheet)

    def test_sheet_name_is_sanitized(self) -> None:
        _path, parts = self._write(
            [("a/b:c*d?e[f]g", ["x"], [[1]])]
        )
        workbook = parts["xl/workbook.xml"].decode("utf-8")
        self.assertIn("a_b_c_d_e_f_g", workbook)
        self.assertNotIn("a/b:c", workbook)

    def test_long_sheet_name_is_truncated_to_31_chars(self) -> None:
        long_name = "Очень длинное имя листа " * 3
        _path, parts = self._write([(long_name, ["x"], [[1]])])
        workbook = parts["xl/workbook.xml"].decode("utf-8")
        self.assertIn(long_name[:31], workbook)
        self.assertNotIn(long_name, workbook)

    def test_missing_extension_is_added(self) -> None:
        path = write_xlsx_sheets(self.root / "book", [("Лист", ["x"], [[1]])])
        self.assertEqual(path.suffix, ".xlsx")
        self.assertTrue(path.exists())

    def test_empty_sheet_list_raises(self) -> None:
        with self.assertRaises(ValueError):
            write_xlsx_sheets(self.root / "empty.xlsx", [])


if __name__ == "__main__":
    unittest.main()
