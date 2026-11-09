"""Экспорт таблиц в Excel без внешних зависимостей.

Запись простейшего валидного XLSX: XML-части пакета, листы и встроенные
строковые ячейки. Числа записываются как числа, всё остальное — как текст.
"""

from __future__ import annotations

import datetime
import re
import zipfile
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple, Union

CellValue = Union[str, int, float, None]

SheetSpec = Tuple[str, Sequence[str], Iterable[Sequence[CellValue]]]

_XML_ESCAPE_RE = re.compile(r'[&<>"\']')

_XML_ESCAPES = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&apos;",
}


def _xml_escape(text: str) -> str:
    return _XML_ESCAPE_RE.sub(lambda match: _XML_ESCAPES[match.group(0)], text)


def _sanitize_sheet_name(name: str) -> str:
    """Ограничить длину и убрать недопустимые символы имени листа."""
    cleaned = re.sub(r'[\\/*?:\[\]]', "_", str(name))
    cleaned = cleaned.strip() or "Sheet"
    return cleaned[:31]


def _column_letter(index: int) -> str:
    """Индекс столбца (с нуля) -> буквенное имя Excel."""
    letters = ""
    index += 1
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _cell_ref(row: int, column: int) -> str:
    return f"{_column_letter(column)}{row + 1}"


def _cell_xml(row: int, column: int, value: CellValue) -> str:
    ref = _cell_ref(row, column)
    if isinstance(value, bool):
        return f'<c r="{ref}" t="b"><v>{"1" if value else "0"}</v></c>'
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{ref}"><v>{value}</v></c>'
    if value is None:
        return f'<c r="{ref}"/>'
    text_value = str(value)
    if isinstance(value, datetime.datetime):
        text_value = value.isoformat(sep=" ")
    return (
        f'<c r="{ref}" t="inlineStr">'
        f"<is><t xml:space=\"preserve\">{_xml_escape(text_value)}</t></is></c>"
    )


def write_xlsx_sheets(path: Path, sheets: Iterable[SheetSpec]) -> Path:
    """Записать книгу XLSX с несколькими листами.

    Args:
        path: Путь к файлу .xlsx.
        sheets: Последовательность кортежей (имя листа, заголовки, строки).
    """
    sheets = [(name, headers, list(rows)) for name, headers, rows in sheets]
    if not sheets:
        raise ValueError("no sheets")

    path = Path(path)
    if path.suffix.lower() != ".xlsx":
        path = path.with_suffix(".xlsx")
    path.parent.mkdir(parents=True, exist_ok=True)

    names = [_sanitize_sheet_name(name) for name, _headers, _rows in sheets]
    workbook_xml = _workbook_xml(names)
    rels_xml = _rels_xml(len(sheets))
    content_types_xml = _content_types_xml(len(sheets))

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("_rels/.rels", _root_rels_xml())
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", rels_xml)
        for index, (name, headers, rows) in enumerate(sheets):
            sheet_xml = _sheet_xml(headers, rows)
            archive.writestr(f"xl/worksheets/sheet{index + 1}.xml", sheet_xml)
            archive.writestr(
                f"xl/worksheets/_rels/sheet{index + 1}.xml.rels",
                _sheet_rels_xml(),
            )

    return path


def _content_types_xml(sheet_count: int) -> str:
    overrides = "".join(
        '<Override PartName="/xl/worksheets/sheet{}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'.format(
            index
        )
        for index in range(1, sheet_count + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        + overrides
        + "</Types>"
    )


def _root_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )


def _workbook_xml(names: Sequence[str]) -> str:
    sheets = "".join(
        '<sheet name="{}" sheetId="{}" r:id="rId{}"/>'.format(
            _xml_escape(_sanitize_sheet_name(name)), index + 1, index + 1
        )
        for index, name in enumerate(names)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<sheets>"
        + sheets
        + "</sheets>"
        + "</workbook>"
    )


def _rels_xml(sheet_count: int) -> str:
    rels = "".join(
        '<Relationship Id="rId{}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{}.xml"/>'.format(
            index + 1, index + 1
        )
        for index in range(sheet_count)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + rels
        + "</Relationships>"
    )


def _sheet_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
    )


def _sheet_xml(headers: Sequence[str], rows: Sequence[Sequence[CellValue]]) -> str:
    cells: List[str] = []
    max_columns = 0

    def append_row(row_index: int, values: Sequence[CellValue]) -> None:
        nonlocal max_columns
        row_cells = []
        for column_index, value in enumerate(values):
            row_cells.append(_cell_xml(row_index, column_index, value))
        if values:
            max_columns = max(max_columns, len(values))
        if row_cells:
            cells.append(f'<row r="{row_index + 1}">{"".join(row_cells)}</row>')

    if headers:
        append_row(0, list(headers))
    for row_index, row in enumerate(rows, start=1):
        append_row(row_index, row)

    dimension = (
        f'<dimension ref="A1:{_cell_ref(len(rows) + (1 if headers else 0), max(1, max_columns))}"/>'
        if cells
        else '<dimension ref="A1"/>'
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        + dimension
        + "<sheetData>"
        + "".join(cells)
        + "</sheetData>"
        + "</worksheet>"
    )