"""Столбчатые диаграммы без внешних зависимостей."""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple

from qgis.PyQt.QtCore import QSize, Qt
from qgis.PyQt.QtGui import QColor, QFont, QPainter, QPen
from qgis.PyQt.QtWidgets import QWidget

from .formatting import format_size

BAR_COLORS = (
    "#316395",
    "#2b9f6e",
    "#b07c3c",
    "#8e4d9b",
    "#c0504d",
    "#4f81bd",
    "#8064a2",
    "#9bbb59",
    "#f79646",
    "#4bacc6",
)


def _parse_color(value: str) -> QColor:
    color = QColor(value)
    return color if color.isValid() else QColor("#316395")


class BarChart(QWidget):
    """Горизонтальная столбчатая диаграмма с размерными подписями."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: List[Tuple[str, int, int]] = []  # (label, count, total_size)
        self._title = ""
        self.setMinimumHeight(180)

    def set_title(self, title: str) -> None:
        self._title = title
        self.update()

    def set_items(
        self,
        labels: Sequence[str],
        counts: Sequence[int],
        sizes: Sequence[int],
    ) -> None:
        self._items = list(zip(labels, counts, sizes))
        self.update()

    def sizeHint(self) -> QSize:  # noqa: N802
        height = 60 + len(self._items) * 30
        return QSize(420, max(120, height))

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            self._draw(painter)
        finally:
            painter.end()

    def _draw(self, painter: QPainter) -> None:
        width = self.width()
        height = self.height()
        margin_left = 14
        margin_right = 96
        margin_top = 26
        chart_width = max(20, width - margin_left - margin_right)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(10)
        painter.setFont(title_font)
        painter.setPen(QColor("#303030"))
        painter.drawText(10, 8, chart_width - 20, 22, Qt.AlignmentFlag.AlignLeft, self._title)

        if not self._items:
            return

        max_count = max(item[1] for item in self._items) or 1
        row_height = 30
        label_font = QFont()
        label_font.setPointSize(9)
        painter.setFont(label_font)

        for index, (label, count, size) in enumerate(self._items):
            y = margin_top + index * row_height
            bar_span = chart_width * count / max_count
            bar_width = max(2, int(bar_span))
            color = _parse_color(BAR_COLORS[index % len(BAR_COLORS)])
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(margin_left, y, bar_width, 18, 3, 3)

            painter.setPen(QColor("#303030"))
            painter.drawText(margin_left, y - 1, chart_width, 18, Qt.AlignmentFlag.AlignLeft, str(count))
            value_x = margin_left + chart_width + 6
            painter.drawText(value_x, y - 1, margin_right - 10, 18, Qt.AlignmentFlag.AlignRight, format_size(size))

        # Подписи категорий справа от значений.
        label_font.setPointSize(8)
        painter.setFont(label_font)
        start = margin_top
        for index, (label, count, size) in enumerate(self._items):
            y = start + index * row_height
            painter.setPen(QColor("#606060"))
            painter.drawText(
                width - margin_right + 4,
                y + 16,
                margin_right - 10,
                16,
                Qt.AlignmentFlag.AlignLeft,
                label,
            )