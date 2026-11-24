"""Структурные проверки пакета: компиляция и разрешимость импортов.

Тесты не импортируют ``qgis``: модули разбираются через ``ast``. Так
проверяется то, чего не видит линтер — что ``from .module import name``
указывает на существующий модуль и на имя, которое в нём действительно
объявлено. Именно такая ошибка (``query_error`` без импорта) однажды прошла
в релиз.
"""

from __future__ import annotations

import ast
import unittest

from .support import ROOT, plugin_files


def module_names() -> "set[str]":
    """Имена модулей пакета без расширения."""

    return {path.stem for path in plugin_files()}


def defined_names(tree: ast.Module) -> "set[str]":
    """Имена, объявленные в модуле на верхнем уровне."""

    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
    return names


def relative_imports(tree: ast.Module):
    """Относительные импорты вида ``from .module import name``."""

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
            yield node


class ModuleCompilesTest(unittest.TestCase):
    """Каждый модуль пакета компилируется."""

    def test_all_modules_compile(self) -> None:
        for path in plugin_files():
            with self.subTest(module=path.name):
                source = path.read_text(encoding="utf-8")
                compile(source, str(path), "exec")


class RelativeImportTest(unittest.TestCase):
    """Относительные импорты указывают на существующие имена."""

    def setUp(self) -> None:
        self.modules = module_names()
        self.trees = {
            path.stem: ast.parse(path.read_text(encoding="utf-8"))
            for path in plugin_files()
        }
        self.definitions = {
            name: defined_names(tree) for name, tree in self.trees.items()
        }

    def test_target_module_exists(self) -> None:
        for name, tree in self.trees.items():
            for node in relative_imports(tree):
                with self.subTest(module=name, imported=node.module):
                    self.assertIn(
                        node.module,
                        self.modules,
                        "{} imports from missing module .{}".format(name, node.module),
                    )

    def test_imported_names_are_defined(self) -> None:
        for name, tree in self.trees.items():
            for node in relative_imports(tree):
                available = self.definitions.get(node.module, set())
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    with self.subTest(module=name, source=node.module, name=alias.name):
                        self.assertIn(
                            alias.name,
                            available,
                            "{} imports {} from .{}, but .{} does not define it".format(
                                name, alias.name, node.module, node.module
                            ),
                        )

    def test_package_init_is_import_free(self) -> None:
        """``__init__.py`` не тянет QGIS: classFactory импортирует плагин лениво."""

        tree = self.trees["__init__"]
        top_level = [
            node for node in tree.body
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]
        self.assertEqual(top_level, [], "__init__.py imports at module level")


class ModuleLayoutTest(unittest.TestCase):
    """Набор модулей и их ответственность."""

    EXPECTED = {
        "__init__",
        "catalog",
        "charts",
        "check_history",
        "connection",
        "excel_export",
        "explorer",
        "formatting",
        "html_export",
        "i18n",
        "info_dialog",
        "layer_loader",
        "load_task",
        "nsi",
        "panel",
        "plugin",
        "quality",
        "sql_errors",
        "sql_identifiers",
        "stats",
        "table_export",
        "version",
    }

    def test_expected_modules_exist(self) -> None:
        self.assertEqual(module_names(), self.EXPECTED)

    def test_readme_documents_every_module(self) -> None:
        for name in ("README.md", "README_eng.md"):
            text = (ROOT / name).read_text(encoding="utf-8")
            missing = [
                module for module in sorted(self.EXPECTED)
                if "{}.py".format(module) not in text
            ]
            with self.subTest(readme=name):
                self.assertEqual(
                    missing, [], "{} does not mention: {}".format(name, missing)
                )


if __name__ == "__main__":
    unittest.main()
