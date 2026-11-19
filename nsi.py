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

from .catalog import quote_ident
from .i18n import tr

# Защита от «разгона» памяти на больших справочниках.
VALUE_LIMIT = 100000

TABLES_SQL = (
    "SELECT n.nspname, c.relname "
    "FROM pg_catalog.pg_class c "
    "JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace "
    "WHERE c.relkind IN ('r', 'p', 'v', 'm', 'f') "
    "  AND n.nspname NOT IN ('pg_catalog', 'information_schema') "
    "  AND n.nspname NOT LIKE 'pg\\_toast%' "
    "  AND n.nspname NOT LIKE 'pg\\_temp%' "
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


def list_tables(db) -> List[Tuple[str, str]]:
    """Все таблицы и представления базы: список пар (схема, имя)."""

    query = QSqlQuery(db)
    tables: List[Tuple[str, str]] = []
    if not query.exec(TABLES_SQL):
        return tables
    while query.next():
        schema = str(query.value(0) or "")
        name = str(query.value(1) or "")
        if schema and name:
            tables.append((schema, name))
    return tables


def list_text_columns(db, schema: str, name: str) -> List[str]:
    """Текстовые столбцы таблицы в порядке объявления."""

    query = QSqlQuery(db)
    query.prepare(COLUMNS_SQL)
    query.addBindValue(schema)
    query.addBindValue(name)
    columns: List[str] = []
    if not query.exec():
        return columns
    while query.next():
        column = str(query.value(0) or "")
        if column:
            columns.append(column)
    return columns


def unique_values_sql(schema: str, name: str, column: str, limit: int) -> str:
    """SQL отсортированного списка уникальных значений столбца."""

    return (
        "SELECT DISTINCT {column}::text AS value FROM {table} "
        "WHERE {column} IS NOT NULL ORDER BY 1 LIMIT {limit}"
    ).format(
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
        raise RuntimeError(query.lastError().text() or tr("Ошибка запроса"))
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
