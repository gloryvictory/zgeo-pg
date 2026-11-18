"""Экспорт таблиц интерфейса в HTML без внешних зависимостей.

Файл получается самодостаточным: стили встроены, картинок и внешних
ресурсов нет, поэтому его можно открыть в браузере или вложить в отчёт.
"""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Optional, Sequence

from .formatting import format_number

_PAGE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
body {{
    font-family: "Segoe UI", "Noto Sans", Arial, sans-serif;
    font-size: 13px;
    color: #202020;
    margin: 18px;
}}
h1 {{
    font-size: 16px;
    font-weight: 600;
    margin: 0 0 12px;
}}
table {{
    border-collapse: collapse;
    min-width: 60%;
}}
th, td {{
    border: 1px solid #c8c8c8;
    padding: 4px 8px;
    text-align: left;
    vertical-align: top;
}}
th {{
    background: #eef2f7;
    font-weight: 600;
    white-space: nowrap;
}}
tbody tr:nth-child(even) td {{
    background: #fafafa;
}}
td.number {{
    text-align: right;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
}}
tr.total td {{
    font-weight: 600;
    background: #eef2f7;
    border-top: 2px solid #9aa7b6;
}}
p.footer {{
    color: #707070;
    font-size: 11px;
    margin-top: 12px;
}}
</style>
</head>
<body>
<h1>{title}</h1>
<table>
<thead>
<tr>{head}</tr>
</thead>
<tbody>
{body}
</tbody>
</table>
<p class="footer">{footer}</p>
</body>
</html>
"""


def _format_cell(value) -> tuple:
    """Вернуть (текст, признак числовой ячейки)."""

    if value is None:
        return "", False
    if isinstance(value, bool):
        return ("1" if value else "0"), True
    if isinstance(value, (int, float)):
        return format_number(value), True
    return str(value), False


def _row_html(
    values: Sequence, tag: str = "td", total: bool = False
) -> str:
    cells = []
    for value in values:
        text, is_number = _format_cell(value)
        css = ' class="number"' if is_number and not total else ""
        cells.append(f"<{tag}{css}>{escape(text)}</{tag}>")
    row_class = ' class="total"' if total else ""
    return f'<tr{row_class}>{"".join(cells)}</tr>'


def write_html_table(
    path: Path,
    headers: Sequence[str],
    rows: Sequence[Sequence],
    title: str = "",
    total_index: Optional[int] = None,
    footer: str = "",
    lang: str = "ru",
) -> Path:
    """Записать таблицу в HTML-файл.

    Args:
        path: Путь к файлу .html.
        headers: Заголовки столбцов.
        rows: Строки таблицы; числа выводятся с разделителями тысяч.
        title: Заголовок страницы и таблицы.
        total_index: Индекс строки «Итого» для выделения жирным.
        footer: Подпись под таблицей.
        lang: Код языка для атрибута ``lang``.

    Returns:
        Путь к записанному файлу.
    """

    path = Path(path)
    if path.suffix.lower() not in (".html", ".htm"):
        path = path.with_suffix(".html")
    path.parent.mkdir(parents=True, exist_ok=True)

    body_rows = []
    for index, row in enumerate(rows):
        body_rows.append(
            _row_html(row, total=(total_index is not None and index == total_index))
        )

    page = _PAGE.format(
        lang=escape(lang or "ru"),
        title=escape(title or ""),
        head=_row_html(headers, tag="th"),
        body="\n".join(body_rows),
        footer=escape(footer or ""),
    )
    path.write_text(page, encoding="utf-8")
    return path
