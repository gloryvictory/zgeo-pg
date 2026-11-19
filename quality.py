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


MODE_OR = "or"
MODE_PER_COLUMN = "per_column"
MODE_GROUP = "group"

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
]


def check_by_key(key: str):
    """Найти проверку (пространственную или атрибутивную) по её ключу."""

    for check in QUALITY_CHECKS:
        if check.key == key:
            return check
    for check in ATTRIBUTE_CHECKS:
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
    "  )"
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
                    try:
                        columns = fetch_attribute_columns(db, table)
                        count = run_attribute_check(db, table, check, columns)
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
