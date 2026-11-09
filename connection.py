"""Работа с подключениями к базе PostgreSQL / PostGIS.

Модуль использует встроенный драйвер QPSQL из Qt, поэтому не требует
дополнительных зависимостей. Сохранённые соединения хранятся в настройках
QGIS; пароли — только в открытой сессии.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtSql import QSqlDatabase

from .i18n import tr

SETTINGS_PREFIX = "zgeopg/connections"


@dataclass
class PGConnection:
    """Параметры подключения к базе данных."""

    name: str
    host: str = "localhost"
    port: int = 5432
    database: str = ""
    user: str = "postgres"
    password: str = ""

    @property
    def qualified(self) -> str:
        return f"{self.host}:{self.port}/{self.database}"


def list_saved_connections() -> List[str]:
    """Вернуть имена сохранённых соединений."""
    settings = QSettings()
    settings.beginGroup(SETTINGS_PREFIX)
    try:
        names = settings.childGroups()
    finally:
        settings.endGroup()
    return names


def load_connection(name: str) -> Optional[PGConnection]:
    """Загрузить соединение по имени из настроек QGIS."""
    settings = QSettings()
    settings.beginGroup(SETTINGS_PREFIX)
    settings.beginGroup(name)
    try:
        host = settings.value("host", "localhost")
        try:
            port = int(settings.value("port", 5432) or 5432)
        except (TypeError, ValueError):
            port = 5432
        database = settings.value("database", "") or ""
        user = settings.value("user", "postgres") or "postgres"
        password = settings.value("password", "") or ""
    finally:
        settings.endGroup()
        settings.endGroup()
    return PGConnection(name, str(host), port, str(database), str(user), str(password))


def save_connection(conn: PGConnection) -> None:
    """Сохранить соединение в настройках QGIS."""
    settings = QSettings()
    settings.beginGroup(SETTINGS_PREFIX)
    settings.beginGroup(conn.name)
    try:
        settings.setValue("host", conn.host)
        settings.setValue("port", conn.port)
        settings.setValue("database", conn.database)
        settings.setValue("user", conn.user)
        settings.setValue("password", conn.password)
    finally:
        settings.endGroup()
        settings.endGroup()


def delete_connection(name: str) -> None:
    """Удалить сохранённое соединение."""
    settings = QSettings()
    settings.beginGroup(SETTINGS_PREFIX)
    try:
        settings.remove(name)
    finally:
        settings.endGroup()


def _connection_name(conn: PGConnection) -> str:
    return f"zgeopg_{conn.name or conn.qualified}"


def open_connection(conn: PGConnection) -> QSqlDatabase:
    """Открыть соединение QtSql к базе данных.

    Raises:
        RuntimeError: Если драйвер QPSQL недоступен или подключение не удалось.
    """
    available = [str(name) for name in QSqlDatabase.drivers()]
    if "QPSQL" not in available:
        raise RuntimeError(tr("Драйвер QPSQL не найден"))

    db_name = _connection_name(conn)
    if QSqlDatabase.contains(db_name):
        db = QSqlDatabase.database(db_name, open=True)
        if db.isOpen():
            return db
        QSqlDatabase.removeDatabase(db_name)

    db = QSqlDatabase.addDatabase("QPSQL", db_name)
    db.setHostName(conn.host)
    db.setPort(conn.port)
    db.setDatabaseName(conn.database)
    db.setUserName(conn.user)
    db.setPassword(conn.password)
    db.setConnectOptions("connect_timeout=15")

    if not db.open():
        error = db.lastError().text() if db.lastError().isValid() else ""
        QSqlDatabase.removeDatabase(db_name)
        message = tr("Невозможно подключиться к базе данных")
        if error:
            message += ": " + error
        raise RuntimeError(message)

    # Приводим search_path, чтобы были видны схема postgis и каталог.
    _exec(db, "SET search_path TO public,postgis,topology")

    return db


def close_connection(conn: PGConnection) -> None:
    """Закрыть и удалить соединение QtSql."""
    db_name = _connection_name(conn)
    if QSqlDatabase.contains(db_name):
        db = QSqlDatabase.database(db_name, open=False)
        db.close()
        QSqlDatabase.removeDatabase(db_name)


def _exec(db, query: str):
    from qgis.PyQt.QtSql import QSqlQuery

    q = QSqlQuery(db)
    if not q.exec(query):
        raise RuntimeError(tr("Ошибка запроса") + f": {q.lastError().text()}")
    return q