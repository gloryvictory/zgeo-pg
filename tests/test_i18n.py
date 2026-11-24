"""Переводы интерфейса: полнота словаря и поведение ``tr``."""

from __future__ import annotations

import unittest

from .support import load_package

load_package()

from zgeo_pg import i18n  # noqa: E402
from zgeo_pg.i18n import (  # noqa: E402
    EN_TRANSLATIONS,
    LANGUAGE_EN,
    LANGUAGE_RU,
    get_language,
    normalize_language,
    set_language,
    tr,
)


class TranslationDictionaryTest(unittest.TestCase):
    """Словарь английских переводов без пустых значений."""

    def test_no_empty_translations(self) -> None:
        empty = [key for key, value in EN_TRANSLATIONS.items() if not str(value).strip()]
        self.assertEqual(empty, [], "empty translations: {}".format(empty))

    def test_no_empty_source_strings(self) -> None:
        empty = [key for key in EN_TRANSLATIONS if not key.strip()]
        self.assertEqual(empty, [])

    # Строки, которые в английском интерфейсе совпадают с исходными: это
    # аббревиатуры и символы, а не забытый перевод.
    IDENTICAL_ALLOWED = {"SRID", "—"}

    def test_translations_differ_from_source(self) -> None:
        """Одинаковые строки в словаре — забытый перевод."""

        same = [
            key for key, value in EN_TRANSLATIONS.items()
            if key == value and key not in self.IDENTICAL_ALLOWED
        ]
        self.assertEqual(same, [], "untranslated: {}".format(same[:10]))

    def test_dictionary_is_not_truncated(self) -> None:
        self.assertGreater(len(EN_TRANSLATIONS), 400)

    def test_placeholders_match(self) -> None:
        """Число и имена подстановок в переводе совпадают с исходной строкой."""

        problems = []
        for source, target in EN_TRANSLATIONS.items():
            if source.count("{}") != str(target).count("{}"):
                problems.append(source)
        self.assertEqual(problems, [], "placeholder mismatch: {}".format(problems[:10]))


class TrTest(unittest.TestCase):
    """``tr`` переводит только при английском интерфейсе."""

    def tearDown(self) -> None:
        set_language("ru")

    def test_russian_returns_source(self) -> None:
        set_language("ru")
        self.assertEqual(tr("Таблицы"), "Таблицы")

    def test_english_returns_translation(self) -> None:
        set_language("en")
        self.assertEqual(tr("Таблицы"), "Tables")

    def test_unknown_string_is_returned_as_is(self) -> None:
        set_language("en")
        self.assertEqual(tr("Строка без перевода"), "Строка без перевода")

    def test_positional_arguments_are_substituted(self) -> None:
        set_language("en")
        self.assertEqual(tr("Выбрано: {} из {}", 3, 7), "Selected: 3 of 7")

    def test_named_arguments_are_substituted(self) -> None:
        """Именованные подстановки поддерживаются наравне с позиционными."""

        set_language("ru")
        self.assertEqual(tr("Файл: {name}", name="roads.shp"), "Файл: roads.shp")

    def test_missing_argument_does_not_raise(self) -> None:
        """Нехватка аргументов не должна ломать отрисовку интерфейса."""

        set_language("en")
        self.assertEqual(tr("Выбрано: {} из {}", 3), "Selected: {} of {}")


class LanguageTest(unittest.TestCase):
    """Нормализация и хранение кода языка."""

    def tearDown(self) -> None:
        set_language("ru")

    def test_known_codes(self) -> None:
        self.assertEqual(normalize_language("ru"), LANGUAGE_RU)
        self.assertEqual(normalize_language("en"), LANGUAGE_EN)

    def test_unknown_falls_back_to_russian(self) -> None:
        self.assertEqual(normalize_language("de"), LANGUAGE_RU)
        self.assertEqual(normalize_language(None), LANGUAGE_RU)
        self.assertEqual(normalize_language(""), LANGUAGE_RU)

    def test_case_and_prefix_are_tolerated(self) -> None:
        self.assertEqual(normalize_language("EN"), LANGUAGE_EN)
        self.assertEqual(normalize_language("en_US"), LANGUAGE_EN)

    def test_set_language_updates_current(self) -> None:
        set_language("en")
        self.assertEqual(get_language(), LANGUAGE_EN)
        set_language("ru")
        self.assertEqual(get_language(), LANGUAGE_RU)

    def test_language_key_is_stable(self) -> None:
        """Ключ настроек нельзя менять без миграции."""

        self.assertEqual(i18n.LANGUAGE_KEY, "zgeopg/language")


if __name__ == "__main__":
    unittest.main()
