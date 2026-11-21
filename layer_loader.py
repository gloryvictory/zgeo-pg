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


def select_problems(layer, where: str) -> int:
    """Оставить на слое только проблемные объекты и выделить их.

    Слой получает подмножество по условию проверки, поэтому на карте видны
    ровно те объекты, в которых найдена проблема, а выделение делает их
    заметными сразу.

    Returns:
        Количество выделенных объектов.
    """

    if layer is None or not where:
        return 0
    layer.removeSelection()
    layer.setSubsetString(where)
    if not layer.isValid():
        layer.setSubsetString("")
        raise RuntimeError(tr("Условие проверки не подходит к слою"))
    count = layer.featureCount()
    if count > 0:
        layer.selectAll()
    return count


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


def find_layer(project, conn: PGConnection, table: SpatialTable):
    """Найти в проекте слой этой же таблицы.

    Сравниваются подключение, схема, таблица и столбец геометрии, а не
    ``publicSource()``: после ``setSubsetString()`` источник меняется на
    подзапрос, и слой перестал бы находиться, из-за чего таблица добавлялась
    в проект второй раз.
    """

    for candidate in project.mapLayers().values():
        if candidate.providerType() != "postgres":
            continue
        uri = QgsDataSourceUri(candidate.source())
        if (
            uri.host() == conn.host
            and str(uri.port()) == str(conn.port)
            and uri.database() == conn.database
            and uri.schema() == table.schema
            and uri.table() == table.name
            and uri.geometryColumn() == (table.geom_column or "geom")
        ):
            return candidate
    return None


def load_table_layer(
    iface,
    conn: PGConnection,
    table: SpatialTable,
    where: str = "",
) -> str:
    """Добавить слой таблицы в текущий проект и показать его на карте.

    Args:
        where: условие проверки; если задано, на слое остаются только
            проблемные объекты и они выделяются.

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

    existing = find_layer(project, conn, table)
    if existing is not None:
        layer = existing
        message = tr("Слой уже в проекте") + ": " + table.full_name
    else:
        project.addMapLayer(layer)
        message = tr("Слой добавлен на карту") + ": " + table.full_name

    if where:
        try:
            selected = select_problems(layer, where)
        except Exception as error:  # noqa: BLE001
            message += " — " + tr("не удалось выделить объекты") + ": " + str(error)
            selected = 0
        else:
            message += " — " + tr("выделено объектов: {}").format(selected)
    elif layer.subsetString():
        # Обычная загрузка должна показать всю таблицу, а не остаток
        # предыдущего выделения.
        layer.removeSelection()
        layer.setSubsetString("")

    layer.updateExtents()
    canvas = getattr(iface, "mapCanvas", lambda: None)()
    if canvas is not None:
        extent = layer.extent()
        if not extent.isEmpty():
            canvas.setExtent(extent)
        canvas.refresh()
    return message
