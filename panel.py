"""Плавающая панель ZGeo-PG: список таблиц, статистика и соединение."""

from __future__ import annotations

from typing import Dict, List, Optional

from qgis.PyQt.QtCore import QSettings, Qt, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDockWidget,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .catalog import (
    SpatialTable,
    crs_label,
    fetch_crs_auth,
    fetch_spatial_tables,
    parse_srid,
)
from .charts import BarChart
from .connection import (
    PGConnection,
    close_connection,
    delete_connection,
    list_saved_connections,
    load_connection,
    open_connection,
    save_connection,
)
from .formatting import format_number, format_size
from .i18n import EN_TRANSLATIONS, LANGUAGE_EN, LANGUAGE_KEY, get_language, set_language, tr
from .load_task import LoadTablesTask
from .stats import (
    build_geometry_type_distribution,
    build_schema_distribution,
    build_size_distribution,
    totals,
)
from .table_export import export_rows_with_dialog, export_table_with_dialog
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
        self.setWindowTitle("ZGeo-PG")
        self._settings = QSettings()
        self._conn: Optional[PGConnection] = None
        self._db = None
        self._tables: List[SpatialTable] = []
        self._task: Optional[LoadTablesTask] = None
        self._schema_filter: Optional[str] = None
        self._only_geometry = True

        self._build_ui()
        self._build_connection_tab()
        self._build_tables_tab()
        self._build_stats_tab()
        self._retranslate()

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

        self._status = QStatusBar()
        self._status.setSizeGripEnabled(True)
        self._status_label = QLabel()
        self._selected_label = QLabel()
        self._status.addWidget(self._status_label, 1)
        self._status.addPermanentWidget(self._selected_label)
        outer.addWidget(self._status)

        self.setWidget(container)

    def _build_tables_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(6, 6, 6, 6)

        bar = QHBoxLayout()
        self._connect_button = QPushButton()
        self._connect_button.clicked.connect(self._on_connect)
        bar.addWidget(self._connect_button)
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
        layout.addWidget(self._table, 1)

        self._summary_label = QLabel()
        layout.addWidget(self._summary_label)

        self._tabs.addTab(page, tr("Таблицы"))

    def _build_stats_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(6, 6, 6, 6)

        self._size_chart = BarChart()
        self._geom_chart = BarChart()
        layout.addWidget(self._size_chart)
        layout.addWidget(self._geom_chart)

        self._schema_table = QTableWidget(0, 3)
        self._schema_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._schema_table.verticalHeader().setVisible(False)
        layout.addWidget(self._schema_table, 1)

        stats_bar = QHBoxLayout()
        self._stats_export_button = QPushButton()
        self._stats_export_button.clicked.connect(self._on_stats_export)
        stats_bar.addWidget(self._stats_export_button)
        stats_bar.addStretch(1)
        layout.addLayout(stats_bar)

        self._tabs.addTab(page, tr("Статистика"))

    def _build_connection_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(6, 6, 6, 6)

        saved_box = QGroupBox(tr("Сохранённые соединения"))
        saved_layout = QHBoxLayout(saved_box)
        self._saved_combo = QComboBox()
        self._saved_combo.currentTextChanged.connect(self._on_saved_selected)
        saved_layout.addWidget(self._saved_combo, 1)
        load_btn = QPushButton(tr("Загрузить"))
        load_btn.clicked.connect(self._on_load_saved)
        saved_layout.addWidget(load_btn)
        del_btn = QPushButton(tr("Удалить"))
        del_btn.clicked.connect(self._on_delete_saved)
        saved_layout.addWidget(del_btn)
        layout.addWidget(saved_box)

        form_box = QGroupBox(tr("Параметры подключения"))
        form = _FormLayout(form_box)

        self._conn_name = form.add_line(tr("Имя"))
        self._conn_host = form.add_line(tr("Хост"), "localhost")
        self._conn_port = form.add_spin(tr("Порт"), 5432, 1, 65535)
        self._conn_db = form.add_line(tr("База данных"))
        self._conn_user = form.add_line(tr("Пользователь"), "postgres")
        self._conn_password = form.add_line(tr("Пароль"), "", password=True)
        layout.addWidget(form_box)

        actions = QHBoxLayout()
        save_btn = QPushButton(tr("Сохранить соединение"))
        save_btn.clicked.connect(self._on_save_connection)
        actions.addWidget(save_btn)
        test_btn = QPushButton(tr("Проверить подключение"))
        test_btn.clicked.connect(self._on_test_connection)
        actions.addWidget(test_btn)
        actions.addStretch(1)
        layout.addLayout(actions)
        layout.addStretch(1)

        self._tabs.addTab(page, tr("Соединение"))

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

    def _retranslate(self) -> None:
        self.setWindowTitle("ZGeo-PG")
        self._title_label.setText(
            tr("ZGeo-PG — каталог пространственных данных PostGIS") + "  v" + get_plugin_version()
        )
        self._lang_button.setText("RU" if get_language() == LANGUAGE_EN else "EN")
        self._tabs.setTabText(0, tr("Таблицы"))
        self._tabs.setTabText(1, tr("Статистика"))
        self._tabs.setTabText(2, tr("Соединение"))
        self._connect_button.setText(tr("Отключиться") if self._db else tr("Подключиться"))
        self._refresh_button.setText(tr("Обновить"))
        self._info_button.setText(tr("Информация"))
        self._export_button.setText(tr("Экспорт"))
        self._cancel_button.setText(tr("Отмена"))
        self._search_edit.setPlaceholderText(tr("Поиск"))
        self._only_geometry_check.setText(tr("Только с геометрией"))
        self._stats_export_button.setText(tr("Экспорт в Excel"))
        self._populate_table_headers()
        self._populate_stats_table()
        self._update_summary()
        self._update_selected()

    # -------------------------------------------------------------- database
    def _on_connect(self) -> None:
        if self._db is not None:
            self._disconnect()
            return
        conn = self._current_connection_form()
        try:
            self._set_status(tr("Подключение") + "...")
            self._db = open_connection(conn)
            self._conn = conn
        except Exception as error:  # noqa: BLE001
            self._db = None
            self._conn = None
            self._set_status(tr("Готово"))
            QMessageBox.critical(self, "ZGeo-PG", tr("Ошибка подключения") + ":\n" + str(error))
            return
        self._retranslate()
        self._reload_tables()

    def _disconnect(self) -> None:
        self._stop_task()
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
        self._retranslate()
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
            tr("Столбец"),
            tr("Тип"),
            tr("SRID"),
            tr("Система координат"),
            tr("Строк (оценка)"),
            tr("Строк (точно)"),
            tr("Размер"),
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
                haystack = f"{table.schema} {table.name} {table.geom_column}".casefold()
                if query not in haystack:
                    continue
            result.append(table)
        return result

    def _write_table_row(self, row: int, table: SpatialTable) -> None:
        geom_label = _geometry_label(table)
        cells = [
            table.schema,
            table.name,
            table.geom_column,
            geom_label,
            "" if table.srid is None else str(table.srid),
            crs_label(table.srid, self._auth_for(table.srid)),
            format_number(table.estimated_rows),
            format_number(table.feature_count),
            format_size(table.total_size) if table.total_size is not None else "—",
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
        self._info_button.setEnabled(len(self._selected_indexes()) == 1)
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
        if len(indexes) != 1:
            return
        table = self._visible_tables()[indexes[0]]
        from .info_dialog import show_table_info

        show_table_info(self, table)

    def _on_export(self) -> None:
        visible = self._visible_tables()
        if not visible:
            return
        headers = [
            tr("Схема"),
            tr("Таблица"),
            tr("Столбец"),
            tr("Тип"),
            tr("SRID"),
            tr("Система координат"),
            tr("Строк (оценка)"),
            tr("Строк (точно)"),
            tr("Размер"),
        ]
        rows = []
        for table in visible:
            rows.append(
                [
                    table.schema,
                    table.name,
                    table.geom_column,
                    _geometry_label(table),
                    "" if table.srid is None else table.srid,
                    crs_label(table.srid, self._auth_for(table.srid)),
                    table.estimated_rows,
                    table.feature_count if table.feature_count is not None else "",
                    table.total_size if table.total_size is not None else "",
                ]
            )
        count, features, size = totals(visible)
        rows.append(
            [
                "",
                "",
                "",
                "",
                "",
                tr("Итого"),
                count,
                features,
                size,
            ]
        )
        export_rows_with_dialog(
            self,
            headers,
            rows,
            "zgeo-pg_tables.xlsx",
            tr("Таблицы"),
        )

    def _on_stats_export(self) -> None:
        if self._schema_table.rowCount() == 0:
            return
        export_table_with_dialog(
            self,
            self._schema_table,
            "zgeo-pg_stats.xlsx",
            tr("Статистика по схемам"),
        )

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
        self._schema_table.setColumnCount(3)
        self._schema_table.setHorizontalHeaderLabels(
            [tr("Схема"), tr("Кол-во"), tr("Размер")]
        )
        for row, stat in enumerate(schema_stats):
            self._schema_table.setItem(row, 0, QTableWidgetItem(stat.name))
            self._schema_table.setItem(row, 1, QTableWidgetItem(str(stat.count)))
            self._schema_table.setItem(row, 2, QTableWidgetItem(format_size(stat.total_size)))
        self._schema_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._schema_table.horizontalHeader().setStretchLastSection(True)
        self._populate_stats_table()

    def _populate_stats_table(self) -> None:
        if not hasattr(self, "_schema_table"):
            return
        header = self._schema_table.horizontalHeader()
        if header is not None:
            self._schema_table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.ResizeToContents
            )
            self._schema_table.horizontalHeader().setStretchLastSection(True)

    # --------------------------------------------------------- connection tab
    def _reload_saved_combo(self) -> None:
        names = list_saved_connections()
        current = self._saved_combo.currentText()
        self._saved_combo.blockSignals(True)
        self._saved_combo.clear()
        self._saved_combo.addItems(names)
        index = self._saved_combo.findText(current)
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
        self._conn_name.setText(conn.name)
        self._conn_host.setText(conn.host)
        self._conn_port.setValue(conn.port)
        self._conn_db.setText(conn.database)
        self._conn_user.setText(conn.user)
        self._conn_password.setText(conn.password)

    def _on_delete_saved(self) -> None:
        name = self._saved_combo.currentText()
        if not name:
            return
        delete_connection(name)
        self._reload_saved_combo()

    def _on_save_connection(self) -> None:
        conn = self._current_connection_form()
        save_connection(conn)
        self._reload_saved_combo()
        index = self._saved_combo.findText(conn.name)
        if index >= 0:
            self._saved_combo.setCurrentIndex(index)

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
        if self._conn is not None:
            try:
                close_connection(self._conn)
            except RuntimeError:
                pass
            self._conn = None
            self._db = None


def _cell_raw(table: SpatialTable, column: int):
    if column == 4:
        return table.srid
    if column == 6:
        return table.estimated_rows
    if column == 7:
        return table.feature_count
    if column == 8:
        return table.total_size
    return None


class _FormLayout:
    """Простая помощь для построения формы «подпись — поле»."""

    def __init__(self, box: QGroupBox) -> None:
        self._layout = QVBoxLayout(box)
        self._box = box

    def add_line(self, label: str, default: str = "", password: bool = False) -> QLineEdit:
        row = QHBoxLayout()
        lab = QLabel(label)
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
        lab.setFixedWidth(120)
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(default)
        row.addWidget(lab)
        row.addWidget(spin, 1)
        self._layout.addLayout(row)
        return spin