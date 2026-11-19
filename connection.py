"""Работа с подключениями к базе PostgreSQL / PostGIS.

Модуль использует встроенный драйвер QPSQL из Qt, поэтому не требует
дополнительных зависимостей. Сохранённые соединения пишутся и в настройки
QGIS, и в локальную базу SQLite профиля QGIS, поэтому параметры подключения
(включая пароль) доступны в следующем сеансе.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from qgis.PyQt.QtCore import QSettings, QStandardPaths
from qgis.PyQt.QtSql import QSqlDatabase, QSqlQuery

from .i18n import tr

SETTINGS_PREFIX = "zgeopg/connections"
LAST_CONNECTION_KEY = "zgeopg/last_connection"

SQLITE_DRIVER = "QSQLITE"
SQLITE_CONNECTION = "zgeopg_sqlite"
SQLITE_DIR_NAME = "zgeo-pg"
SQLITE_FILE_NAME = "connections.sqlite"
SQLITE_TIMEOUT = 5

FIELDS = ("host", "port", "database", "user", "password")


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


def sqlite_path() -> Path:
    """Путь к локальной базе SQLite с параметрами подключений."""

    base = ""
    try:
        from qgis.core import QgsApplication

        base = QgsApplication.qgisSettingsDirPath() or ""
    except Exception:  # noqa: BLE001 - вне QGIS используем стандартный путь
        base = ""
    if not base:
        base = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )
    if not base:
        base = str(Path.home())
    return Path(base) / SQLITE_DIR_NAME / SQLITE_FILE_NAME


def _sqlite_db() -> Optional[QSqlDatabase]:
    """Открыть (один раз) базу SQLite с сохранёнными соединениями."""

    if SQLITE_DRIVER not in [str(name) for name in QSqlDatabase.drivers()]:
        return None

    if QSqlDatabase.contains(SQLITE_CONNECTION):
        db = QSqlDatabase.database(SQLITE_CONNECTION, open=True)
        if db.isOpen():
            return db
        QSqlDatabase.removeDatabase(SQLITE_CONNECTION)

    path = Path(sqlite_path())
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None

    db = QSqlDatabase.addDatabase(SQLITE_DRIVER, SQLITE_CONNECTION)
    db.setDatabaseName(str(path))
    db.setConnectOptions(f"QSQLITE_BUSY_TIMEOUT={SQLITE_TIMEOUT * 1000}")
    if not db.open():
        QSqlDatabase.removeDatabase(SQLITE_CONNECTION)
        return None
    if not _ensure_sqlite_schema(db):
        db.close()
        QSqlDatabase.removeDatabase(SQLITE_CONNECTION)
        return None
    return db


def _ensure_sqlite_schema(db: QSqlDatabase) -> bool:
    statements = (
        'CREATE TABLE IF NOT EXISTS "connections" ('
        '"name" TEXT PRIMARY KEY NOT NULL, '
        '"host" TEXT NOT NULL DEFAULT \'localhost\', '
        '"port" INTEGER NOT NULL DEFAULT 5432, '
        '"database" TEXT NOT NULL DEFAULT \'\', '
        '"user" TEXT NOT NULL DEFAULT \'postgres\', '
        '"password" TEXT NOT NULL DEFAULT \'\', '
        '"updated" TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)',
        'CREATE TABLE IF NOT EXISTS "settings" ('
        '"key" TEXT PRIMARY KEY NOT NULL, '
        '"value" TEXT NOT NULL DEFAULT \'\')',
    )
    for statement in statements:
        query = QSqlQuery(db)
        if not query.exec(statement):
            return False
    return True


def _sqlite_save(conn: PGConnection) -> bool:
    db = _sqlite_db()
    if db is None:
        return False
    query = QSqlQuery(db)
    query.prepare(
        'INSERT INTO "connections" ("name", "host", "port", "database", "user", "password", "updated") '
        "VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP) "
        'ON CONFLICT("name") DO UPDATE SET "host" = excluded."host", '
        '"port" = excluded."port", "database" = excluded."database", '
        '"user" = excluded."user", "password" = excluded."password", '
        '"updated" = CURRENT_TIMESTAMP'
    )
    query.addBindValue(conn.name)
    query.addBindValue(conn.host)
    query.addBindValue(int(conn.port))
    query.addBindValue(conn.database)
    query.addBindValue(conn.user)
    query.addBindValue(conn.password)
    return bool(query.exec())


def _sqlite_delete(name: str) -> bool:
    db = _sqlite_db()
    if db is None:
        return False
    query = QSqlQuery(db)
    query.prepare('DELETE FROM "connections" WHERE "name" = ?')
    query.addBindValue(name)
    return bool(query.exec())


def _sqlite_records() -> List[PGConnection]:
    db = _sqlite_db()
    if db is None:
        return []
    query = QSqlQuery(db)
    if not query.exec(
        'SELECT "name", "host", "port", "database", "user", "password" '
        'FROM "connections" ORDER BY "name"'
    ):
        return []
    records: List[PGConnection] = []
    while query.next():
        name = str(query.value(0) or "")
        if not name:
            continue
        try:
            port = int(query.value(2) or 5432)
        except (TypeError, ValueError):
            port = 5432
        records.append(
            PGConnection(
                name=name,
                host=str(query.value(1) or "localhost"),
                port=port,
                database=str(query.value(3) or ""),
                user=str(query.value(4) or "postgres"),
                password=str(query.value(5) or ""),
            )
        )
    return records


def _write_settings(conn: PGConnection) -> None:
    settings = QSettings()
    settings.beginGroup(SETTINGS_PREFIX)
    settings.beginGroup(conn.name)
    try:
        for field in FIELDS:
            settings.setValue(field, getattr(conn, field))
    finally:
        settings.endGroup()
        settings.endGroup()


def _set_sqlite_setting(key: str, value: str) -> None:
    db = _sqlite_db()
    if db is None:
        return
    query = QSqlQuery(db)
    query.prepare(
        'INSERT INTO "settings" ("key", "value") VALUES (?, ?) '
        'ON CONFLICT("key") DO UPDATE SET "value" = excluded."value"'
    )
    query.addBindValue(key)
    query.addBindValue(value)
    query.exec()


def _sqlite_setting(key: str) -> str:
    db = _sqlite_db()
    if db is None:
        return ""
    query = QSqlQuery(db)
    query.prepare('SELECT "value" FROM "settings" WHERE "key" = ?')
    query.addBindValue(key)
    if not query.exec() or not query.next():
        return ""
    return str(query.value(0) or "")


def remember_last_connection(name: str) -> None:
    """Запомнить имя последнего использованного соединения."""

    QSettings().setValue(LAST_CONNECTION_KEY, name)
    _set_sqlite_setting(LAST_CONNECTION_KEY, name)


def last_connection_name() -> str:
    """Имя последнего сохранённого соединения: SQLite, затем настройки QGIS."""

    name = _sqlite_setting(LAST_CONNECTION_KEY)
    if name:
        return name
    return str(QSettings().value(LAST_CONNECTION_KEY, "") or "")


def sync_connections_from_sqlite() -> List[str]:
    """Перенести соединения из SQLite в настройки QGIS и вернуть их имена.

    Вызывается при загрузке плагина: если SQLite недоступна, работают
    соединения, уже сохранённые в настройках QGIS.
    """

    names: List[str] = []
    for conn in _sqlite_records():
        _write_settings(conn)
        names.append(conn.name)
    return names


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
    """Загрузить соединение по имени из настроек QGIS или из SQLite."""
    settings = QSettings()
    settings.beginGroup(SETTINGS_PREFIX)
    settings.beginGroup(name)
    try:
        has_settings = bool(settings.childKeys())
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

    if has_settings:
        return PGConnection(
            name, str(host), port, str(database), str(user), str(password)
        )

    for conn in _sqlite_records():
        if conn.name == name:
            _write_settings(conn)
            return conn
    return None


def save_connection(conn: PGConnection) -> bool:
    """Сохранить соединение в настройках QGIS и в локальной базе SQLite.

    Returns:
        True, если параметры удалось записать в SQLite.
    """
    _write_settings(conn)
    remember_last_connection(conn.name)
    return _sqlite_save(conn)


def delete_connection(name: str) -> None:
    """Удалить сохранённое соединение из настроек QGIS и из SQLite."""
    settings = QSettings()
    settings.beginGroup(SETTINGS_PREFIX)
    try:
        settings.remove(name)
    finally:
        settings.endGroup()
    _sqlite_delete(name)


def _connection_name(conn: PGConnection, tag: Optional[str] = None) -> str:
    base = f"zgeopg_{conn.name or conn.qualified}"
    return f"{base}_{tag}" if tag else base


def open_connection(conn: PGConnection, tag: Optional[str] = None) -> QSqlDatabase:
    """Открыть соединение QtSql к базе данных.

    Args:
        conn: параметры подключения.
        tag: суффикс имени соединения QtSql. Фоновые потоки передают свой
            тег, чтобы работать с отдельным соединением и не закрыть то,
            которым пользуется интерфейс.

    Raises:
        RuntimeError: Если драйвер QPSQL недоступен или подключение не удалось.
    """
    available = [str(name) for name in QSqlDatabase.drivers()]
    if "QPSQL" not in available:
        raise RuntimeError(tr("Драйвер QPSQL не найден"))

    db_name = _connection_name(conn, tag)
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


def close_connection(conn: PGConnection, tag: Optional[str] = None) -> None:
    """Закрыть и удалить соединение QtSql (или соединение потока с тегом).

    Ссылка на QSqlDatabase удаляется до removeDatabase: пока объект жив, Qt
    предупреждает «connection is still in use» и обрывает все запросы этого
    соединения, из-за чего вкладка НСИ падала при переключении подключения.
    """

    db_name = _connection_name(conn, tag)
    if not QSqlDatabase.contains(db_name):
        return
    db = QSqlDatabase.database(db_name, open=False)
    if db.isOpen():
        db.close()
    del db
    QSqlDatabase.removeDatabase(db_name)


def _exec(db, query: str):
    from qgis.PyQt.QtSql import QSqlQuery

    q = QSqlQuery(db)
    if not q.exec(query):
        raise RuntimeError(tr("Ошибка запроса") + f": {q.lastError().text()}")
    return q