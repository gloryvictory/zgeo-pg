"""Чтение каталога пространственных таблиц из базы PostGIS.

Модуль не зависит от виджетов и может тестироваться без интерфейса.
Поиск таблиц ведётся через представления geometry_columns и
geography_columns PostGIS.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from qgis.PyQt.QtSql import QSqlQuery

from .i18n import tr
from .sql_identifiers import quote_ident, render_sql

# Типы геометрии, упорядоченные для группировки в статистике.
GEOMETRY_ORDER = (
    "POINT",
    "MULTIPOINT",
    "LINESTRING",
    "MULTILINESTRING",
    "POLYGON",
    "MULTIPOLYGON",
    "GEOMETRYCOLLECTION",
    "GEOMETRY",
    "GEOGRAPHY",
)


def normalize_geometry_type(raw) -> str:
    """Нормализовать тип геометрии для группировки."""
    value = str(raw or "").strip().upper()
    if not value:
        return "GEOMETRY"
    return value


def geometry_rank(geom_type: str) -> int:
    """Вернуть индекс типа геометрии для упорядочивания."""
    value = normalize_geometry_type(geom_type)
    try:
        return GEOMETRY_ORDER.index(value)
    except ValueError:
        return len(GEOMETRY_ORDER)


def parse_srid(value) -> Optional[int]:
    """Привести значение SRID к целому числу."""
    try:
        srid = int(value)
    except (TypeError, ValueError):
        return None
    return srid if srid > 0 else None


def crs_label(srid, auth) -> str:
    """Построить подпись системы координат по SRID."""
    if srid is None:
        return tr("—")
    if auth:
        return f"{auth}:{srid}"
    return str(srid)


@dataclass(frozen=True)
class SpatialTable:
    """Пространственная таблица в базе PostGIS."""

    schema: str
    name: str
    geom_column: str
    geom_type: str
    srid: Optional[int]
    estimated_rows: int = 0
    spatial_type: str = "geometry"  # "geometry" | "geography"

    feature_count: Optional[int] = None
    data_size: Optional[int] = None
    index_size: Optional[int] = None
    has_geometry: bool = True
    comment: str = ""
    spatial_index_name: Optional[str] = None
    spatial_index_size: Optional[int] = None

    @property
    def has_spatial_index(self) -> bool:
        """Есть ли у таблицы пространственный индекс."""
        return bool(self.spatial_index_name)

    @property
    def full_size(self) -> int:
        """Размер данных + прочих индексов + пространственного индекса."""
        return (
            (self.data_size or 0)
            + (self.index_size or 0)
            + (self.spatial_index_size or 0)
        )

    @property
    def total_size(self) -> int:
        """Совместимость: полный размер таблицы (см. ``full_size``)."""
        return self.full_size

    @property
    def qualified(self) -> str:
        return quote_ident(self.schema) + "." + quote_ident(self.name)

    @property
    def full_name(self) -> str:
        return f"{self.schema}.{self.name}"

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, SpatialTable):
            return NotImplemented
        return (self.schema.casefold(), self.name.casefold()) < (
            other.schema.casefold(),
            other.name.casefold(),
        )


# Запросы по представлениям PostGIS собраны как константы: имена представлений
# и столбцов — часть схемы PostgreSQL и не зависят от данных пользователя.
VIEW_SQL = {
    "geometry": (
        "SELECT geometry_columns.f_table_schema, "
        "geometry_columns.f_table_name, "
        "geometry_columns.f_geometry_column, "
        "geometry_columns.type, "
        "geometry_columns.srid, "
        "COALESCE(c.reltuples, 0)::bigint AS estimated, "
        "COALESCE(pg_catalog.obj_description(c.oid, 'pg_class'), '') "
        "FROM geometry_columns "
        "LEFT JOIN pg_catalog.pg_class c "
        "  ON c.relname = geometry_columns.f_table_name "
        "WHERE c.relnamespace = ("
        "  SELECT n.oid FROM pg_catalog.pg_namespace n "
        "  WHERE n.nspname = geometry_columns.f_table_schema"
        ") "
        # Таблицы без права SELECT только мешают: любой запрос к ним
        # заканчивается ошибкой «нет доступа к таблице».
        "AND pg_catalog.has_table_privilege(c.oid, 'SELECT')"
    ),
    "geography": (
        "SELECT geography_columns.f_table_schema, "
        "geography_columns.f_table_name, "
        "geography_columns.f_geography_column, "
        "geography_columns.type, "
        "geography_columns.srid, "
        "COALESCE(c.reltuples, 0)::bigint AS estimated, "
        "COALESCE(pg_catalog.obj_description(c.oid, 'pg_class'), '') "
        "FROM geography_columns "
        "LEFT JOIN pg_catalog.pg_class c "
        "  ON c.relname = geography_columns.f_table_name "
        "WHERE c.relnamespace = ("
        "  SELECT n.oid FROM pg_catalog.pg_namespace n "
        "  WHERE n.nspname = geography_columns.f_table_schema"
        ") "
        "AND pg_catalog.has_table_privilege(c.oid, 'SELECT')"
    ),
}


def fetch_spatial_tables(db, schemas: Optional[List[str]] = None) -> List[SpatialTable]:
    """Получить список пространственных таблиц из PostGIS.

    Args:
        db: Открытое соединение QtSql.
        schemas: Если задано — только таблицы из этих схем.

    Returns:
        Список SpatialTable, отсортированный по схеме и имени.
    """

    rows: List[SpatialTable] = []
    wanted = set(schemas) if schemas else None
    for spatial_type in ("geometry", "geography"):
        # Запрос — готовая строка-константа: ни имена представлений, ни
        # столбцы не подставляются извне, поэтому склейки SQL здесь нет.
        q = QSqlQuery(db)
        q.prepare(VIEW_SQL[spatial_type])
        if not q.exec():
            continue  # представление отсутствует в старых версиях PostGIS

        while q.next():
            schema = str(q.value(0) or "")
            name = str(q.value(1) or "")
            if wanted is not None and schema not in wanted:
                continue
            geom_column = str(q.value(2) or "")
            geom_type = normalize_geometry_type(str(q.value(3) or ""))
            srid = parse_srid(q.value(4))
            try:
                estimated = int(q.value(5) or 0)
            except (TypeError, ValueError):
                estimated = 0
            rows.append(
                SpatialTable(
                    schema=schema,
                    name=name,
                    geom_column=geom_column,
                    geom_type=geom_type,
                    srid=srid,
                    estimated_rows=max(0, estimated),
                    spatial_type=spatial_type,
                    comment=str(q.value(6) or "").strip(),
                )
            )

    rows.sort()
    return rows


def fetch_spatial_index(
    db, table: SpatialTable
) -> Tuple[Optional[str], Optional[int]]:
    """Имя и размер пространственного индекса таблицы.

    Возвращает ``(None, None)``, если индекса по столбцу геометрии нет.
    """

    column = table.geom_column or "geom"
    q = QSqlQuery(db)
    q.prepare(
        "SELECT i.relname, pg_catalog.pg_relation_size(i.oid) "
        "FROM pg_catalog.pg_index x "
        "JOIN pg_catalog.pg_class i ON i.oid = x.indexrelid "
        "JOIN pg_catalog.pg_class t ON t.oid = x.indrelid "
        "JOIN pg_catalog.pg_namespace n ON n.oid = t.relnamespace "
        "JOIN pg_catalog.pg_am a ON a.oid = i.relam "
        "JOIN pg_catalog.pg_attribute at "
        "  ON at.attrelid = t.oid AND at.attname = ? "
        "WHERE n.nspname = ? AND t.relname = ? "
        "  AND a.amname IN ('gist', 'spgist') "
        "  AND at.attnum = ANY (x.indkey) "
        "ORDER BY pg_catalog.pg_relation_size(i.oid) DESC "
        "LIMIT 1"
    )
    q.addBindValue(column)
    q.addBindValue(table.schema)
    q.addBindValue(table.name)
    if not q.exec():
        return None, None
    if not q.next():
        return None, None
    name = str(q.value(0) or "")
    if not name:
        return None, None
    try:
        size: Optional[int] = int(q.value(1) or 0)
    except (TypeError, ValueError):
        size = None
    return name, size


def default_spatial_index_name(table: SpatialTable) -> str:
    """Имя для нового пространственного индекса (не длиннее 63 символов)."""

    column = table.geom_column or "geom"
    return f"{table.name}_{column}_idx"[:63]


def create_spatial_index(db, table: SpatialTable, name: Optional[str] = None) -> str:
    """Создать GiST-индекс по столбцу геометрии и вернуть его имя."""

    column = table.geom_column or "geom"
    index_name = name or default_spatial_index_name(table)
    q = QSqlQuery(db)
    sql = render_sql(
        "CREATE INDEX IF NOT EXISTS {name} ON {table} USING gist ({column})",
        name=quote_ident(index_name),
        table=table.qualified,
        column=quote_ident(column),
    )
    if not q.exec(sql):
        raise RuntimeError(_query_error(q, table))
    return index_name


def reindex_spatial_index(
    db, table: SpatialTable, index_name: Optional[str] = None
) -> str:
    """Перестроить пространственный индекс таблицы и вернуть его имя."""

    name = index_name or (fetch_spatial_index(db, table)[0])
    if not name:
        name = create_spatial_index(db, table)
        return name
    q = QSqlQuery(db)
    sql = render_sql(
        "REINDEX INDEX {index}",
        index=quote_ident(table.schema) + "." + quote_ident(name),
    )
    if not q.exec(sql):
        raise RuntimeError(_query_error(q, table))
    return name


def drop_spatial_index(
    db, table: SpatialTable, index_name: Optional[str] = None
) -> str:
    """Удалить пространственный индекс таблицы и вернуть его имя."""

    name = index_name or (fetch_spatial_index(db, table)[0])
    if not name:
        raise RuntimeError(tr("Пространственный индекс не найден"))
    q = QSqlQuery(db)
    sql = render_sql(
        "DROP INDEX IF EXISTS {index}",
        index=quote_ident(table.schema) + "." + quote_ident(name),
    )
    if not q.exec(sql):
        raise RuntimeError(_query_error(q, table))
    return name


def _query_error(q, table: SpatialTable) -> str:
    message = ""
    try:
        message = q.lastError().text()
    except AttributeError:
        message = ""
    return message or (tr("Ошибка запроса") + ": " + table.full_name)


def fetch_crs_auth(db, srid) -> Optional[str]:
    """Вернуть авторитетную подпись (например EPSG:4326) для SRID."""
    if srid is None:
        return None
    q = QSqlQuery(db)
    q.prepare("SELECT auth_name || ':' || auth_srid FROM spatial_ref_sys WHERE srid = ?")
    q.addBindValue(srid)
    if not q.exec():
        return None
    if q.next():
        return str(q.value(0) or "")
    return None


# Шаблоны запросов к конкретной таблице: подставляются только кавыченные
# идентификаторы, поэтому render_sql безопасен.
COUNT_SQL = "SELECT count(*) FROM {table}"

EXISTS_SQL = (
    "SELECT EXISTS (SELECT 1 FROM {table} "
    "WHERE {column} IS NOT NULL AND NOT ST_IsEmpty({column}))"
)


def count_rows(db, table: SpatialTable) -> int:
    """Точное количество строк в таблице."""
    q = QSqlQuery(db)
    q.prepare(render_sql(COUNT_SQL, table=table.qualified))
    if not q.exec():
        return 0
    if q.next():
        try:
            return int(q.value(0) or 0)
        except (TypeError, ValueError):
            return 0
    return 0


def table_sizes(db, table: SpatialTable) -> Tuple[Optional[int], Optional[int]]:
    """Размер данных таблицы и суммарный размер её индексов.

    Второе значение включает все индексы, в том числе пространственный:
    «прочие» индексы получаются как разность (см. ``SpatialTable.index_size``).
    """

    q = QSqlQuery(db)
    q.prepare("SELECT pg_table_size(?::regclass), pg_indexes_size(?::regclass)")
    q.addBindValue(table.qualified)
    q.addBindValue(table.qualified)
    if not q.exec():
        return None, None
    if not q.next():
        return None, None
    return _to_int(q.value(0)), _to_int(q.value(1))


def _to_int(value) -> Optional[int]:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return None
    return result if result >= 0 else None


def geometry_has_data(db, table: SpatialTable) -> bool:
    """Проверить, что в столбце геометрии есть ненулевые объекты."""
    column = table.geom_column or "geom"
    q = QSqlQuery(db)
    q.prepare(
        render_sql(
            EXISTS_SQL,
            table=table.qualified,
            column=quote_ident(column),
        )
    )
    if not q.exec():
        return True
    if q.next():
        try:
            return bool(q.value(0))
        except (TypeError, ValueError):
            return True
    return True