"""Метаданные плагина, версия и лицензия.

Лицензия проверяется дословно: GitHub определяет MIT только по каноническому
тексту. Лишние строки («Version N/A», шаблонные скобки, типографские кавычки)
переводят лицензию в NOASSERTION, поэтому текст сверяется с шаблоном.
"""

from __future__ import annotations

import configparser
import re
import unittest

from .support import ROOT, load_package

load_package()

from zgeo_pg.version import get_plugin_version  # noqa: E402

METADATA = ROOT / "metadata.txt"

MIT_TEMPLATE = '''MIT License

Copyright (c) {year} {holder}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''


def metadata() -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    config.read(METADATA, encoding="utf-8")
    return config


class MetadataTest(unittest.TestCase):
    """Обязательные поля metadata.txt."""

    def setUp(self) -> None:
        self.config = metadata()

    def test_required_keys(self) -> None:
        for key in (
            "name",
            "qgisMinimumVersion",
            "qgisMaximumVersion",
            "description",
            "about",
            "version",
            "author",
            "email",
            "repository",
            "license",
            "category",
        ):
            with self.subTest(key=key):
                self.assertTrue(self.config.get("general", key, fallback="").strip())

    def test_name_and_license(self) -> None:
        self.assertEqual(self.config.get("general", "name"), "ZGeo-PG")
        self.assertEqual(self.config.get("general", "license"), "MIT")

    def test_qgis_version_range(self) -> None:
        minimum = self.config.get("general", "qgisMinimumVersion")
        maximum = self.config.get("general", "qgisMaximumVersion")
        self.assertEqual(minimum, "3.16")
        self.assertTrue(maximum.startswith("4."))

    def test_deprecated_qt6_flag_is_absent(self) -> None:
        """Флаг supportsQt6 удалён из QGIS: совместимость задаёт qgisMaximumVersion."""

        self.assertNotIn("supportsQt6", self.config["general"])

    # Бюджет длины полей: в менеджере плагинов длинный текст нечитаем, а
    # подробности живут в README. Значения подобраны так, чтобы обе языковые
    # версии уместились и в список плагинов, и в карточку.
    DESCRIPTION_LIMIT = 512
    ABOUT_LIMIT = 1024

    def test_description_fits_plugin_manager(self) -> None:
        value = self.config.get("general", "description")
        self.assertLessEqual(len(value), self.DESCRIPTION_LIMIT)

    def test_about_fits_plugin_card(self) -> None:
        value = self.config.get("general", "about")
        self.assertLessEqual(len(value), self.ABOUT_LIMIT)

    def test_description_and_about_link_to_documentation(self) -> None:
        self.assertIn(
            "github.com/gloryvictory/zgeo-pg",
            self.config.get("general", "about"),
        )

    def test_description_and_about_are_bilingual(self) -> None:
        for key in ("description", "about"):
            value = self.config.get("general", key)
            with self.subTest(key=key):
                self.assertTrue(
                    " / " in value, "{} must contain both languages".format(key)
                )

    def test_changelog_starts_with_current_version(self) -> None:
        version = self.config.get("general", "version")
        changelog = self.config.get("general", "changelog")
        self.assertTrue(
            changelog.startswith(version + " "),
            "changelog must start with {}".format(version),
        )

    def test_metadata_is_readable_by_version_module(self) -> None:
        self.assertEqual(get_plugin_version(), self.config.get("general", "version"))


class VersionTest(unittest.TestCase):
    """Версия плагина в metadata.txt и README."""

    def test_version_format(self) -> None:
        version = metadata().get("general", "version")
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")

    def test_readme_mentions_version(self) -> None:
        version = metadata().get("general", "version")
        for name in ("README.md", "README_eng.md"):
            text = (ROOT / name).read_text(encoding="utf-8")
            with self.subTest(readme=name):
                self.assertIn(version, text)

    def test_change_log_has_section_for_version(self) -> None:
        version = metadata().get("general", "version")
        text = (ROOT / "change.log").read_text(encoding="utf-8")
        self.assertRegex(text, r"## \[" + re.escape(version) + r"\]")


class LicenseTest(unittest.TestCase):
    """Лицензия распознаётся GitHub как MIT."""

    def setUp(self) -> None:
        self.text = (ROOT / "LICENSE").read_text(encoding="utf-8")

    def test_single_license_file(self) -> None:
        """Два файла лицензии — источник расхождений: остаётся один."""

        self.assertTrue((ROOT / "LICENSE").exists())
        self.assertFalse((ROOT / "LICENSE.md").exists())

    def test_text_matches_canonical_mit(self) -> None:
        normalized = re.sub(
            r"^Copyright \(c\) \d{4} .+$", "Copyright (c) {year} {holder}",
            self.text, count=1, flags=re.M,
        )
        self.assertEqual(normalized, MIT_TEMPLATE)

    def test_no_placeholder_lines(self) -> None:
        for marker in ("Version N/A", "SPDX short identifier", "Open Source Initiative"):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, self.text)

    def test_no_bracket_placeholders(self) -> None:
        self.assertNotIn("[2026]", self.text)
        self.assertNotIn("[Zamaraev", self.text)

    def test_ascii_quotes_only(self) -> None:
        """Типографские кавычки мешают точному совпадению с шаблоном."""

        for char in ("\u201c", "\u201d", "\u2018", "\u2019"):
            with self.subTest(char=char):
                self.assertNotIn(char, self.text)

    def test_line_endings_are_lf(self) -> None:
        self.assertNotIn("\r\n", self.text)


if __name__ == "__main__":
    unittest.main()
