"""Проверки качества пространственных данных PostGIS.

Каждая проверка описана декларативно (QualityCheck): название, полное
описание, способ исправления и SQL-шаблон. Шаблон получает имя таблицы и
выражение геометрического столбца, поэтому одна и та же проверка работает
для любой таблицы. Фоновый поток QualityTask выполняет проверки по очереди,
сообщает о ходе работы и умеет прерываться между запросами.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from qgis.PyQt.QtCore import QThread, pyqtSignal
from qgis.PyQt.QtSql import QSqlQuery

from .catalog import SpatialTable, quote_ident
from .connection import PGConnection, close_connection, open_connection
from .i18n import tr

# Типы, для которых имеет смысл проверка "смешанные типы геометрии".
KNOWN_GEOMETRY_TYPES = (
    "POINT",
    "LINESTRING",
    "POLYGON",
    "MULTIPOINT",
    "MULTILINESTRING",
    "MULTIPOLYGON",
)

# Проверка, которая берёт сведения из каталога и не обращается к данным.
CHECK_MISSING_INDEX = "missing_spatial_index"


@dataclass(frozen=True)
class QualityCheck:
    """Описание одной проверки качества данных."""

    key: str
    title: str
    summary: str
    description: str
    fix: str
    sql: Optional[str] = None
    sql_geographic: Optional[str] = None
    needs_srid: bool = False
    needs_type: bool = False
    from_catalog: bool = False


QUALITY_CHECKS: List[QualityCheck] = [
    QualityCheck(
        key="invalid_geometry",
        title="Невалидная геометрия",
        summary="ST_IsValid возвращает false: геометрию нельзя корректно обработать.",
        description=(
            "Проверка ищет объекты, геометрия которых нарушает правила OGC Simple "
            "Features: самопересечения, дыры вне оболочки, незамкнутые кольца, "
            "аномалии вершин. Используется ST_IsValid, а количество таких объектов "
            "показывается в результатах. Невалидная геометрия ломает буферизацию, "
            "наложение, обрезку и экспорт в другие форматы, а часть операций PostGIS "
            "завершается ошибкой GEOS на всей таблице."
        ),
        fix=(
            "Исправить геометрию запросом UPDATE ... SET geom = ST_MakeValid(geom) "
            "или найти объекты и отредактировать их вручную. Причину невалидности "
            "показывает ST_IsValidReason."
        ),
        sql=(
            "SELECT count(*) FROM {table}\n"
            "WHERE {geom} IS NOT NULL AND NOT ST_IsValid({geom})"
        ),
    ),
    QualityCheck(
        key="empty_geometry",
        title="Пустая или отсутствующая геометрия",
        summary="Геометрия NULL или ST_IsEmpty: у объекта нет координат.",
        description=(
            "Проверка считает строки, в которых геометрический столбец пуст (NULL) "
            "или содержит геометрию без координат (ST_IsEmpty). Такие объекты "
            "попадают в статистику и выгрузки, но не отображаются на карте, а часть "
            "пространственных операций возвращает для них NULL."
        ),
        fix=(
            "Удалить пустые строки или заполнить геометрию: DELETE FROM ... "
            "WHERE geom IS NULL OR ST_IsEmpty(geom)."
        ),
        sql=(
            "SELECT count(*) FROM {table}\n"
            "WHERE {geom} IS NULL OR ST_IsEmpty({geom})"
        ),
    ),
    QualityCheck(
        key="duplicate_geometry",
        title="Дублирующиеся геометрии",
        summary="Несколько объектов имеют одну и ту же геометрию.",
        description=(
            "Проверка группирует объекты по геометрии и считает лишние копии, то "
            "есть суммарное число объектов сверх одного в каждой группе. Дубликаты "
            "завышают статистику, дают двойную подпись объектов и мешают объединению "
            "слоёв из разных источников."
        ),
        fix=(
            "Найти повторы запросом SELECT ST_AsEWKB(geom), count(*) ... GROUP BY 1 "
            "HAVING count(*) > 1, затем удалить лишние строки или объединить их "
            "атрибуты."
        ),
        sql=(
            "SELECT COALESCE(sum(n - 1), 0) FROM (\n"
            "  SELECT count(*) AS n FROM {table}\n"
            "  WHERE {geom} IS NOT NULL\n"
            "  GROUP BY ST_AsEWKB({geom}) HAVING count(*) > 1\n"
            ") AS duplicates"
        ),
    ),
    QualityCheck(
        key="self_intersection",
        title="Самопересечения",
        summary="Причина невалидности — самопересечение контура.",
        description=(
            "Подмножество проверки валидности: объекты, у которых ST_IsValidReason "
            "начинается с Self-intersection. Это полигоны, контур которых заходит "
            "сам в себя, и линии, проходящие через собственную точку. Такие объекты "
            "нельзя использовать в наложениях, топологических операциях и расчёте "
            "площадей."
        ),
        fix=(
            "Исправить через ST_MakeValid или вручную: удалить лишние вершины и "
            "разорвать контур на отдельные части."
        ),
        sql=(
            "SELECT count(*) FROM {table}\n"
            "WHERE {geom} IS NOT NULL AND NOT ST_IsValid({geom})\n"
            "  AND ST_IsValidReason({geom}) LIKE 'Self-intersection%'"
        ),
    ),
    QualityCheck(
        key="mixed_geometry_type",
        title="Смешанные типы геометрии",
        summary="Тип объекта не совпадает с типом геометрии таблицы.",
        description=(
            "Проверка сравнивает GeometryType(geom) с типом, объявленным для "
            "таблицы в geometry_columns. Смешанные типы появляются при загрузке без "
            "ограничения типа и ломают оформление, легенду и выгрузку в Shapefile "
            "или GeoPackage. Для таблиц с типом GEOMETRY проверка не выполняется."
        ),
        fix=(
            "Привести объекты к одному типу функциями ST_Multi и "
            "ST_CollectionExtract или вынести объекты другого типа в отдельную "
            "таблицу."
        ),
        sql=(
            "SELECT count(*) FROM {table}\n"
            "WHERE {geom} IS NOT NULL AND GeometryType({geom}) <> '{type}'"
        ),
        needs_type=True,
    ),
    QualityCheck(
        key="srid_mismatch",
        title="Неверный SRID объектов",
        summary="SRID объекта отличается от SRID таблицы.",
        description=(
            "Проверка считает объекты, у которых ST_SRID(geom) отличается от SRID, "
            "объявленного для таблицы. Обычно это результат вставки геометрии без "
            "SRID (0) или загрузки данных в другой системе координат: такие объекты "
            "отображаются не на своём месте и портят расчёт охвата слоя."
        ),
        fix=(
            "Задать SRID запросом UPDATE ... SET geom = ST_SetSRID(geom, <SRID>), "
            "если координаты уже в нужной системе, или ST_Transform, если систему "
            "нужно пересчитать."
        ),
        sql=(
            "SELECT count(*) FROM {table}\n"
            "WHERE {geom} IS NOT NULL AND ST_SRID({geom}) <> {srid}"
        ),
        needs_srid=True,
    ),
    QualityCheck(
        key="coordinate_range",
        title="Координаты вне допустимого диапазона",
        summary="Долгота и широта вне пределов или бесконечные координаты.",
        description=(
            "Для географических данных (SRID 4326) проверяются пределы долготы от "
            "-180 до 180 и широты от -90 до 90; для остальных систем координат — "
            "наличие бесконечных значений и NaN. Такие объекты растягивают охват "
            "слоя, из-за чего «Приблизить к слою» показывает весь мир, а мозаика "
            "и тайлы строятся неправильно."
        ),
        fix=(
            "Найти объекты запросом SELECT * FROM ... WHERE NOT (ST_XMax(geom) "
            "BETWEEN -180 AND 180 ...) и исправить координаты вручную."
        ),
        sql=(
            "SELECT count(*) FROM {table}\n"
            "WHERE {geom} IS NOT NULL AND (\n"
            "  NOT ST_XMin({geom}) > '-Infinity'::float8\n"
            "  OR NOT ST_XMax({geom}) < 'Infinity'::float8\n"
            "  OR NOT ST_YMin({geom}) > '-Infinity'::float8\n"
            "  OR NOT ST_YMax({geom}) < 'Infinity'::float8)"
        ),
        sql_geographic=(
            "SELECT count(*) FROM {table}\n"
            "WHERE {geom} IS NOT NULL AND NOT (\n"
            "  ST_XMin({geom}) BETWEEN -180 AND 180\n"
            "  AND ST_XMax({geom}) BETWEEN -180 AND 180\n"
            "  AND ST_YMin({geom}) BETWEEN -90 AND 90\n"
            "  AND ST_YMax({geom}) BETWEEN -90 AND 90)"
        ),
    ),
    QualityCheck(
        key="degenerate_geometry",
        title="Вырожденные объекты",
        summary="Полигоны нулевой площади и линии нулевой длины.",
        description=(
            "Проверка ищет объекты без площади (полигон, все вершины которого "
            "совпадают) и без длины (линия из одной точки). На карте они выглядят "
            "как точки, не участвуют в расчёте площадей и создают пустые записи в "
            "выгрузках и отчётах."
        ),
        fix=(
            "Удалить такие объекты или исправить вершины: SELECT * FROM ... "
            "WHERE ST_Area(geom) = 0."
        ),
        sql=(
            "SELECT count(*) FROM {table}\n"
            "WHERE {geom} IS NOT NULL AND NOT ST_IsEmpty({geom}) AND (\n"
            "  (GeometryType({geom}) IN ('POLYGON', 'MULTIPOLYGON')\n"
            "    AND ST_Area({geom}) = 0)\n"
            "  OR (GeometryType({geom}) IN ('LINESTRING', 'MULTILINESTRING')\n"
            "    AND ST_Length({geom}) = 0))"
        ),
    ),
    QualityCheck(
        key="unclosed_rings",
        title="Незамкнутые и битые кольца",
        summary="Кольца полигонов не замкнуты или содержат слишком мало точек.",
        description=(
            "Проверка ищет полигоны, у которых причина невалидности связана с "
            "кольцом: незамкнутое кольцо, самопересечение кольца, слишком мало "
            "точек во внешнем или внутреннем кольце. Выполняется только для "
            "полигональных таблиц, остальные пропускаются."
        ),
        fix=(
            "Причину показывает ST_IsValidReason; исправление — ST_MakeValid или "
            "ручная правка вершин в редакторе QGIS."
        ),
        sql=(
            "SELECT count(*) FROM {table}\n"
            "WHERE {geom} IS NOT NULL\n"
            "  AND GeometryType({geom}) IN ('POLYGON', 'MULTIPOLYGON')\n"
            "  AND NOT ST_IsValid({geom})\n"
            "  AND (lower(ST_IsValidReason({geom})) LIKE '%ring%'\n"
            "    OR lower(ST_IsValidReason({geom})) LIKE '%too few points%')"
        ),
    ),
    QualityCheck(
        key=CHECK_MISSING_INDEX,
        title="Нет пространственного индекса",
        summary="У таблицы нет индекса GiST по столбцу геометрии.",
        description=(
            "Сведения берутся из каталога PostGIS: у таблицы отсутствует индекс "
            "GiST или SP-GiST по геометрическому столбцу. Без такого индекса любой "
            "пространственный фильтр читает таблицу целиком, поэтому карта, выборки "
            "и проверки качества работают медленно. Проверка не обращается к данным "
            "таблицы и выполняется мгновенно."
        ),
        fix=(
            "Построить индекс запросом CREATE INDEX ... USING gist (geom) или "
            "кнопкой «Создать все пространственные индексы» на вкладке «Таблицы»."
        ),
        from_catalog=True,
    ),
]


def check_by_key(key: str) -> Optional[QualityCheck]:
    """Найти проверку по её ключу."""

    for check in QUALITY_CHECKS:
        if check.key == key:
            return check
    return None


def build_sql(check: QualityCheck, table: SpatialTable) -> Optional[str]:
    """Собрать SQL проверки для таблицы; None — проверка не применима."""

    if check.from_catalog:
        return None
    geometry_type = (table.geom_type or "").upper()
    if check.needs_type and geometry_type not in KNOWN_GEOMETRY_TYPES:
        return None
    if check.needs_srid and not table.srid:
        return None
    template = check.sql
    if check.sql_geographic and table.srid == 4326:
        template = check.sql_geographic
    if not template:
        return None
    geom = quote_ident(table.geom_column or "geom") + "::geometry"
    return template.format(
        table=table.qualified,
        geom=geom,
        type=geometry_type,
        srid=int(table.srid or 0),
    )


def run_check(db, table: SpatialTable, check: QualityCheck) -> Optional[int]:
    """Выполнить проверку для таблицы и вернуть число проблемных объектов.

    Возвращает None, если проверка к таблице не применима, и поднимает
    RuntimeError с текстом ошибки PostGIS, если запрос не выполнился.
    """

    if check.from_catalog:
        return 0 if table.has_spatial_index else 1
    sql = build_sql(check, table)
    if sql is None:
        return None
    query = QSqlQuery(db)
    if not query.exec(sql):
        raise RuntimeError(query.lastError().text() or tr("Ошибка запроса"))
    if not query.next():
        return 0
    try:
        return int(query.value(0) or 0)
    except (TypeError, ValueError):
        return 0


class QualityTask(QThread):
    """Фоновый поток выполнения выбранных проверок по всем таблицам."""

    CONNECTION_TAG = "quality"

    check_started = pyqtSignal(str)  # название проверки (строка-источник)
    check_done = pyqtSignal(str, str, object, str)  # ключ, таблица, итог, ошибка
    progress = pyqtSignal(int, int)  # (готово, всего)
    finished_all = pyqtSignal(bool, str)  # (отменено, текст ошибки)

    def __init__(
        self,
        connection: PGConnection,
        tables: Sequence[SpatialTable],
        checks: Sequence[QualityCheck],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._connection = connection
        self._tables = list(tables)
        self._checks = list(checks)
        self._cancel_requested = False

    def request_cancel(self) -> None:
        """Попросить поток остановиться после текущего запроса."""
        self._cancel_requested = True

    def run(self) -> None:
        db = None
        try:
            db = open_connection(self._connection, self.CONNECTION_TAG)
            total = len(self._checks) * len(self._tables)
            done = 0
            for check in self._checks:
                if self._cancel_requested:
                    self.finished_all.emit(True, "")
                    return
                self.check_started.emit(check.title)
                for table in self._tables:
                    if self._cancel_requested:
                        self.finished_all.emit(True, "")
                        return
                    count = None
                    error = ""
                    try:
                        count = run_check(db, table, check)
                    except Exception as exc:  # noqa: BLE001
                        error = str(exc)
                    self.check_done.emit(check.key, table.full_name, count, error)
                    done += 1
                    self.progress.emit(done, total)
            self.finished_all.emit(False, "")
        except Exception as exc:  # noqa: BLE001
            self.finished_all.emit(False, str(exc))
        finally:
            if db is not None:
                close_connection(self._connection, self.CONNECTION_TAG)
                db = None
