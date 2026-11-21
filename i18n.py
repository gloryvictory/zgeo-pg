"""Минимальная система переводов интерфейса ZGeo-PG.

Строки-исходники в коде остаются на русском языке. Для английского
интерфейса используется словарь EN_TRANSLATIONS. Такой подход не
требует Qt Linguist и позволяет переключать язык без перезапуска QGIS.
"""

from __future__ import annotations

from typing import Any

LANGUAGE_RU = "ru"
LANGUAGE_EN = "en"
DEFAULT_LANGUAGE = LANGUAGE_RU
LANGUAGE_KEY = "zgeopg/language"

_current_language = DEFAULT_LANGUAGE

EN_TRANSLATIONS = {
    # Общие элементы
    "Готово": "Ready",
    "Схема": "Schema",
    "Схемы": "Schemas",
    "Таблица": "Table",
    "Таблицы": "Tables",
    "Столбец": "Column",
    "Тип": "Type",
    "Тип геометрии": "Geometry type",
    "SRID": "SRID",
    "Система координат": "CRS",
    "Строк (оценка)": "Rows (est.)",
    "Строк (точно)": "Rows (exact)",
    "Строк": "Rows",
    "Объектов": "Features",
    "Элементов": "Features",
    "Размер": "Size",
    "Статистика": "Statistics",
    "Подключения": "Connections",
    "Соединения": "Connections",
    "Информация": "Information",
    "Фильтр": "Filter",
    "Поиск": "Search",
    "Файл": "File",
    "Файлы": "Files",
    "Настройки": "Settings",
    "Комментарий": "Comment",
    "Описание": "Description",

    # Единицы измерения
    "Б": "B",
    "КБ": "KB",
    "МБ": "MB",
    "ГБ": "GB",
    "ТБ": "TB",

    # Соединение
    "Имя": "Name",
    "Хост": "Host",
    "Порт": "Port",
    "База данных": "Database",
    "База": "Database",
    "Пользователь": "User",
    "Пароль": "Password",
    "Подключиться": "Connect",
    "Отключиться": "Disconnect",
    "Обновить": "Refresh",
    "Сохранить соединение": "Save connection",
    "Удалить соединение": "Delete connection",
    "Проверить подключение": "Test connection",
    "Новое соединение": "New connection",
    "Соединение сохранено": "The connection was saved",
    "Не удалось сохранить соединение в SQLite": "Failed to save the connection to SQLite",
    "Сохранённые соединения": "Saved connections",
    "Параметры подключения": "Connection parameters",
    "Загрузить": "Load",
    "Удалить": "Delete",
    "Выбрано: {} из {}": "Selected: {} of {}",
    "Подключено к": "Connected to",
    "Подключено": "Connected",
    "Не подключено": "Not connected",
    "Ошибка подключения": "Connection error",
    "Невозможно подключиться к базе данных": "Unable to connect to the database",
    "Не выбрано соединение": "No connection selected",
    "Драйвер QPSQL не найден": "The QPSQL driver was not found",
    "PostGIS не установлен в базе": "PostGIS is not installed in the database",
    "Не удалось открыть соединение": "Failed to open the connection",
    "из": "of",
    "таблиц": "tables",
    "таблица": "table",
    "Всего таблиц": "Total tables",
    "Всего объектов": "Total features",
    "Всего размер": "Total size",
    "Всего": "Total",
    "Скрыть пустые схемы": "Hide empty schemas",
    "Только с геометрией": "Only with geometry",
    "Пустая геометрия": "Empty geometry",
    "Все схемы": "All schemas",
    "Нет пространственных таблиц": "No spatial tables found",
    "Показаны": "Shown",
    "Пространственный индекс": "Spatial index",
    "Имя пространственного индекса": "Spatial index name",
    "Размер пространственного индекса": "Spatial index size",
    "Размер индексов": "Indexes size",
    "Полный размер": "Full size",
    "Выберите одну таблицу в списке": "Select a single table in the list",
    "Создать пространственный индекс": "Create spatial index",
    "Обновить пространственный индекс": "Refresh spatial index",
    "Удалить пространственный индекс": "Drop spatial index",
    "Удаление пространственного индекса": "Dropping the spatial index",
    "Создать все пространственные индексы": "Create all spatial indexes",
    "Обновить все пространственные индексы": "Refresh all spatial indexes",
    "Пространственный индекс уже создан": "The spatial index already exists",
    "Пространственный индекс не найден": "No spatial index found",
    "Создание пространственного индекса": "Creating the spatial index",
    "Обновление пространственного индекса": "Refreshing the spatial index",
    "Не удалось выполнить операцию": "The operation failed",

    # Статистика
    "По размеру": "By size",
    "По типу": "By type",
    "По типу геометрии": "By geometry type",
    "По схеме": "By schema",
    "Статистика по схемам": "Statistics by schema",
    "Статистика по типу геометрии": "Statistics by geometry type",
    "Другие схемы": "Other schemas",
    "Другие типы": "Other types",
    "Кол-во": "Count",
    "До 1 МБ": "Up to 1 MB",
    "1–10 МБ": "1–10 MB",
    "10–100 МБ": "10–100 MB",
    "100 МБ–1 ГБ": "100 MB–1 GB",
    "1 ГБ и более": "1 GB and more",

    # Экспорт
    "Экспорт в Excel": "Export to Excel",
    "Экспорт в HTML": "Export to HTML",
    "Экспорт": "Export",
    "Не удалось экспортировать таблицу": "Failed to export the table",
    "Таблица экспортирована": "The table was exported",
    "Не удалось открыть проводник": "Failed to open the Explorer",
    "Не удалось экспортировать таблицу:\n{}": "Failed to export the table:\n{}",
    "Таблица экспортирована:\n{}\n\nНе удалось открыть проводник:\n{}": (
        "The table was exported:\n{}\n\nFailed to open the Explorer:\n{}"
    ),
    "Итого": "Total",
    "Итого таблиц": "Total tables",
    "Итого объектов": "Total features",
    "Итого размер": "Total size",

    # Действия и статус
    "Подключение": "Connecting",
    "Чтение характеристик": "Reading characteristics",
    "Отмена": "Cancel",
    "Отменено": "Cancelled",
    "Выбрано": "Selected",
    "Открыть в проводнике": "Open in Explorer",
    "Ошибка": "Error",
    "Предупреждение": "Warning",
    "неизвестна": "unknown",
    "Разные": "Different",
    "Да": "Yes",
    "Нет": "No",
    "—": "—",
    "Обновить список": "Refresh the list",
    "Отменить операцию": "Cancel the operation",

    # Информация о таблице
    "Информация о таблице": "Table information",
    "Полное имя": "Full name",
    "Пространственный тип": "Spatial type",
    "Закрыть": "Close",
    "Атрибутивные столбцы": "Attribute columns",
    "Столбец геометрии": "Geometry column",
    "Геометрия / география": "Geometry / geography",

    # Качество пространственных данных
    "Качество пространственных данных": "Geospatial data quality",
    "Проверки": "Checks",
    "Проверить": "Run checks",
    "Прервать": "Abort",
    "Прерывание": "Stopping",
    "Описание проверки": "Check description",
    "Как исправить": "How to fix",
    "Текущая проверка": "Current check",
    "Подготовка проверок": "Preparing checks",
    "Проверка качества данных": "Data quality check",
    "Проверка прервана": "Check aborted",
    "Найдено проблем: {}": "Problems found: {}",
    "ошибок запросов: {}": "failed queries: {}",
    "Не применимо": "Not applicable",
    "Экспорт результатов проверок": "Export of check results",
    "Результатов нет — нажмите «Проверить»": (
        "There are no results — click \"Run checks\""
    ),
    "Ошибка запроса": "Query failed",
    "Сначала подключитесь к базе данных": "Connect to a database first",
    "Список таблиц пуст — нажмите «Обновить»": (
        "The table list is empty — click \"Refresh\""
    ),
    "Отметьте хотя бы одну проверку": "Select at least one check",
    "Невалидная геометрия": "Invalid geometry",
    "ST_IsValid возвращает false: геометрию нельзя корректно обработать.": (
        "ST_IsValid returns false: the geometry cannot be processed correctly."
    ),
    "Проверка ищет объекты, геометрия которых нарушает правила OGC Simple "
    "Features: самопересечения, дыры вне оболочки, незамкнутые кольца, "
    "аномалии вершин. Используется ST_IsValid, а количество таких объектов "
    "показывается в результатах. Невалидная геометрия ломает буферизацию, "
    "наложение, обрезку и экспорт в другие форматы, а часть операций PostGIS "
    "завершается ошибкой GEOS на всей таблице.": (
        "The check looks for features whose geometry violates the OGC Simple "
        "Features rules: self-intersections, holes outside the shell, unclosed "
        "rings, vertex anomalies. ST_IsValid is used and the number of such "
        "features is shown in the results. Invalid geometry breaks buffering, "
        "overlay, clipping and export to other formats, and some PostGIS "
        "operations fail with a GEOS error for the whole table."
    ),
    "Исправить геометрию запросом UPDATE ... SET geom = ST_MakeValid(geom) "
    "или найти объекты и отредактировать их вручную. Причину невалидности "
    "показывает ST_IsValidReason.": (
        "Repair the geometry with UPDATE ... SET geom = ST_MakeValid(geom) or "
        "find the features and edit them manually. ST_IsValidReason shows the "
        "cause of the invalidity."
    ),
    "Пустая или отсутствующая геометрия": "Empty or missing geometry",
    "Геометрия NULL или ST_IsEmpty: у объекта нет координат.": (
        "Geometry is NULL or ST_IsEmpty: the feature has no coordinates."
    ),
    "Проверка считает строки, в которых геометрический столбец пуст (NULL) "
    "или содержит геометрию без координат (ST_IsEmpty). Такие объекты "
    "попадают в статистику и выгрузки, но не отображаются на карте, а часть "
    "пространственных операций возвращает для них NULL.": (
        "The check counts rows whose geometry column is empty (NULL) or holds a "
        "geometry without coordinates (ST_IsEmpty). Such features appear in "
        "statistics and exports but are not drawn on the map, and some spatial "
        "operations return NULL for them."
    ),
    "Удалить пустые строки или заполнить геометрию: DELETE FROM ... "
    "WHERE geom IS NULL OR ST_IsEmpty(geom).": (
        "Delete the empty rows or fill in the geometry: DELETE FROM ... "
        "WHERE geom IS NULL OR ST_IsEmpty(geom)."
    ),
    "Дублирующиеся геометрии": "Duplicate geometries",
    "Несколько объектов имеют одну и ту же геометрию.": (
        "Several features share the same geometry."
    ),
    "Проверка группирует объекты по геометрии и считает лишние копии, то "
    "есть суммарное число объектов сверх одного в каждой группе. Дубликаты "
    "завышают статистику, дают двойную подпись объектов и мешают объединению "
    "слоёв из разных источников.": (
        "The check groups features by geometry and counts the extra copies, that "
        "is the number of features beyond one in every group. Duplicates "
        "inflate statistics, double the labels and get in the way when layers "
        "from different sources are merged."
    ),
    "Найти повторы запросом SELECT ST_AsEWKB(geom), count(*) ... GROUP BY 1 "
    "HAVING count(*) > 1, затем удалить лишние строки или объединить их "
    "атрибуты.": (
        "Find the repeats with SELECT ST_AsEWKB(geom), count(*) ... GROUP BY 1 "
        "HAVING count(*) > 1, then delete the extra rows or merge their "
        "attributes."
    ),
    "Самопересечения": "Self-intersections",
    "Причина невалидности — самопересечение контура.": (
        "The cause of the invalidity is a self-intersecting ring."
    ),
    "Подмножество проверки валидности: объекты, у которых ST_IsValidReason "
    "начинается с Self-intersection. Это полигоны, контур которых заходит "
    "сам в себя, и линии, проходящие через собственную точку. Такие объекты "
    "нельзя использовать в наложениях, топологических операциях и расчёте "
    "площадей.": (
        "A subset of the validity check: features whose ST_IsValidReason starts "
        "with Self-intersection. These are polygons whose ring crosses itself "
        "and lines passing through their own point. Such features cannot be "
        "used in overlays, topology operations or area calculations."
    ),
    "Исправить через ST_MakeValid или вручную: удалить лишние вершины и "
    "разорвать контур на отдельные части.": (
        "Repair with ST_MakeValid or manually: remove the extra vertices and "
        "split the ring into separate parts."
    ),
    "Смешанные типы геометрии": "Mixed geometry types",
    "Тип объекта не совпадает с типом геометрии таблицы.": (
        "The feature type does not match the geometry type of the table."
    ),
    "Проверка сравнивает GeometryType(geom) с типом, объявленным для "
    "таблицы в geometry_columns. Смешанные типы появляются при загрузке без "
    "ограничения типа и ломают оформление, легенду и выгрузку в Shapefile "
    "или GeoPackage. Для таблиц с типом GEOMETRY проверка не выполняется.": (
        "The check compares GeometryType(geom) with the type declared for the "
        "table in geometry_columns. Mixed types come from loading data without "
        "a type constraint and break styling, the legend and export to "
        "Shapefile or GeoPackage. The check is skipped for GEOMETRY tables."
    ),
    "Привести объекты к одному типу функциями ST_Multi и "
    "ST_CollectionExtract или вынести объекты другого типа в отдельную "
    "таблицу.": (
        "Bring the features to one type with ST_Multi and ST_CollectionExtract "
        "or move the features of the other type into a separate table."
    ),
    "Неверный SRID объектов": "Wrong feature SRID",
    "SRID объекта отличается от SRID таблицы.": (
        "The feature SRID differs from the table SRID."
    ),
    "Проверка считает объекты, у которых ST_SRID(geom) отличается от SRID, "
    "объявленного для таблицы. Обычно это результат вставки геометрии без "
    "SRID (0) или загрузки данных в другой системе координат: такие объекты "
    "отображаются не на своём месте и портят расчёт охвата слоя.": (
        "The check counts features whose ST_SRID(geom) differs from the SRID "
        "declared for the table. Usually this comes from inserting geometry "
        "without an SRID (0) or from loading data in another coordinate system: "
        "such features are drawn in the wrong place and spoil the layer extent."
    ),
    "Задать SRID запросом UPDATE ... SET geom = ST_SetSRID(geom, <SRID>), "
    "если координаты уже в нужной системе, или ST_Transform, если систему "
    "нужно пересчитать.": (
        "Set the SRID with UPDATE ... SET geom = ST_SetSRID(geom, <SRID>) if the "
        "coordinates are already in the right system, or ST_Transform if the "
        "system has to be reprojected."
    ),
    "Координаты вне допустимого диапазона": "Coordinates out of range",
    "Долгота и широта вне пределов или бесконечные координаты.": (
        "Longitude and latitude out of bounds, or infinite coordinates."
    ),
    "Для географических данных (SRID 4326) проверяются пределы долготы от "
    "-180 до 180 и широты от -90 до 90; для остальных систем координат — "
    "наличие бесконечных значений и NaN. Такие объекты растягивают охват "
    "слоя, из-за чего «Приблизить к слою» показывает весь мир, а мозаика и "
    "тайлы строятся неправильно.": (
        "For geographic data (SRID 4326) the longitude range -180 to 180 and the "
        "latitude range -90 to 90 are checked; for other coordinate systems the "
        "presence of infinite values and NaN. Such features stretch the layer "
        "extent, so \"Zoom to layer\" shows the whole world and tiles and "
        "mosaics are built incorrectly."
    ),
    "Найти объекты запросом SELECT * FROM ... WHERE NOT (ST_XMax(geom) "
    "BETWEEN -180 AND 180 ...) и исправить координаты вручную.": (
        "Find the features with SELECT * FROM ... WHERE NOT (ST_XMax(geom) "
        "BETWEEN -180 AND 180 ...) and fix the coordinates manually."
    ),
    "Вырожденные объекты": "Degenerate features",
    "Полигоны нулевой площади и линии нулевой длины.": (
        "Polygons with zero area and lines with zero length."
    ),
    "Проверка ищет объекты без площади (полигон, все вершины которого "
    "совпадают) и без длины (линия из одной точки). На карте они выглядят "
    "как точки, не участвуют в расчёте площадей и создают пустые записи в "
    "выгрузках и отчётах.": (
        "The check looks for features without area (a polygon whose vertices "
        "all coincide) and without length (a line made of one point). On the map "
        "they look like points, contribute nothing to area totals and leave "
        "empty records in exports and reports."
    ),
    "Удалить такие объекты или исправить вершины: SELECT * FROM ... "
    "WHERE ST_Area(geom) = 0.": (
        "Delete such features or fix the vertices: SELECT * FROM ... "
        "WHERE ST_Area(geom) = 0."
    ),
    "Незамкнутые и битые кольца": "Unclosed and broken rings",
    "Кольца полигонов не замкнуты или содержат слишком мало точек.": (
        "Polygon rings are not closed or contain too few points."
    ),
    "Проверка ищет полигоны, у которых причина невалидности связана с "
    "кольцом: незамкнутое кольцо, самопересечение кольца, слишком мало точек "
    "во внешнем или внутреннем кольце. Выполняется только для полигональных "
    "таблиц, остальные пропускаются.": (
        "The check looks for polygons whose invalidity reason is about a ring: "
        "an unclosed ring, a self-intersecting ring, too few points in the outer "
        "or an inner ring. It runs only for polygon tables, the rest are "
        "skipped."
    ),
    "Причину показывает ST_IsValidReason; исправление — ST_MakeValid или "
    "ручная правка вершин в редакторе QGIS.": (
        "ST_IsValidReason shows the cause; the fix is ST_MakeValid or editing "
        "the vertices in the QGIS editor."
    ),
    "Нет пространственного индекса": "No spatial index",
    "У таблицы нет индекса GiST по столбцу геометрии.": (
        "The table has no GiST index on its geometry column."
    ),
    "Сведения берутся из каталога PostGIS: у таблицы отсутствует индекс "
    "GiST или SP-GiST по геометрическому столбцу. Без такого индекса любой "
    "пространственный фильтр читает таблицу целиком, поэтому карта, выборки "
    "и проверки качества работают медленно. Проверка не обращается к данным "
    "таблицы и выполняется мгновенно.": (
        "The information comes from the PostGIS catalog: the table has no GiST "
        "or SP-GiST index on its geometry column. Without such an index every "
        "spatial filter scans the whole table, so the map, selections and "
        "quality checks are slow. The check does not read the table data and "
        "returns instantly."
    ),
    "Построить индекс запросом CREATE INDEX ... USING gist (geom) или "
    "кнопкой «Создать все пространственные индексы» на вкладке «Таблицы».": (
        "Build the index with CREATE INDEX ... USING gist (geom) or with the "
        "\"Create all spatial indexes\" button on the \"Tables\" tab."
    ),

    # Качество атрибутивных данных
    "Качество атрибутивных данных": "Attribute data quality",
    "Пустые значения NULL": "NULL values",
    "В атрибутивных столбцах встречаются значения NULL.": (
        "Attribute columns contain NULL values."
    ),
    "Проверка считает объекты, у которых хотя бы один атрибутивный "
    "столбец (все столбцы, кроме геометрического) не заполнен. Значения "
    "NULL ломают фильтры, соединения и расчёт сводок: строка выпадает "
    "из выборок «WHERE поле = значение» и из подсчёта сумм и средних.": (
        "The check counts features where at least one attribute column (every "
        "column except the geometry one) is empty. NULL values break filters, "
        "joins and summaries: the row drops out of \"WHERE field = value\" "
        "selections and out of sum and average calculations."
    ),
    "Заполнить обязательные поля или запретить пустые значения "
    "ограничением ALTER TABLE ... ALTER COLUMN ... SET NOT NULL.": (
        "Fill in the required fields or forbid empty values with ALTER TABLE "
        "... ALTER COLUMN ... SET NOT NULL."
    ),
    "Пустые строки": "Empty strings",
    "В текстовых столбцах есть значения из пробелов или пустые строки.": (
        "Text columns contain empty strings or strings of spaces."
    ),
    "Проверка ищет строки, где текстовое поле пустое или состоит только "
    "из пробелов. От NULL такие значения не отличаются для "
    "пользователя, но ведут себя иначе в запросах: IS NULL их не "
    "находит, а сортировка и группировка дают отдельную группу.": (
        "The check looks for rows where a text field is empty or contains only "
        "spaces. To the user such values look like NULL, but they behave "
        "differently in queries: IS NULL does not find them and sorting and "
        "grouping put them into a separate group."
    ),
    "Заменить пустые строки на NULL или на осмысленное значение: "
    "UPDATE ... SET поле = NULL WHERE btrim(поле) = ''.": (
        "Replace the empty strings with NULL or with a meaningful value: "
        "UPDATE ... SET field = NULL WHERE btrim(field) = ''."
    ),
    "Пробелы по краям значений": "Leading and trailing spaces",
    "Текстовые значения начинаются или заканчиваются пробелом.": (
        "Text values start or end with a space."
    ),
    "Проверка ищет значения с ведущими или замыкающими пробелами, "
    "табуляцией и переводами строк. Такие значения не совпадают при "
    "сравнении и соединении: «Москва» и «Москва » считаются разными, "
    "из-за чего ломаются справочники, фильтры и связи между слоями.": (
        "The check looks for values with leading or trailing spaces, tabs and "
        "line breaks. Such values do not match on comparison and join: "
        "\"Moscow\" and \"Moscow \" count as different, which breaks "
        "reference lists, filters and links between layers."
    ),
    "Очистить значения от лишних пробелов: UPDATE ... SET поле = "
    "btrim(поле).": (
        "Strip the extra spaces: UPDATE ... SET field = btrim(field)."
    ),
    "Двойные пробелы внутри значений": "Double spaces inside values",
    "В тексте встречаются два и более пробела подряд.": (
        "The text contains two or more spaces in a row."
    ),
    "Проверка находит значения, внутри которых стоят два и более "
    "пробела подряд. Обычно это следствие ручного ввода или склейки "
    "полей, и такие записи не находятся поиском по точному значению и "
    "выглядят неряшливо в отчётах.": (
        "The check finds values with two or more spaces in a row inside them. "
        "This usually comes from manual input or from concatenated fields, and "
        "such records are not found by an exact match search and look untidy "
        "in reports."
    ),
    "Заменить повторяющиеся пробелы одним: UPDATE ... SET поле = "
    "regexp_replace(поле, '\\s+', ' ', 'g').": (
        "Replace the repeated spaces with one: UPDATE ... SET field = "
        "regexp_replace(field, '\\s+', ' ', 'g')."
    ),
    "Дублирующиеся записи": "Duplicate records",
    "Полностью совпадающие атрибутивные записи в таблице.": (
        "Attribute records in the table that match completely."
    ),
    "Проверка группирует объекты по всем атрибутивным столбцам и "
    "считает лишние копии. Полные дубликаты завышают статистику, "
    "приводят к двойным подписям на карте и мешают объединению данных "
    "из разных источников.": (
        "The check groups features by all attribute columns and counts the "
        "extra copies. Complete duplicates inflate statistics, double the map "
        "labels and get in the way when data from different sources is merged."
    ),
    "Найти повторы запросом SELECT столбцы, count(*) ... GROUP BY "
    "столбцы HAVING count(*) > 1 и удалить лишние строки.": (
        "Find the repeats with SELECT columns, count(*) ... GROUP BY columns "
        "HAVING count(*) > 1 and delete the extra rows."
    ),
    "Числа, записанные как текст": "Numbers stored as text",
    "В текстовом столбце значение целиком состоит из числа.": (
        "A text column holds values that are entirely numeric."
    ),
    "Проверка ищет текстовые столбцы, где значение является числом. "
    "Обычно так выглядят поля, которые нужно хранить числом: "
    "идентификаторы, площади, коды. Из-за текстового типа сравнение идёт "
    "по алфавиту («10» меньше «9») и невозможны арифметические операции.": (
        "The check looks for text columns whose values are numbers. Fields "
        "that should be stored as numbers look like this: identifiers, areas, "
        "codes. Because of the text type the comparison is alphabetical "
        "(\"10\" is less than \"9\") and arithmetic operations are "
        "impossible."
    ),
    "Изменить тип столбца с приведением значений: ALTER TABLE ... "
    "ALTER COLUMN ... TYPE numeric USING поле::numeric.": (
        "Change the column type converting the values: ALTER TABLE ... "
        "ALTER COLUMN ... TYPE numeric USING field::numeric."
    ),
    "Управляющие и невидимые символы": "Control and invisible characters",
    "В тексте есть табуляция, переводы строк и другие служебные символы.": (
        "The text contains tabs, line breaks and other service characters."
    ),
    "Проверка ищет управляющие символы (табуляция, перевод строки, "
    "возврат каретки) и невидимые символы в текстовых значениях. Они "
    "портят вёрстку подписей и отчётов, ломают разбор CSV и мешают "
    "сравнению строк.": (
        "The check looks for control characters (tabs, line feeds, carriage "
        "returns) and invisible characters in text values. They ruin the "
        "layout of labels and reports, break CSV parsing and get in the way of "
        "string comparison."
    ),
    "Удалить служебные символы: UPDATE ... SET поле = "
    "regexp_replace(поле, '[[:cntrl:]]', '', 'g').": (
        "Remove the service characters: UPDATE ... SET field = "
        "regexp_replace(field, '[[:cntrl:]]', '', 'g')."
    ),
    "Аномальная длина текста": "Abnormal text length",
    "Длина значения резко отличается от средней по столбцу.": (
        "The value length differs sharply from the column average."
    ),
    "Для каждого текстового столбца считается средняя длина значения и "
    "стандартное отклонение, затем ищутся значения длиннее среднего "
    "более чем на три отклонения. Так находятся обрезанные поля "
    "справочника и, наоборот, значения со склеенным или лишним текстом.": (
        "For every text column the average value length and the standard "
        "deviation are calculated, then the values longer than the average by "
        "more than three deviations are searched for. This finds truncated "
        "reference fields and, the other way round, values with glued or extra "
        "text."
    ),
    "Просмотреть найденные значения и привести их к длине, принятой в "
    "справочнике: SELECT * FROM ... ORDER BY length(поле) DESC.": (
        "Review the found values and bring them to the length accepted in the "
        "reference list: SELECT * FROM ... ORDER BY length(field) DESC."
    ),
    "Выбросы в числовых столбцах": "Outliers in numeric columns",
    "Числовое значение выходит за три стандартных отклонения.": (
        "A numeric value falls outside three standard deviations."
    ),
    "Для каждого числового столбца считается среднее и стандартное "
    "отклонение, затем ищутся значения вне диапазона «среднее ± 3 "
    "отклонения». Обычно это опечатки в разрядах и нулевые значения "
    "вместо пропусков; они сильно искажают суммы и средние в сводках.": (
        "For every numeric column the average and the standard deviation are "
        "calculated, then the values outside the \"average +/- 3 deviations\" "
        "range are searched for. Usually these are typos in digits and zeros "
        "used instead of empty values; they distort sums and averages in "
        "summaries a lot."
    ),
    "Проверить найденные значения и исправить или заменить на NULL: "
    "SELECT * FROM ... ORDER BY поле DESC LIMIT 100.": (
        "Review the found values and fix them or replace them with NULL: "
        "SELECT * FROM ... ORDER BY field DESC LIMIT 100."
    ),
    "Даты вне разумного диапазона": "Dates out of the reasonable range",
    # Дубли по атрибутам
    "Дубли по атрибутам ( очень долго! )": (
        "Attribute duplicates (very slow!)"
    ),
    "Полные дубли строк": "Exact duplicate rows",
    "Дубли составного ключа": "Composite key duplicates",
    "Совпадения без учёта регистра и пробелов": (
        "Matches ignoring case and spaces"
    ),
    "Частичные вхождения": "Partial matches",
    "Вид дубля": "Duplicate kind",
    "Совпадение": "Match",
    "Процент вхождения": "Match percentage",
    "Записей в списке: {}": "Rows in the list: {}",
    "Дата раньше 1900 года или позже чем через год от текущей.": (
        "The date is before 1900 or later than a year from today."
    ),
    "Проверка ищет значения дат и отметок времени раньше 1900 года и "
    "позже года от текущей даты. Так выглядят даты, записанные в "
    "неверном формате, и результат подстановки нулевой даты. Такие "
    "значения ломают временные фильтры и хронологию в отчётах.": (
        "The check looks for date and timestamp values before 1900 and later "
        "than a year from today. Dates written in a wrong format and the "
        "result of a zero date substitution look like this. Such values break "
        "time filters and the chronology in reports."
    ),
    "Исправить даты вручную или заменить невозможные значения на NULL: "
    "UPDATE ... SET поле = NULL WHERE поле < DATE '1900-01-01'.": (
        "Fix the dates manually or replace the impossible values with NULL: "
        "UPDATE ... SET field = NULL WHERE field < DATE '1900-01-01'."
    ),

    # Пороги проверок качества
    "Пороги проверок": "Check thresholds",
    "Пороги": "Thresholds",
    "Максимум вершин в объекте": "Maximum vertices per feature",
    "Минимальная площадь полигона": "Minimum polygon area",
    "Минимальная площадь полигона, м²": "Minimum polygon area, m²",
    "Максимум частей в объекте": "Maximum parts per feature",
    "Максимум размера геометрии, байт": "Maximum geometry size, bytes",
    "Устаревание статистики, дней": "Statistics staleness, days",
    "Тип геометрии не задан": "Geometry type is not specified",
    "Столбец объявлен как geometry без типа и SRID.": (
        "The column is declared as geometry without type and SRID."
    ),
    "SRID не зарегистрирован": "SRID is not registered",
    "Кода SRID таблицы нет в spatial_ref_sys.": (
        "The table SRID is missing from spatial_ref_sys."
    ),
    "Геометрия допускает NULL": "Geometry allows NULL",
    "У геометрического столбца нет ограничения NOT NULL.": (
        "The geometry column has no NOT NULL constraint."
    ),
    "Индекс по геометрии не GiST": "The geometry index is not GiST",
    "Пространственный столбец индексирован не GiST и не SP-GiST.": (
        "The spatial column is indexed with something other than GiST or SP-GiST."
    ),
    "Лишние пространственные индексы": "Redundant spatial indexes",
    "По столбцу геометрии построено больше одного GiST-индекса.": (
        "The geometry column has more than one GiST index."
    ),
    "Устаревшая статистика таблицы": "Stale table statistics",
    "ANALYZE не запускался дольше заданного числа дней.": (
        "ANALYZE has not run for longer than the configured number of days."
    ),
    "Самопересекающиеся линии": "Self-intersecting lines",
    "Линия проходит через собственную точку.": (
        "The line passes through its own point."
    ),
    "Перепутаны широта и долгота": "Swapped latitude and longitude",
    "Для SRID 4326 координаты похожи на перевёрнутые оси.": (
        "For SRID 4326 the coordinates look like swapped axes."
    ),
    "Слишком много вершин": "Too many vertices",
    "Объект содержит больше вершин, чем задано порогом.": (
        "The feature has more vertices than the configured threshold."
    ),
    "Микрообъекты": "Tiny polygons",
    "Площадь полигона меньше порога из настроек.": (
        "The polygon area is below the configured threshold."
    ),
    "Лишняя размерность Z или M": "Extra Z or M dimension",
    "Геометрия имеет Z или M там, где ожидается плоская 2D.": (
        "The geometry has Z or M where a flat 2D is expected."
    ),
    "Коллекции геометрий": "Geometry collections",
    "Объект имеет тип GEOMETRYCOLLECTION.": (
        "The feature is a GEOMETRYCOLLECTION."
    ),
    "Слишком много частей в объекте": "Too many parts per feature",
    "Число частей мультигеометрии выше порога из настроек.": (
        "The number of parts in the multi-geometry is above the configured threshold."
    ),
    "Очень крупная геометрия": "Very large geometry",
    "Размер геометрии в байтах выше порога из настроек.": (
        "The geometry size in bytes is above the configured threshold."
    ),
    "Дыры в полигонах": "Holes in polygons",
    "У полигона есть внутренние кольца.": "The polygon has interior rings.",

    "Сведения берутся из системного каталога: у геометрического столбца нет ограничения типа (typmod), поэтому в таблице могут оказаться точки, линии и полигоны одновременно. Без ограничения типа PostGIS не проверяет корректность вставки, а QGIS не может построить оформление и легенду по типу слоя. Проверка мгновенная: данные таблицы не читаются.": (
        "The information comes from the system catalog: the geometry column has no type constraint (typmod), so the table may hold points, lines and polygons at once. Without a type constraint PostGIS does not validate inserts and QGIS cannot build styling and a legend from the layer type. The check is instant: the table data is not read."
    ),
    "Задать тип и SRID ограничением: ALTER TABLE ... ALTER COLUMN geom TYPE geometry(Point, 4326) USING geom::geometry(Point, 4326).": (
        "Set the type and SRID with a constraint: ALTER TABLE ... ALTER COLUMN geom TYPE geometry(Point, 4326) USING geom::geometry(Point, 4326)."
    ),
    "Каталог PostGIS сообщает SRID, которого нет в spatial_ref_sys: PostGIS не знает параметров этой системы координат. Объекты отображаются в неизвестной системе, ST_Transform невозможен, а расчёт площадей и длин даёт неверные числа. Проверка выполняется по каталогу и не читает данные.": (
        "The PostGIS catalog reports an SRID that is missing from spatial_ref_sys: PostGIS does not know the parameters of that coordinate system. Features are drawn in an unknown system, ST_Transform is impossible and area and length calculations give wrong numbers. The check runs over the catalog and does not read the data."
    ),
    "Добавить систему координат в spatial_ref_sys или пересоздать столбец с корректным SRID: ALTER TABLE ... ALTER COLUMN geom TYPE geometry(Point, <SRID>) USING ST_SetSRID(geom, <SRID>).": (
        "Add the coordinate system to spatial_ref_sys or recreate the column with a valid SRID: ALTER TABLE ... ALTER COLUMN geom TYPE geometry(Point, <SRID>) USING ST_SetSRID(geom, <SRID>)."
    ),
    "Каталог показывает, что столбец геометрии допускает пустые значения. Пока ограничения нет, любой импорт или ручная вставка может добавить объект без координат, и такие строки всплывут позже как «пустая геометрия». Ограничение ставится один раз и закрывает эту возможность. Проверка мгновенная.": (
        "The catalog shows that the geometry column allows empty values. While the constraint is missing, any import or manual insert can add a feature without coordinates, and such rows show up later as empty geometry. The constraint is set once and closes that possibility. The check is instant."
    ),
    "Убедиться, что пустых объектов нет, и запретить их: ALTER TABLE ... ALTER COLUMN geom SET NOT NULL.": (
        "Make sure there are no empty features and forbid them: ALTER TABLE ... ALTER COLUMN geom SET NOT NULL."
    ),
    "По столбцу геометрии построен индекс другого типа (btree, hash) — PostGIS не использует его в пространственных операторах. Такой индекс занимает место и замедляет вставку, но не ускоряет фильтры ST_Intersects, ST_DWithin и поиск по рамке. Сведения берутся из каталога, данные не читаются.": (
        "The geometry column has an index of another type (btree, hash) which PostGIS does not use for spatial operators. Such an index takes space and slows inserts down but does not speed up ST_Intersects, ST_DWithin or bounding box searches. The information comes from the catalog, the data is not read."
    ),
    "Удалить бесполезный индекс и построить GiST: DROP INDEX ...; CREATE INDEX ... ON ... USING gist (geom).": (
        "Drop the useless index and build a GiST one: DROP INDEX ...; CREATE INDEX ... ON ... USING gist (geom)."
    ),
    "Каталог показывает два и более GiST-индекса по одному и тому же столбцу геометрии. Планировщик использует только один, а каждый лишний занимает диск и замедляет каждую вставку и обновление. Обычно так остаётся после экспериментов с индексами. Проверка мгновенная, данные не читаются.": (
        "The catalog shows two or more GiST indexes on the same geometry column. The planner uses only one of them, while every extra index takes disk space and slows every insert and update. This usually stays behind after index experiments. The check is instant and does not read the data."
    ),
    "Оставить один индекс и удалить остальные: DROP INDEX ... для каждого лишнего GiST-индекса.": (
        "Keep one index and drop the rest: DROP INDEX ... for every extra GiST index."
    ),
    "PostgreSQL хранит дату последнего ANALYZE. Если она старше порога из настроек (по умолчанию 30 дней) или её нет, планировщик оценивает количество строк по устаревшим данным: пространственные фильтры начинают читать таблицу целиком, а сводки и проверки качества идут в разы дольше. Сведения берутся из pg_stat_user_tables, данные не читаются.": (
        "PostgreSQL stores the date of the last ANALYZE. If it is older than the threshold from the settings (30 days by default) or missing, the planner estimates row counts from outdated data: spatial filters start reading the whole table and summaries and quality checks take many times longer. The information comes from pg_stat_user_tables, the data is not read."
    ),
    "Обновить статистику: ANALYZE <схема>.<таблица>; при частых изменениях проверить настройки autovacuum.": (
        "Refresh the statistics: ANALYZE <schema>.<table>; with frequent changes check the autovacuum settings."
    ),
    "Проверка ищет линии, которые не являются простыми: контур заходит сам в себя или линия дважды проходит через одну точку. ST_IsValid для линий это не проверяет, поэтому обычная проверка валидности такие объекты пропускает. Непростые линии дают некорректную длину, ломают маршрутизацию и топологические операции.": (
        "The check looks for lines that are not simple: the path crosses itself or the line passes through the same point twice. ST_IsValid does not test this for lines, so the usual validity check skips such features. Non-simple lines give a wrong length and break routing and topology operations."
    ),
    "Разрезать линию на простые части: ST_LineMerge или ST_Node(geom), затем проверить результат ST_IsSimple.": (
        "Split the line into simple parts: ST_LineMerge or ST_Node(geom), then verify the result with ST_IsSimple."
    ),
    "Для географических данных проверяется признак перевёрнутых осей: долгота по модулю не больше 90, а широта больше 90 — значит координаты вставлены как (широта, долгота). Такие объекты уезжают на другой конец планеты, и «Приблизить к слою» показывает весь мир. Проверка выполняется только для SRID 4326.": (
        "For geographic data the check looks for swapped axes: the longitude modulo is at most 90 while the latitude is above 90, which means the coordinates were inserted as (latitude, longitude). Such features move to the other side of the planet and Zoom to layer shows the whole world. The check runs only for SRID 4326."
    ),
    "Поменять координаты местами: UPDATE ... SET geom = ST_FlipCoordinates(geom) WHERE ... — только для найденных объектов.": (
        "Swap the coordinates: UPDATE ... SET geom = ST_FlipCoordinates(geom) WHERE ... — only for the found features."
    ),
    "Сравнивается число вершин объекта (ST_NPoints) с порогом из настроек — по умолчанию 10 000. Такие объекты появляются после сложения геометрий без упрощения и делают слой тяжёлым: QGIS долго рисует карту, медленно работают выборки и экспорт. Порог задаётся на вкладке проверок.": (
        "The number of vertices (ST_NPoints) is compared with the threshold from the settings — 10 000 by default. Such features appear after merging geometries without simplification and make the layer heavy: QGIS draws the map slowly and selections and exports are slow. The threshold is set on the checks tab."
    ),
    "Упростить геометрию: UPDATE ... SET geom = ST_SimplifyPreserveTopology(geom, <допуск>) или ST_Subdivide для очень длинных объектов.": (
        "Simplify the geometry: UPDATE ... SET geom = ST_SimplifyPreserveTopology(geom, <tolerance>) or ST_Subdivide for very long features."
    ),
    "Проверка ищет полигоны с площадью меньше порога — по умолчанию 1 квадратная единица. Такие «осколки» обычно остаются после обрезки и наложения слоёв, засоряют атрибутивные таблицы и попадают в отчёты как полноценные объекты. Для географических данных площадь считается в квадратных метрах.": (
        "The check looks for polygons whose area is below the threshold — 1 square unit by default. Such splinters usually stay behind after clipping and overlaying layers, clutter the attribute table and end up in reports as full features. For geographic data the area is measured in square metres."
    ),
    "Удалить осколки или объединить их с соседями: DELETE FROM ... WHERE ST_Area(geom) < <порог>.": (
        "Delete the splinters or merge them with neighbours: DELETE FROM ... WHERE ST_Area(geom) < <threshold>."
    ),
    "Проверка ищет объекты с третьей координатой или измерением M (ST_NDims и ST_Zmflag). Разная размерность в одном столбце ломает сравнение геометрий, мешает экспорту в простые форматы и даёт неожиданные результаты в операциях наложения.": (
        "The check looks for features with a third coordinate or an M measure (ST_NDims and ST_Zmflag). Mixed dimensionality in one column breaks geometry comparison, prevents export to simple formats and gives unexpected results in overlay operations."
    ),
    "Привести объекты к 2D: UPDATE ... SET geom = ST_Force2D(geom), затем задать тип столбца geometry(<Тип>, <SRID>).": (
        "Bring the features to 2D: UPDATE ... SET geom = ST_Force2D(geom), then set the column type to geometry(<Type>, <SRID>)."
    ),
    "Проверка ищет объекты-коллекции, в которых смешаны точки, линии и полигоны. Коллекции не поддерживаются частью операций PostGIS и плохо отображаются в QGIS: оформление задаётся по одному типу, экспорт в Shapefile такие объекты теряет.": (
        "The check looks for collection features that mix points, lines and polygons. Collections are not supported by part of the PostGIS operations and are drawn poorly in QGIS: styling is set per single type and a Shapefile export loses such features."
    ),
    "Разобрать коллекции на однотипные объекты: ST_CollectionExtract(geom, 1|2|3) или ST_Dump с созданием отдельных строк.": (
        "Split the collections into single-type features: ST_CollectionExtract(geom, 1|2|3) or ST_Dump writing the parts as separate rows."
    ),
    "Сравнивается ST_NumGeometries с порогом — по умолчанию 1000. Объект из тысяч частей (например, мультиполигон всей страны) рисуется и обрабатывается как единое целое: одна операция блокирует таблицу на минуты, а редактор QGIS зависает при выделении такого объекта.": (
        "ST_NumGeometries is compared with the threshold — 1000 by default. A feature of thousands of parts (for example a multipolygon of a whole country) is drawn and processed as a whole: one operation locks the table for minutes and the QGIS editor freezes when such a feature is selected."
    ),
    "Разделить объект: ST_Subdivide(geom, <число вершин>) с записью частей отдельными строками.": (
        "Split the feature: ST_Subdivide(geom, <vertex count>) writing the parts as separate rows."
    ),
    "Сравнивается pg_column_size(geom) с порогом — по умолчанию 1 МБ. Крупные объекты вычитываются целиком при любом обращении, из-за чего карта и проверки качества замедляются, а TOAST-таблица растёт быстрее данных.": (
        "pg_column_size(geom) is compared with the threshold — 1 MB by default. Large features are read entirely on any access, so the map and the quality checks slow down and the TOAST table grows faster than the data."
    ),
    "Упростить или разбить объект: ST_SimplifyPreserveTopology или ST_Subdivide.": (
        "Simplify or split the feature: ST_SimplifyPreserveTopology or ST_Subdivide."
    ),
    "Проверка ищет полигоны с внутренними кольцами (ST_NumInteriorRings). Иногда дыры нужны, но чаще это следствие плохого наложения или обрезки: объект разваливается на кольцо, и площадь считается меньше настоящей. Список таких объектов помогает быстро понять, где геометрия испорчена.": (
        "The check looks for polygons with interior rings (ST_NumInteriorRings). Sometimes holes are intended, but more often they are the result of a bad overlay or clipping: the feature falls apart into a ring and the area is counted as smaller than it is. The list of such features shows quickly where the geometry is damaged."
    ),
    "Проверить дыры на карте и при необходимости залить их: ST_MakePolygon(ST_ExteriorRing(geom)).": (
        "Inspect the holes on the map and fill them in when needed: ST_MakePolygon(ST_ExteriorRing(geom))."
    ),
    "Дубли по атрибутам": (
        "Attribute duplicates"
    ),
    "Сохранить": (
        "Save"
    ),

    "Полные дубли строк, дубли составного ключа, совпадения без учёта регистра и частичные вхождения.": (
        "Exact duplicate rows, composite key duplicates, matches ignoring case and partial matches."
    ),
    "Одна проверка объединяет четыре вида дублей по атрибутам: полные дубли строк (совпадают все атрибутивные столбцы), дубли составного ключа (совпадают все текстовые столбцы), совпадения без учёта регистра и лишних пробелов («Москва» и «москва ») и частичные вхождения — когда значение целиком входит в другое значение, например «ЯмалоНенецкий автономный окру» входит в «ЯмалоНенецкий автономный округ». Для частичных вхождений показывается процент вхождения — доля длины короткого значения в длинном. Дубли завышают статистику, дают двойные подписи на карте и мешают объединять данные из разных источников. Подробный список с процентами открывается двойным щелчком по ячейке.": (
        "One check unites four kinds of attribute duplicates: exact duplicate rows (all attribute columns match), composite key duplicates (all text columns match), matches ignoring case and repeated spaces (\"Moscow\" and \"moscow \") and partial matches, when one value is contained in another, for example \"Yamalo-Nenets autonomous okru\" is contained in \"Yamalo-Nenets autonomous okrug\". Partial matches carry the match percentage, the share of the shorter value in the longer one. Duplicates inflate statistics, double the map labels and get in the way when data from different sources is merged. The detailed list with percentages opens on a double click on the cell."
    ),
    "Просмотреть подробный список двойным щелчком по ячейке и объединить или удалить лишние записи; для совпадений без учёта регистра привести значения к единому написанию, для частичных вхождений — заменить обрезанное значение полным.": (
        "Open the detailed list with a double click on the cell and merge or delete the extra records; for case-insensitive matches bring the values to one spelling, for partial matches replace the truncated value with the full one."
    ),

    "По спецификации OGC внешнее кольцо полигона обходится против часовой стрелки, внутренние — по часовой. Проверка сравнивает геометрию с ST_ForcePolygonCCW: если они различаются, ориентация обратная. Часть ГИС и форматов (Shapefile, некоторые веб-сервисы) ожидают именно такую ориентацию, иначе полигон рисуется «вывернутым» или считается внешней областью.": (
        "By the OGC specification the outer ring of a polygon is walked counter-clockwise and the inner rings clockwise. The check compares the geometry with ST_ForcePolygonCCW: if they differ, the orientation is reversed. Part of the GIS and formats (Shapefile, some web services) expect exactly this orientation, otherwise the polygon is drawn inverted or is treated as the outer area."
    ),
    "Привести ориентацию колец к спецификации: UPDATE ... SET geom = ST_ForcePolygonCCW(geom).": (
        "Bring the ring orientation to the specification: UPDATE ... SET geom = ST_ForcePolygonCCW(geom)."
    ),
    "Проверка ищет линии с длиной меньше порога — по умолчанию 1 единица. Такие обрезки появляются после наложения и обрезки слоёв и выглядят на карте точками: они завышают количество объектов, мешают генерализации и попадают в отчёты как самостоятельные дороги или реки. Для географических данных длина считается в метрах.": (
        "The check looks for lines shorter than the threshold — 1 unit by default. Such clippings stay behind after overlaying and clipping layers and look like points on the map: they inflate the feature count, get in the way of generalisation and end up in reports as separate roads or rivers. For geographic data the length is measured in metres."
    ),
    "Удалить обрезки или объединить их с соседними линиями: DELETE FROM ... WHERE ST_Length(geom) < <порог>.": (
        "Delete the clippings or merge them with neighbouring lines: DELETE FROM ... WHERE ST_Length(geom) < <threshold>."
    ),
    "Проверка ищет полигоны, у которых внутреннее кольцо лежит вне внешней оболочки: PostGIS сообщает причину «Hole lies outside shell». Обычно это следствие ручной правки или неудачного объединения: дыра «висит» снаружи и вырезает чужие территории, из-за чего ломается расчёт площадей при наложении.": (
        "The check looks for polygons whose inner ring lies outside the outer shell: PostGIS reports the reason Hole lies outside shell. Usually this comes from manual editing or a failed merge: the hole hangs outside and cuts out other territories, which breaks area calculations on overlay."
    ),
    "Удалить или залить внешние дыры: ST_MakePolygon(ST_ExteriorRing(geom)) либо исправить кольца вручную в редакторе QGIS.": (
        "Delete or fill the outside holes: ST_MakePolygon(ST_ExteriorRing(geom)) or fix the rings manually in the QGIS editor."
    ),
    "Кольца против часовой стрелки": "Clockwise ring orientation",
    "Ориентация внешнего кольца не по спецификации OGC.": "The outer ring orientation does not follow the OGC specification.",
    "Микролинии": "Tiny lines",
    "Длина линии меньше порога из настроек.": "The line length is below the configured threshold.",
    "Дыры за пределами полигона": "Holes outside the polygon",
    "Внутреннее кольцо выходит за внешнюю оболочку.": "The inner ring lies outside the outer shell.",
    "Минимальная длина линии": "Minimum line length",
    "Минимальная длина линии, м": "Minimum line length, m",

    "По спецификации OGC внешнее кольцо полигона обходится против часовой стрелки, внутренние — по часовой. Проверка сравнивает геометрию с ST_ForcePolygonCCW: если порядок вершин отличается, ориентация обратная. Часть ГИС и форматов (Shapefile, некоторые веб-сервисы) ожидают именно такую ориентацию, иначе полигон рисуется «вывернутым» или считается внешней областью.": (
        "By the OGC specification the outer ring of a polygon is walked counter-clockwise and the inner rings clockwise. The check compares the geometry with ST_ForcePolygonCCW: if the vertex order differs, the orientation is reversed. Part of the GIS and formats (Shapefile, some web services) expect exactly this orientation, otherwise the polygon is drawn inverted or is treated as the outer area."
    ),


    "Пересечения полигонов внутри слоя": "Overlaps between polygons of the same layer",
    "Полигоны одного слоя накладываются друг на друга.": "Polygons of one layer overlap each other.",
    "Проверка ищет пары объектов одного слоя, которые пересекаются с ненулевой площадью (ST_Overlaps). В корректном полигональном слое объекты могут касаться границами, но не накладываться: наложения дают двойной учёт площади, ломают пространственные соединения и приводят к тому, что один и тот же участок попадает в два района. Проверка тяжёлая: это соединение таблицы с самой собой по рамке (&&), поэтому по умолчанию выключена и включается вручную.": (
        "The check looks for pairs of features in the same layer that intersect with a non-zero area (ST_Overlaps). A valid polygon layer may touch along boundaries but must not overlap: overlaps double-count the area, break spatial joins and put the same patch of land into two districts. The check is heavy: it joins the table with itself on the bounding box (&&), so it is switched off by default and enabled manually."
    ),
    "Найти пары запросом SELECT a.id, b.id FROM ... a JOIN ... b ON a.geom && b.geom AND ST_Overlaps(a.geom, b.geom) и устранить наложение: разрезать объекты (ST_Difference) или объединить их (ST_Union).": (
        "Find the pairs with SELECT a.id, b.id FROM ... a JOIN ... b ON a.geom && b.geom AND ST_Overlaps(a.geom, b.geom) and remove the overlap: cut the features (ST_Difference) or merge them (ST_Union)."
    ),
    "Почти дубли геометрий": "Near-duplicate geometries",
    "Объекты совпадают со сдвигом в пределах допуска.": "Features match within the tolerance distance.",
    "Проверка ищет пары объектов одного слоя, расстояние между которыми меньше допуска из настроек — по умолчанию 1 единица, для географических данных 1 метр. Так выглядят объекты, загруженные дважды с небольшим сдвигом или оцифрованные повторно: они выдают себя за разные записи, но описывают одно и то же место. Точное сравнение геометрий такие пары не находит. Проверка тяжёлая (соединение таблицы с самой собой), по умолчанию выключена.": (
        "The check looks for pairs of features in the same layer whose distance is below the threshold from the settings — 1 unit by default, 1 metre for geographic data. This is how features look when they were loaded twice with a small shift or digitised again: they pose as separate records but describe the same place. An exact geometry comparison does not find such pairs. The check is heavy (it joins the table with itself) and is switched off by default."
    ),
    "Сравнить пары запросом SELECT a.id, b.id, ST_Distance(a.geom, b.geom) ... WHERE ST_DWithin(a.geom, b.geom, <допуск>) и удалить лишнюю запись.": (
        "Compare the pairs with SELECT a.id, b.id, ST_Distance(a.geom, b.geom) ... WHERE ST_DWithin(a.geom, b.geom, <tolerance>) and delete the extra record."
    ),
    "Сливеры (узкие щели)": "Slivers (narrow gaps)",
    "Полигоны касаются друг друга с почти нулевой площадью наложения.": "Polygons touch with a nearly zero overlap area.",
    "Проверка ищет пары полигонов одного слоя, которые касаются границами, но наложение у них меньше порога из настроек — по умолчанию 1 квадратная единица, для географических данных 1 м². Такие «сливеры» остаются после неточной оцифровки смежных границ и после оверлеев: вместо общей границы между объектами появляется тонкая щель или нахлёст. Проверка тяжёлая (соединение таблицы с самой собой), по умолчанию выключена.": (
        "The check looks for pairs of polygons in the same layer that touch along boundaries with an overlap below the threshold from the settings — 1 square unit by default, 100 m² for geographic data. Such slivers stay behind after imprecise digitising of shared borders and after overlays: instead of a common border there is a thin gap or overlap. The check is heavy (it joins the table with itself) and is switched off by default."
    ),
    "Сшить границы соседних объектов: ST_Snap(a.geom, b.geom, <допуск>) для каждой пары или пересобрать слой топологически.": (
        "Stitch the borders of neighbouring features: ST_Snap(a.geom, b.geom, <tolerance>) for each pair or rebuild the layer topologically."
    ),
    "Допуск для почти дублей": "Tolerance for near duplicates",
    "Допуск для почти дублей, м": "Tolerance for near duplicates, m",
    "Максимальная площадь сливера": "Maximum sliver area",
    "Максимальная площадь сливера, м²": "Maximum sliver area, m²",

    "Раздувание таблицы": "Table bloat",
    "Мёртвых строк больше порога от числа живых.": "Dead rows exceed the configured share of live rows.",
    "PostgreSQL хранит мёртвые строки до очистки, и pg_stat_user_tables показывает их число. Если мёртвых строк больше порога из настроек (по умолчанию 20 % от живых), таблица занимает лишнее место, а чтение проходит по страницам, где уже нет нужных данных: карта, выборки и проверки качества замедляются. Сведения берутся из каталога, данные не читаются.": (
        "PostgreSQL keeps dead rows until they are cleaned up, and pg_stat_user_tables reports their count. If dead rows exceed the threshold from the settings (20 % of live rows by default), the table takes extra space and reads walk through pages that no longer hold the needed data: the map, selections and quality checks slow down. The information comes from the catalog, the data is not read."
    ),
    "Очистить таблицу: VACUUM (ANALYZE) <схема>.<таблица>; при сильном раздувании — VACUUM FULL (блокирует запись) или pg_repack.": (
        "Clean the table up: VACUUM (ANALYZE) <schema>.<table>; with heavy bloat use VACUUM FULL (it blocks writes) or pg_repack."
    ),
    "Нет первичного ключа": "No primary key",
    "У таблицы нет ограничения PRIMARY KEY.": "The table has no PRIMARY KEY constraint.",
    "Каталог показывает, что первичного ключа нет. Такую таблицу нельзя корректно редактировать в QGIS: слой открывается только на чтение, потому что редактору нечем однозначно указать строку. Кроме того, ничто не мешает появлению полных дублей. Проверка мгновенная, данные не читаются.": (
        "The catalog shows there is no primary key. Such a table cannot be edited in QGIS properly: the layer opens read-only because the editor has no way to address a single row. Nothing prevents exact duplicate rows either. The check is instant and does not read the data."
    ),
    "Добавить первичный ключ: ALTER TABLE ... ADD PRIMARY KEY (id) или создать столбец-идентификатор (GENERATED ALWAYS AS IDENTITY).": (
        "Add a primary key: ALTER TABLE ... ADD PRIMARY KEY (id) or create an identifier column (GENERATED ALWAYS AS IDENTITY)."
    ),
    "Геометрия не первая в индексе": "Geometry is not first in the index",
    "В индексе первым идёт другой столбец, поэтому фильтры его не используют.": "Another column comes first in the index, so spatial filters do not use it.",
    "Индекс по геометрии составной и геометрический столбец стоит в нём не первым (например, (тип, geom)). PostGIS использует такой индекс только при условии по первому столбцу, поэтому поиск по рамке и ST_Intersects его не применяют. Индекс занимает место и замедляет вставку. Сведения берутся из каталога, данные не читаются.": (
        "The geometry index is composite and the geometry column is not first in it (for example (kind, geom)). PostGIS uses such an index only with a condition on the first column, so bounding box searches and ST_Intersects skip it. The index takes space and slows inserts down. The information comes from the catalog, the data is not read."
    ),
    "Построить отдельный индекс по геометрии: CREATE INDEX ... ON ... USING gist (geom) — или переставить столбцы в существующем.": (
        "Build a separate index on the geometry: CREATE INDEX ... ON ... USING gist (geom) — or reorder the columns of the existing one."
    ),
    "Нет комментария к таблице": "No table comment",
    "У таблицы нет описания в каталоге.": "The table has no description in the catalog.",
    "Слой без комментария непонятен пользователю: в списке таблиц вместо описания пусто, и приходится угадывать содержимое по имени. Комментарий виден в QGIS, в каталоге и в выгрузках плагина, поэтому это дешёвый способ задокументировать данные. Проверка мгновенная, данные не читаются.": (
        "A layer without a comment is unclear to the user: the table list shows an empty description and the content has to be guessed from the name. The comment is visible in QGIS, in the catalog and in the plugin exports, so it is a cheap way to document the data. The check is instant and does not read the data."
    ),
    "Добавить описание: COMMENT ON TABLE <схема>.<таблица> IS 'что это за данные'.": (
        "Add a description: COMMENT ON TABLE <schema>.<table> IS 'what this data is'."
    ),
    "Схема вне search_path": "Schema is outside search_path",
    "Схемы таблицы нет в пути поиска текущего соединения.": "The table schema is missing from the search path of the connection.",
    "PostgreSQL ищет объекты без указания схемы по search_path. Если схемы таблицы в нём нет, слой может «пропасть»: QGIS и другие клиенты не находят таблицу по короткому имени, а функции PostGIS возвращают ошибку. Плагин добавляет в путь public, postgis и topology, поэтому проверка ловит слои из остальных схем. Сведения берутся из каталога, данные не читаются.": (
        "PostgreSQL looks up unqualified objects through search_path. If the table schema is not in it, the layer may disappear: QGIS and other clients cannot find the table by its short name and PostGIS functions return an error. The plugin adds public, postgis and topology to the path, so the check catches layers from other schemas. The information comes from the catalog, the data is not read."
    ),
    "Добавить схему в путь поиска: SET search_path TO <схема>, public или ALTER DATABASE ... SET search_path.": (
        "Add the schema to the search path: SET search_path TO <schema>, public or ALTER DATABASE ... SET search_path."
    ),
    "Геометрия из чужой схемы": "Geometry type from another schema",
    "Тип geometry принадлежит нестандартной схеме.": "The geometry type belongs to a non-standard schema.",
    "Тип столбца geometry зарегистрирован не в public, а в другой схеме (например, после переноса базы или установки расширения в отдельную схему). При восстановлении дампа или переносе в другую базу такой столбец не находится, и таблица читается как обычная без геометрии. Сведения берутся из каталога, данные не читаются.": (
        "The geometry column type is registered not in public but in another schema (for example after moving the database or installing the extension into a separate schema). When a dump is restored or the table is moved to another database, such a column is not found and the table reads as an ordinary one without geometry. The information comes from the catalog, the data is not read."
    ),
    "Перенести тип в public: ALTER EXTENSION postgis SET SCHEMA public или привести столбец к public.geometry.": (
        "Move the type into public: ALTER EXTENSION postgis SET SCHEMA public or cast the column to public.geometry."
    ),
    "Доля мёртвых строк, %": "Dead row share, %",
    "Пороги применяются к проверкам «Слишком много вершин», «Микрообъекты», «Микролинии», «Слишком много частей», «Очень крупная геометрия», «Устаревшая статистика таблицы», «Почти дубли геометрий», «Сливеры (узкие щели)» и «Раздувание таблицы».": (
        "The thresholds apply to the checks \"Too many vertices\", \"Tiny polygons\", \"Tiny lines\", \"Too many parts\", \"Very large geometry\", \"Stale table statistics\", \"Near-duplicate geometries\", \"Slivers (narrow gaps)\" and \"Table bloat\"."
    ),

    "Загрузить в текущий проект и показать на карте": (
        "Load into the current project and show on the map"
    ),
    "Загрузить в текущий проект и выделить проблемные объекты": (
        "Load into the current project and select the problem features"
    ),
    "Проверка не выделяет объекты на карте": (
        "The check does not select features on the map"
    ),
    "Условие проверки не подходит к слою": (
        "The check condition does not fit the layer"
    ),
    "не удалось выделить объекты": "failed to select features",
    "выделено объектов: {}": "features selected: {}",
    "Не удалось загрузить слой": "Failed to load the layer",
    "Слой уже в проекте": "The layer is already in the project",
    "Слой добавлен на карту": "The layer was added to the map",
    "Нет доступа к окну QGIS": "No access to the QGIS window",
    "Не открыт проект QGIS": "No QGIS project is open",
    "Нет доступа к карте QGIS": "No access to the QGIS map canvas",

    "Выбрать все": "Select all",
    "Сбросить все": "Clear all",
    "По умолчанию": "Defaults",
    "Вернуть выбор по умолчанию": "Restore the default selection",
    "Выбрано {}/{}": "Selected {}/{}",

    "Объект с числом вершин больше этого значения считается тяжёлым: карта рисуется медленно, выборки и экспорт тормозят. Проверка «Слишком много вершин». По умолчанию 10 000.": (
        "A feature with more vertices than this is considered heavy: the map draws slowly and selections and exports lag. Check \"Too many vertices\". 10 000 by default."
    ),
    "Полигоны с площадью меньше этого значения считаются осколками после наложения и обрезки слоёв. Единицы — единицы системы координат слоя (для метровых СК это квадратные метры). Проверка «Микрообъекты».": (
        "Polygons with an area below this value count as splinters left after overlaying and clipping layers. The unit is the unit of the layer CRS (square metres for metre-based systems). Check \"Tiny polygons\"."
    ),
    "То же для слоёв в SRID 4326: площадь считается через ST_Area(geography), поэтому порог задаётся в квадратных метрах и не зависит от градусов. Проверка «Микрообъекты».": (
        "The same for SRID 4326 layers: the area is measured with ST_Area(geography), so the threshold is set in square metres and does not depend on degrees. Check \"Tiny polygons\"."
    ),
    "Линии короче этого значения считаются обрезками и на карте выглядят точками. Единицы — единицы системы координат слоя. Проверка «Микролинии».": (
        "Lines shorter than this value count as clippings and look like points on the map. The unit is the unit of the layer CRS. Check \"Tiny lines\"."
    ),
    "То же для слоёв в SRID 4326: длина считается через ST_Length(geography), порог задаётся в метрах. Проверка «Микролинии».": (
        "The same for SRID 4326 layers: the length is measured with ST_Length(geography), so the threshold is set in metres. Check \"Tiny lines\"."
    ),
    "Объекты, расстояние между которыми меньше этого допуска, считаются почти дублями: загружены дважды со сдвигом или оцифрованы повторно. Единицы — единицы системы координат слоя. Проверка «Почти дубли геометрий».": (
        "Features whose distance is below this tolerance count as near duplicates: loaded twice with a shift or digitised again. The unit is the unit of the layer CRS. Check \"Near-duplicate geometries\"."
    ),
    "То же для слоёв в SRID 4326: расстояние считается в метрах, поэтому допуск задаётся в метрах. Проверка «Почти дубли геометрий».": (
        "The same for SRID 4326 layers: the distance is measured in metres, so the tolerance is set in metres. Check \"Near-duplicate geometries\"."
    ),
    "Наложение соседних полигонов меньше этого значения считается сливером — узкой щелью на месте общей границы. Единицы — единицы площади системы координат слоя. Проверка «Сливеры (узкие щели)».": (
        "An overlap of neighbouring polygons below this value counts as a sliver, a narrow gap in place of the shared border. The unit is the area unit of the layer CRS. Check \"Slivers (narrow gaps)\"."
    ),
    "То же для слоёв в SRID 4326: площадь наложения считается в квадратных метрах. Значение по умолчанию 100 м², потому что в градусах тонкая щель даёт тысячи квадратных метров. Проверка «Сливеры (узкие щели)».": (
        "The same for SRID 4326 layers: the overlap area is measured in square metres. The default is 100 m², because in degrees a thin gap easily reaches thousands of square metres. Check \"Slivers (narrow gaps)\"."
    ),
    "Объект с числом частей больше этого значения (мультиполигон из тысяч кусков) тяжело рисуется и блокирует таблицу при правке. Проверка «Слишком много частей в объекте». По умолчанию 1000.": (
        "A feature with more parts than this (a multipolygon of thousands of pieces) draws slowly and locks the table when edited. Check \"Too many parts per feature\". 1000 by default."
    ),
    "Геометрия крупнее этого размера в байтах читается целиком при каждом обращении, из-за чего карта и проверки замедляются. Проверка «Очень крупная геометрия». По умолчанию 1 000 000 байт.": (
        "A geometry larger than this size in bytes is read entirely on every access, which slows the map and the checks down. Check \"Very large geometry\". 1 000 000 bytes by default."
    ),
    "Если ANALYZE не запускался дольше этого числа дней, планировщик оценивает строки по устаревшим данным и читает таблицу целиком. Проверка «Устаревшая статистика таблицы». По умолчанию 30 дней.": (
        "If ANALYZE has not run for longer than this number of days, the planner estimates rows from outdated data and reads the whole table. Check \"Stale table statistics\". 30 days by default."
    ),
    "Если мёртвых строк больше этого процента от числа живых, таблица занимает лишнее место и читается медленнее. Проверка «Раздувание таблицы». По умолчанию 20 %.": (
        "If dead rows exceed this share of the live rows, the table takes extra space and reads more slowly. Check \"Table bloat\". 20 % by default."
    ),

    # Качество по НСИ
    "Качество по НСИ": "Reference data quality",
    "Соединение": "Connection",
    "Поле": "Field",
    "Сравнить": "Compare",
    "Значение": "Value",
    "Категория": "Category",
    "Что выбрано": "Selected sources",
    "Параметр": "Parameter",
    "Левая панель": "Left panel",
    "Правая панель": "Right panel",
    "Количество": "Count",
    "Совпало": "Matched",
    "Есть в левой панели, но нет в правой": (
        "Present in the left panel but not in the right"
    ),
    "Есть в правой, но нет в левой": (
        "Present in the right panel but not in the left"
    ),
    "Все из левой панели есть в правой": (
        "Everything from the left panel is present in the right"
    ),
    "Уникальных значений: {}": "Unique values: {}",
    "Всего уникальных значений в сравнении: {}": (
        "Total unique values compared: {}"
    ),
    "Сравнение не выполнялось": "No comparison has been run",
    "Соединение не найдено": "Connection not found",
    "Соединение не выбрано": "No connection selected",
    "Сохраните его": "Save it first",
    "Подключено, но доступных таблиц нет": (
        "Connected, but no tables are available"
    ),
    "Подключено, но нет прав на чтение таблиц: {} (таблиц в базе: {})": (
        "Connected, but no privilege to read tables: {} (tables in the database: {})"
    ),
    "Подключено, но в базе нет таблиц": (
        "Connected, but the database has no tables"
    ),
    "Таблиц в базе: {}, доступно для чтения: {}": (
        "Tables in the database: {}, readable: {}"
    ),
    "Нет доступа к таблице": "No access to the table",
    "Дождитесь окончания текущих проверок": (
        "Wait until the running checks finish"
    ),
    "Загрузите значения с обеих сторон": (
        "Load values on both sides first"
    ),
    "Сначала выполните сравнение": "Run the comparison first",
    "Экспорт списка значений": "Export the list of values",
    "Экспорт результатов сверки": "Export the comparison results",

    # Плагин и панель
    "ZGeo-PG-Каталог": "ZGeo-PG Catalog",
    "ZGeo-PG-Каталог — каталог пространственных данных PostGIS": (
        "ZGeo-PG Catalog — PostGIS spatial data catalog"
    ),
    "Открыть плавающую панель ZGeo-PG-Каталог": (
        "Open the ZGeo-PG Catalog dock"
    ),
    "ZGeo-PG — каталог пространственных данных PostGIS": (
        "ZGeo-PG — PostGIS spatial data catalog"
    ),
}

_CATEGORY_SOURCES = {}


def normalize_language(value: Any) -> str:
    """Привести значение к поддерживаемому коду языка."""
    text = str(value or DEFAULT_LANGUAGE).strip().lower()
    return LANGUAGE_EN if text.startswith(LANGUAGE_EN) else LANGUAGE_RU


def get_language() -> str:
    return _current_language


def set_language(value: Any) -> str:
    """Установить язык интерфейса и вернуть нормализованный код."""
    global _current_language
    _current_language = normalize_language(value)
    return _current_language


def tr(text: str, *args: Any, **kwargs: Any) -> str:
    """Перевести строку, если включён английский интерфейс."""
    result = text
    if _current_language == LANGUAGE_EN:
        result = EN_TRANSLATIONS.get(text, text)
    if args:
        try:
            result = result.format(*args)
        except (IndexError, KeyError):
            pass
    elif kwargs:
        try:
            result = result.format(**kwargs)
        except (IndexError, KeyError):
            pass
    return result