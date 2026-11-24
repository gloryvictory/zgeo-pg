"""Сверка НСИ: сравнение уникальных значений двух таблиц.

Модуль даёт всё, что нужно вкладке «Качество по НСИ»: список таблиц базы,
список текстовых столбцов таблицы, отсортированные уникальные значения и
сравнение двух наборов значений. Работает через QtSql, поэтому одинаково
подходит для любой базы PostgreSQL, доступной плагину.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from qgis.PyQt.QtSql import QSqlQuery

from .catalog import quote_ident, render_sql
# Тексты ошибок запросов и пометка прав доступа общие для модулей плагина.
from .sql_errors import query_error

# Защита от «разгона» памяти на больших справочниках.
VALUE_LIMIT = 100000

# Служебные таблицы PostGIS и pgAdmin: в справочниках они только мешают.
# Список — часть строковой константы запроса ниже.
TABLES_SQL = (
    "SELECT n.nspname, c.relname "
    "FROM pg_catalog.pg_class c "
    "JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace "
    "WHERE c.relkind IN ('r', 'p', 'v', 'm', 'f') "
    "  AND n.nspname NOT IN ('pg_catalog', 'information_schema') "
    "  AND n.nspname NOT LIKE 'pg\\_toast%' "
    "  AND n.nspname NOT LIKE 'pg\\_temp%' "
    "  AND pg_catalog.has_table_privilege(c.oid, 'SELECT') "
    "  AND c.relname NOT IN ("
    "'geometry_columns', 'geography_columns', 'spatial_ref_sys', "
    "'raster_columns', 'raster_overviews') "
    "ORDER BY n.nspname, c.relname"
)

COLUMNS_SQL = (
    "SELECT a.attname "
    "FROM pg_catalog.pg_attribute a "
    "JOIN pg_catalog.pg_class c ON c.oid = a.attrelid "
    "JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace "
    "JOIN pg_catalog.pg_type t ON t.oid = a.atttypid "
    "WHERE n.nspname = ? AND c.relname = ? "
    "  AND a.attnum > 0 AND NOT a.attisdropped "
    "  AND t.typname IN ('varchar', 'bpchar', 'text', 'char', 'citext', 'name') "
    "ORDER BY a.attnum"
)


COUNT_SQL = (
    "SELECT count(*) "
    "FROM pg_catalog.pg_class c "
    "JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace "
    "WHERE c.relkind IN ('r', 'p', 'v', 'm', 'f') "
    "  AND n.nspname NOT IN ('pg_catalog', 'information_schema') "
    "  AND n.nspname NOT LIKE 'pg\\_toast%' "
    "  AND n.nspname NOT LIKE 'pg\\_temp%'"
)

UNFILTERED_TABLES_SQL = (
    COUNT_SQL.replace("count(*)", "n.nspname, c.relname")
    + " ORDER BY n.nspname, c.relname"
)


def _read_tables(query, sql: str) -> List[Tuple[str, str]]:
    """Выполнить запрос списка таблиц и собрать пары (схема, имя)."""

    tables: List[Tuple[str, str]] = []
    if not query.exec(sql):
        raise RuntimeError(query_error(query))
    while query.next():
        schema = str(query.value(0) or "")
        name = str(query.value(1) or "")
        if schema and name:
            tables.append((schema, name))
    return tables




def list_tables(db) -> Tuple[List[Tuple[str, str]], int, int]:
    """Таблицы для выбора в справочнике и счётчики для диагностики.

    Возвращает ``(таблицы, всего_в_базе, читаемых)``. Сначала берутся только
    читаемые таблицы: выбор таблицы без права SELECT всё равно закончился бы
    ошибкой. Если читаемых нет, а таблицы в базе есть, список отдаётся целиком
    — пустой выпадающий список не объясняет причину, а ошибка по конкретной
    таблице объясняет.
    """

    readable = _read_tables(QSqlQuery(db), TABLES_SQL)
    if readable:
        return readable, len(readable), len(readable)
    query = QSqlQuery(db)
    total = 0
    if query.exec(COUNT_SQL) and query.next():
        try:
            total = int(query.value(0) or 0)
        except (TypeError, ValueError):
            total = 0
    if not total:
        return [], 0, 0
    return _read_tables(QSqlQuery(db), UNFILTERED_TABLES_SQL), total, 0



def list_text_columns(db, schema: str, name: str) -> List[str]:
    """Текстовые столбцы таблицы в порядке объявления.

    Raises:
        RuntimeError: если столбцы прочитать не удалось.
    """

    query = QSqlQuery(db)
    query.prepare(COLUMNS_SQL)
    query.addBindValue(schema)
    query.addBindValue(name)
    columns: List[str] = []
    if not query.exec():
        raise RuntimeError(query_error(query, schema + "." + name))
    while query.next():
        column = str(query.value(0) or "")
        if column:
            columns.append(column)
    return columns


def unique_values_sql(schema: str, name: str, column: str, limit: int) -> str:
    """SQL отсортированного списка уникальных значений столбца."""

    return render_sql(
        "SELECT DISTINCT {column}::text AS value FROM {table} "
        "WHERE {column} IS NOT NULL ORDER BY 1 LIMIT {limit}",
        column=quote_ident(column),
        table=quote_ident(schema) + "." + quote_ident(name),
        limit=int(limit),
    )


def fetch_unique_values(
    db,
    schema: str,
    name: str,
    column: str,
    limit: int = VALUE_LIMIT,
) -> List[str]:
    """Отсортированный список уникальных значений столбца.

    Raises:
        RuntimeError: если запрос не выполнился.
    """

    query = QSqlQuery(db)
    if not query.exec(unique_values_sql(schema, name, column, limit)):
        raise RuntimeError(query_error(query, schema + "." + name))
    values: List[str] = []
    while query.next():
        values.append(str(query.value(0) or ""))
    return values


@dataclass
class NsiComparison:
    """Результат сверки: совпадения и различия двух наборов значений."""

    matched: List[str] = field(default_factory=list)
    left_only: List[str] = field(default_factory=list)
    right_only: List[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.matched) + len(self.left_only) + len(self.right_only)


def compare_values(left: Sequence[str], right: Sequence[str]) -> NsiComparison:
    """Сравнить два набора значений; результат отсортирован по значениям."""

    left_set = {value for value in left if value != ""}
    right_set = {value for value in right if value != ""}
    return NsiComparison(
        matched=sorted(left_set & right_set),
        left_only=sorted(left_set - right_set),
        right_only=sorted(right_set - left_set),
    )
