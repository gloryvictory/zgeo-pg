"""Форматирование размеров и чисел для интерфейса и экспорта."""

from __future__ import annotations

import unittest

from .support import load_package

load_package()

from zgeo_pg.formatting import format_number, format_size  # noqa: E402
from zgeo_pg.i18n import set_language  # noqa: E402


class FormatSizeTest(unittest.TestCase):
    """Размеры в байтах превращаются в читаемую строку."""

    def setUp(self) -> None:
        set_language("ru")

    def test_bytes_have_no_fraction(self) -> None:
        self.assertEqual(format_size(0), "0 Б")
        self.assertEqual(format_size(512), "512 Б")
        self.assertEqual(format_size(1023), "1023 Б")

    def test_kilobytes_keep_one_decimal(self) -> None:
        self.assertEqual(format_size(1024), "1 КБ")
        self.assertEqual(format_size(1536), "1.5 КБ")

    def test_large_values_drop_the_fraction(self) -> None:
        self.assertEqual(format_size(1024 * 1024), "1 МБ")
        self.assertEqual(format_size(1024 * 1024 * 150), "150 МБ")

    def test_gigabytes_and_terabytes(self) -> None:
        self.assertEqual(format_size(1024 ** 3), "1 ГБ")
        self.assertEqual(format_size(1024 ** 4), "1 ТБ")
        self.assertEqual(format_size(1024 ** 4 * 5), "5 ТБ")

    def test_terabytes_are_the_last_unit(self) -> None:
        """Больше ТБ единицы нет: значение остаётся в ТБ, а не уходит в цикл."""

        self.assertEqual(format_size(1024 ** 5), "1024 ТБ")

    def test_english_units(self) -> None:
        set_language("en")
        try:
            self.assertEqual(format_size(1024), "1 KB")
            self.assertEqual(format_size(1024 ** 3), "1 GB")
        finally:
            set_language("ru")


class FormatNumberTest(unittest.TestCase):
    """Разделители тысяч зависят от языка."""

    def setUp(self) -> None:
        set_language("ru")

    def test_none_is_a_dash(self) -> None:
        self.assertEqual(format_number(None), "—")

    def test_russian_separator_is_a_space(self) -> None:
        self.assertEqual(format_number(1234567), "1 234 567")

    def test_english_separator_is_a_comma(self) -> None:
        set_language("en")
        try:
            self.assertEqual(format_number(1234567), "1,234,567")
        finally:
            set_language("ru")

    def test_float_is_truncated_to_int(self) -> None:
        self.assertEqual(format_number(12.7), "12")

    def test_text_is_returned_as_is(self) -> None:
        self.assertEqual(format_number("нет данных"), "нет данных")


if __name__ == "__main__":
    unittest.main()
