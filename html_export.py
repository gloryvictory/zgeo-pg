"""Экспорт таблиц интерфейса в HTML без внешних зависимостей.

Файл получается самодостаточным: стили встроены, картинок и внешних
ресурсов нет, поэтому его можно открыть в браузере или вложить в отчёт.
"""

from __future__ import annotations

import re
from html import escape
from pathlib import Path
from typing import Optional, Sequence, Tuple

from .formatting import format_number
from .i18n import tr

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


_SIZE_RE = re.compile(r"^[\d\s\u00a0.,]+(?:Б|КБ|МБ|ГБ|ТБ|B|KB|MB|GB|TB)$")


_SECTIONS_PAGE = """<!DOCTYPE html>
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
h2 {{
    font-size: 14px;
    font-weight: 600;
    margin: 20px 0 8px;
}}
table {{
    border-collapse: collapse;
    min-width: 40%;
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
p.footer {{
    color: #707070;
    font-size: 11px;
    margin-top: 18px;
}}
</style>
</head>
<body>
<h1>{title}</h1>
{sections}
<p class="footer">{footer}</p>
</body>
</html>
"""



_REPORT_PAGE = """<!DOCTYPE html>
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
h2 {{
    font-size: 14px;
    font-weight: 600;
    margin: 22px 0 8px;
    scroll-margin-top: 56px;
}}
nav.toc {{
    position: sticky;
    top: 0;
    z-index: 2;
    background: #f4f6f9;
    border: 1px solid #d5dce4;
    border-radius: 4px;
    padding: 8px 10px;
    margin-bottom: 16px;
}}
nav.toc a {{
    color: #1f4e79;
    text-decoration: none;
    margin-right: 14px;
    white-space: nowrap;
}}
nav.toc a:hover {{
    text-decoration: underline;
}}
table {{
    border-collapse: collapse;
    min-width: 40%;
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
p.footer {{
    color: #707070;
    font-size: 11px;
    margin-top: 24px;
}}
</style>
</head>
<body>
<h1>{title}</h1>
<nav class="toc">{toc}</nav>
{body}
<p class="footer">{footer}</p>
</body>
</html>
"""


def write_html_report(
    path: Path,
    title: str,
    info: Sequence[Sequence],
    stats: Sequence[Sequence],
    sections: Sequence[Tuple[str, Sequence[str], Sequence[Sequence]]],
    footer: str = "",
    lang: str = "ru",
) -> Path:
    """Записать отчёт: панель ссылок, что выбрано, статистика и значения.

    Args:
        info: Строки таблицы «что выбрано» (параметр и значения сторон).
        stats: Строки таблицы статистики (категория и количество).
        sections: Разделы со значениями: (имя, заголовки, строки).
    """

    path = Path(path)
    if path.suffix.lower() not in (".html", ".htm"):
        path = path.with_suffix(".html")
    path.parent.mkdir(parents=True, exist_ok=True)

    def table(headers: Sequence[str], rows: Sequence[Sequence]) -> str:
        # _row_html уже оборачивает ячейки в <tr>, второй раз не нужно.
        body = "\n".join(_row_html(row) for row in rows)
        return (
            "<table>\n<thead>\n{}\n</thead>\n<tbody>\n{}\n"
            "</tbody>\n</table>"
        ).format(_row_html(headers, tag="th"), body)

    blocks = []
    links = []

    if info:
        links.append('<a href="#sources">{}</a>'.format(escape(tr("Что выбрано"))))
        blocks.append(
            '<h2 id="sources">{}</h2>\n{}'.format(
                escape(tr("Что выбрано")),
                table([tr("Параметр"), tr("Левая панель"), tr("Правая панель")], info),
            )
        )

    if stats:
        links.append('<a href="#stats">{}</a>'.format(escape(tr("Статистика"))))
        blocks.append(
            '<h2 id="stats">{}</h2>\n{}'.format(
                escape(tr("Статистика")),
                table([tr("Категория"), tr("Количество")], stats),
            )
        )

    for index, (name, headers, rows) in enumerate(sections):
        anchor = "section-{}".format(index + 1)
        links.append('<a href="#{}">{}</a>'.format(anchor, escape(name)))
        blocks.append(
            '<h2 id="{}">{}</h2>\n{}'.format(anchor, escape(name), table(headers, rows))
        )

    page = _REPORT_PAGE.format(
        lang=escape(lang or "ru"),
        title=escape(title or ""),
        toc="\n".join(links),
        body="\n".join(blocks),
        footer=escape(footer or ""),
    )
    path.write_text(page, encoding="utf-8")
    return path


def write_html_sections(
    path: Path,
    sections: Sequence[Tuple[str, Sequence[str], Sequence[Sequence]]],
    title: str = "",
    footer: str = "",
    lang: str = "ru",
) -> Path:
    """Записать несколько таблиц на одну HTML-страницу.

    Каждый раздел выводится своим заголовком и своей таблицей, поэтому в
    одном файле видно и совпадения, и оба списка расхождений.
    """

    path = Path(path)
    if path.suffix.lower() not in (".html", ".htm"):
        path = path.with_suffix(".html")
    path.parent.mkdir(parents=True, exist_ok=True)

    blocks = []
    for name, headers, rows in sections:
        body_rows = [_row_html(row) for row in rows]
        blocks.append(
            '<h2>{}</h2>\n<table>\n<thead>\n{}\n</thead>\n'
            "<tbody>\n{}\n</tbody>\n</table>".format(
                escape(name),
                _row_html(headers, tag="th"),
                "\n".join(body_rows),
            )
        )

    page = _SECTIONS_PAGE.format(
        lang=escape(lang or "ru"),
        title=escape(title or ""),
        sections="\n".join(blocks),
        footer=escape(footer or ""),
    )
    path.write_text(page, encoding="utf-8")
    return path


def _format_cell(value) -> tuple:
    """Вернуть (текст, признак числовой ячейки)."""

    if value is None:
        return "", False
    if isinstance(value, bool):
        return ("1" if value else "0"), True
    if isinstance(value, (int, float)):
        return format_number(value), True
    text = str(value)
    # Человеко-читаемые размеры («80 КБ», «1.5 ГБ») выравниваем как числа.
    return text, bool(_SIZE_RE.match(text.strip()))


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
