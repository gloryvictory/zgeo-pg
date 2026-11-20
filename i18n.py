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
    "Соединение": "Connection",
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
    "Ошибка запроса": "Query error",

    # Таблицы
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
    "Дождитесь окончания текущих проверок": (
        "Wait until the running checks finish"
    ),
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

    # Качество по НСИ
    "Качество по НСИ": "Reference data quality",
    "Соединение": "Connection",
    "Поле": "Field",
    "Сравнить": "Compare",
    "Значение": "Value",
    "Категория": "Category",
    "Количество": "Count",
    "Совпало": "Matched",
    "Есть в левой панели, но нет в правой": (
        "Present in the left panel but not in the right"
    ),
    "Есть в правой, но нет в левой": (
        "Present in the right panel but not in the left"
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