"""Сборка ZIP-архива плагина: имя корневой папки и состав."""

from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from .support import ROOT, load_package

load_package()

sys.path.insert(0, str(ROOT / "scripts"))

import build_zip  # noqa: E402


class PackageNameTest(unittest.TestCase):
    """Имя корневой папки архива — корректный идентификатор Python."""

    def test_hyphen_becomes_underscore(self) -> None:
        self.assertEqual(build_zip.package_name("zgeo-pg"), "zgeo_pg")

    def test_dots_and_spaces_are_replaced(self) -> None:
        self.assertEqual(build_zip.package_name("zgeo.pg v2"), "zgeo_pg_v2")

    def test_leading_digit_gets_underscore(self) -> None:
        self.assertEqual(build_zip.package_name("2zgeo"), "_2zgeo")

    def test_already_valid_name_is_kept(self) -> None:
        self.assertEqual(build_zip.package_name("zgeo_pg"), "zgeo_pg")


class BuildArchiveTest(unittest.TestCase):
    """Архив содержит плагин и ничего лишнего."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.output = Path(self._dir.name)
        self.path = build_zip.build(output_dir=self.output)
        # Архив читается сразу: на Windows открытый файл нельзя перезаписать,
        # а часть тестов собирает архив повторно.
        with zipfile.ZipFile(self.path) as archive:
            self.names = archive.namelist()
            self.contents = {name: archive.read(name) for name in self.names}

    def test_archive_name_and_version(self) -> None:
        version = build_zip.read_version(ROOT)
        self.assertEqual(self.path.name, "zgeo-pg-{}.zip".format(version))

    def test_single_root_folder(self) -> None:
        roots = {name.split("/")[0] for name in self.names}
        self.assertEqual(roots, {"zgeo_pg"})

    def test_plugin_modules_are_inside(self) -> None:
        for module in ("__init__.py", "plugin.py", "panel.py", "quality.py"):
            with self.subTest(module=module):
                self.assertIn("zgeo_pg/" + module, self.names)

    def test_development_files_are_excluded(self) -> None:
        forbidden = (
            "img/",
            "tests/",
            "scripts/",
            "dist/",
            "__pycache__/",
            ".ruff_cache/",
            ".github/",
            "AGENTS.md",
            "agents.md",
            "ruff.toml",
        )
        for marker in forbidden:
            with self.subTest(marker=marker):
                hits = [name for name in self.names if marker in name]
                self.assertEqual(hits, [])

    def test_metadata_version_matches_archive_name(self) -> None:
        metadata = self.contents["zgeo_pg/metadata.txt"].decode("utf-8")
        version = [
            line.split("=", 1)[1].strip()
            for line in metadata.splitlines()
            if line.startswith("version=")
        ][0]
        self.assertIn(version, self.path.name)

    def test_license_is_packed(self) -> None:
        self.assertIn("zgeo_pg/LICENSE", self.names)
        self.assertNotIn("zgeo_pg/LICENSE.md", self.names)

    def test_no_bytecode_inside(self) -> None:
        self.assertEqual([name for name in self.names if name.endswith(".pyc")], [])

    def test_stale_archives_are_removed(self) -> None:
        stale = self.output / "zgeo-pg-0.0.1.zip"
        stale.write_bytes(b"old")
        build_zip.build(output_dir=self.output)
        self.assertFalse(stale.exists())


if __name__ == "__main__":
    unittest.main()
