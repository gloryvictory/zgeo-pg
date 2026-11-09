"""Чтение каталога пространственных таблиц из базы PostGIS.

Модуль не зависит от виджетов и может тестироваться без интерфейса.
Поиск таблиц ведётся через представления geometry_columns и
geography_columns PostGIS.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from qgis.PyQt.QtSql import QSqlQuery

from .i18n import tr

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
    total_size: Optional[int] = None
    has_geometry: bool = True

    @property
    def qualified(self) -> str:
        return '"' + self.schema + '"."' + self.name + '"'

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


def fetch_spatial_tables(db, schemas: Optional[List[str]] = None) -> List[SpatialTable]:
    """Получить список пространственных таблиц из PostGIS.

    Args:
        db: Открытое соединение QtSql.
        schemas: Если задано — только таблицы из этих схем.

    Returns:
        Список SpatialTable, отсортированный по схеме и имени.
    """

    rows: List[SpatialTable] = []
    for spatial_type, view in (
        ("geometry", "geometry_columns"),
        ("geography", "geography_columns"),
    ):
        column = (
            "f_geometry_column" if spatial_type == "geometry" else "f_geography_column"
        )
        sql = (
            "SELECT "
            + view + ".f_table_schema, "
            + view + ".f_table_name, "
            + view + "." + column + ", "
            + view + ".type, "
            + view + ".srid, "
            + "COALESCE(c.reltuples, 0)::bigint AS estimated "
            + "FROM " + view + " "
            + "LEFT JOIN pg_catalog.pg_class c "
            + "  ON c.relname = " + view + ".f_table_name "
            + "WHERE c.relnamespace = ("
            + "  SELECT n.oid FROM pg_catalog.pg_namespace n "
            + "  WHERE n.nspname = " + view + ".f_table_schema"
            + ")"
        )
        if schemas:
            where = " AND " + view + ".f_table_schema IN ("
            for index, _schema in enumerate(schemas):
                if index:
                    where += ", "
                where += "?"
            where += ")"
            sql += where

        q = QSqlQuery(db)
        q.prepare(sql)
        if schemas:
            for schema in schemas:
                q.addBindValue(schema)
        if not q.exec():
            continue  # представление отсутствует в старых версиях PostGIS

        while q.next():
            schema = str(q.value(0) or "")
            name = str(q.value(1) or "")
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
                )
            )

    rows.sort()
    return rows


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


def count_rows(db, table: SpatialTable) -> int:
    """Точное количество строк в таблице."""
    q = QSqlQuery(db)
    q.prepare("SELECT count(*) FROM " + table.qualified)
    if not q.exec():
        return 0
    if q.next():
        try:
            return int(q.value(0) or 0)
        except (TypeError, ValueError):
            return 0
    return 0


def table_size(db, table: SpatialTable) -> Optional[int]:
    """Полный размер таблицы с индексами и TOAST."""
    q = QSqlQuery(db)
    q.prepare("SELECT pg_total_relation_size('" + table.qualified + "'::regclass)")
    if not q.exec():
        return None
    if q.next():
        try:
            return int(q.value(0) or 0)
        except (TypeError, ValueError):
            return None
    return None


def geometry_has_data(db, table: SpatialTable) -> bool:
    """Проверить, что в столбце геометрии есть ненулевые объекты."""
    column = table.geom_column or "geom"
    q = QSqlQuery(db)
    q.prepare(
        "SELECT EXISTS (SELECT 1 FROM "
        + table.qualified
        + " WHERE "
        + column
        + " IS NOT NULL AND NOT ST_IsEmpty("
        + column
        + "))"
    )
    if not q.exec():
        return True
    if q.next():
        try:
            return bool(q.value(0))
        except (TypeError, ValueError):
            return True
    return True