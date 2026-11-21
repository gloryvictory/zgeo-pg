"""Экспорт таблиц интерфейса в Excel и HTML с выбором файла."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional, Sequence

from qgis.PyQt.QtCore import QStandardPaths, Qt
from qgis.PyQt.QtWidgets import QFileDialog, QMenu, QMessageBox, QTableWidget

from .excel_export import CellValue, SheetSpec, write_xlsx_sheets
from .explorer import reveal_files
from .formatting import format_size
from .html_export import write_html_report, write_html_sections, write_html_table
from .i18n import tr

FORMAT_XLSX = "xlsx"
FORMAT_HTML = "html"


def ask_export_format(parent, anchor=None) -> Optional[str]:
    """Спросить формат экспорта: Excel или HTML."""

    menu = QMenu(parent)
    excel_action = menu.addAction(tr("Экспорт в Excel"))
    html_action = menu.addAction(tr("Экспорт в HTML"))
    position = anchor.mapToGlobal(anchor.rect().bottomLeft()) if anchor else None
    chosen = menu.exec(position) if position is not None else menu.exec()
    if chosen == excel_action:
        return FORMAT_XLSX
    if chosen == html_action:
        return FORMAT_HTML
    return None


def export_table_with_dialog(
    parent,
    table: QTableWidget,
    default_filename: str,
    sheet_name: str,
    summary_rows: Optional[Iterable[Sequence[CellValue]]] = None,
    export_format: str = FORMAT_XLSX,
    size_columns: Optional[Sequence[int]] = None,
) -> Optional[Path]:
    """Предложить сохранить таблицу и записать её в .xlsx или .html."""

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
        export_format=export_format,
        total_index=len(rows) - 1 if summary_rows else None,
        size_columns=size_columns,
    )


def export_rows_with_dialog(
    parent,
    headers: Sequence[str],
    rows: Iterable[Sequence[CellValue]],
    default_filename: str,
    sheet_name: str,
    extra_sheets: Optional[Iterable[SheetSpec]] = None,
    export_format: str = FORMAT_XLSX,
    total_index: Optional[int] = None,
    size_columns: Optional[Sequence[int]] = None,
) -> Optional[Path]:
    """Предложить сохранить строки в выбранном формате и открыть проводник.

    Аргумент size_columns перечисляет столбцы с размерами в байтах: перед
    записью их значения приводятся к читаемому виду (80 КБ, 1.5 ГБ).
    """

    rows = list(rows)
    if not rows:
        return None
    if size_columns:
        rows = [_humanize_sizes(row, size_columns) for row in rows]

    html = export_format == FORMAT_HTML
    suffix = ".html" if html else ".xlsx"
    documents = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.DocumentsLocation
    )
    start_dir = Path(documents) if documents else Path.home()
    selected, _filter = QFileDialog.getSaveFileName(
        parent,
        tr("Экспорт в HTML") if html else tr("Экспорт в Excel"),
        str(_with_suffix(start_dir / default_filename, suffix)),
        "HTML (*.html)" if html else "Excel (*.xlsx)",
    )
    if not selected:
        return None

    path = _with_suffix(selected, suffix)

    try:
        if html:
            write_html_table(
                path,
                headers,
                rows,
                title=sheet_name,
                total_index=total_index,
                footer=tr("ZGeo-PG — контроль качества пространственных данных PostGIS"),
            )
        else:
            sheets: list = [(sheet_name, headers, rows)]
            if extra_sheets:
                sheets.extend(list(extra_sheets))
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


def export_sections_with_dialog(
    parent,
    sections: Sequence[Tuple[str, Sequence[str], Iterable[Sequence[CellValue]]]],
    default_filename: str,
    title: str,
    export_format: str = FORMAT_XLSX,
) -> Optional[Path]:
    """Сохранить несколько разделов: листы Excel или таблицы на одной странице.

    Args:
        sections: Последовательность (имя раздела, заголовки, строки).
        title: Заголовок страницы HTML и имя файла по умолчанию.
    """

    prepared = [(name, list(headers), list(rows)) for name, headers, rows in sections]
    if not prepared:
        return None

    html = export_format == FORMAT_HTML
    suffix = ".html" if html else ".xlsx"
    documents = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.DocumentsLocation
    )
    start_dir = Path(documents) if documents else Path.home()
    selected, _filter = QFileDialog.getSaveFileName(
        parent,
        tr("Экспорт в HTML") if html else tr("Экспорт в Excel"),
        str(_with_suffix(start_dir / default_filename, suffix)),
        "HTML (*.html)" if html else "Excel (*.xlsx)",
    )
    if not selected:
        return None

    path = _with_suffix(selected, suffix)
    try:
        if html:
            write_html_sections(
                path,
                prepared,
                title=title,
                footer=tr("ZGeo-PG — контроль качества пространственных данных PostGIS"),
            )
        else:
            write_xlsx_sheets(path, prepared)
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


def export_report_with_dialog(
    parent,
    info: Sequence[Sequence[CellValue]],
    stats: Sequence[Sequence[CellValue]],
    sections: Sequence[Tuple[str, Sequence[str], Iterable[Sequence[CellValue]]]],
    default_filename: str,
    title: str,
    export_format: str = FORMAT_XLSX,
) -> Optional[Path]:
    """Сохранить отчёт: листы Excel по разделам или страница HTML с оглавлением.

    Args:
        info: Строки таблицы «что выбрано».
        stats: Строки таблицы статистики.
        sections: Разделы со значениями: (имя, заголовки, строки).
    """

    prepared = [(name, list(headers), list(rows)) for name, headers, rows in sections]
    if not prepared:
        return None

    html = export_format == FORMAT_HTML
    suffix = ".html" if html else ".xlsx"
    documents = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.DocumentsLocation
    )
    start_dir = Path(documents) if documents else Path.home()
    selected, _filter = QFileDialog.getSaveFileName(
        parent,
        tr("Экспорт в HTML") if html else tr("Экспорт в Excel"),
        str(_with_suffix(start_dir / default_filename, suffix)),
        "HTML (*.html)" if html else "Excel (*.xlsx)",
    )
    if not selected:
        return None

    path = _with_suffix(selected, suffix)
    try:
        if html:
            write_html_report(
                path,
                title,
                list(info),
                list(stats),
                prepared,
                footer=tr("ZGeo-PG — контроль качества пространственных данных PostGIS"),
            )
        else:
            sheets: list = []
            if stats:
                sheets.append((tr("Статистика"), [tr("Категория"), tr("Количество")], list(stats)))
            sheets.extend(prepared)
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


def _humanize_sizes(row: Sequence[CellValue], size_columns: Sequence[int]) -> list:
    """Заменить размеры в байтах на читаемые строки."""

    values = list(row)
    for column in size_columns:
        if column >= len(values):
            continue
        value = values[column]
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            values[column] = format_size(int(value))
    return values


def _with_suffix(path, suffix: str) -> Path:
    """Привести путь к нужному расширению."""

    path = Path(path)
    return path if path.suffix.lower() == suffix else path.with_suffix(suffix)


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