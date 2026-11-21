"""Проверки качества пространственных данных PostGIS.

Каждая проверка описана декларативно (QualityCheck): название, полное
описание, способ исправления и SQL-шаблон. Шаблон получает имя таблицы и
выражение геометрического столбца, поэтому одна и та же проверка работает
для любой таблицы. Фоновый поток QualityTask выполняет проверки по очереди,
сообщает о ходе работы и умеет прерываться между запросами.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from qgis.PyQt.QtCore import QSettings, QThread, pyqtSignal
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

# Пороги проверок: читаются из настроек QGIS, чтобы не зашивать числа в код.
THRESHOLD_DEFAULTS = {
    "max_points": 10000,
    "min_area": 1.0,
    "min_area_geographic": 1.0,
    "min_length": 1.0,
    "min_length_geographic": 1.0,
    "max_parts": 1000,
    "max_bytes": 1000000,
    "stale_days": 30,
    # Допуск для «почти дублей»: расстояние между объектами.
    "overlap_tolerance": 1.0,
    "overlap_tolerance_geographic": 1.0,
    # Площадь наложения, ниже которой пересечение считается сливером.
    "sliver_area": 1.0,
    "sliver_area_geographic": 100.0,
}

THRESHOLD_KEY = "zgeopg/quality"


def load_thresholds() -> dict:
    """Пороги проверок из настроек QGIS с подстановкой значений по умолчанию."""

    settings = QSettings()
    values = {}
    for name, default in THRESHOLD_DEFAULTS.items():
        raw = settings.value(THRESHOLD_KEY + "/" + name, default)
        try:
            values[name] = float(raw) if isinstance(default, float) else int(raw)
        except (TypeError, ValueError):
            values[name] = default
    return values


def save_thresholds(values) -> None:
    """Сохранить пороги проверок в настройках QGIS."""

    settings = QSettings()
    for name, default in THRESHOLD_DEFAULTS.items():
        if name in values:
            settings.setValue(THRESHOLD_KEY + "/" + name, values[name])


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
    # Запрос к каталогу PostGIS: 1 — проблема есть, 0 — нет.
    catalog_sql: Optional[str] = None
    # Проверка имеет смысл только для географических данных (SRID 4326).
    only_geographic: bool = False
    # Тяжёлые проверки (self-join по таблице) по умолчанию выключены.
    enabled_by_default: bool = True


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
    # ---------------------------------------------------- быстрые из каталога
    QualityCheck(
        key="geometry_type_unspecified",
        title="Тип геометрии не задан",
        summary="Столбец объявлен как geometry без типа и SRID.",
        description=(
            "Сведения берутся из системного каталога: у геометрического столбца "
            "нет ограничения типа (typmod), поэтому в таблице могут оказаться "
            "точки, линии и полигоны одновременно. Без ограничения типа PostGIS "
            "не проверяет корректность вставки, а QGIS не может построить "
            "оформление и легенду по типу слоя. Проверка мгновенная: данные "
            "таблицы не читаются."
        ),
        fix=(
            "Задать тип и SRID ограничением: ALTER TABLE ... ALTER COLUMN geom "
            "TYPE geometry(Point, 4326) USING geom::geometry(Point, 4326)."
        ),
        from_catalog=True,
        catalog_sql=(
            "SELECT CASE WHEN EXISTS ("
            "  SELECT 1 FROM pg_catalog.pg_attribute a "
            "  JOIN pg_catalog.pg_class c ON c.oid = a.attrelid "
            "  JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace "
            "  WHERE n.nspname = {schema_lit} AND c.relname = {name_lit} "
            "    AND a.attnum > 0 AND NOT a.attisdropped "
            "    AND a.atttypid = 'geometry'::regtype AND a.atttypmod = -1"
            ") THEN 1 ELSE 0 END"
        ),
    ),
    QualityCheck(
        key="srid_unregistered",
        title="SRID не зарегистрирован",
        summary="Кода SRID таблицы нет в spatial_ref_sys.",
        description=(
            "Каталог PostGIS сообщает SRID, которого нет в spatial_ref_sys: "
            "PostGIS не знает параметров этой системы координат. Объекты "
            "отображаются в неизвестной системе, ST_Transform невозможен, а "
            "расчёт площадей и длин даёт неверные числа. Проверка выполняется "
            "по каталогу и не читает данные."
        ),
        fix=(
            "Добавить систему координат в spatial_ref_sys или пересоздать "
            "столбец с корректным SRID: ALTER TABLE ... ALTER COLUMN geom TYPE "
            "geometry(Point, <SRID>) USING ST_SetSRID(geom, <SRID>)."
        ),
        from_catalog=True,
        catalog_sql=(
            "SELECT CASE WHEN EXISTS ("
            "  SELECT 1 FROM pg_catalog.pg_attribute a "
            "  JOIN pg_catalog.pg_class c ON c.oid = a.attrelid "
            "  JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace "
            "  WHERE n.nspname = {schema_lit} AND c.relname = {name_lit} "
            "    AND a.attnum > 0 AND NOT a.attisdropped "
            "    AND a.atttypid = 'geometry'::regtype "
            "    AND postgis_typmod_srid(a.atttypmod) > 0 "
            "    AND NOT EXISTS ("
            "      SELECT 1 FROM public.spatial_ref_sys s "
            "      WHERE s.srid = postgis_typmod_srid(a.atttypmod)"
            "    )"
            ") THEN 1 ELSE 0 END"
        ),
    ),
    QualityCheck(
        key="geometry_nullable",
        title="Геометрия допускает NULL",
        summary="У геометрического столбца нет ограничения NOT NULL.",
        description=(
            "Каталог показывает, что столбец геометрии допускает пустые "
            "значения. Пока ограничения нет, любой импорт или ручная вставка "
            "может добавить объект без координат, и такие строки всплывут "
            "позже как «пустая геометрия». Ограничение ставится один раз и "
            "закрывает эту возможность. Проверка мгновенная."
        ),
        fix=(
            "Убедиться, что пустых объектов нет, и запретить их: ALTER TABLE "
            "... ALTER COLUMN geom SET NOT NULL."
        ),
        from_catalog=True,
        catalog_sql=(
            "SELECT CASE WHEN EXISTS ("
            "  SELECT 1 FROM pg_catalog.pg_attribute a "
            "  JOIN pg_catalog.pg_class c ON c.oid = a.attrelid "
            "  JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace "
            "  WHERE n.nspname = {schema_lit} AND c.relname = {name_lit} "
            "    AND a.attnum > 0 AND NOT a.attisdropped "
            "    AND a.atttypid = 'geometry'::regtype AND NOT a.attnotnull"
            ") THEN 1 ELSE 0 END"
        ),
    ),
    QualityCheck(
        key="index_not_gist",
        title="Индекс по геометрии не GiST",
        summary="Пространственный столбец индексирован не GiST и не SP-GiST.",
        description=(
            "По столбцу геометрии построен индекс другого типа (btree, hash) — "
            "PostGIS не использует его в пространственных операторах. Такой "
            "индекс занимает место и замедляет вставку, но не ускоряет "
            "фильтры ST_Intersects, ST_DWithin и поиск по рамке. Сведения "
            "берутся из каталога, данные не читаются."
        ),
        fix=(
            "Удалить бесполезный индекс и построить GiST: DROP INDEX ...; "
            "CREATE INDEX ... ON ... USING gist (geom)."
        ),
        from_catalog=True,
        catalog_sql=(
            "SELECT CASE WHEN EXISTS ("
            "  SELECT 1 FROM pg_catalog.pg_index i "
            "  JOIN pg_catalog.pg_class c ON c.oid = i.indrelid "
            "  JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace "
            "  JOIN pg_catalog.pg_class idx ON idx.oid = i.indexrelid "
            "  JOIN pg_catalog.pg_am am ON am.oid = idx.relam "
            "  JOIN pg_catalog.pg_attribute a "
            "    ON a.attrelid = c.oid AND a.attnum = ANY (i.indkey) "
            "  WHERE n.nspname = {schema_lit} AND c.relname = {name_lit} "
            "    AND a.atttypid = 'geometry'::regtype "
            "    AND am.amname NOT IN ('gist', 'spgist')"
            ") THEN 1 ELSE 0 END"
        ),
    ),
    QualityCheck(
        key="duplicate_spatial_indexes",
        title="Лишние пространственные индексы",
        summary="По столбцу геометрии построено больше одного GiST-индекса.",
        description=(
            "Каталог показывает два и более GiST-индекса по одному и тому же "
            "столбцу геометрии. Планировщик использует только один, а каждый "
            "лишний занимает диск и замедляет каждую вставку и обновление. "
            "Обычно так остаётся после экспериментов с индексами. Проверка "
            "мгновенная, данные не читаются."
        ),
        fix=(
            "Оставить один индекс и удалить остальные: DROP INDEX ... для "
            "каждого лишнего GiST-индекса."
        ),
        from_catalog=True,
        catalog_sql=(
            "SELECT CASE WHEN ("
            "  SELECT count(*) FROM pg_catalog.pg_index i "
            "  JOIN pg_catalog.pg_class c ON c.oid = i.indrelid "
            "  JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace "
            "  JOIN pg_catalog.pg_class idx ON idx.oid = i.indexrelid "
            "  JOIN pg_catalog.pg_am am ON am.oid = idx.relam "
            "  JOIN pg_catalog.pg_attribute a "
            "    ON a.attrelid = c.oid AND a.attnum = ANY (i.indkey) "
            "  WHERE n.nspname = {schema_lit} AND c.relname = {name_lit} "
            "    AND a.atttypid = 'geometry'::regtype "
            "    AND am.amname IN ('gist', 'spgist')"
            ") > 1 THEN 1 ELSE 0 END"
        ),
    ),
    QualityCheck(
        key="statistics_stale",
        title="Устаревшая статистика таблицы",
        summary="ANALYZE не запускался дольше заданного числа дней.",
        description=(
            "PostgreSQL хранит дату последнего ANALYZE. Если она старше порога "
            "из настроек (по умолчанию 30 дней) или её нет, планировщик "
            "оценивает количество строк по устаревшим данным: пространственные "
            "фильтры начинают читать таблицу целиком, а сводки и проверки "
            "качества идут в разы дольше. Сведения берутся из "
            "pg_stat_user_tables, данные не читаются."
        ),
        fix=(
            "Обновить статистику: ANALYZE <схема>.<таблица>; при частых "
            "изменениях проверить настройки autovacuum."
        ),
        from_catalog=True,
        catalog_sql=(
            "SELECT CASE WHEN EXISTS ("
            "  SELECT 1 FROM pg_catalog.pg_stat_user_tables s "
            "  WHERE s.schemaname = {schema_lit} AND s.relname = {name_lit} "
            "    AND s.n_live_tup > 0 "
            "    AND coalesce(greatest(s.last_analyze, s.last_autoanalyze), "
            "        '-infinity'::timestamptz) < now() - interval '{stale_days} days'"
            ") THEN 1 ELSE 0 END"
        ),
    ),
    # ------------------------------------------------ один проход по таблице
    QualityCheck(
        key="not_simple",
        title="Самопересекающиеся линии",
        summary="Линия проходит через собственную точку.",
        description=(
            "Проверка ищет линии, которые не являются простыми: контур заходит "
            "сам в себя или линия дважды проходит через одну точку. "
            "ST_IsValid для линий это не проверяет, поэтому обычная проверка "
            "валидности такие объекты пропускает. Непростые линии дают "
            "некорректную длину, ломают маршрутизацию и топологические "
            "операции."
        ),
        fix=(
            "Разрезать линию на простые части: ST_LineMerge или "
            "ST_Node(geom), затем проверить результат ST_IsSimple."
        ),
        sql=(
            "SELECT count(*) FROM {table}\n"
            "WHERE {geom} IS NOT NULL AND NOT ST_IsEmpty({geom})\n"
            "  AND GeometryType({geom}) IN ('LINESTRING', 'MULTILINESTRING')\n"
            "  AND NOT ST_IsSimple({geom})"
        ),
    ),
    QualityCheck(
        key="swapped_axes",
        title="Перепутаны широта и долгота",
        summary="Для SRID 4326 координаты похожи на перевёрнутые оси.",
        description=(
            "Для географических данных проверяется признак перевёрнутых осей: "
            "долгота по модулю не больше 90, а широта больше 90 — значит "
            "координаты вставлены как (широта, долгота). Такие объекты "
            "уезжают на другой конец планеты, и «Приблизить к слою» "
            "показывает весь мир. Проверка выполняется только для SRID 4326."
        ),
        fix=(
            "Поменять координаты местами: UPDATE ... SET geom = "
            "ST_FlipCoordinates(geom) WHERE ... — только для найденных "
            "объектов."
        ),
        sql=(
            "SELECT count(*) FROM {table}\n"
            "WHERE {geom} IS NOT NULL AND NOT ST_IsEmpty({geom})\n"
            "  AND abs(ST_X(ST_Centroid({geom}))) <= 90\n"
            "  AND abs(ST_Y(ST_Centroid({geom}))) > 90"
        ),
        only_geographic=True,
    ),
    QualityCheck(
        key="too_many_points",
        title="Слишком много вершин",
        summary="Объект содержит больше вершин, чем задано порогом.",
        description=(
            "Сравнивается число вершин объекта (ST_NPoints) с порогом из "
            "настроек — по умолчанию 10 000. Такие объекты появляются после "
            "сложения геометрий без упрощения и делают слой тяжёлым: QGIS "
            "долго рисует карту, медленно работают выборки и экспорт. Порог "
            "задаётся на вкладке проверок."
        ),
        fix=(
            "Упростить геометрию: UPDATE ... SET geom = "
            "ST_SimplifyPreserveTopology(geom, <допуск>) или "
            "ST_Subdivide для очень длинных объектов."
        ),
        sql=(
            "SELECT count(*) FROM {table}\n"
            "WHERE {geom} IS NOT NULL AND ST_NPoints({geom}) > {max_points}"
        ),
    ),
    QualityCheck(
        key="tiny_polygons",
        title="Микрообъекты",
        summary="Площадь полигона меньше порога из настроек.",
        description=(
            "Проверка ищет полигоны с площадью меньше порога — по умолчанию "
            "1 квадратная единица. Такие «осколки» обычно остаются после "
            "обрезки и наложения слоёв, засоряют атрибутивные таблицы и "
            "попадают в отчёты как полноценные объекты. Для географических "
            "данных площадь считается в квадратных метрах."
        ),
        fix=(
            "Удалить осколки или объединить их с соседями: DELETE FROM ... "
            "WHERE ST_Area(geom) < <порог>."
        ),
        sql=(
            "SELECT count(*) FROM {table}\n"
            "WHERE {geom} IS NOT NULL AND NOT ST_IsEmpty({geom})\n"
            "  AND GeometryType({geom}) IN ('POLYGON', 'MULTIPOLYGON')\n"
            "  AND ST_Area({geom}) < {min_area}"
        ),
        sql_geographic=(
            "SELECT count(*) FROM {table}\n"
            "WHERE {geom} IS NOT NULL AND NOT ST_IsEmpty({geom})\n"
            "  AND GeometryType({geom}) IN ('POLYGON', 'MULTIPOLYGON')\n"
            "  AND ST_Area({geom}::geography) < {min_area_geographic}"
        ),
    ),
    QualityCheck(
        key="has_z_or_m",
        title="Лишняя размерность Z или M",
        summary="Геометрия имеет Z или M там, где ожидается плоская 2D.",
        description=(
            "Проверка ищет объекты с третьей координатой или измерением M "
            "(ST_NDims и ST_Zmflag). Разная размерность в одном столбце "
            "ломает сравнение геометрий, мешает экспорту в простые форматы и "
            "даёт неожиданные результаты в операциях наложения."
        ),
        fix=(
            "Привести объекты к 2D: UPDATE ... SET geom = ST_Force2D(geom), "
            "затем задать тип столбца geometry(<Тип>, <SRID>)."
        ),
        sql=(
            "SELECT count(*) FROM {table}\n"
            "WHERE {geom} IS NOT NULL\n"
            "  AND (ST_NDims({geom}) <> 2 OR ST_Zmflag({geom}) <> 0)"
        ),
    ),
    QualityCheck(
        key="geometry_collections",
        title="Коллекции геометрий",
        summary="Объект имеет тип GEOMETRYCOLLECTION.",
        description=(
            "Проверка ищет объекты-коллекции, в которых смешаны точки, линии и "
            "полигоны. Коллекции не поддерживаются частью операций PostGIS и "
            "плохо отображаются в QGIS: оформление задаётся по одному типу, "
            "экспорт в Shapefile такие объекты теряет."
        ),
        fix=(
            "Разобрать коллекции на однотипные объекты: "
            "ST_CollectionExtract(geom, 1|2|3) или ST_Dump с созданием "
            "отдельных строк."
        ),
        sql=(
            "SELECT count(*) FROM {table}\n"
            "WHERE {geom} IS NOT NULL AND NOT ST_IsEmpty({geom})\n"
            "  AND GeometryType({geom}) = 'GEOMETRYCOLLECTION'"
        ),
    ),
    QualityCheck(
        key="too_many_parts",
        title="Слишком много частей в объекте",
        summary="Число частей мультигеометрии выше порога из настроек.",
        description=(
            "Сравнивается ST_NumGeometries с порогом — по умолчанию 1000. "
            "Объект из тысяч частей (например, мультиполигон всей страны) "
            "рисуется и обрабатывается как единое целое: одна операция "
            "блокирует таблицу на минуты, а редактор QGIS зависает при "
            "выделении такого объекта."
        ),
        fix=(
            "Разделить объект: ST_Subdivide(geom, <число вершин>) с записью "
            "частей отдельными строками."
        ),
        sql=(
            "SELECT count(*) FROM {table}\n"
            "WHERE {geom} IS NOT NULL AND NOT ST_IsEmpty({geom})\n"
            "  AND ST_NumGeometries({geom}) > {max_parts}"
        ),
    ),
    QualityCheck(
        key="large_geometry",
        title="Очень крупная геометрия",
        summary="Размер геометрии в байтах выше порога из настроек.",
        description=(
            "Сравнивается pg_column_size(geom) с порогом — по умолчанию "
            "1 МБ. Крупные объекты вычитываются целиком при любом обращении, "
            "из-за чего карта и проверки качества замедляются, а TOAST-таблица "
            "растёт быстрее данных."
        ),
        fix=(
            "Упростить или разбить объект: ST_SimplifyPreserveTopology или "
            "ST_Subdivide."
        ),
        sql=(
            "SELECT count(*) FROM {table}\n"
            "WHERE {geom} IS NOT NULL AND pg_column_size({geom}) > {max_bytes}"
        ),
    ),
    QualityCheck(
        key="polygon_holes",
        title="Дыры в полигонах",
        summary="У полигона есть внутренние кольца.",
        description=(
            "Проверка ищет полигоны с внутренними кольцами (ST_NumInteriorRings). "
            "Иногда дыры нужны, но чаще это следствие плохого наложения или "
            "обрезки: объект разваливается на кольцо, и площадь считается "
            "меньше настоящей. Список таких объектов помогает быстро понять, "
            "где геометрия испорчена."
        ),
        fix=(
            "Проверить дыры на карте и при необходимости залить их: "
            "ST_MakePolygon(ST_ExteriorRing(geom))."
        ),
        sql=(
            "SELECT count(*) FROM {table}\n"
            "WHERE {geom} IS NOT NULL AND NOT ST_IsEmpty({geom})\n"
            "  AND GeometryType({geom}) IN ('POLYGON', 'MULTIPOLYGON')\n"
            "  AND ST_NumInteriorRings(ST_GeometryN({geom}, 1)) > 0"
        ),
    ),
    QualityCheck(
        key="ring_orientation",
        title="Кольца против часовой стрелки",
        summary="Ориентация внешнего кольца не по спецификации OGC.",
        description=(
            "По спецификации OGC внешнее кольцо полигона обходится против "
            "часовой стрелки, внутренние — по часовой. Проверка сравнивает "
            "геометрию с ST_ForcePolygonCCW: если порядок вершин отличается, "
            "ориентация обратная. Часть ГИС и форматов (Shapefile, некоторые "
            "веб-сервисы) ожидают именно такую ориентацию, иначе полигон "
            "рисуется «вывернутым» или считается внешней областью."
        ),
        fix=(
            "Привести ориентацию колец к спецификации: UPDATE ... SET geom = "
            "ST_ForcePolygonCCW(geom)."
        ),
        sql=(
            "SELECT count(*) FROM {table}\n"
            "WHERE {geom} IS NOT NULL AND NOT ST_IsEmpty({geom})\n"
            "  AND GeometryType({geom}) IN ('POLYGON', 'MULTIPOLYGON')\n"
            "  AND NOT ST_OrderingEquals(ST_ForcePolygonCCW({geom}), {geom})"
        ),
    ),
    QualityCheck(
        key="tiny_lines",
        title="Микролинии",
        summary="Длина линии меньше порога из настроек.",
        description=(
            "Проверка ищет линии с длиной меньше порога — по умолчанию "
            "1 единица. Такие обрезки появляются после наложения и обрезки "
            "слоёв и выглядят на карте точками: они завышают количество "
            "объектов, мешают генерализации и попадают в отчёты как "
            "самостоятельные дороги или реки. Для географических данных длина "
            "считается в метрах."
        ),
        fix=(
            "Удалить обрезки или объединить их с соседними линиями: DELETE FROM "
            "... WHERE ST_Length(geom) < <порог>."
        ),
        sql=(
            "SELECT count(*) FROM {table}\n"
            "WHERE {geom} IS NOT NULL AND NOT ST_IsEmpty({geom})\n"
            "  AND GeometryType({geom}) IN ('LINESTRING', 'MULTILINESTRING')\n"
            "  AND ST_Length({geom}) < {min_length}"
        ),
        sql_geographic=(
            "SELECT count(*) FROM {table}\n"
            "WHERE {geom} IS NOT NULL AND NOT ST_IsEmpty({geom})\n"
            "  AND GeometryType({geom}) IN ('LINESTRING', 'MULTILINESTRING')\n"
            "  AND ST_Length({geom}::geography) < {min_length_geographic}"
        ),
    ),
    QualityCheck(
        key="nested_holes",
        title="Дыры за пределами полигона",
        summary="Внутреннее кольцо выходит за внешнюю оболочку.",
        description=(
            "Проверка ищет полигоны, у которых внутреннее кольцо лежит вне "
            "внешней оболочки: PostGIS сообщает причину «Hole lies outside "
            "shell». Обычно это следствие ручной правки или неудачного "
            "объединения: дыра «висит» снаружи и вырезает чужие территории, "
            "из-за чего ломается расчёт площадей при наложении."
        ),
        fix=(
            "Удалить или залить внешние дыры: ST_MakePolygon("
            "ST_ExteriorRing(geom)) либо исправить кольца вручную в редакторе "
            "QGIS."
        ),
        sql=(
            "SELECT count(*) FROM {table}\n"
            "WHERE {geom} IS NOT NULL AND NOT ST_IsEmpty({geom})\n"
            "  AND GeometryType({geom}) IN ('POLYGON', 'MULTIPOLYGON')\n"
            "  AND NOT ST_IsValid({geom})\n"
            "  AND ST_IsValidReason({geom}) LIKE 'Hole lies outside shell%'"
        ),
    ),
    QualityCheck(
        key="polygon_overlaps",
        title="Пересечения полигонов внутри слоя",
        summary="Полигоны одного слоя накладываются друг на друга.",
        description=(
            "Проверка ищет пары объектов одного слоя, которые пересекаются с "
            "ненулевой площадью (ST_Overlaps). В корректном полигональном слое "
            "объекты могут касаться границами, но не накладываться: наложения "
            "дают двойной учёт площади, ломают пространственные соединения и "
            "приводят к тому, что один и тот же участок попадает в два района. "
            "Проверка тяжёлая: это соединение таблицы с самой собой по рамке "
            "(&&), поэтому по умолчанию выключена и включается вручную."
        ),
        fix=(
            "Найти пары запросом SELECT a.id, b.id FROM ... a JOIN ... b ON "
            "a.geom && b.geom AND ST_Overlaps(a.geom, b.geom) и устранить "
            "наложение: разрезать объекты (ST_Difference) или объединить их "
            "(ST_Union)."
        ),
        sql=(
            "SELECT count(*) FROM {table} a JOIN {table} b\n"
            "  ON a.ctid < b.ctid AND a.{geom_col} && b.{geom_col}\n"
            "WHERE a.{geom_col} IS NOT NULL AND b.{geom_col} IS NOT NULL\n"
            "  AND NOT ST_IsEmpty(a.{geom_col}) AND NOT ST_IsEmpty(b.{geom_col})\n"
            "  AND ST_Overlaps(a.{geom_col}, b.{geom_col})"
        ),
        enabled_by_default=False,
    ),
    QualityCheck(
        key="near_duplicate_geometry",
        title="Почти дубли геометрий",
        summary="Объекты совпадают со сдвигом в пределах допуска.",
        description=(
            "Проверка ищет пары объектов одного слоя, расстояние между которыми "
            "меньше допуска из настроек — по умолчанию 1 единица, для "
            "географических данных 1 метр. Так выглядят объекты, загруженные "
            "дважды с небольшим сдвигом или оцифрованные повторно: они выдают "
            "себя за разные записи, но описывают одно и то же место. Точное "
            "сравнение геометрий такие пары не находит. Проверка тяжёлая "
            "(соединение таблицы с самой собой), по умолчанию выключена."
        ),
        fix=(
            "Сравнить пары запросом SELECT a.id, b.id, ST_Distance(a.geom, "
            "b.geom) ... WHERE ST_DWithin(a.geom, b.geom, <допуск>) и удалить "
            "лишнюю запись."
        ),
        sql=(
            "SELECT count(*) FROM {table} a JOIN {table} b\n"
            "  ON a.ctid < b.ctid AND a.{geom_col} && b.{geom_col}\n"
            "WHERE a.{geom_col} IS NOT NULL AND b.{geom_col} IS NOT NULL\n"
            "  AND NOT ST_Equals(a.{geom_col}, b.{geom_col})\n"
            "  AND ST_DWithin(a.{geom_col}, b.{geom_col}, {overlap_tolerance})"
        ),
        sql_geographic=(
            "SELECT count(*) FROM {table} a JOIN {table} b\n"
            "  ON a.ctid < b.ctid AND a.{geom_col} && b.{geom_col}\n"
            "WHERE a.{geom_col} IS NOT NULL AND b.{geom_col} IS NOT NULL\n"
            "  AND NOT ST_Equals(a.{geom_col}, b.{geom_col})\n"
            "  AND ST_DWithin(a.{geom_col}::geography, b.{geom_col}::geography, "
            "{overlap_tolerance_geographic})"
        ),
        enabled_by_default=False,
    ),
    QualityCheck(
        key="polygon_slivers",
        title="Сливеры (узкие щели)",
        summary="Полигоны касаются друг друга с почти нулевой площадью наложения.",
        description=(
            "Проверка ищет пары полигонов одного слоя, которые касаются "
            "границами, но наложение у них меньше порога из настроек — по "
            "умолчанию 1 квадратная единица, для географических данных 1 м². "
            "Такие «сливеры» остаются после неточной оцифровки смежных границ "
            "и после оверлеев: вместо общей границы между объектами появляется "
            "тонкая щель или нахлёст. Проверка тяжёлая (соединение таблицы с "
            "самой собой), по умолчанию выключена."
        ),
        fix=(
            "Сшить границы соседних объектов: ST_Snap(a.geom, b.geom, <допуск>) "
            "для каждой пары или пересобрать слой топологически."
        ),
        sql=(
            "SELECT count(*) FROM {table} a JOIN {table} b\n"
            "  ON a.ctid < b.ctid AND a.{geom_col} && b.{geom_col}\n"
            "WHERE a.{geom_col} IS NOT NULL AND b.{geom_col} IS NOT NULL\n"
            "  AND GeometryType(a.{geom_col}) IN ('POLYGON', 'MULTIPOLYGON')\n"
            "  AND GeometryType(b.{geom_col}) IN ('POLYGON', 'MULTIPOLYGON')\n"
            "  AND ST_Intersects(a.{geom_col}, b.{geom_col})\n"
            "  AND ST_Area(ST_Intersection(a.{geom_col}, b.{geom_col})) "
            "> 0 AND ST_Area(ST_Intersection(a.{geom_col}, b.{geom_col})) "
            "< {sliver_area}"
        ),
        sql_geographic=(
            "SELECT count(*) FROM {table} a JOIN {table} b\n"
            "  ON a.ctid < b.ctid AND a.{geom_col} && b.{geom_col}\n"
            "WHERE a.{geom_col} IS NOT NULL AND b.{geom_col} IS NOT NULL\n"
            "  AND GeometryType(a.{geom_col}) IN ('POLYGON', 'MULTIPOLYGON')\n"
            "  AND GeometryType(b.{geom_col}) IN ('POLYGON', 'MULTIPOLYGON')\n"
            "  AND ST_Intersects(a.{geom_col}, b.{geom_col})\n"
            "  AND ST_Area(ST_Intersection(a.{geom_col}, b.{geom_col})::geography) "
            "> 0 AND ST_Area(ST_Intersection(a.{geom_col}, b.{geom_col})::geography) "
            "< {sliver_area_geographic}"
        ),
        enabled_by_default=False,
    ),
]


@dataclass(frozen=True)
class AttributeCheck:
    """Описание одной проверки качества атрибутивных данных.

    Проверка работает по столбцам таблицы, подходящим под ``kind``:
    ``text``, ``numeric``, ``date`` или ``all``. Режим определяет, как
    строится запрос: ``or`` объединяет условия по столбцам, ``per_column``
    считает каждый столбец отдельно (нужно для статистики), ``group``
    группирует строки по всем атрибутивным столбцам.
    """

    key: str
    title: str
    summary: str
    description: str
    fix: str
    kind: str = "text"
    mode: str = "or"
    condition: str = ""
    # Проверка по умолчанию выключена: она слишком долгая для обычного прогона.
    enabled_by_default: bool = True


MODE_OR = "or"
MODE_PER_COLUMN = "per_column"
MODE_GROUP = "group"
MODE_DUPLICATES = "duplicates"

ATTRIBUTE_CHECKS: List[AttributeCheck] = [
    AttributeCheck(
        key="attr_null_values",
        title="Пустые значения NULL",
        summary="В атрибутивных столбцах встречаются значения NULL.",
        description=(
            "Проверка считает объекты, у которых хотя бы один атрибутивный "
            "столбец (все столбцы, кроме геометрического) не заполнен. Значения "
            "NULL ломают фильтры, соединения и расчёт сводок: строка выпадает "
            "из выборок «WHERE поле = значение» и из подсчёта сумм и средних."
        ),
        fix=(
            "Заполнить обязательные поля или запретить пустые значения "
            "ограничением ALTER TABLE ... ALTER COLUMN ... SET NOT NULL."
        ),
        kind="all",
        condition="{col} IS NULL",
    ),
    AttributeCheck(
        key="attr_empty_strings",
        title="Пустые строки",
        summary="В текстовых столбцах есть значения из пробелов или пустые строки.",
        description=(
            "Проверка ищет строки, где текстовое поле пустое или состоит только "
            "из пробелов. От NULL такие значения не отличаются для "
            "пользователя, но ведут себя иначе в запросах: IS NULL их не "
            "находит, а сортировка и группировка дают отдельную группу."
        ),
        fix=(
            "Заменить пустые строки на NULL или на осмысленное значение: "
            "UPDATE ... SET поле = NULL WHERE btrim(поле) = ''."
        ),
        kind="text",
        condition="btrim({col}) = ''",
    ),
    AttributeCheck(
        key="attr_whitespace_padding",
        title="Пробелы по краям значений",
        summary="Текстовые значения начинаются или заканчиваются пробелом.",
        description=(
            "Проверка ищет значения с ведущими или замыкающими пробелами, "
            "табуляцией и переводами строк. Такие значения не совпадают при "
            "сравнении и соединении: «Москва» и «Москва » считаются разными, "
            "из-за чего ломаются справочники, фильтры и связи между слоями."
        ),
        fix=(
            "Очистить значения от лишних пробелов: UPDATE ... SET поле = "
            "btrim(поле)."
        ),
        kind="text",
        condition="{col} <> btrim({col})",
    ),
    AttributeCheck(
        key="attr_double_spaces",
        title="Двойные пробелы внутри значений",
        summary="В тексте встречаются два и более пробела подряд.",
        description=(
            "Проверка находит значения, внутри которых стоят два и более "
            "пробела подряд. Обычно это следствие ручного ввода или склейки "
            "полей, и такие записи не находятся поиском по точному значению и "
            "выглядят неряшливо в отчётах."
        ),
        fix=(
            "Заменить повторяющиеся пробелы одним: UPDATE ... SET поле = "
            "regexp_replace(поле, '\\s+', ' ', 'g')."
        ),
        kind="text",
        condition="{col} LIKE '%  %'",
    ),
    AttributeCheck(
        key="attr_duplicate_rows",
        title="Дублирующиеся записи",
        summary="Полностью совпадающие атрибутивные записи в таблице.",
        description=(
            "Проверка группирует объекты по всем атрибутивным столбцам и "
            "считает лишние копии. Полные дубликаты завышают статистику, "
            "приводят к двойным подписям на карте и мешают объединению данных "
            "из разных источников."
        ),
        fix=(
            "Найти повторы запросом SELECT столбцы, count(*) ... GROUP BY "
            "столбцы HAVING count(*) > 1 и удалить лишние строки."
        ),
        kind="all",
        mode=MODE_GROUP,
    ),
    AttributeCheck(
        key="attr_numeric_text",
        title="Числа, записанные как текст",
        summary="В текстовом столбце значение целиком состоит из числа.",
        description=(
            "Проверка ищет текстовые столбцы, где значение является числом. "
            "Обычно так выглядят поля, которые нужно хранить числом: "
            "идентификаторы, площади, коды. Из-за текстового типа сравнение идёт "
            "по алфавиту («10» меньше «9») и невозможны арифметические операции."
        ),
        fix=(
            "Изменить тип столбца с приведением значений: ALTER TABLE ... "
            "ALTER COLUMN ... TYPE numeric USING поле::numeric."
        ),
        kind="text",
        condition=(
            "{col} ~ '^[[:space:]]*[+-]?[0-9]+([.,][0-9]+)?[[:space:]]*$'"
        ),
    ),
    AttributeCheck(
        key="attr_control_chars",
        title="Управляющие и невидимые символы",
        summary="В тексте есть табуляция, переводы строк и другие служебные символы.",
        description=(
            "Проверка ищет управляющие символы (табуляция, перевод строки, "
            "возврат каретки) и невидимые символы в текстовых значениях. Они "
            "портят вёрстку подписей и отчётов, ломают разбор CSV и мешают "
            "сравнению строк."
        ),
        fix=(
            "Удалить служебные символы: UPDATE ... SET поле = "
            "regexp_replace(поле, '[[:cntrl:]]', '', 'g')."
        ),
        kind="text",
        condition="{col} ~ '[[:cntrl:]]'",
    ),
    AttributeCheck(
        key="attr_outlier_length",
        title="Аномальная длина текста",
        summary="Длина значения резко отличается от средней по столбцу.",
        description=(
            "Для каждого текстового столбца считается средняя длина значения и "
            "стандартное отклонение, затем ищутся значения длиннее среднего "
            "более чем на три отклонения. Так находятся обрезанные поля "
            "справочника и, наоборот, значения со склеенным или лишним текстом."
        ),
        fix=(
            "Просмотреть найденные значения и привести их к длине, принятой в "
            "справочнике: SELECT * FROM ... ORDER BY length(поле) DESC."
        ),
        kind="text",
        mode=MODE_PER_COLUMN,
        condition=(
            "WITH s AS (SELECT avg(length({col})) AS a,\n"
            "  coalesce(stddev_pop(length({col})), 0) AS d FROM {table})\n"
            "SELECT count(*) FROM {table}, s\n"
            "WHERE {col} IS NOT NULL AND length({col}) > s.a + 3 * s.d"
        ),
    ),
    AttributeCheck(
        key="attr_numeric_outliers",
        title="Выбросы в числовых столбцах",
        summary="Числовое значение выходит за три стандартных отклонения.",
        description=(
            "Для каждого числового столбца считается среднее и стандартное "
            "отклонение, затем ищутся значения вне диапазона «среднее ± 3 "
            "отклонения». Обычно это опечатки в разрядах и нулевые значения "
            "вместо пропусков; они сильно искажают суммы и средние в сводках."
        ),
        fix=(
            "Проверить найденные значения и исправить или заменить на NULL: "
            "SELECT * FROM ... ORDER BY поле DESC LIMIT 100."
        ),
        kind="numeric",
        mode=MODE_PER_COLUMN,
        condition=(
            "WITH s AS (SELECT avg({col}) AS a,\n"
            "  coalesce(stddev_pop({col}), 0) AS d FROM {table})\n"
            "SELECT count(*) FROM {table}, s\n"
            "WHERE {col} IS NOT NULL\n"
            "  AND ({col} > s.a + 3 * s.d OR {col} < s.a - 3 * s.d)"
        ),
    ),
    AttributeCheck(
        key="attr_date_range",
        title="Даты вне разумного диапазона",
        summary="Дата раньше 1900 года или позже чем через год от текущей.",
        description=(
            "Проверка ищет значения дат и отметок времени раньше 1900 года и "
            "позже года от текущей даты. Так выглядят даты, записанные в "
            "неверном формате, и результат подстановки нулевой даты. Такие "
            "значения ломают временные фильтры и хронологию в отчётах."
        ),
        fix=(
            "Исправить даты вручную или заменить невозможные значения на NULL: "
            "UPDATE ... SET поле = NULL WHERE поле < DATE '1900-01-01'."
        ),
        kind="date",
        condition=(
            "{col} < DATE '1900-01-01' OR {col} > now() + interval '1 year'"
        ),
    ),
    AttributeCheck(
        key="attr_attribute_duplicates",
        title="Дубли по атрибутам ( очень долго! )",
        summary=(
            "Полные дубли строк, дубли составного ключа, совпадения без учёта "
            "регистра и частичные вхождения."
        ),
        description=(
            "Одна проверка объединяет четыре вида дублей по атрибутам: полные "
            "дубли строк (совпадают все атрибутивные столбцы), дубли составного "
            "ключа (совпадают все текстовые столбцы), совпадения без учёта "
            "регистра и лишних пробелов («Москва» и «москва ») и частичные "
            "вхождения — когда значение целиком входит в другое значение, "
            "например «ЯмалоНенецкий автономный окру» входит в «ЯмалоНенецкий "
            "автономный округ». Для частичных вхождений показывается процент "
            "вхождения — доля длины короткого значения в длинном. Дубли "
            "завышают статистику, дают двойные подписи на карте и мешают "
            "объединять данные из разных источников. Подробный список с "
            "процентами открывается двойным щелчком по ячейке."
        ),
        fix=(
            "Просмотреть подробный список двойным щелчком по ячейке и "
            "объединить или удалить лишние записи; для совпадений без учёта "
            "регистра привести значения к единому написанию, для частичных "
            "вхождений — заменить обрезанное значение полным."
        ),
        kind="all",
        mode=MODE_DUPLICATES,
        enabled_by_default=False,
    ),
]



# Сначала мгновенные проверки по каталогу, затем проход по данным таблицы:
# так пользователь получает быстрые ответы, не дожидаясь тяжёлых запросов.
QUALITY_CHECKS.sort(key=lambda check: 0 if check.from_catalog else 1)


def check_by_key(key: str):
    """Найти проверку (пространственную или атрибутивную) по её ключу."""

    for check in QUALITY_CHECKS:
        if check.key == key:
            return check
    for check in ATTRIBUTE_CHECKS:
        if check.key == key:
            return check
    return None


def _sql_literal(value: str) -> str:
    """Строковый литерал SQL с экранированием кавычек."""

    return "'" + str(value).replace("'", "''") + "'"


def build_catalog_sql(
    check: QualityCheck,
    table: SpatialTable,
    thresholds: Optional[dict] = None,
) -> Optional[str]:
    """Собрать запрос проверки по каталогу; None — проверка не применима."""

    template = check.catalog_sql
    if not template:
        return None
    if thresholds is None:
        thresholds = load_thresholds()
    return template.format(
        schema_lit=_sql_literal(table.schema),
        name_lit=_sql_literal(table.name),
        stale_days=int(thresholds.get("stale_days", 30)),
    )


def build_sql(
    check: QualityCheck,
    table: SpatialTable,
    thresholds: Optional[dict] = None,
) -> Optional[str]:
    """Собрать SQL проверки для таблицы; None — проверка не применима."""

    if check.from_catalog:
        return build_catalog_sql(check, table, thresholds)
    geometry_type = (table.geom_type or "").upper()
    if check.needs_type and geometry_type not in KNOWN_GEOMETRY_TYPES:
        return None
    if check.needs_srid and not table.srid:
        return None
    if check.only_geographic and table.srid != 4326:
        return None
    template = check.sql
    if check.sql_geographic and table.srid == 4326:
        template = check.sql_geographic
    if not template:
        return None
    geom = quote_ident(table.geom_column or "geom") + "::geometry"
    if thresholds is None:
        thresholds = load_thresholds()
    return template.format(
        table=table.qualified,
        geom=geom,
        geom_col=quote_ident(table.geom_column or "geom"),
        type=geometry_type,
        srid=int(table.srid or 0),
        max_points=int(thresholds.get("max_points", 10000)),
        min_area=float(thresholds.get("min_area", 1.0)),
        min_area_geographic=float(thresholds.get("min_area_geographic", 1.0)),
        min_length=float(thresholds.get("min_length", 1.0)),
        min_length_geographic=float(thresholds.get("min_length_geographic", 1.0)),
        max_parts=int(thresholds.get("max_parts", 1000)),
        max_bytes=int(thresholds.get("max_bytes", 1000000)),
        overlap_tolerance=float(thresholds.get("overlap_tolerance", 1.0)),
        overlap_tolerance_geographic=float(
            thresholds.get("overlap_tolerance_geographic", 1.0)
        ),
        sliver_area=float(thresholds.get("sliver_area", 1.0)),
        sliver_area_geographic=float(
            thresholds.get("sliver_area_geographic", 100.0)
        ),
    )


def run_check(
    db,
    table: SpatialTable,
    check: QualityCheck,
    thresholds: Optional[dict] = None,
) -> Optional[int]:
    """Выполнить проверку для таблицы и вернуть число проблемных объектов.

    Возвращает None, если проверка к таблице не применима, и поднимает
    RuntimeError с текстом ошибки PostGIS, если запрос не выполнился.
    """

    if check.key == CHECK_MISSING_INDEX:
        return 0 if table.has_spatial_index else 1
    sql = build_sql(check, table, thresholds)
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


COLUMN_SQL = (
    "SELECT a.attname, t.typname "
    "FROM pg_catalog.pg_attribute a "
    "JOIN pg_catalog.pg_class c ON c.oid = a.attrelid "
    "JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace "
    "JOIN pg_catalog.pg_type t ON t.oid = a.atttypid "
    "WHERE n.nspname = ? AND c.relname = ? AND a.attnum > 0 AND NOT a.attisdropped "
    "  AND NOT EXISTS ("
    "    SELECT 1 FROM pg_catalog.pg_index i "
    "    WHERE i.indrelid = c.oid AND i.indisprimary "
    "      AND a.attnum = ANY (i.indkey)"
    "  ) "
    "ORDER BY a.attnum"
)

TEXT_TYPES = (
    "varchar",
    "bpchar",
    "text",
    "citext",
    "name",
    "char",
)

NUMERIC_TYPES = (
    "int2",
    "int4",
    "int8",
    "numeric",
    "float4",
    "float8",
    "money",
)

DATE_TYPES = ("date", "timestamp", "timestamptz")

# Служебные типы PostGIS: проверять их как атрибуты не имеет смысла.
SPATIAL_TYPES = ("geometry", "geography", "raster", "box2d", "box3d")


def column_kind(type_name: str) -> Optional[str]:
    """Отнести тип PostgreSQL к текстовым, числовым или датам."""

    name = (type_name or "").lower()
    if name in TEXT_TYPES:
        return "text"
    if name in NUMERIC_TYPES:
        return "numeric"
    if name in DATE_TYPES:
        return "date"
    return None


def fetch_attribute_columns(db, table: SpatialTable) -> List[Tuple[str, str]]:
    """Вернуть атрибутивные столбцы таблицы и их вид: (имя, вид)."""

    query = QSqlQuery(db)
    query.prepare(COLUMN_SQL)
    query.addBindValue(table.schema)
    query.addBindValue(table.name)
    columns: List[Tuple[str, str]] = []
    if not query.exec():
        return columns
    while query.next():
        name = str(query.value(0) or "")
        type_name = str(query.value(1) or "")
        if not name or type_name.lower() in SPATIAL_TYPES:
            continue
        kind = column_kind(type_name)
        if kind:
            columns.append((name, kind))
    return columns


DUPLICATE_CATEGORY_FULL = "full"
DUPLICATE_CATEGORY_KEY = "key"
DUPLICATE_CATEGORY_CASE = "case"
DUPLICATE_CATEGORY_PARTIAL = "partial"

# Ограничение на число пар частичных вхождений: проверка не должна
# превращаться в декартово произведение на большой таблице.
PARTIAL_PAIR_LIMIT = 10000
DETAIL_LIMIT = 500


def _text_columns(columns: Sequence[Tuple[str, str]]) -> List[str]:
    """Текстовые столбцы из списка атрибутивных."""

    return [name for name, kind in columns if kind == "text"]


def duplicates_union_sql(
    table: SpatialTable,
    columns: Sequence[Tuple[str, str]],
) -> str:
    """SQL со всеми видами дублей по атрибутам: четыре ветки UNION ALL.

    Каждая ветка возвращает строку (category, a, b, percent): полные дубли
    строк, дубли составного ключа из текстовых столбцов, совпадения без учёта
    регистра и лишних пробелов и частичные вхождения с процентом вхождения
    короткого значения в длинное.
    """

    target = table.qualified
    names = [name for name, _kind in columns]
    quoted = [quote_ident(name) for name in names]
    parts: List[str] = []

    if quoted:
        group = ", ".join(quoted)
        parts.append(
            "(SELECT '{full}' AS category, "
            "concat_ws(' | ', {group})::text AS a, "
            "'×' || count(*)::text AS b, "
            "NULL::numeric AS percent FROM {target} GROUP BY {group} "
            "HAVING count(*) > 1)".format(
                full=DUPLICATE_CATEGORY_FULL, group=group, target=target
            )
        )

    text = _text_columns(columns)
    if text:
        group = ", ".join(quote_ident(name) for name in text)
        parts.append(
            "(SELECT '{key}' AS category, "
            "concat_ws(' | ', {group})::text AS a, "
            "'×' || count(*)::text AS b, "
            "NULL::numeric AS percent FROM {target} GROUP BY {group} "
            "HAVING count(*) > 1)".format(
                key=DUPLICATE_CATEGORY_KEY, group=group, target=target
            )
        )
        for name in text:
            column = quote_ident(name)
            parts.append(
                "(SELECT '{case}' AS category, "
                "lower(regexp_replace(btrim({column}), '\\s+', ' ', 'g'))::text AS a, "
                "string_agg(DISTINCT {column}::text, ' | ') AS b, "
                "NULL::numeric AS percent "
                "FROM {target} WHERE {column} IS NOT NULL "
                "GROUP BY 2 HAVING count(DISTINCT {column}) > 1)".format(
                    case=DUPLICATE_CATEGORY_CASE, column=column, target=target
                )
            )
            parts.append(
                "(SELECT DISTINCT '{partial}' AS category, btrim(a.{column})::text AS a, "
                "btrim(b.{column})::text AS b, "
                "round(100.0 * length(btrim(a.{column})) "
                "  / NULLIF(length(btrim(b.{column})), 0), 1) AS percent "
                "FROM {target} a JOIN {target} b "
                "ON position(btrim(a.{column}) IN btrim(b.{column})) > 0 "
                "AND btrim(a.{column}) <> btrim(b.{column}) "
                "AND length(btrim(a.{column})) >= 3 "
                "LIMIT {limit})".format(
                    partial=DUPLICATE_CATEGORY_PARTIAL,
                    column=column,
                    target=target,
                    limit=PARTIAL_PAIR_LIMIT,
                )
            )

    return "\nUNION ALL\n".join(parts)


def duplicate_details(
    db,
    table: SpatialTable,
    columns: Sequence[Tuple[str, str]],
    limit: int = DETAIL_LIMIT,
) -> List[Tuple[str, str, str, object]]:
    """Подробный список дублей: (вид, значение, совпадение, процент)."""

    union = duplicates_union_sql(table, columns)
    if not union:
        return []
    query = QSqlQuery(db)
    sql = "SELECT category, a, b, percent FROM (" + union + ") AS d LIMIT {}".format(
        int(limit)
    )
    if not query.exec(sql):
        raise RuntimeError(query_error(query, table.full_name))
    rows: List[Tuple[str, str, str, object]] = []
    while query.next():
        percent = query.value(3)
        rows.append(
            (
                str(query.value(0) or ""),
                str(query.value(1) or ""),
                str(query.value(2) or ""),
                None if percent is None else float(percent),
            )
        )
    return rows



def build_attribute_sql(
    check: AttributeCheck,
    table: SpatialTable,
    columns: Sequence[Tuple[str, str]],
) -> Optional[str]:
    """Собрать SQL проверки атрибутов; None — проверка не применима."""

    usable = [
        (name, kind)
        for name, kind in columns
        if check.kind == "all" or kind == check.kind
    ]
    if not usable:
        return None

    def render(template: str, column: str) -> str:
        return template.format(
            col=quote_ident(column),
            table=table.qualified,
        )

    if check.mode == MODE_GROUP:
        names = ", ".join(quote_ident(name) for name, _kind in usable)
        return (
            "SELECT COALESCE(sum(n - 1), 0) FROM (\n"
            "  SELECT count(*) AS n FROM {table}\n"
            "  GROUP BY {columns} HAVING count(*) > 1\n"
            ") AS duplicates"
        ).format(table=table.qualified, columns=names)

    if check.mode == MODE_DUPLICATES:
        union = duplicates_union_sql(table, usable)
        if not union:
            return None
        return "SELECT count(*) FROM (" + union + ") AS d"

    if check.mode == MODE_PER_COLUMN:
        parts = [
            "(" + render(check.condition, name) + ")" for name, _kind in usable
        ]
        return (
            "SELECT COALESCE(sum(c), 0) FROM ("
            + " UNION ALL ".join(parts)
            + ") AS t(c)"
        )

    conditions = " OR ".join(
        "(" + render(check.condition, name) + ")" for name, _kind in usable
    )
    return "SELECT count(*) FROM {table} WHERE {conditions}".format(
        table=table.qualified,
        conditions=conditions,
    )


def run_attribute_check(
    db,
    table: SpatialTable,
    check: AttributeCheck,
    columns: Sequence[Tuple[str, str]],
) -> Optional[int]:
    """Выполнить проверку атрибутов и вернуть число проблемных объектов."""

    sql = build_attribute_sql(check, table, columns)
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


class AttributeTask(QThread):
    """Фоновый поток проверок качества атрибутивных данных."""

    CONNECTION_TAG = "attribute"

    check_started = pyqtSignal(str)  # название проверки (строка-источник)
    check_done = pyqtSignal(str, str, object, str)  # ключ, таблица, итог, ошибка
    check_details = pyqtSignal(str, str, object)  # ключ, таблица, список дублей
    progress = pyqtSignal(int, int)  # (готово, всего)
    finished_all = pyqtSignal(bool, str)  # (отменено, текст ошибки)

    def __init__(
        self,
        connection: PGConnection,
        tables: Sequence[SpatialTable],
        checks: Sequence[AttributeCheck],
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
                    details: List[Tuple[str, str, str, object]] = []
                    try:
                        columns = fetch_attribute_columns(db, table)
                        count = run_attribute_check(db, table, check, columns)
                        if check.mode == MODE_DUPLICATES and count:
                            details = duplicate_details(db, table, columns)
                    except Exception as exc:  # noqa: BLE001
                        error = str(exc)
                    self.check_done.emit(check.key, table.full_name, count, error)
                    if details:
                        self.check_details.emit(check.key, table.full_name, details)
                    done += 1
                    self.progress.emit(done, total)
            self.finished_all.emit(False, "")
        except Exception as exc:  # noqa: BLE001
            self.finished_all.emit(False, str(exc))
        finally:
            if db is not None:
                close_connection(self._connection, self.CONNECTION_TAG)
                db = None


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
        thresholds: Optional[dict] = None,
    ) -> None:
        super().__init__(parent)
        self._connection = connection
        self._tables = list(tables)
        self._checks = list(checks)
        self._thresholds = dict(thresholds) if thresholds else load_thresholds()
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
                        count = run_check(db, table, check, self._thresholds)
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
