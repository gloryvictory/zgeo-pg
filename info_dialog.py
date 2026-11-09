"""Диалог «Информация» о пространственной таблице."""

from __future__ import annotations

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QDialog,
    QFormLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from .catalog import SpatialTable, crs_label, fetch_crs_auth
from .formatting import format_number, format_size
from .i18n import tr


def show_table_info(parent, table: SpatialTable) -> None:
    """Показать сведения о таблице в модальном диалоге."""
    dialog = QDialog(parent)
    dialog.setWindowTitle(tr("Информация о таблице"))
    dialog.setMinimumWidth(420)

    layout = QVBoxLayout(dialog)

    form = QFormLayout()
    form.addRow(tr("Таблица"), _label(table.name))
    form.addRow(tr("Схема"), _label(table.schema))
    form.addRow(tr("Полное имя"), _label(table.full_name))
    form.addRow(tr("Столбец геометрии"), _label(table.geom_column))
    form.addRow(tr("Геометрия / география"), _label(table.spatial_type))
    form.addRow(tr("Тип"), _label(table.geom_type))
    form.addRow("SRID", _label("" if table.srid is None else str(table.srid)))
    form.addRow(tr("Система координат"), _label(crs_label(table.srid, None)))
    form.addRow(tr("Строк (оценка)"), _label(format_number(table.estimated_rows)))
    form.addRow(tr("Строк (точно)"), _label(format_number(table.feature_count)))
    form.addRow(
        tr("Размер"),
        _label(format_size(table.total_size) if table.total_size is not None else "—"),
    )
    form.addRow(tr("Пустая геометрия"), _label(tr("—") if table.has_geometry else tr("Да")))
    layout.addLayout(form)

    close_btn = QPushButton(tr("Закрыть"))
    close_btn.clicked.connect(dialog.accept)
    layout.addWidget(close_btn)

    dialog.exec()


def _label(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setTextInteractionFlags(label.textInteractionFlags() | 0x1)  # TextSelectableByMouse
    return label