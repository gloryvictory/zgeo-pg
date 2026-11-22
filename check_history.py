"""История проверок качества в локальной базе SQLite профиля QGIS.

Пространственные и атрибутивные проверки пишутся в разные таблицы, чтобы
статистика по ним не смешивалась. Модуль использует собственное именованное
соединение QtSql к тому же файлу, что и сохранённые подключения, поэтому не
мешает работе с соединениями.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from qgis.PyQt.QtSql import QSqlDatabase, QSqlQuery

from .connection import sqlite_path

DRIVER = "QSQLITE"
CONNECTION = "zgeopg_history"
BUSY_TIMEOUT = 5000

KIND_SPATIAL = "spatial"
KIND_ATTRIBUTE = "attribute"

SPATIAL_TABLE = "spatial_checks"
ATTRIBUTE_TABLE = "attribute_checks"

TABLE_OF = {
    KIND_SPATIAL: SPATIAL_TABLE,
    KIND_ATTRIBUTE: ATTRIBUTE_TABLE,
}

COLUMNS = (
    '"id" INTEGER PRIMARY KEY AUTOINCREMENT, '
    '"run_id" TEXT NOT NULL, '
    '"created" TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, '
    '"connection" TEXT NOT NULL DEFAULT \'\', '
    '"schema" TEXT NOT NULL DEFAULT \'\', '
    '"table_name" TEXT NOT NULL DEFAULT \'\', '
    '"check_key" TEXT NOT NULL, '
    '"check_title" TEXT NOT NULL DEFAULT \'\', '
    '"problems" INTEGER NOT NULL DEFAULT 0, '
    '"error" TEXT NOT NULL DEFAULT \'\''
)

SELECT_COLUMNS = (
    '"id", "run_id", "created", "connection", "schema", '
    '"table_name", "check_key", "check_title", "problems", "error"'
)

# Готовые тексты INSERT: целиком константы, значения передаются связанными
# параметрами, поэтому запрос не собирается из данных пользователя.
SPATIAL_INSERT_SQL = (
    'INSERT INTO "spatial_checks" ("run_id", "connection", "schema", '
    '"table_name", "check_key", "check_title", "problems", "error") '
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
)

ATTRIBUTE_INSERT_SQL = (
    'INSERT INTO "attribute_checks" ("run_id", "connection", "schema", '
    '"table_name", "check_key", "check_title", "problems", "error") '
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
)

INSERT_SQL = {
    KIND_SPATIAL: SPATIAL_INSERT_SQL,
    KIND_ATTRIBUTE: ATTRIBUTE_INSERT_SQL,
}


@dataclass(frozen=True)
class CheckRecord:
    """Одна запись истории проверок."""

    run_id: str
    created: str
    connection: str
    schema: str
    table_name: str
    check_key: str
    check_title: str
    problems: int
    error: str

    @property
    def table_full_name(self) -> str:
        return "{}.{}".format(self.schema, self.table_name) if self.schema else self.table_name


def _open() -> Optional[QSqlDatabase]:
    """Открыть (один раз) базу истории проверок."""

    if DRIVER not in [str(name) for name in QSqlDatabase.drivers()]:
        return None

    if QSqlDatabase.contains(CONNECTION):
        db = QSqlDatabase.database(CONNECTION, open=True)
        if db.isOpen():
            return db
        QSqlDatabase.removeDatabase(CONNECTION)

    path = Path(sqlite_path())
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None

    db = QSqlDatabase.addDatabase(DRIVER, CONNECTION)
    db.setDatabaseName(str(path))
    db.setConnectOptions("QSQLITE_BUSY_TIMEOUT={}".format(BUSY_TIMEOUT))
    if not db.open():
        QSqlDatabase.removeDatabase(CONNECTION)
        return None
    if not _ensure_schema(db):
        db.close()
        QSqlDatabase.removeDatabase(CONNECTION)
        return None
    return db


def _ensure_schema(db) -> bool:
    """Создать таблицы истории, если их ещё нет."""

    # Имена таблиц и столбцов — константы модуля, внешних данных в тексте
    # запросов нет.
    statements = (
        'CREATE TABLE IF NOT EXISTS "{table}" ({columns})'.format(
            table=SPATIAL_TABLE, columns=COLUMNS
        ),
        'CREATE TABLE IF NOT EXISTS "{table}" ({columns})'.format(
            table=ATTRIBUTE_TABLE, columns=COLUMNS
        ),
        'CREATE INDEX IF NOT EXISTS "{table}_check_idx" '
        'ON "{table}" ("check_key", "id")'.format(table=SPATIAL_TABLE),
        'CREATE INDEX IF NOT EXISTS "{table}_check_idx" '
        'ON "{table}" ("check_key", "id")'.format(table=ATTRIBUTE_TABLE),
    )
    for statement in statements:
        query = QSqlQuery(db)
        if not query.exec(statement):
            return False
    return True


def record_run(
    kind: str,
    run_id: str,
    connection_name: str,
    rows: Sequence[Tuple[str, str, str, str, object, str]],
) -> int:
    """Сохранить результаты прогона проверок.

    Args:
        kind: ``spatial`` или ``attribute``.
        run_id: метка прогона, одна на все строки одного запуска.
        connection_name: имя соединения, по которому шли проверки.
        rows: (схема, таблица, ключ проверки, название, число проблем, ошибка).

    Returns:
        Сколько строк удалось записать.
    """

    table = TABLE_OF.get(kind)
    if table is None or not rows:
        return 0
    db = _open()
    if db is None:
        return 0

    written = 0
    for schema, table_name, check_key, title, problems, error in rows:
        query = QSqlQuery(db)
        query.prepare(INSERT_SQL[kind])
        query.addBindValue(run_id)
        query.addBindValue(connection_name)
        query.addBindValue(schema)
        query.addBindValue(table_name)
        query.addBindValue(check_key)
        query.addBindValue(title)
        query.addBindValue(int(problems) if problems is not None else 0)
        query.addBindValue(error or "")
        if query.exec():
            written += 1
    return written


def _records(sql: str, bindings: Sequence[object] = ()) -> List[CheckRecord]:
    db = _open()
    if db is None:
        return []
    query = QSqlQuery(db)
    query.prepare(sql)
    for value in bindings:
        query.addBindValue(value)
    if not query.exec():
        return []
    records: List[CheckRecord] = []
    while query.next():
        try:
            problems = int(query.value(8) or 0)
        except (TypeError, ValueError):
            problems = 0
        records.append(
            CheckRecord(
                run_id=str(query.value(1) or ""),
                created=str(query.value(2) or ""),
                connection=str(query.value(3) or ""),
                schema=str(query.value(4) or ""),
                table_name=str(query.value(5) or ""),
                check_key=str(query.value(6) or ""),
                check_title=str(query.value(7) or ""),
                problems=problems,
                error=str(query.value(9) or ""),
            )
        )
    return records


def _filter(check_key: str = "", layer: str = "") -> Tuple[str, List[object]]:
    """Собрать WHERE-условие по проверке и слою (схема.таблица)."""

    clauses: List[str] = []
    bindings: List[object] = []
    if check_key:
        clauses.append('"check_key" = ?')
        bindings.append(check_key)
    if layer:
        schema, _, name = layer.partition(".")
        if schema and name:
            clauses.append('"schema" = ? AND "table_name" = ?')
            bindings.extend([schema, name])
        else:
            clauses.append('"table_name" = ?')
            bindings.append(layer)
    if not clauses:
        return "", []
    return " WHERE " + " AND ".join(clauses), bindings


def history(
    kind: str,
    check_key: str = "",
    layer: str = "",
    limit: int = 300,
) -> List[CheckRecord]:
    """Последние записи истории, при желании только по проверке и слою."""

    table = TABLE_OF.get(kind)
    if table is None:
        return []
    where, bindings = _filter(check_key, layer)
    sql = 'SELECT {columns} FROM "{table}"{where} ORDER BY "id" DESC LIMIT ?'.format(  # nosec B608
        columns=SELECT_COLUMNS, table=table, where=where
    )
    return _records(sql, list(bindings) + [int(limit)])


def layers(kind: str) -> List[str]:
    """Слои (схема.таблица), встречавшиеся в истории проверок."""

    table = TABLE_OF.get(kind)
    if table is None:
        return []
    db = _open()
    if db is None:
        return []
    query = QSqlQuery(db)
    sql = (
        'SELECT DISTINCT "schema", "table_name" FROM "{table}" '  # nosec B608 - только кавыченные идентификаторы и константы
        'ORDER BY "schema", "table_name"'
    ).format(table=table)
    if not query.exec(sql):
        return []
    names: List[str] = []
    while query.next():
        schema = str(query.value(0) or "")
        name = str(query.value(1) or "")
        if not name:
            continue
        names.append(schema + "." + name if schema else name)
    return names


def check_keys(kind: str) -> List[Tuple[str, str]]:
    """Пары (ключ, название) проверок, встречавшихся в истории."""

    table = TABLE_OF.get(kind)
    if table is None:
        return []
    db = _open()
    if db is None:
        return []
    query = QSqlQuery(db)
    sql = (
        'SELECT "check_key", max("check_title") FROM "{table}" '  # nosec B608 - только кавыченные идентификаторы и константы
        'GROUP BY "check_key" ORDER BY "check_key"'
    ).format(table=table)
    if not query.exec(sql):
        return []
    pairs: List[Tuple[str, str]] = []
    while query.next():
        key = str(query.value(0) or "")
        if key:
            pairs.append((key, str(query.value(1) or key)))
    return pairs


def series(
    kind: str,
    check_key: str = "",
    layer: str = "",
    limit: int = 30,
) -> List[Tuple[str, int]]:
    """Динамика: сумма проблем по прогонам, от старых к новым."""

    table = TABLE_OF.get(kind)
    if table is None:
        return []
    db = _open()
    if db is None:
        return []
    where, bindings = _filter(check_key, layer)
    query = QSqlQuery(db)
    query.prepare(
        'SELECT min("created"), sum("problems") FROM "{table}"{where} '  # nosec B608 - только кавыченные идентификаторы и константы
        'GROUP BY "run_id" ORDER BY min("id") DESC LIMIT ?'.format(
            table=table, where=where
        )
    )
    for value in bindings:
        query.addBindValue(value)
    query.addBindValue(int(limit))
    if not query.exec():
        return []
    points: List[Tuple[str, int]] = []
    while query.next():
        created = str(query.value(0) or "")
        try:
            total = int(query.value(1) or 0)
        except (TypeError, ValueError):
            total = 0
        points.append((created, total))
    points.reverse()
    return points


def _run_ids(kind: str, count: int, check_key: str = "", layer: str = "") -> List[str]:
    """Метки последних прогонов, от нового к старому."""

    table = TABLE_OF.get(kind)
    if table is None:
        return []
    db = _open()
    if db is None:
        return []
    where, bindings = _filter(check_key, layer)
    query = QSqlQuery(db)
    query.prepare(
        'SELECT "run_id" FROM "{table}"{where} GROUP BY "run_id" '  # nosec B608 - только кавыченные идентификаторы и константы
        'ORDER BY min("id") DESC LIMIT ?'.format(table=table, where=where)
    )
    for value in bindings:
        query.addBindValue(value)
    query.addBindValue(int(count))
    if not query.exec():
        return []
    runs: List[str] = []
    while query.next():
        run_id = str(query.value(0) or "")
        if run_id:
            runs.append(run_id)
    return runs


def _run_totals(
    kind: str,
    run_id: str,
    check_key: str = "",
    layer: str = "",
) -> List[Tuple[str, str, int]]:
    """Суммы проблем по проверкам одного прогона: (ключ, название, сумма)."""

    table = TABLE_OF.get(kind)
    if table is None or not run_id:
        return []
    db = _open()
    if db is None:
        return []
    where, bindings = _filter(check_key, layer)
    separator = " AND " if where else " WHERE "
    query = QSqlQuery(db)
    query.prepare(
        'SELECT "check_key", max("check_title"), sum("problems") FROM "{table}"'  # nosec B608 - только кавыченные идентификаторы и константы
        '{where}{separator}"run_id" = ? GROUP BY "check_key"'.format(
            table=table, where=where, separator=separator
        )
    )
    for value in bindings:
        query.addBindValue(value)
    query.addBindValue(run_id)
    if not query.exec():
        return []
    totals: List[Tuple[str, str, int]] = []
    while query.next():
        key = str(query.value(0) or "")
        if not key:
            continue
        try:
            total = int(query.value(2) or 0)
        except (TypeError, ValueError):
            total = 0
        totals.append((key, str(query.value(1) or key), total))
    return totals


def compare_runs(
    kind: str,
    check_key: str = "",
    layer: str = "",
) -> List[Tuple[str, str, Optional[int], Optional[int]]]:
    """Было/стало: суммы проблем последнего и предыдущего прогонов.

    Returns:
        Список (ключ, название, было, стало). ``None`` означает, что проверки
        не было в соответствующем прогоне.
    """

    runs = _run_ids(kind, 2, check_key, layer)
    if not runs:
        return []
    current = dict(
        (key, (title, total))
        for key, title, total in _run_totals(kind, runs[0], check_key, layer)
    )
    previous: dict = {}
    if len(runs) > 1:
        previous = dict(
            (key, (title, total))
            for key, title, total in _run_totals(kind, runs[1], check_key, layer)
        )

    rows: List[Tuple[str, str, Optional[int], Optional[int]]] = []
    for key in sorted(set(current) | set(previous)):
        title = (current.get(key) or previous.get(key))[0]
        was = previous[key][1] if key in previous else None
        now = current[key][1] if key in current else None
        rows.append((key, title, was, now))
    return rows


def clear(kind: str) -> bool:
    """Удалить историю проверок указанного вида."""

    table = TABLE_OF.get(kind)
    if table is None:
        return False
    db = _open()
    if db is None:
        return False
    query = QSqlQuery(db)
    return bool(query.exec('DELETE FROM "{table}"'.format(table=table)))  # nosec B608 - только кавыченные идентификаторы и константы
