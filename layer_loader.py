"""Загрузка пространственной таблицы PostGIS в текущий проект QGIS.

Модуль отдельный, чтобы проверки качества не зависели от qgis.core напрямую:
панель вызывает его только по действию пользователя, а тесты могут
подставить свой объект iface.
"""

from __future__ import annotations

from qgis.core import QgsDataSourceUri, QgsProject, QgsVectorLayer

from .catalog import SpatialTable
from .connection import PGConnection
from .i18n import tr


def resolve_iface(iface=None):
    """Найти интерфейс QGIS: переданный или текущий из qgis.utils."""

    if iface is not None:
        return iface
    try:
        from qgis.utils import iface as current_iface

        return current_iface
    except Exception:  # noqa: BLE001 - вне QGIS интерфейса нет
        return None


def build_layer(conn: PGConnection, table: SpatialTable) -> QgsVectorLayer:
    """Собрать слой PostGIS для таблицы, не добавляя его в проект."""

    uri = QgsDataSourceUri()
    uri.setConnection(
        conn.host,
        str(conn.port),
        conn.database,
        conn.user,
        conn.password,
    )
    uri.setDataSource(
        table.schema,
        table.name,
        table.geom_column or "geom",
        "",
        "",
    )
    if table.srid:
        uri.setSrid(str(table.srid))
    return QgsVectorLayer(uri.uri(False), table.full_name, "postgres")


def load_table_layer(iface, conn: PGConnection, table: SpatialTable) -> str:
    """Добавить слой таблицы в текущий проект и показать его на карте.

    Returns:
        Сообщение для статусной строки.

    Raises:
        RuntimeError: если слой не удалось создать или показать.
    """

    iface = resolve_iface(iface)
    if iface is None:
        raise RuntimeError(tr("Нет доступа к окну QGIS"))

    project = QgsProject.instance()
    if project is None:
        raise RuntimeError(tr("Не открыт проект QGIS"))

    layer = build_layer(conn, table)
    if not layer.isValid():
        raise RuntimeError(
            tr("Не удалось загрузить слой") + ": " + table.full_name
        )

    source = layer.publicSource()
    existing = None
    for candidate in project.mapLayers().values():
        if candidate.publicSource() == source:
            existing = candidate
            break

    if existing is not None:
        layer = existing
        message = tr("Слой уже в проекте") + ": " + table.full_name
    else:
        project.addMapLayer(layer)
        message = tr("Слой добавлен на карту") + ": " + table.full_name

    canvas = getattr(iface, "mapCanvas", lambda: None)()
    if canvas is not None:
        extent = layer.extent()
        if not extent.isEmpty():
            canvas.setExtent(extent)
        canvas.refresh()
    return message
