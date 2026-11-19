"""Плавающая панель ZGeo-PG: список таблиц, статистика и соединение."""

from __future__ import annotations

from dataclasses import replace
from typing import Dict, List, Optional, Tuple

from qgis.PyQt.QtCore import QSettings, Qt, pyqtSignal
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDockWidget,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .catalog import (
    SpatialTable,
    create_spatial_index,
    crs_label,
    fetch_crs_auth,
    fetch_spatial_index,
    fetch_spatial_tables,
    parse_srid,
    reindex_spatial_index,
)
from .charts import BarChart
from .connection import (
    PGConnection,
    close_connection,
    delete_connection,
    last_connection_name,
    list_saved_connections,
    load_connection,
    open_connection,
    save_connection,
    sync_connections_from_sqlite,
)
from .formatting import format_number, format_size
from .i18n import EN_TRANSLATIONS, LANGUAGE_EN, LANGUAGE_KEY, get_language, set_language, tr
from .load_task import IndexTask, LoadTablesTask
from .quality import QUALITY_CHECKS, QualityTask, check_by_key
from .stats import (
    build_geometry_type_distribution,
    build_schema_distribution,
    build_size_distribution,
    totals,
)
from .table_export import (
    FORMAT_HTML,
    FORMAT_XLSX,
    ask_export_format,
    export_rows_with_dialog,
    export_table_with_dialog,
)
from .version import get_plugin_version

GEO_TYPE_COLORS = {}


def _geometry_label(table: SpatialTable) -> str:
    return table.geom_type


class ZGeoPgPanel(QDockWidget):
    """Плавающая панель каталога пространственных данных PostGIS."""

    language_changed = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("ZGeoPgPanel")
        self.setWindowTitle(self._window_title())
        self._settings = QSettings()
        self._conn: Optional[PGConnection] = None
        self._db = None
        self._tables: List[SpatialTable] = []
        self._task: Optional[LoadTablesTask] = None
        self._index_task: Optional[IndexTask] = None
        self._index_action = IndexTask.ACTION_CREATE
        self._index_changed: List[int] = []
        self._index_errors: List[str] = []
        self._schema_filter: Optional[str] = None
        self._only_geometry = True
        self._quality_task: Optional[QualityTask] = None
        self._quality_check_boxes: Dict[str, QCheckBox] = {}
        self._quality_info_buttons: Dict[str, QPushButton] = {}
        self._quality_columns: List[str] = []
        self._quality_row_of: Dict[str, int] = {}
        self._quality_problems = 0
        self._quality_errors = 0

        self._build_ui()
        self._build_connection_tab()
        self._build_tables_tab()
        self._build_stats_tab()
        self._build_quality_tab()
        self._retranslate()
        self._restore_connections()

        self.setMinimumWidth(560)
        self.setMinimumHeight(420)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        container = QWidget()
        outer = QVBoxLayout(container)
        outer.setContentsMargins(6, 6, 6, 4)

        header = QHBoxLayout()
        self._title_label = QLabel()
        header.addWidget(self._title_label)
        header.addStretch(1)
        self._lang_button = QPushButton()
        self._lang_button.setFixedWidth(52)
        self._lang_button.clicked.connect(self._toggle_language)
        header.addWidget(self._lang_button)
        outer.addLayout(header)

        self._tabs = QTabWidget()
        outer.addWidget(self._tabs, 1)

        self._progress_label = QLabel()
        self._progress_label.setVisible(False)
        outer.addWidget(self._progress_label)

        self._status = QStatusBar()
        self._status.setSizeGripEnabled(True)
        self._connection_dot = QLabel()
        self._connection_dot.setFixedSize(10, 10)
        self._connection_label = QLabel()
        self._status_label = QLabel()
        self._selected_label = QLabel()
        self._status.addWidget(self._connection_dot)
        self._status.addWidget(self._connection_label)
        self._status.addWidget(self._status_label, 1)
        self._status.addPermanentWidget(self._selected_label)
        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedWidth(180)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setVisible(False)
        self._status.addPermanentWidget(self._progress_bar)
        outer.addWidget(self._status)

        self.setWidget(container)

    def _build_tables_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(6, 6, 6, 6)

        bar = QHBoxLayout()
        self._refresh_button = QPushButton()
        self._refresh_button.clicked.connect(self._on_refresh)
        self._refresh_button.setEnabled(False)
        bar.addWidget(self._refresh_button)
        self._info_button = QPushButton()
        self._info_button.clicked.connect(self._on_info)
        self._info_button.setEnabled(False)
        bar.addWidget(self._info_button)
        self._export_button = QPushButton()
        self._export_button.clicked.connect(self._on_export)
        self._export_button.setEnabled(False)
        bar.addWidget(self._export_button)
        self._create_all_indexes_button = QPushButton()
        self._create_all_indexes_button.clicked.connect(self._on_create_indexes_for_all)
        self._create_all_indexes_button.setEnabled(False)
        bar.addWidget(self._create_all_indexes_button)
        self._refresh_all_indexes_button = QPushButton()
        self._refresh_all_indexes_button.clicked.connect(
            self._on_refresh_indexes_for_all
        )
        self._refresh_all_indexes_button.setEnabled(False)
        bar.addWidget(self._refresh_all_indexes_button)
        bar.addStretch(1)
        self._cancel_button = QPushButton()
        self._cancel_button.clicked.connect(self._on_cancel)
        self._cancel_button.setEnabled(False)
        bar.addWidget(self._cancel_button)
        layout.addLayout(bar)

        filter_row = QHBoxLayout()
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText(tr("Поиск"))
        self._search_edit.textChanged.connect(self._apply_filters)
        filter_row.addWidget(self._search_edit, 1)
        self._schema_combo = QComboBox()
        self._schema_combo.currentIndexChanged.connect(self._on_schema_changed)
        filter_row.addWidget(self._schema_combo)
        layout.addLayout(filter_row)

        self._only_geometry_check = QCheckBox()
        self._only_geometry_check.setChecked(True)
        self._only_geometry_check.toggled.connect(self._apply_filters)
        layout.addWidget(self._only_geometry_check)

        self._table = QTableWidget(0, 0)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_tables_context_menu)
        layout.addWidget(self._table, 1)

        self._summary_label = QLabel()
        layout.addWidget(self._summary_label)

        self._tables_page = page
        self._tabs.addTab(page, tr("Таблицы"))

    def _build_stats_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(6, 6, 6, 6)

        self._size_chart = BarChart()
        self._geom_chart = BarChart()
        layout.addWidget(self._size_chart)
        layout.addWidget(self._geom_chart)

        self._schema_table = QTableWidget(0, 4)
        self._schema_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._schema_table.verticalHeader().setVisible(False)
        self._schema_table.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self._schema_table.customContextMenuRequested.connect(
            self._on_stats_context_menu
        )
        layout.addWidget(self._schema_table, 1)

        stats_bar = QHBoxLayout()
        self._stats_export_button = QPushButton()
        self._stats_export_button.clicked.connect(self._on_stats_export)
        stats_bar.addWidget(self._stats_export_button)
        stats_bar.addStretch(1)

        layout.addLayout(stats_bar)

        self._stats_page = page
        self._tabs.addTab(page, tr("Статистика"))

    def _build_quality_tab(self) -> None:
        """Вкладка проверок качества данных: список проверок и результаты."""

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(6, 6, 6, 6)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        checks_box = QGroupBox()
        self._quality_checks_box = checks_box
        checks_layout = QVBoxLayout(checks_box)
        checks_layout.setContentsMargins(6, 6, 6, 6)
        for check in QUALITY_CHECKS:
            row = QHBoxLayout()
            box = QCheckBox(tr(check.title))
            box.setChecked(True)
            box.setToolTip(tr(check.summary))
            self._quality_check_boxes[check.key] = box
            row.addWidget(box, 1)
            info = QPushButton("i")
            info.setFixedWidth(26)
            info.setToolTip(tr("Описание проверки"))
            info.clicked.connect(
                lambda _checked=False, key=check.key: self._show_check_description(key)
            )
            self._quality_info_buttons[check.key] = info
            row.addWidget(info)
            checks_layout.addLayout(row)
        checks_layout.addStretch(1)
        splitter.addWidget(checks_box)

        self._quality_help = QTextBrowser()
        self._quality_help.setMinimumWidth(240)
        self._quality_help.setVisible(False)
        splitter.addWidget(self._quality_help)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 4)
        layout.addWidget(splitter, 1)

        self._quality_table = QTableWidget(0, 0)
        self._quality_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._quality_table.verticalHeader().setVisible(False)
        layout.addWidget(self._quality_table, 1)

        self._quality_summary_label = QLabel()
        layout.addWidget(self._quality_summary_label)

        buttons = QHBoxLayout()
        self._quality_run_button = QPushButton()
        self._quality_run_button.clicked.connect(self._run_quality_checks)
        self._quality_run_button.setEnabled(False)
        buttons.addWidget(self._quality_run_button)
        self._quality_cancel_button = QPushButton()
        self._quality_cancel_button.clicked.connect(self._cancel_quality_checks)
        self._quality_cancel_button.setEnabled(False)
        buttons.addWidget(self._quality_cancel_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self._quality_page = page
        self._tabs.addTab(page, tr("Качество пространственных данных"))

    def _build_connection_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(6, 6, 6, 6)

        self._saved_box = QGroupBox(tr("Сохранённые соединения"))
        saved_layout = QHBoxLayout(self._saved_box)
        self._saved_combo = QComboBox()
        self._saved_combo.currentTextChanged.connect(self._on_saved_selected)
        saved_layout.addWidget(self._saved_combo, 1)
        self._load_btn = QPushButton(tr("Загрузить"))
        self._load_btn.clicked.connect(self._on_load_saved)
        saved_layout.addWidget(self._load_btn)
        self._del_btn = QPushButton(tr("Удалить"))
        self._del_btn.clicked.connect(self._on_delete_saved)
        saved_layout.addWidget(self._del_btn)
        layout.addWidget(self._saved_box)

        form_box = QGroupBox(tr("Параметры подключения"))
        self._form_box = form_box
        form = _FormLayout(form_box)
        self._conn_form = form

        self._conn_name = form.add_line(tr("Имя"))
        self._conn_host = form.add_line(tr("Хост"), "localhost")
        self._conn_port = form.add_spin(tr("Порт"), 5432, 1, 65535)
        self._conn_db = form.add_line(tr("База данных"))
        self._conn_user = form.add_line(tr("Пользователь"), "postgres")
        self._conn_password = form.add_line(tr("Пароль"), "", password=True)
        layout.addWidget(form_box)

        actions = QHBoxLayout()
        save_btn = QPushButton(tr("Сохранить соединение"))
        self._save_btn = save_btn
        save_btn.clicked.connect(self._on_save_connection)
        actions.addWidget(save_btn)
        test_btn = QPushButton(tr("Проверить подключение"))
        self._test_btn = test_btn
        test_btn.clicked.connect(self._on_test_connection)
        actions.addWidget(test_btn)
        self._connect_button = QPushButton()
        self._connect_button.clicked.connect(self._on_connect)
        actions.addWidget(self._connect_button)
        actions.addStretch(1)
        layout.addLayout(actions)
        layout.addStretch(1)

        self._connection_page = page
        self._tabs.addTab(page, tr("Подключения"))

    # --------------------------------------------------------------- helpers
    def _current_connection_form(self) -> PGConnection:
        return PGConnection(
            name=self._conn_name.text().strip() or self._conn_db.text().strip() or "connection",
            host=self._conn_host.text().strip() or "localhost",
            port=int(self._conn_port.value()),
            database=self._conn_db.text().strip(),
            user=self._conn_user.text().strip() or "postgres",
            password=self._conn_password.text(),
        )

    def _set_status(self, text: str) -> None:
        self._status_label.setText(text)

    def _update_connection_state(self) -> None:
        """Зелёный кружок и «Подключено», если соединение открыто."""

        connected = self._db is not None
        color = "#2e9e4f" if connected else "#c0392b"
        self._connection_dot.setStyleSheet(
            f"background-color: {color}; border-radius: 5px;"
        )
        self._connection_dot.setToolTip(
            tr("Подключено") if connected else tr("Не подключено")
        )
        self._connection_label.setText(
            tr("Подключено") if connected else tr("Не подключено")
        )

    def _update_selected(self) -> None:
        rows = self._table.rowCount()
        self._selected_label.setText(tr("Выбрано: {} из {}").format(len(self._selected_indexes()), rows))

    def _selected_indexes(self) -> List[int]:
        indexes = []
        for index in self._table.selectionModel().selectedRows():
            indexes.append(index.row())
        return indexes

    # ------------------------------------------------------------------ i18n
    def _toggle_language(self) -> None:
        current = get_language()
        new_lang = LANGUAGE_EN if current != LANGUAGE_EN else "ru"
        set_language(new_lang)
        self._settings.setValue(LANGUAGE_KEY, new_lang)
        self._retranslate()
        self.language_changed.emit(new_lang)

    def _window_title(self) -> str:
        """Заголовок окна с текущей версией плагина."""
        return "ZGeo-PG " + get_plugin_version()

    def _retranslate(self) -> None:
        self.setWindowTitle(self._window_title())
        self._title_label.setText(
            tr("ZGeo-PG — каталог пространственных данных PostGIS") + "  v" + get_plugin_version()
        )
        self._lang_button.setText("RU" if get_language() == LANGUAGE_EN else "EN")
        self._tabs.setTabText(self._tabs.indexOf(self._connection_page), tr("Подключения"))
        self._tabs.setTabText(self._tabs.indexOf(self._tables_page), tr("Таблицы"))
        self._tabs.setTabText(self._tabs.indexOf(self._stats_page), tr("Статистика"))
        self._tabs.setTabText(
            self._tabs.indexOf(self._quality_page),
            tr("Качество пространственных данных"),
        )
        self._quality_checks_box.setTitle(tr("Проверки"))
        self._quality_run_button.setText(tr("Проверить"))
        self._quality_cancel_button.setText(tr("Прервать"))
        for check in QUALITY_CHECKS:
            self._quality_check_boxes[check.key].setText(tr(check.title))
            self._quality_check_boxes[check.key].setToolTip(tr(check.summary))
        self._populate_quality_headers()
        self._connect_button.setText(tr("Отключиться") if self._db else tr("Подключиться"))
        self._refresh_button.setText(tr("Обновить"))
        self._info_button.setText(tr("Информация"))
        self._export_button.setText(tr("Экспорт"))
        self._cancel_button.setText(tr("Отмена"))
        self._search_edit.setPlaceholderText(tr("Поиск"))
        self._only_geometry_check.setText(tr("Только с геометрией"))
        self._stats_export_button.setText(tr("Экспорт в Excel"))
        self._create_all_indexes_button.setText(
            tr("Создать все пространственные индексы")
        )
        self._refresh_all_indexes_button.setText(
            tr("Обновить все пространственные индексы")
        )
        self._saved_box.setTitle(tr("Сохранённые соединения"))
        self._load_btn.setText(tr("Загрузить"))
        self._del_btn.setText(tr("Удалить"))
        self._save_btn.setText(tr("Сохранить соединение"))
        self._test_btn.setText(tr("Проверить подключение"))
        self._form_box.setTitle(tr("Параметры подключения"))
        self._conn_form.retranslate()
        self._size_chart.set_title(tr("По размеру"))
        self._geom_chart.set_title(tr("По типу геометрии"))
        self._populate_table_headers()
        self._populate_stats_table()
        self._update_summary()
        self._update_selected()
        self._update_connection_state()

    # -------------------------------------------------------------- database
    def _on_connect(self) -> None:
        if self._db is not None:
            self._disconnect()
            return
        conn = self._current_connection_form()
        try:
            self._set_status(tr("Подключение") + "...")
            self._update_connection_state()
            self._db = open_connection(conn)
            self._conn = conn
        except Exception as error:  # noqa: BLE001
            self._db = None
            self._conn = None
            self._set_status(tr("Готово"))
            self._update_connection_state()
            QMessageBox.critical(self, "ZGeo-PG", tr("Ошибка подключения") + ":\n" + str(error))
            return
        self._retranslate()
        self._update_connection_state()
        self._reload_tables()

    def _disconnect(self) -> None:
        self._stop_task()
        self._stop_quality_task()
        self._quality_run_button.setEnabled(False)
        if self._conn is not None:
            close_connection(self._conn)
        self._conn = None
        self._db = None
        self._tables = []
        self._table.setRowCount(0)
        self._populate_schemas()
        self._refresh_button.setEnabled(False)
        self._info_button.setEnabled(False)
        self._export_button.setEnabled(False)
        self._create_all_indexes_button.setEnabled(False)
        self._refresh_all_indexes_button.setEnabled(False)
        self._retranslate()
        self._update_connection_state()
        self._set_status(tr("Готово"))

    def _on_refresh(self) -> None:
        self._reload_tables()

    def _reload_tables(self) -> None:
        if self._db is None:
            return
        self._stop_task()
        schemas = [self._schema_filter] if self._schema_filter else None
        try:
            tables = fetch_spatial_tables(self._db, schemas=schemas)
        except Exception as error:  # noqa: BLE001
            self._set_status(tr("Ошибка") + ": " + str(error))
            return
        self._tables = tables
        self._populate_schemas()
        self._populate_table()
        self._refresh_button.setEnabled(True)
        self._export_button.setEnabled(True)
        self._create_all_indexes_button.setEnabled(True)
        self._refresh_all_indexes_button.setEnabled(True)
        self._quality_run_button.setEnabled(True)
        self._populate_stats()
        self._set_status(tr("Готово"))
        if tables:
            self._start_load_task()

    def _start_load_task(self) -> None:
        if self._conn is None or not self._tables:
            return
        self._stop_task()
        self._task = LoadTablesTask(self._conn, list(self._tables), self)
        self._task.table_loaded.connect(self._on_table_loaded)
        self._task.progress.connect(self._on_load_progress)
        self._task.finished_all.connect(self._on_load_finished)
        self._cancel_button.setEnabled(True)
        self._refresh_button.setEnabled(False)
        self._refresh_all_indexes_button.setEnabled(False)
        self._set_status(tr("Чтение характеристик") + "...")
        self._task.start()

    def _stop_task(self) -> None:
        if self._task is not None:
            try:
                self._task.request_cancel()
                self._task.wait(200)
            except RuntimeError:
                pass
            self._task = None
        self._cancel_button.setEnabled(False)

    def _on_cancel(self) -> None:
        if self._task is not None:
            self._task.request_cancel()

    def _on_table_loaded(self, index: int, updated: SpatialTable) -> None:
        if 0 <= index < len(self._tables):
            self._tables[index] = updated
        self._refresh_table_row(index)
        self._update_summary()

    def _on_load_progress(self, done: int, total: int) -> None:
        self._set_status(tr("Чтение характеристик") + f"... {done} / {total}")

    def _on_load_finished(self, cancelled: bool, error: str) -> None:
        self._cancel_button.setEnabled(False)
        self._refresh_button.setEnabled(True)
        self._refresh_all_indexes_button.setEnabled(self._db is not None)
        self._populate_stats()
        if error:
            self._set_status(tr("Ошибка") + ": " + error)
        elif cancelled:
            self._set_status(tr("Отменено"))
        else:
            self._set_status(tr("Готово"))
        self._task = None

    # ----------------------------------------------------------------- table
    def _populate_table_headers(self) -> None:
        headers = [
            tr("Схема"),
            tr("Таблица"),
            tr("Комментарий"),
            tr("Столбец"),
            tr("Тип"),
            tr("SRID"),
            tr("Система координат"),
            tr("Строк (оценка)"),
            tr("Строк (точно)"),
            tr("Размер"),
            tr("Размер индексов"),
            tr("Пространственный индекс"),
            tr("Имя пространственного индекса"),
            tr("Размер пространственного индекса"),
            tr("Полный размер"),
        ]
        self._table.setColumnCount(len(headers))
        self._table.setHorizontalHeaderLabels(headers)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setStretchLastSection(True)

    def _populate_table(self) -> None:
        visible = self._visible_tables()
        self._table.setRowCount(len(visible))
        for row, table in enumerate(visible):
            self._write_table_row(row, table)
        self._populate_table_headers()
        self._update_summary()
        self._update_selected()

    def _visible_tables(self) -> List[SpatialTable]:
        query = self._search_edit.text().strip().casefold() if hasattr(self, "_search_edit") else ""
        result: List[SpatialTable] = []
        for table in self._tables:
            if self._schema_filter and table.schema != self._schema_filter:
                continue
            if self._only_geometry and not table.has_geometry:
                continue
            if query:
                haystack = (
                    f"{table.schema} {table.name} {table.geom_column} "
                    f"{table.comment}"
                ).casefold()
                if query not in haystack:
                    continue
            result.append(table)
        return result

    def _write_table_row(self, row: int, table: SpatialTable) -> None:
        geom_label = _geometry_label(table)
        cells = [
            table.schema,
            table.name,
            table.comment,
            table.geom_column,
            geom_label,
            "" if table.srid is None else str(table.srid),
            crs_label(table.srid, self._auth_for(table.srid)),
            format_number(table.estimated_rows),
            format_number(table.feature_count),
            format_size(table.data_size) if table.data_size is not None else "—",
            format_size(table.index_size) if table.index_size is not None else "—",
            tr("Да") if table.has_spatial_index else tr("Нет"),
            table.spatial_index_name or "—",
            (
                format_size(table.spatial_index_size)
                if table.spatial_index_size is not None
                else "—"
            ),
            format_size(table.full_size),
        ]
        for column, value in enumerate(cells):
            item = QTableWidgetItem(str(value))
            item.setData(Qt.ItemDataRole.UserRole, _cell_raw(table, column))
            self._table.setItem(row, column, item)
        # Отметить таблицы без геометрии.
        if not table.has_geometry:
            color = self._table.item(row, 0)
            if color is not None:
                color.setBackground(Qt.GlobalColor.lightGray)

    def _refresh_table_row(self, index: int) -> None:
        visible = self._visible_tables()
        table = self._tables[index]
        if table not in visible:
            self._populate_table()
            return
        row = visible.index(table)
        self._write_table_row(row, table)

    def _auth_for(self, srid) -> Optional[str]:
        if srid is None:
            return None
        if self._db is None:
            return None
        return fetch_crs_auth(self._db, srid)

    def _populate_schemas(self) -> None:
        schemas = sorted({t.schema for t in self._tables})
        current = self._schema_combo.currentText() if hasattr(self, "_schema_combo") else ""
        self._schema_combo.blockSignals(True)
        self._schema_combo.clear()
        self._schema_combo.addItem(tr("Все схемы"), "")
        for schema in schemas:
            self._schema_combo.addItem(schema, schema)
        index = self._schema_combo.findData(current)
        self._schema_combo.setCurrentIndex(index if index >= 0 else 0)
        self._schema_combo.blockSignals(False)
        self._schema_filter = self._schema_combo.currentData()

    def _on_schema_changed(self) -> None:
        self._schema_filter = self._schema_combo.currentData()
        self._populate_table()

    def _apply_filters(self) -> None:
        self._populate_table()

    def _on_selection_changed(self) -> None:
        enabled = len(self._selected_indexes()) == 1
        self._info_button.setEnabled(enabled)
        self._update_selected()

    def _update_summary(self) -> None:
        visible = self._visible_tables()
        count, features, size = totals(visible)
        self._summary_label.setText(
            tr("Показаны") + f": {len(visible)} " + tr("из") + f" {len(self._tables)} "
            + tr("таблиц") + f"    {tr('Всего объектов')}: {format_number(features)}"
            + f"    {tr('Всего размер')}: {format_size(size)}"
        )

    # ---------------------------------------------------------------- actions
    def _on_info(self) -> None:
        indexes = self._selected_indexes()
        visible = self._visible_tables()
        if len(indexes) != 1 or indexes[0] >= len(visible):
            QMessageBox.information(
                self, "ZGeo-PG", tr("Выберите одну таблицу в списке")
            )
            return
        table = visible[indexes[0]]
        from .info_dialog import show_table_info

        show_table_info(self, table)

    def _on_export(self) -> None:
        """Экспорт списка таблиц: выбор «Excel» или «HTML»."""

        visible = self._visible_tables()
        if not visible:
            return
        export_format = ask_export_format(self, self._export_button)
        if export_format is None:
            return

        headers = [
            tr("Схема"),
            tr("Таблица"),
            tr("Комментарий"),
            tr("Столбец"),
            tr("Тип"),
            tr("SRID"),
            tr("Система координат"),
            tr("Строк (оценка)"),
            tr("Строк (точно)"),
            tr("Размер"),
            tr("Размер индексов"),
            tr("Пространственный индекс"),
            tr("Имя пространственного индекса"),
            tr("Размер пространственного индекса"),
            tr("Полный размер"),
        ]
        rows = []
        for table in visible:
            rows.append(
                [
                    table.schema,
                    table.name,
                    table.comment,
                    table.geom_column,
                    _geometry_label(table),
                    "" if table.srid is None else table.srid,
                    crs_label(table.srid, self._auth_for(table.srid)),
                    table.estimated_rows,
                    table.feature_count if table.feature_count is not None else "",
                    table.data_size if table.data_size is not None else "",
                    table.index_size if table.index_size is not None else "",
                    tr("Да") if table.has_spatial_index else tr("Нет"),
                    table.spatial_index_name or "",
                    (
                        table.spatial_index_size
                        if table.spatial_index_size is not None
                        else ""
                    ),
                    table.full_size,
                ]
            )
        rows.append(self._totals_row(visible))

        default_name = (
            "zgeo-pg_tables.html"
            if export_format == FORMAT_HTML
            else "zgeo-pg_tables.xlsx"
        )
        export_rows_with_dialog(
            self,
            headers,
            rows,
            default_name,
            tr("Таблицы"),
            export_format=export_format,
            total_index=len(rows) - 1,
            size_columns=(9, 10, 13, 14),
        )

    def _totals_row(self, visible: List[SpatialTable]) -> List[object]:
        """Строка «Итого»: суммы по каждому числовому столбцу списка."""

        count, features, _size = totals(visible)
        estimated = sum(table.estimated_rows or 0 for table in visible)
        data_size = sum(table.data_size or 0 for table in visible)
        indexes = sum(table.index_size or 0 for table in visible)
        spatial_index_size = sum(
            table.spatial_index_size
            for table in visible
            if table.spatial_index_size is not None
        )
        full_size = sum(table.full_size for table in visible)
        return [
            tr("Итого"),
            f"{count} " + tr("таблиц"),
            "",
            "",
            "",
            "",
            "",
            estimated,
            features,
            data_size,
            indexes,
            "",
            "",
            spatial_index_size,
            full_size,
        ]

    def _on_stats_export(self) -> None:
        """Экспорт статистики по схемам с итоговой строкой."""

        if self._schema_table.rowCount() == 0:
            return
        export_format = ask_export_format(self, self._stats_export_button)
        if export_format is None:
            return
        count_total = 0
        size_total = 0
        for row in range(self._schema_table.rowCount()):
            count_item = self._schema_table.item(row, 1)
            size_item = self._schema_table.item(row, 2)
            count_raw = (
                count_item.data(Qt.ItemDataRole.UserRole) if count_item else None
            )
            size_raw = size_item.data(Qt.ItemDataRole.UserRole) if size_item else None
            if isinstance(count_raw, int):
                count_total += count_raw
            if isinstance(size_raw, int):
                size_total += size_raw
        default_name = (
            "zgeo-pg_stats.html" if export_format == FORMAT_HTML else "zgeo-pg_stats.xlsx"
        )
        export_table_with_dialog(
            self,
            self._schema_table,
            default_name,
            tr("Статистика по схемам"),
            summary_rows=[[tr("Итого"), count_total, size_total, ""]],
            export_format=export_format,
            size_columns=(2,),
        )

    # ------------------------------------------------------------ quality tab
    def _show_check_description(self, key: str) -> None:
        """Открыть справа описание проверки; повторное нажатие закрывает его."""

        check = check_by_key(key)
        if check is None:
            return
        if self._quality_help.isVisible() and self._quality_help.property("check") == key:
            self._quality_help.setVisible(False)
            return
        self._quality_help.setProperty("check", key)
        self._quality_help.setHtml(
            "<h3>{}</h3><p>{}</p><p><b>{}</b> {}</p>".format(
                tr(check.title),
                tr(check.description),
                tr("Как исправить") + ":",
                tr(check.fix),
            )
        )
        self._quality_help.setVisible(True)

    def _selected_checks(self) -> List:
        """Проверки, отмеченные галочкой."""

        return [
            check
            for check in QUALITY_CHECKS
            if self._quality_check_boxes[check.key].isChecked()
        ]

    def _run_quality_checks(self) -> None:
        """Запустить выбранные проверки в фоновом потоке."""

        if self._db is None or self._conn is None:
            QMessageBox.information(
                self, "ZGeo-PG", tr("Сначала подключитесь к базе данных")
            )
            return
        if not self._tables:
            QMessageBox.information(
                self, "ZGeo-PG", tr("Список таблиц пуст — нажмите «Обновить»")
            )
            return
        checks = self._selected_checks()
        if not checks:
            QMessageBox.information(
                self, "ZGeo-PG", tr("Отметьте хотя бы одну проверку")
            )
            return

        self._stop_quality_task()
        self._quality_columns = [check.key for check in checks]
        self._quality_problems = 0
        self._quality_errors = 0
        self._build_quality_table(checks)

        self._quality_task = QualityTask(self._conn, list(self._tables), checks, self)
        self._quality_task.check_started.connect(self._on_quality_check_started)
        self._quality_task.check_done.connect(self._on_quality_check_done)
        self._quality_task.progress.connect(self._on_quality_progress)
        self._quality_task.finished_all.connect(self._on_quality_finished)

        self._quality_run_button.setEnabled(False)
        self._quality_cancel_button.setEnabled(True)
        self._progress_bar.setRange(0, len(checks) * len(self._tables))
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)
        self._progress_label.setVisible(True)
        self._progress_label.setText(tr("Подготовка проверок") + "...")
        self._set_status(tr("Проверка качества данных") + "...")
        self._quality_task.start()

    def _build_quality_table(self, checks: List) -> None:
        """Подготовить таблицу результатов: строка на таблицу, столбец на проверку."""

        headers = [tr("Схема"), tr("Таблица")] + [
            self._quality_column_title(check.key) for check in checks
        ]
        self._quality_table.clear()
        self._quality_table.setColumnCount(len(headers))
        self._quality_table.setHorizontalHeaderLabels(headers)
        self._quality_table.setRowCount(len(self._tables))
        self._quality_row_of = {}
        for row, table in enumerate(self._tables):
            self._quality_row_of[table.full_name] = row
            self._quality_table.setItem(row, 0, QTableWidgetItem(table.schema))
            self._quality_table.setItem(row, 1, QTableWidgetItem(table.name))
        self._quality_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._quality_summary_label.setText("")

    def _quality_column_title(self, key: str) -> str:
        """Название проверки по её ключу для заголовка столбца."""

        check = check_by_key(key)
        return tr(check.title) if check is not None else key

    def _populate_quality_headers(self) -> None:
        """Обновить заголовки таблицы результатов при смене языка."""

        if self._quality_table.columnCount() < 2:
            return
        headers = [tr("Схема"), tr("Таблица")] + [
            self._quality_column_title(key) for key in self._quality_columns
        ]
        self._quality_table.setHorizontalHeaderLabels(headers)

    def _on_quality_check_started(self, title: str) -> None:
        self._progress_label.setText(tr("Текущая проверка") + ": " + tr(title))

    def _on_quality_check_done(
        self, key: str, table_name: str, count, error: str
    ) -> None:
        if key not in self._quality_columns:
            return
        column = 2 + self._quality_columns.index(key)
        row = self._quality_row_of.get(table_name)
        if row is None:
            return
        if error:
            self._quality_errors += 1
            item = QTableWidgetItem(tr("Ошибка"))
            item.setToolTip(error)
        elif count is None:
            item = QTableWidgetItem(tr("Не применимо"))
        else:
            item = QTableWidgetItem(str(count))
            item.setData(Qt.ItemDataRole.UserRole, int(count))
            if count:
                self._quality_problems += int(count)
                item.setBackground(QColor("#ffd9d4"))
        self._quality_table.setItem(row, column, item)

    def _on_quality_progress(self, done: int, total: int) -> None:
        self._progress_bar.setRange(0, max(1, total))
        self._progress_bar.setValue(done)

    def _on_quality_finished(self, cancelled: bool, error: str) -> None:
        self._quality_task = None
        self._quality_run_button.setEnabled(self._db is not None)
        self._quality_cancel_button.setEnabled(False)
        self._progress_bar.setVisible(False)
        self._progress_label.setVisible(False)
        if error:
            self._set_status(tr("Ошибка") + ": " + error)
        elif cancelled:
            self._set_status(tr("Отменено"))
            self._quality_summary_label.setText(tr("Проверка прервана"))
        else:
            self._set_status(tr("Готово"))
            self._quality_summary_label.setText(
                tr("Найдено проблем: {}").format(self._quality_problems)
            )
        if self._quality_errors:
            self._quality_summary_label.setText(
                self._quality_summary_label.text()
                + " — "
                + tr("ошибок запросов: {}").format(self._quality_errors)
            )

    def _cancel_quality_checks(self) -> None:
        if self._quality_task is not None:
            self._quality_task.request_cancel()
            self._set_status(tr("Прерывание") + "...")

    def _stop_quality_task(self) -> None:
        if self._quality_task is not None:
            try:
                self._quality_task.request_cancel()
                self._quality_task.wait(200)
            except RuntimeError:
                pass
            self._quality_task = None
        self._quality_cancel_button.setEnabled(False)
        self._progress_bar.setVisible(False)
        self._progress_label.setVisible(False)

    # -------------------------------------------------------------- stats tab
    def _populate_stats(self) -> None:
        size_stats = build_size_distribution(self._tables)
        self._size_chart.set_title(tr("По размеру"))
        self._size_chart.set_items(
            [s.label for s in size_stats],
            [s.count for s in size_stats],
            [s.total_size for s in size_stats],
        )

        geom_stats = build_geometry_type_distribution(self._tables, limit=10)
        self._geom_chart.set_title(tr("По типу геометрии"))
        self._geom_chart.set_items(
            [s.name for s in geom_stats],
            [s.count for s in geom_stats],
            [s.total_size for s in geom_stats],
        )

        schema_stats = build_schema_distribution(self._tables)
        self._schema_table.setRowCount(len(schema_stats))
        self._schema_table.setColumnCount(4)
        for row, stat in enumerate(schema_stats):
            self._schema_table.setItem(row, 0, QTableWidgetItem(stat.name))
            count_item = QTableWidgetItem(str(stat.count))
            count_item.setData(Qt.ItemDataRole.UserRole, stat.count)
            self._schema_table.setItem(row, 1, count_item)
            size_item = QTableWidgetItem(format_size(stat.total_size))
            size_item.setData(Qt.ItemDataRole.UserRole, stat.total_size)
            self._schema_table.setItem(row, 2, size_item)
            indexed = all(
                table.has_spatial_index for table in self._tables_of_schema(stat.name)
            )
            self._schema_table.setItem(
                row, 3, QTableWidgetItem(tr("Да") if indexed else tr("Нет"))
            )
        self._schema_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._schema_table.horizontalHeader().setStretchLastSection(True)
        self._populate_stats_table()

    def _populate_stats_table(self) -> None:
        if not hasattr(self, "_schema_table"):
            return
        self._schema_table.setHorizontalHeaderLabels(
            [
                tr("Схема"),
                tr("Кол-во"),
                tr("Размер"),
                tr("Пространственный индекс"),
            ]
        )
        header = self._schema_table.horizontalHeader()
        if header is not None:
            self._schema_table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.ResizeToContents
            )
            self._schema_table.horizontalHeader().setStretchLastSection(True)

    # -------------------------------------------------------- spatial indexes
    def _tables_of_schema(self, schema: str) -> List[SpatialTable]:
        return [table for table in self._tables if table.schema == schema]

    def _on_tables_context_menu(self, position) -> None:
        """Меню индекса для строки списка таблиц под курсором."""

        index = self._table.indexAt(position)
        if not index.isValid():
            return
        visible = self._visible_tables()
        if index.row() >= len(visible):
            return
        if index.row() not in self._selected_indexes():
            self._table.selectRow(index.row())
        tables = [
            visible[row] for row in self._selected_indexes() if row < len(visible)
        ]
        if not tables:
            return
        # Состав меню зависит от значения в колонке «Пространственный индекс»
        # строки, на которой вызвано меню.
        has_index = visible[index.row()].has_spatial_index
        menu = QMenu(self)
        if has_index:
            refresh_action = menu.addAction(tr("Обновить пространственный индекс"))
            drop_action = menu.addAction(tr("Удалить пространственный индекс"))
        else:
            create_action = menu.addAction(tr("Создать пространственный индекс"))
            refresh_action = None
            drop_action = None
        for item in menu.actions():
            item.setEnabled(self._db is not None)
        chosen = menu.exec(self._table.viewport().mapToGlobal(position))
        if chosen is None:
            return
        if chosen == refresh_action:
            self._refresh_indexes(tables)
        elif chosen == drop_action:
            self._drop_indexes(tables)
        else:
            self._create_indexes(tables)

    def _on_stats_context_menu(self, position) -> None:
        """Меню индекса для строки статистики по схемам."""

        index = self._schema_table.indexAt(position)
        if not index.isValid():
            return
        self._schema_table.selectRow(index.row())
        schema_item = self._schema_table.item(index.row(), 0)
        value_item = self._schema_table.item(index.row(), 3)
        if schema_item is None or value_item is None:
            return
        tables = self._tables_of_schema(schema_item.text())
        if not tables:
            return
        # Меню показывается только для строк со значением «Нет» в колонке
        # наличия пространственного индекса.
        if value_item.text() != tr("Нет"):
            return
        menu = QMenu(self)
        action = menu.addAction(tr("Создать пространственный индекс"))
        action.setEnabled(self._db is not None)
        if menu.exec(self._schema_table.viewport().mapToGlobal(position)) != action:
            return
        self._create_indexes(tables)

    def _on_create_indexes_for_all(self) -> None:
        self._create_indexes(list(self._tables))

    def _on_refresh_indexes_for_all(self) -> None:
        self._refresh_indexes(list(self._tables))

    def _on_refresh_indexes_for_all(self) -> None:
        self._refresh_indexes(list(self._tables))

    def _create_indexes(self, tables: List[SpatialTable]) -> None:
        self._run_index_action(IndexTask.ACTION_CREATE, tables)

    def _refresh_indexes(self, tables: List[SpatialTable]) -> None:
        self._run_index_action(IndexTask.ACTION_REINDEX, tables)

    def _drop_indexes(self, tables: List[SpatialTable]) -> None:
        names = [table.full_name for table in tables if table.has_spatial_index]
        if not names:
            QMessageBox.information(
                self, "ZGeo-PG", tr("Пространственный индекс не найден")
            )
            return
        answer = QMessageBox.question(
            self,
            "ZGeo-PG",
            tr("Удалить пространственный индекс") + f"?\n\n" + "\n".join(names[:10]),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._run_index_action(IndexTask.ACTION_DROP, tables)

    def _run_index_action(self, action: str, tables: List[SpatialTable]) -> None:
        if self._db is None or self._conn is None:
            return
        if not tables:
            QMessageBox.information(
                self, "ZGeo-PG", tr("Выберите одну таблицу в списке")
            )
            return
        if action in (IndexTask.ACTION_REINDEX, IndexTask.ACTION_DROP):
            targets = [table for table in tables if table.has_spatial_index]
            if not targets:
                QMessageBox.information(
                    self, "ZGeo-PG", tr("Пространственный индекс не найден")
                )
                return
        else:
            targets = [table for table in tables if not table.has_spatial_index]
            if not targets:
                QMessageBox.information(
                    self, "ZGeo-PG", tr("Пространственный индекс уже создан")
                )
                return

        keys = {(table.schema, table.name) for table in targets}
        jobs = [
            (position, table, action)
            for position, table in enumerate(self._tables)
            if (table.schema, table.name) in keys
        ]
        self._stop_index_task()
        self._index_action = action
        self._index_changed = []
        self._index_errors = []
        self._index_task = IndexTask(self._conn, jobs, self)
        self._index_task.table_done.connect(self._on_index_done)
        self._index_task.progress.connect(self._on_index_progress)
        self._index_task.finished_all.connect(self._on_index_finished)
        self._create_all_indexes_button.setEnabled(False)
        self._refresh_all_indexes_button.setEnabled(False)
        self._set_status(self._index_action_label() + "...")
        self._index_task.start()

    def _stop_index_task(self) -> None:
        if self._index_task is not None:
            try:
                self._index_task.request_cancel()
                self._index_task.wait(200)
            except RuntimeError:
                pass
            self._index_task = None

    def _on_index_done(self, index: int, _action: str, error: str) -> None:
        if error:
            self._index_errors.append(error)
            return
        self._index_changed.append(index)

    def _index_action_label(self) -> str:
        if self._index_action == IndexTask.ACTION_CREATE:
            return tr("Создание пространственного индекса")
        if self._index_action == IndexTask.ACTION_DROP:
            return tr("Удаление пространственного индекса")
        return tr("Обновление пространственного индекса")

    def _on_index_progress(self, done: int, total: int) -> None:
        self._set_status(f"{self._index_action_label()}... {done} / {total}")

    def _on_index_finished(self, cancelled: bool, error: str) -> None:
        for position in list(self._index_changed):
            self._refresh_index_info(position)
        self._index_changed = []
        self._populate_stats()
        self._create_all_indexes_button.setEnabled(self._db is not None)
        self._refresh_all_indexes_button.setEnabled(self._db is not None)
        if error:
            self._set_status(tr("Ошибка") + ": " + error)
            QMessageBox.critical(self, "ZGeo-PG", tr("Ошибка") + ":\n" + error)
        elif self._index_errors:
            details = "\n".join(self._index_errors[:10])
            self._set_status(tr("Ошибка"))
            QMessageBox.warning(
                self, "ZGeo-PG", tr("Не удалось выполнить операцию") + "\n\n" + details
            )
        elif cancelled:
            self._set_status(tr("Отменено"))
        else:
            self._set_status(tr("Готово"))
        self._index_errors = []
        self._index_task = None

    def _refresh_index_info(self, position: int) -> None:
        if self._db is None or position >= len(self._tables):
            return
        table = self._tables[position]
        name, size = fetch_spatial_index(self._db, table)
        self._tables[position] = replace(
            table, spatial_index_name=name, spatial_index_size=size
        )
        self._refresh_table_row(position)
        self._update_summary()

    # --------------------------------------------------------- connection tab
    def _restore_connections(self) -> None:
        """Подтянуть соединения из SQLite и заполнить форму последним из них."""

        sync_connections_from_sqlite()
        self._reload_saved_combo()
        name = last_connection_name()
        conn = load_connection(name) if name else None
        if conn is None:
            return
        self._fill_connection_form(conn)
        index = self._saved_combo.findText(conn.name)
        if index >= 0:
            self._saved_combo.setCurrentIndex(index)

    def _fill_connection_form(self, conn: PGConnection) -> None:
        self._conn_name.setText(conn.name)
        self._conn_host.setText(conn.host)
        self._conn_port.setValue(conn.port)
        self._conn_db.setText(conn.database)
        self._conn_user.setText(conn.user)
        self._conn_password.setText(conn.password)

    def _reload_saved_combo(self) -> None:
        names = list_saved_connections()
        current = self._saved_combo.currentText()
        self._saved_combo.blockSignals(True)
        self._saved_combo.clear()
        self._saved_combo.addItems(names)
        index = self._saved_combo.findText(current)
        if index < 0 and self._saved_combo.count() > 0:
            index = 0
        self._saved_combo.setCurrentIndex(index if index >= 0 else -1)
        self._saved_combo.blockSignals(False)

    def _on_saved_selected(self, _name: str) -> None:
        pass

    def _on_load_saved(self) -> None:
        name = self._saved_combo.currentText()
        if not name:
            return
        conn = load_connection(name)
        if conn is None:
            return
        self._fill_connection_form(conn)
        # Подключаемся сразу после загрузки параметров выбранного соединения.
        if self._db is not None:
            self._disconnect()
        self._on_connect()

    def _on_delete_saved(self) -> None:
        name = self._saved_combo.currentText()
        if not name:
            return
        delete_connection(name)
        self._reload_saved_combo()

    def _on_save_connection(self) -> None:
        conn = self._current_connection_form()
        stored = save_connection(conn)
        self._reload_saved_combo()
        index = self._saved_combo.findText(conn.name)
        if index >= 0:
            self._saved_combo.setCurrentIndex(index)
        if stored:
            self._set_status(tr("Соединение сохранено"))
        else:
            self._set_status(tr("Не удалось сохранить соединение в SQLite"))

    def _on_test_connection(self) -> None:
        conn = self._current_connection_form()
        try:
            db = open_connection(conn)
        except Exception as error:  # noqa: BLE001
            QMessageBox.critical(self, "ZGeo-PG", tr("Ошибка подключения") + ":\n" + str(error))
            return
        try:
            close_connection(conn)
        except RuntimeError:
            pass
        QMessageBox.information(self, "ZGeo-PG", tr("Подключено к") + f" {conn.qualified}")

    def shutdown(self) -> None:
        self._stop_task()
        self._stop_index_task()
        self._stop_quality_task()
        if self._conn is not None:
            try:
                close_connection(self._conn)
            except RuntimeError:
                pass
            self._conn = None
            self._db = None


def _cell_raw(table: SpatialTable, column: int):
    if column == 5:
        return table.srid
    if column == 7:
        return table.estimated_rows
    if column == 8:
        return table.feature_count
    if column == 9:
        return table.data_size
    if column == 10:
        return table.index_size
    if column == 13:
        return table.spatial_index_size
    if column == 14:
        return table.full_size
    return None


class _FormLayout:
    """Простая помощь для построения формы «подпись — поле»."""

    def __init__(self, box: QGroupBox) -> None:
        self._layout = QVBoxLayout(box)
        self._box = box
        self._labels: List[Tuple[QLabel, str]] = []

    def retranslate(self) -> None:
        """Обновить подписи полей при смене языка."""
        for label, source in self._labels:
            label.setText(tr(source))

    def add_line(self, label: str, default: str = "", password: bool = False) -> QLineEdit:
        row = QHBoxLayout()
        lab = QLabel(label)
        self._labels.append((lab, label))
        lab.setFixedWidth(120)
        edit = QLineEdit(default)
        if password:
            edit.setEchoMode(QLineEdit.EchoMode.Password)
        row.addWidget(lab)
        row.addWidget(edit, 1)
        self._layout.addLayout(row)
        return edit

    def add_spin(self, label: str, default: int, minimum: int, maximum: int) -> QSpinBox:
        row = QHBoxLayout()
        lab = QLabel(label)
        self._labels.append((lab, label))
        lab.setFixedWidth(120)
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(default)
        row.addWidget(lab)
        row.addWidget(spin, 1)
        self._layout.addLayout(row)
        return spin