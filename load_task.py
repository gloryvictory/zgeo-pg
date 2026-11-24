"""Фоновое чтение характеристик пространственных таблиц PostGIS.

Работа выполняется в отдельном потоке QThread, чтобы не блокировать
интерфейс QGIS. Поток закрывает собственное соединение к базе и
отправляет результаты сигналом ``table_updated``.
"""

from __future__ import annotations

from typing import List, Tuple

from qgis.PyQt.QtCore import QThread, pyqtSignal

from .catalog import (
    SpatialTable,
    count_rows,
    create_spatial_index,
    drop_spatial_index,
    fetch_spatial_index,
    geometry_has_data,
    reindex_spatial_index,
    table_sizes,
)
from .connection import PGConnection, close_connection, open_connection


class IndexTask(QThread):
    """Поток фонового создания или перестроения пространственных индексов."""

    CONNECTION_TAG = "index"

    table_done = pyqtSignal(int, str, str)  # (index, action, error_text)
    progress = pyqtSignal(int, int)  # (done, total)
    finished_all = pyqtSignal(bool, str)  # (cancelled, error_text)

    ACTION_CREATE = "create"
    ACTION_REINDEX = "reindex"
    ACTION_DROP = "drop"

    def __init__(
        self,
        connection: PGConnection,
        jobs: List[Tuple[int, SpatialTable, str]],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._connection = connection
        self._jobs = jobs
        self._cancel_requested = False

    def request_cancel(self) -> None:
        """Попросить поток остановиться."""
        self._cancel_requested = True

    def run(self) -> None:
        db = None
        try:
            db = open_connection(self._connection, self.CONNECTION_TAG)
            total = len(self._jobs)
            for position, (index, table, action) in enumerate(self._jobs):
                if self._cancel_requested:
                    self.finished_all.emit(True, "")
                    return
                error = ""
                try:
                    if action == self.ACTION_REINDEX:
                        reindex_spatial_index(db, table)
                    elif action == self.ACTION_DROP:
                        drop_spatial_index(db, table)
                    else:
                        create_spatial_index(db, table)
                except Exception as exc:  # noqa: BLE001
                    error = str(exc)
                self.table_done.emit(index, action, error)
                self.progress.emit(position + 1, total)
            self.finished_all.emit(False, "")
        except Exception as exc:  # noqa: BLE001
            self.finished_all.emit(False, str(exc))
        finally:
            if db is not None:
                close_connection(self._connection, self.CONNECTION_TAG)
                db = None


class LoadTablesTask(QThread):
    """Поток фоновой загрузки количества объектов и размеров таблиц."""

    CONNECTION_TAG = "load"

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
            db = open_connection(self._connection, self.CONNECTION_TAG)
            total = len(self._tables)
            for index, table in enumerate(self._tables):
                if self._cancel_requested:
                    self.finished_all.emit(True, "")
                    return
                # Для тяжёлых таблиц стараемся не блокировать интерфейс
                # дольше одного запроса.
                has_data = geometry_has_data(db, table)
                rows = count_rows(db, table)
                data_size, indexes_size = table_sizes(db, table)
                index_name, spatial_index_size = fetch_spatial_index(db, table)
                # «Размер индексов» — все индексы, кроме пространственного.
                other_indexes = indexes_size
                if other_indexes is not None and spatial_index_size is not None:
                    other_indexes = max(0, other_indexes - spatial_index_size)
                updated = SpatialTable(
                    schema=table.schema,
                    name=table.name,
                    geom_column=table.geom_column,
                    geom_type=table.geom_type,
                    srid=table.srid,
                    estimated_rows=table.estimated_rows,
                    spatial_type=table.spatial_type,
                    feature_count=rows,
                    data_size=data_size,
                    index_size=other_indexes,
                    has_geometry=has_data,
                    comment=table.comment,
                    spatial_index_name=index_name,
                    spatial_index_size=spatial_index_size,
                )
                self.table_loaded.emit(index, updated)
                self.progress.emit(index + 1, total)
            self.finished_all.emit(False, "")
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
            self.finished_all.emit(False, error)
        finally:
            if db is not None:
                close_connection(self._connection, self.CONNECTION_TAG)
                db = None