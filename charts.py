"""Столбчатые диаграммы без внешних зависимостей."""

from __future__ import annotations

from typing import List, Sequence, Tuple

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


class LineChart(QWidget):
    """График динамики: значения по точкам замеров с подписями времени."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._points: List[Tuple[str, int]] = []  # (label, value)
        self._title = ""
        self._color = QColor("#316395")
        self.setMinimumHeight(180)

    def set_title(self, title: str) -> None:
        self._title = title
        self.update()

    def set_points(self, labels: Sequence[str], values: Sequence[int]) -> None:
        self._points = list(zip(labels, values))
        self.update()

    def set_color(self, value: str) -> None:
        self._color = _parse_color(value)
        self.update()

    def point_count(self) -> int:
        return len(self._points)

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(420, 200)

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
        margin_left = 46
        margin_right = 12
        margin_top = 26
        margin_bottom = 34
        plot_width = max(20, width - margin_left - margin_right)
        plot_height = max(20, height - margin_top - margin_bottom)

        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(10)
        painter.setFont(title_font)
        painter.setPen(QColor("#303030"))
        painter.drawText(10, 8, width - 20, 20, Qt.AlignmentFlag.AlignLeft, self._title)

        if not self._points:
            label_font = QFont()
            label_font.setPointSize(9)
            painter.setFont(label_font)
            painter.setPen(QColor("#707070"))
            painter.drawText(
                10,
                margin_top,
                width - 20,
                plot_height,
                Qt.AlignmentFlag.AlignCenter,
                "—",
            )
            return

        max_value = max(value for _label, value in self._points)
        max_value = max(1, max_value)

        axis_pen = QPen(QColor("#c8c8c8"))
        axis_pen.setWidth(1)
        painter.setPen(axis_pen)
        painter.drawLine(margin_left, margin_top, margin_left, margin_top + plot_height)
        painter.drawLine(
            margin_left,
            margin_top + plot_height,
            margin_left + plot_width,
            margin_top + plot_height,
        )

        small_font = QFont()
        small_font.setPointSize(8)
        painter.setFont(small_font)
        painter.setPen(QColor("#707070"))
        painter.drawText(6, margin_top - 2, margin_left - 8, 14, Qt.AlignmentFlag.AlignRight, str(max_value))
        painter.drawText(
            6,
            margin_top + plot_height - 10,
            margin_left - 8,
            14,
            Qt.AlignmentFlag.AlignRight,
            "0",
        )

        count = len(self._points)
        step = plot_width / max(1, count - 1) if count > 1 else 0
        coordinates: List[Tuple[int, int]] = []
        for index, (_label, value) in enumerate(self._points):
            x = margin_left + (index * step if count > 1 else plot_width / 2)
            y = margin_top + plot_height - (value / max_value) * plot_height
            coordinates.append((int(x), int(y)))

        line_pen = QPen(self._color)
        line_pen.setWidth(2)
        painter.setPen(line_pen)
        for index in range(len(coordinates) - 1):
            painter.drawLine(
                coordinates[index][0],
                coordinates[index][1],
                coordinates[index + 1][0],
                coordinates[index + 1][1],
            )

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._color)
        for x, y in coordinates:
            painter.drawEllipse(x - 3, y - 3, 6, 6)

        painter.setPen(QColor("#303030"))
        for index, ((_label, value), (x, y)) in enumerate(zip(self._points, coordinates)):
            painter.drawText(x - 20, y - 18, 40, 14, Qt.AlignmentFlag.AlignCenter, str(value))
            if count <= 8 or index in (0, count - 1) or index % max(1, count // 6) == 0:
                painter.setPen(QColor("#707070"))
                painter.drawText(
                    x - 40,
                    margin_top + plot_height + 4,
                    80,
                    14,
                    Qt.AlignmentFlag.AlignCenter,
                    self._points[index][0],
                )
                painter.setPen(QColor("#303030"))


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