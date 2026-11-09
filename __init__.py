"""ZGeo-PG — каталог пространственных данных из базы PostgreSQL / PostGIS для QGIS."""


def classFactory(iface):
    """Точка входа QGIS-плагина."""

    from .plugin import ZGeoPgPlugin

    return ZGeoPgPlugin(iface)
