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