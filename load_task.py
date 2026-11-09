"""Фоновое чтение характеристик пространственных таблиц PostGIS.

Работа выполняется в отдельном потоке QThread, чтобы не блокировать
интерфейс QGIS. Поток закрывает собственное соединение к базе и
отправляет результаты сигналом ``table_updated``.
"""

from __future__ import annotations

from typing import List, Optional

from qgis.PyQt.QtCore import QThread, pyqtSignal

from .catalog import SpatialTable, count_rows, geometry_has_data, table_size
from .connection import PGConnection, close_connection, open_connection


class LoadTablesTask(QThread):
    """Поток фоновой загрузки количества объектов и размеров таблиц."""

    table_loaded = pyqtSignal(int, object)  # (index, new SpatialTable)
    progress = pyqtSignal(int, int)  # (done, total)
    finished_all = pyqtSignal(bool, str)  # (cancelled, error_text)

    def __init__(
        self,
        connection: PGConnection,
        tables: List[SpatialTable],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._connection = connection
        self._tables = tables
        self._cancel_requested = False

    def request_cancel(self) -> None:
        """Попросить поток остановиться."""
        self._cancel_requested = True

    def run(self) -> None:
        db = None
        error = ""
        try:
            db = open_connection(self._connection)
            total = len(self._tables)
            for index, table in enumerate(self._tables):
                if self._cancel_requested:
                    self.finished_all.emit(True, "")
                    return
                # Для тяжёлых таблиц стараемся не блокировать интерфейс
                # дольше одного запроса.
                has_data = geometry_has_data(db, table)
                rows = count_rows(db, table)
                size = table_size(db, table)
                updated = SpatialTable(
                    schema=table.schema,
                    name=table.name,
                    geom_column=table.geom_column,
                    geom_type=table.geom_type,
                    srid=table.srid,
                    estimated_rows=table.estimated_rows,
                    spatial_type=table.spatial_type,
                    feature_count=rows,
                    total_size=size,
                    has_geometry=has_data,
                )
                self.table_loaded.emit(index, updated)
                self.progress.emit(index + 1, total)
            self.finished_all.emit(False, "")
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
            self.finished_all.emit(False, error)
        finally:
            if db is not None:
                close_connection(self._connection)
                db = None