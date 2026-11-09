"""Экспорт таблиц интерфейса в Excel с выбором файла."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional, Sequence

from qgis.PyQt.QtCore import QStandardPaths, Qt
from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox, QTableWidget

from .excel_export import CellValue, SheetSpec, write_xlsx_sheets
from .explorer import reveal_files
from .i18n import tr


def export_table_with_dialog(
    parent,
    table: QTableWidget,
    default_filename: str,
    sheet_name: str,
    summary_rows: Optional[Iterable[Sequence[CellValue]]] = None,
) -> Optional[Path]:
    """Предложить сохранить таблицу и записать её в .xlsx."""

    if table.rowCount() == 0:
        return None

    headers = [
        table.horizontalHeaderItem(column).text()
        if table.horizontalHeaderItem(column) is not None
        else ""
        for column in range(table.columnCount())
    ]
    rows = _table_rows(table)
    if summary_rows:
        rows.extend([list(row) for row in summary_rows])
    return export_rows_with_dialog(
        parent,
        headers,
        rows,
        default_filename,
        sheet_name,
    )


def export_rows_with_dialog(
    parent,
    headers: Sequence[str],
    rows: Iterable[Sequence[CellValue]],
    default_filename: str,
    sheet_name: str,
    extra_sheets: Optional[Iterable[SheetSpec]] = None,
) -> Optional[Path]:
    """Предложить сохранить строки в .xlsx и открыть проводник."""

    rows = list(rows)
    if not rows:
        return None

    documents = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.DocumentsLocation
    )
    start_dir = Path(documents) if documents else Path.home()
    selected, _filter = QFileDialog.getSaveFileName(
        parent,
        tr("Экспорт в Excel"),
        str(start_dir / default_filename),
        "Excel (*.xlsx)",
    )
    if not selected:
        return None

    path = Path(selected)
    if path.suffix.lower() != ".xlsx":
        path = path.with_suffix(".xlsx")

    sheets: list = [(sheet_name, headers, rows)]
    if extra_sheets:
        sheets.extend(list(extra_sheets))

    try:
        write_xlsx_sheets(path, sheets)
    except Exception as error:  # noqa: BLE001
        QMessageBox.critical(
            parent,
            "ZGeo-PG",
            tr("Не удалось экспортировать таблицу:\n{}", error),
        )
        return None

    errors = reveal_files([path])
    if errors:
        QMessageBox.warning(
            parent,
            "ZGeo-PG",
            tr(
                "Таблица экспортирована:\n{}\n\n"
                "Не удалось открыть проводник:\n{}",
                path,
                "\n".join(errors),
            ),
        )
    return path


def _table_rows(table: QTableWidget) -> list:
    rows = []
    for row in range(table.rowCount()):
        values = []
        for column in range(table.columnCount()):
            item = table.item(row, column)
            if item is None:
                values.append("")
                continue
            raw_value = item.data(Qt.ItemDataRole.UserRole)
            values.append(raw_value if raw_value is not None else item.text())
        rows.append(values)
    return rows