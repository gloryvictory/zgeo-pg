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

TABLE_OF = {
    KIND_SPATIAL: "spatial_checks",
    KIND_ATTRIBUTE: "attribute_checks",
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

    for table in TABLE_OF.values():
        query = QSqlQuery(db)
        if not query.exec(
            'CREATE TABLE IF NOT EXISTS "{table}" ({columns})'.format(
                table=table, columns=COLUMNS
            )
        ):
            return False
        index = QSqlQuery(db)
        index.exec(
            'CREATE INDEX IF NOT EXISTS "{table}_check_idx" '
            'ON "{table}" ("check_key", "id")'.format(table=table)
        )
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
        query.prepare(
            'INSERT INTO "{table}" ("run_id", "connection", "schema", '
            '"table_name", "check_key", "check_title", "problems", "error") '
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)".format(table=table)
        )
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


def history(kind: str, check_key: str = "", limit: int = 300) -> List[CheckRecord]:
    """Последние записи истории, при желании только по одной проверке."""

    table = TABLE_OF.get(kind)
    if table is None:
        return []
    if check_key:
        sql = (
            'SELECT {columns} FROM "{table}" WHERE "check_key" = ? '
            'ORDER BY "id" DESC LIMIT ?'
        ).format(columns=SELECT_COLUMNS, table=table)
        return _records(sql, (check_key, int(limit)))
    sql = 'SELECT {columns} FROM "{table}" ORDER BY "id" DESC LIMIT ?'.format(
        columns=SELECT_COLUMNS, table=table
    )
    return _records(sql, (int(limit),))


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
        'SELECT "check_key", max("check_title") FROM "{table}" '
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


def series(kind: str, check_key: str = "", limit: int = 30) -> List[Tuple[str, int]]:
    """Динамика: сумма проблем по прогонам, от старых к новым."""

    table = TABLE_OF.get(kind)
    if table is None:
        return []
    db = _open()
    if db is None:
        return []
    query = QSqlQuery(db)
    if check_key:
        query.prepare(
            'SELECT min("created"), sum("problems") FROM "{table}" '
            'WHERE "check_key" = ? GROUP BY "run_id" '
            'ORDER BY min("id") DESC LIMIT ?'.format(table=table)
        )
        query.addBindValue(check_key)
    else:
        query.prepare(
            'SELECT min("created"), sum("problems") FROM "{table}" '
            'GROUP BY "run_id" ORDER BY min("id") DESC LIMIT ?'.format(table=table)
        )
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


def clear(kind: str) -> bool:
    """Удалить историю проверок указанного вида."""

    table = TABLE_OF.get(kind)
    if table is None:
        return False
    db = _open()
    if db is None:
        return False
    query = QSqlQuery(db)
    return bool(query.exec('DELETE FROM "{table}"'.format(table=table)))
