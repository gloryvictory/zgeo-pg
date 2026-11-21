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
    QDialog,
    QDockWidget,
    QGridLayout,
    QListWidget,
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
    sync_connections_from_sqlite,
    delete_connection,
    last_connection_name,
    list_saved_connections,
    load_connection,
    open_connection,
    save_connection,
)
from .formatting import format_number, format_size
from .i18n import EN_TRANSLATIONS, LANGUAGE_EN, LANGUAGE_KEY, get_language, set_language, tr
from .load_task import IndexTask, LoadTablesTask
from .nsi import (
    NsiComparison,
    compare_values,
    fetch_unique_values,
    list_tables,
    list_text_columns,
    readable_error,
)
from .quality import (
    ATTRIBUTE_CHECKS,
    THRESHOLD_DEFAULTS,
    QUALITY_CHECKS,
    AttributeTask,
    QualityTask,
    check_by_key,
    load_thresholds,
    save_thresholds,
)
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
    export_report_with_dialog,
    export_rows_with_dialog,
    export_sections_with_dialog,
    export_table_with_dialog,
)
from .version import get_plugin_version

GEO_TYPE_COLORS = {}


def _geometry_label(table: SpatialTable) -> str:
    return table.geom_type


class ThresholdsDialog(QDialog):
    """Пороги проверок качества: числа, выше или ниже которых объект считается проблемным."""

    FIELDS = (
        ("max_points", "Максимум вершин в объекте", 1, 100000000),
        ("min_area", "Минимальная площадь полигона", 0, 1000000000),
        ("min_area_geographic", "Минимальная площадь полигона, м²", 0, 1000000000),
        ("min_length", "Минимальная длина линии", 0, 1000000000),
        ("min_length_geographic", "Минимальная длина линии, м", 0, 1000000000),
        ("overlap_tolerance", "Допуск для почти дублей", 0, 1000000000),
        ("overlap_tolerance_geographic", "Допуск для почти дублей, м", 0, 1000000000),
        ("sliver_area", "Максимальная площадь сливера", 0, 1000000000),
        ("sliver_area_geographic", "Максимальная площадь сливера, м²", 0, 1000000000),
        ("max_parts", "Максимум частей в объекте", 1, 1000000),
        ("max_bytes", "Максимум размера геометрии, байт", 1024, 1000000000),
        ("stale_days", "Устаревание статистики, дней", 1, 3650),
    )

    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setWindowTitle("ZGeo-PG — " + tr("Пороги проверок"))
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        self._labels: List[Tuple[QLabel, str]] = []
        self._spins: Dict[str, QSpinBox] = {}
        values = load_thresholds()
        form = QVBoxLayout()
        for name, label, minimum, maximum in self.FIELDS:
            row = QHBoxLayout()
            caption = QLabel(label)
            caption.setFixedWidth(260)
            self._labels.append((caption, label))
            spin = QSpinBox()
            spin.setRange(minimum, maximum)
            spin.setValue(int(values.get(name, THRESHOLD_DEFAULTS[name])))
            self._spins[name] = spin
            row.addWidget(caption)
            row.addWidget(spin, 1)
            form.addLayout(row)
        layout.addLayout(form)

        self._hint = QLabel()
        self._hint.setWordWrap(True)
        layout.addWidget(self._hint)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self._save_button = QPushButton()
        self._save_button.clicked.connect(self._save)
        buttons.addWidget(self._save_button)
        self._cancel_button = QPushButton()
        self._cancel_button.clicked.connect(self.reject)
        buttons.addWidget(self._cancel_button)
        layout.addLayout(buttons)
        self.retranslate()

    def retranslate(self) -> None:
        for caption, source in self._labels:
            caption.setText(tr(source))
        self._save_button.setText(tr("Сохранить"))
        self._cancel_button.setText(tr("Отмена"))
        self._hint.setText(
            tr(
                "Пороги применяются к проверкам «Слишком много вершин», "
                "«Микрообъекты», «Микролинии», «Слишком много частей», «Очень "
                "крупная геометрия», «Устаревшая статистика таблицы», «Почти "
                "дубли геометрий» и «Сливеры (узкие щели)»."
            )
        )

    def _save(self) -> None:
        save_thresholds({name: spin.value() for name, spin in self._spins.items()})
        self.accept()



class DuplicateDetailsDialog(QDialog):
    """Подробный список дублей по атрибутам с процентом вхождения."""

    CATEGORY_SOURCES = {
        "full": "Полные дубли строк",
        "key": "Дубли составного ключа",
        "case": "Совпадения без учёта регистра и пробелов",
        "partial": "Частичные вхождения",
    }

    def __init__(self, parent, table_name: str, details) -> None:
        super().__init__(parent)
        self.setWindowTitle("ZGeo-PG — " + tr("Дубли по атрибутам"))
        self.resize(760, 460)
        layout = QVBoxLayout(self)

        self._table_label = QLabel(table_name)
        layout.addWidget(self._table_label)

        self._table = QTableWidget(len(details), 4)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        for row, (category, left, right, percent) in enumerate(details):
            category_item = QTableWidgetItem(
                tr(self.CATEGORY_SOURCES.get(category, category))
            )
            category_item.setData(Qt.ItemDataRole.UserRole, category)
            self._table.setItem(row, 0, category_item)
            self._table.setItem(row, 1, QTableWidgetItem(left))
            self._table.setItem(row, 2, QTableWidgetItem(right))
            percent_item = QTableWidgetItem(
                "" if percent is None else "{:.1f} %".format(percent)
            )
            if percent is not None:
                percent_item.setData(Qt.ItemDataRole.UserRole, percent)
            self._table.setItem(row, 3, percent_item)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._table, 1)

        self._summary = QLabel()
        layout.addWidget(self._summary)

        buttons = QHBoxLayout()
        self._export_button = QPushButton()
        self._export_button.clicked.connect(self._on_export)
        buttons.addWidget(self._export_button)
        buttons.addStretch(1)
        close_button = QPushButton(tr("Закрыть"))
        close_button.clicked.connect(self.accept)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        self.retranslate()

    def retranslate(self) -> None:
        self._table.setHorizontalHeaderLabels(
            [
                tr("Вид дубля"),
                tr("Значение"),
                tr("Совпадение"),
                tr("Процент вхождения"),
            ]
        )
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item is None:
                continue
            category = item.data(Qt.ItemDataRole.UserRole)
            if category:
                item.setText(tr(self.CATEGORY_SOURCES.get(category, category)))
        self._export_button.setText(tr("Экспорт"))
        self._summary.setText(
            tr("Записей в списке: {}").format(self._table.rowCount())
        )

    def _rows(self) -> List[List[object]]:
        rows: List[List[object]] = []
        for row in range(self._table.rowCount()):
            values: List[object] = []
            for column in range(self._table.columnCount()):
                item = self._table.item(row, column)
                values.append(item.text() if item is not None else "")
            rows.append(values)
        return rows

    def _on_export(self) -> None:
        if self._table.rowCount() == 0:
            return
        export_format = ask_export_format(self, self._export_button)
        if export_format is None:
            return
        headers = [
            self._table.horizontalHeaderItem(column).text()
            for column in range(self._table.columnCount())
        ]
        suffix = "html" if export_format == FORMAT_HTML else "xlsx"
        export_rows_with_dialog(
            self,
            headers,
            self._rows(),
            "zgeo-pg_duplicates." + suffix,
            tr("Дубли по атрибутам"),
            export_format=export_format,
        )


def show_duplicate_details(parent, table_name: str, details) -> None:
    """Открыть окно с подробным списком дублей."""

    dialog = DuplicateDetailsDialog(parent, table_name, details)
    dialog.exec()


class QualityTabPage(QWidget):
    """Вкладка проверок качества: галочки, описания, результаты и экспорт."""

    def __init__(self, host, checks, task_class, title_source: str, prefix: str) -> None:
        super().__init__()
        self._host = host
        self._checks = list(checks)
        self._task_class = task_class
        self._prefix = prefix
        self.title_source = title_source
        self._task = None
        self._boxes: Dict[str, QCheckBox] = {}
        self._columns: List[str] = []
        self._row_of: Dict[str, int] = {}
        self._problems = 0
        self._errors = 0
        self._state: Tuple[str, str] = ("idle", "")
        self._results: Dict[str, Dict[str, Tuple[object, str]]] = {}
        self._details: Dict[Tuple[str, str], List[tuple]] = {}
        self._help_key: Optional[str] = None
        self._build()

    # ------------------------------------------------------------------ UI
    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        checks_box = QGroupBox()
        self.checks_box = checks_box
        checks_layout = QVBoxLayout(checks_box)
        checks_layout.setContentsMargins(6, 6, 6, 6)
        for check in self._checks:
            row = QHBoxLayout()
            box = QCheckBox()
            # Долгие проверки по умолчанию выключены (см. enabled_by_default).
            box.setChecked(getattr(check, "enabled_by_default", True))
            self._boxes[check.key] = box
            row.addWidget(box, 1)
            info = QPushButton("i")
            info.setFixedWidth(26)
            info.clicked.connect(
                lambda _checked=False, key=check.key: self._show_description(key)
            )
            row.addWidget(info)
            checks_layout.addLayout(row)
        checks_layout.addStretch(1)
        splitter.addWidget(checks_box)

        self._help = QTextBrowser()
        self._help.setMinimumWidth(240)
        self._help.setVisible(False)
        splitter.addWidget(self._help)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 4)
        layout.addWidget(splitter, 1)

        self.table = QTableWidget(0, 0)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        layout.addWidget(self.table, 1)

        self.summary_label = QLabel()
        layout.addWidget(self.summary_label)

        buttons = QHBoxLayout()
        self.run_button = QPushButton()
        self.run_button.clicked.connect(self._run)
        self.run_button.setEnabled(False)
        buttons.addWidget(self.run_button)
        self.cancel_button = QPushButton()
        self.cancel_button.clicked.connect(self._cancel)
        self.cancel_button.setEnabled(False)
        buttons.addWidget(self.cancel_button)
        buttons.addStretch(1)
        self.export_button = QPushButton()
        self.export_button.clicked.connect(self._on_export)
        self.export_button.setEnabled(False)
        buttons.addWidget(self.export_button)
        # Пороги есть только у проверок пространственных данных.
        self._thresholds_button = None
        if any(getattr(check, "sql", None) for check in self._checks):
            self._thresholds_button = QPushButton()
            self._thresholds_button.clicked.connect(self._edit_thresholds)
            buttons.addWidget(self._thresholds_button)
        layout.addLayout(buttons)

    def _edit_thresholds(self) -> None:
        """Открыть окно порогов проверок."""

        dialog = ThresholdsDialog(self)
        dialog.exec()

    def retranslate(self) -> None:
        """Обновить все подписи вкладки при смене языка."""

        self.checks_box.setTitle(tr("Проверки"))
        self.run_button.setText(tr("Проверить"))
        self.cancel_button.setText(tr("Прервать"))
        self.export_button.setText(tr("Экспорт"))
        self.export_button.setToolTip(tr("Экспорт результатов проверок"))
        if self._thresholds_button is not None:
            self._thresholds_button.setText(tr("Пороги"))
            self._thresholds_button.setToolTip(tr("Пороги проверок"))
        for check in self._checks:
            self._boxes[check.key].setText(tr(check.title))
            self._boxes[check.key].setToolTip(tr(check.summary))
        self._populate_headers()
        self._render_cells()
        self._render_summary()
        if self._help_key is not None:
            self._render_description(self._help_key)

    def set_available(self, available: bool) -> None:
        """Разрешить запуск проверок, когда есть подключение и список таблиц."""

        self.run_button.setEnabled(available and self._task is None)

    # --------------------------------------------------------- descriptions
    def _render_description(self, key: str) -> None:
        """Показать описание проверки на текущем языке интерфейса."""

        check = check_by_key(key)
        if check is None:
            return
        self._help_key = key
        self._help.setHtml(
            "<h3>{}</h3><p>{}</p><p><b>{}</b> {}</p>".format(
                tr(check.title),
                tr(check.description),
                tr("Как исправить") + ":",
                tr(check.fix),
            )
        )

    def _show_description(self, key: str) -> None:
        """Открыть описание справа; повторное нажатие закрывает его."""

        if check_by_key(key) is None:
            return
        if self._help.isVisible() and self._help_key == key:
            self._help.setVisible(False)
            return
        self._render_description(key)
        self._help.setVisible(True)

    # ---------------------------------------------------------------- run
    def _selected_checks(self) -> List:
        return [check for check in self._checks if self._boxes[check.key].isChecked()]

    def _run(self) -> None:
        """Запустить выбранные проверки в фоновом потоке."""

        host = self._host
        if host._db is None or host._conn is None:
            QMessageBox.information(
                self, "ZGeo-PG", tr("Сначала подключитесь к базе данных")
            )
            return
        if not host._tables:
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
        self.stop()
        if not host.begin_progress(len(checks) * len(host._tables), self):
            return

        self._columns = [check.key for check in checks]
        self._problems = 0
        self._errors = 0
        self._state = ("running", "")
        self._build_table(checks)

        try:
            self._task = self._task_class(
                host._conn, list(host._tables), checks, self, load_thresholds()
            )
        except TypeError:
            # Атрибутные проверки не используют пороги.
            self._task = self._task_class(host._conn, list(host._tables), checks, self)
        self._task.check_started.connect(self._on_check_started)
        self._task.check_done.connect(self._on_check_done)
        if hasattr(self._task, "check_details"):
            # Подробный список дублей приходит только у проверок, которые
            # умеют его собрать (дубли по атрибутам).
            self._task.check_details.connect(self._on_check_details)
        self._task.progress.connect(host.progress_update)
        self._task.finished_all.connect(self._on_finished)

        self.run_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        host.set_progress_text(tr("Подготовка проверок") + "...")
        host._set_status(tr("Проверка качества данных") + "...")
        self._task.start()

    def _cancel(self) -> None:
        if self._task is not None:
            self._task.request_cancel()
            self._host._set_status(tr("Прерывание") + "...")

    def stop(self) -> None:
        """Прервать и отпустить поток проверок."""

        if self._task is not None:
            try:
                self._task.request_cancel()
                self._task.wait(200)
            except RuntimeError:
                pass
            self._task = None
        self.cancel_button.setEnabled(False)
        if self._host._active_page is self:
            self._host.end_progress()

    # -------------------------------------------------------------- table
    def _column_title(self, key: str) -> str:
        check = check_by_key(key)
        return tr(check.title) if check is not None else key

    def _build_table(self, checks) -> None:
        headers = [tr("Схема"), tr("Таблица")] + [
            self._column_title(check.key) for check in checks
        ]
        self.table.clear()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(self._host._tables))
        self._row_of = {}
        for row, table in enumerate(self._host._tables):
            self._row_of[table.full_name] = row
            self.table.setItem(row, 0, QTableWidgetItem(table.schema))
            self.table.setItem(row, 1, QTableWidgetItem(table.name))
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.summary_label.setText("")
        self.export_button.setEnabled(False)
        self._results = {}
        self._details = {}

    def _populate_headers(self) -> None:
        if self.table.columnCount() < 2:
            return
        headers = [tr("Схема"), tr("Таблица")] + [
            self._column_title(key) for key in self._columns
        ]
        self.table.setHorizontalHeaderLabels(headers)

    def _on_check_started(self, title: str) -> None:
        self._host.set_progress_text(tr("Текущая проверка") + ": " + tr(title))

    def _on_check_done(self, key: str, table_name: str, count, error: str) -> None:
        if key not in self._columns:
            return
        column = 2 + self._columns.index(key)
        row = self._row_of.get(table_name)
        if row is None:
            return
        self._results.setdefault(table_name, {})[key] = (count, error)
        if error:
            self._errors += 1
        elif count:
            self._problems += int(count)
        self._render_cell(row, column, count, error)
        self.export_button.setEnabled(True)

    def _on_check_details(self, key: str, table_name: str, details) -> None:
        """Запомнить подробный список дублей для ячейки."""

        self._details[(key, table_name)] = list(details)

    def _on_cell_double_clicked(self, row: int, column: int) -> None:
        """Показать подробный список дублей по двойному щелчку."""

        if column < 2:
            return
        key = self._columns[column - 2]
        table_name = None
        for name, index in self._row_of.items():
            if index == row:
                table_name = name
                break
        if table_name is None:
            return
        details = self._details.get((key, table_name))
        if not details:
            return
        show_duplicate_details(self, table_name, details)

    def _render_cell(self, row: int, column: int, count, error: str) -> None:
        if error:
            item = QTableWidgetItem(tr("Ошибка"))
            item.setToolTip(error)
        elif count is None:
            item = QTableWidgetItem(tr("Не применимо"))
        else:
            item = QTableWidgetItem(str(count))
            item.setData(Qt.ItemDataRole.UserRole, int(count))
            if count:
                item.setBackground(QColor("#ffd9d4"))
        self.table.setItem(row, column, item)

    def _render_cells(self) -> None:
        for table_name, results in self._results.items():
            row = self._row_of.get(table_name)
            if row is None:
                continue
            for key, (count, error) in results.items():
                if key not in self._columns:
                    continue
                self._render_cell(row, 2 + self._columns.index(key), count, error)

    def _render_summary(self) -> None:
        state, error = self._state
        if state == "error":
            text = tr("Ошибка") + ": " + error
        elif state == "cancelled":
            text = tr("Проверка прервана")
        elif state == "done":
            text = tr("Найдено проблем: {}").format(self._problems)
            if self._errors:
                text += " — " + tr("ошибок запросов: {}").format(self._errors)
        else:
            text = ""
        self.summary_label.setText(text)

    def _on_finished(self, cancelled: bool, error: str) -> None:
        self._task = None
        self.run_button.setEnabled(self._host._db is not None)
        self.cancel_button.setEnabled(False)
        self._host.end_progress()
        if error:
            self._state = ("error", error)
            self._host._set_status(tr("Ошибка") + ": " + error)
        elif cancelled:
            self._state = ("cancelled", "")
            self._host._set_status(tr("Отменено"))
        else:
            self._state = ("done", "")
            self._host._set_status(tr("Готово"))
        self._render_summary()

    # ------------------------------------------------------------- export
    def export_rows(self) -> Tuple[List[str], List[List[object]]]:
        """Заголовки и строки таблицы результатов вместе со строкой «Итого»."""

        headers = [
            self.table.horizontalHeaderItem(column).text()
            if self.table.horizontalHeaderItem(column) is not None
            else ""
            for column in range(self.table.columnCount())
        ]
        rows: List[List[object]] = []
        sums = [0] * self.table.columnCount()
        for row in range(self.table.rowCount()):
            values: List[object] = []
            for column in range(self.table.columnCount()):
                item = self.table.item(row, column)
                if item is None:
                    values.append("")
                    continue
                raw = item.data(Qt.ItemDataRole.UserRole)
                if isinstance(raw, int):
                    sums[column] += raw
                    values.append(raw)
                else:
                    values.append(item.text())
            rows.append(values)

        total: List[object] = [tr("Итого"), f"{self.table.rowCount()} " + tr("таблиц")]
        for column in range(2, self.table.columnCount()):
            total.append(sums[column] if sums[column] else "")
        rows.append(total)
        return headers, rows

    def _on_export(self) -> None:
        """Экспорт результатов проверок в Excel или HTML."""

        if self.table.rowCount() == 0 or not self._columns:
            QMessageBox.information(
                self, "ZGeo-PG", tr("Результатов нет — нажмите «Проверить»")
            )
            return
        export_format = ask_export_format(self, self.export_button)
        if export_format is None:
            return
        headers, rows = self.export_rows()
        suffix = "html" if export_format == FORMAT_HTML else "xlsx"
        export_rows_with_dialog(
            self,
            headers,
            rows,
            "{}.{}".format(self._prefix, suffix),
            tr(self.title_source),
            export_format=export_format,
            total_index=len(rows) - 1,
        )


class NsiSide(QWidget):
    """Одна сторона сверки: соединение, таблица, столбец и список значений."""

    def __init__(self, host, side: str) -> None:
        super().__init__()
        self._host = host
        self._side = side
        self._tag = "nsi_" + side
        self._db = None
        self._conn = None
        self._values: List[str] = []
        self._connected = False
        self._conn_tip = ""
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._conn_combo = QComboBox()
        # Выбор в списке сразу подключает к нему; activated ловит повторный
        # выбор того же пункта, когда currentIndexChanged не срабатывает.
        self._conn_combo.currentIndexChanged.connect(self._on_connection_changed)
        self._conn_combo.activated.connect(self._on_connection_changed)
        self._table_combo = QComboBox()
        self._table_combo.currentIndexChanged.connect(self._on_table_changed)
        self._column_combo = QComboBox()
        self._column_combo.currentIndexChanged.connect(self._on_column_changed)

        form = QGridLayout()
        self._conn_label = QLabel()
        self._table_label = QLabel()
        self._column_label = QLabel()
        # Кружок состояния соединения: зелёный — подключено, красный — нет.
        self._conn_dot = QLabel()
        self._conn_dot.setFixedSize(12, 12)
        self._conn_dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Колонка под точку уже, чем остальные, чтобы она стояла вплотную
        # к выпадающему списку.
        form.setColumnMinimumWidth(1, 14)
        form.addWidget(self._conn_label, 0, 0)
        form.addWidget(self._conn_dot, 0, 1)
        form.addWidget(self._conn_combo, 0, 2)
        form.addWidget(self._table_label, 1, 0)
        form.addWidget(self._table_combo, 1, 2)
        form.addWidget(self._column_label, 2, 0)
        form.addWidget(self._column_combo, 2, 2)
        layout.addLayout(form)
        self._set_connected(False, tr("Не подключено"))

        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        layout.addWidget(self._list, 1)

        self._count_label = QLabel()
        layout.addWidget(self._count_label)

        self._export_button = QPushButton()
        self._export_button.clicked.connect(self._on_export)
        self._export_button.setEnabled(False)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(self._export_button)
        layout.addLayout(row)

    # -------------------------------------------------------------- состояние
    def _set_connected(self, connected: bool, tooltip: str = "") -> None:
        """Зелёный кружок при успешном подключении, красный — при ошибке."""

        self._connected = connected
        self._conn_tip = tooltip
        color = "#2e9e4f" if connected else "#c0392b"
        self._conn_dot.setStyleSheet(
            "background-color: {}; border-radius: 5px;".format(color)
        )
        self._conn_dot.setToolTip(tooltip or tr("Не подключено"))

    def is_connected(self) -> bool:
        """Открыто ли соединение этой стороны."""

        return self._db is not None

    # ------------------------------------------------------------- переводы
    def retranslate(self) -> None:
        self._conn_label.setText(tr("Соединение"))
        self._table_label.setText(tr("Таблица"))
        self._column_label.setText(tr("Поле"))
        self._set_connected(self._connected, self._conn_tip)
        self._export_button.setText(tr("Экспорт"))
        self._export_button.setToolTip(tr("Экспорт списка значений"))
        self._update_count()

    # -------------------------------------------------------------- данные
    def reload_connections(self) -> None:
        """Заполнить список соединений и подключиться к рабочему из них."""

        names = list_saved_connections()
        live = self._host.current_connection()
        if live is not None and live.name not in names:
            names.insert(0, live.name)

        current = self._conn_combo.currentText().strip()
        preferred = current if current in names else last_connection_name()
        if preferred not in names:
            preferred = names[0] if names else ""

        self._conn_combo.blockSignals(True)
        self._close_connection()
        self._conn_combo.clear()
        self._conn_combo.addItems(names)
        self._conn_combo.blockSignals(False)

        # Сначала предпочтительное соединение, затем остальные: сторона должна
        # открыться на базе с таблицами, а не на первом пункте списка.
        candidates = ([preferred] if preferred else []) + [
            name for name in names if name != preferred
        ]
        fallback = ""
        for name in candidates:
            self._conn_combo.blockSignals(True)
            self._conn_combo.setCurrentIndex(names.index(name))
            self._conn_combo.blockSignals(False)
            # Автоподключение не показывает модальных окон: ошибка видна по
            # красному кружку и в статусной строке.
            self._on_connection_changed(silent=True)
            if not self.is_connected():
                continue
            if self._table_combo.count():
                return
            # Соединение открылось, но читать нечего: запомним и поищем лучше.
            fallback = fallback or name
        if fallback:
            self._conn_combo.blockSignals(True)
            self._conn_combo.setCurrentIndex(names.index(fallback))
            self._conn_combo.blockSignals(False)
            self._on_connection_changed(silent=True)

    def _on_connection_changed(self, *_args, silent: bool = False) -> None:
        """Открыть выбранное соединение и заполнить список таблиц.

        silent подавляет модальные сообщения: так соединение пробуется
        автоматически при заполнении списка соединений.
        """

        self._close_connection()
        self._table_combo.clear()
        self._column_combo.clear()
        self._set_values([])
        name = self._conn_combo.currentText().strip()
        if not name:
            self._set_connected(False, tr("Соединение не выбрано"))
            return
        live = self._host.current_connection()
        conn = live if live is not None and live.name == name else load_connection(name)
        if conn is None:
            # Соединение могло остаться только в SQLite: подтягиваем оттуда
            # и пробуем ещё раз, прежде чем сообщать об ошибке.
            sync_connections_from_sqlite()
            conn = load_connection(name)
        if conn is None:
            message = tr("Соединение не найдено") + ": " + name
            self._set_connected(False, message)
            self._host.report_error(message)
            if not silent:
                QMessageBox.warning(
                    self, "ZGeo-PG", message + "\n" + tr("Сохраните его")
                )
            return
        try:
            db = open_connection(conn, self._tag)
            tables, total, readable = list_tables(db)
        except Exception as error:  # noqa: BLE001
            self._close_connection()
            message = str(error)
            self._set_connected(False, message)
            self._host.report_error(message)
            if not silent:
                QMessageBox.critical(
                    self, "ZGeo-PG", tr("Ошибка подключения") + ":\n" + message
                )
            return
        self._db = db
        self._conn = conn
        self._set_connected(True, conn.qualified + " / " + name)
        for schema, table in tables:
            self._table_combo.addItem(schema + "." + table, (schema, table))
        self._host.show_connected(name, len(tables), total, readable)

    def _on_table_changed(self, *_args) -> None:
        self._column_combo.clear()
        self._set_values([])
        target = self._table_combo.currentData()
        if self._db is None or not target:
            return
        try:
            columns = list_text_columns(self._db, target[0], target[1])
        except Exception as error:  # noqa: BLE001
            self._host.report_error(str(error))
            return
        self._column_combo.addItems(columns)

    def _on_column_changed(self, *_args) -> None:
        self._load_values()

    def _load_values(self) -> None:
        target = self._table_combo.currentData()
        column = self._column_combo.currentText().strip()
        if self._db is None or not target or not column:
            self._set_values([])
            return
        try:
            values = fetch_unique_values(self._db, target[0], target[1], column)
        except Exception as error:  # noqa: BLE001
            self._host.report_error(str(error))
            self._set_values([])
            return
        self._set_values(values)

    def _set_values(self, values: List[str]) -> None:
        self._values = list(values)
        self._list.clear()
        self._list.addItems(self._values)
        self._export_button.setEnabled(bool(self._values))
        self._update_count()

    def _update_count(self) -> None:
        self._count_label.setText(tr("Уникальных значений: {}").format(len(self._values)))

    def values(self) -> List[str]:
        return list(self._values)

    def source(self) -> str:
        target = self._table_combo.currentData()
        column = self._column_combo.currentText()
        if not target or not column:
            return ""
        return "{}.{}.{}".format(target[0], target[1], column)

    def _close_connection(self) -> None:
        """Закрыть соединение стороны, сначала отпустив ссылку на базу.

        Qt сообщает «connection is still in use» и обрывает запросы, если
        removeDatabase вызвать, пока объект QSqlDatabase ещё жив, поэтому
        ссылка снимается до закрытия.
        """

        conn = self._conn
        self._conn = None
        self._db = None
        if conn is None:
            return
        try:
            close_connection(conn, self._tag)
        except RuntimeError:
            pass

    def shutdown(self) -> None:
        """Закрыть соединение стороны при выгрузке плагина."""

        self._close_connection()

    def _on_export(self) -> None:
        if not self._values:
            return
        parent = self._host
        export_format = ask_export_format(parent, self._export_button)
        if export_format is None:
            return
        suffix = "html" if export_format == FORMAT_HTML else "xlsx"
        export_rows_with_dialog(
            parent,
            [tr("Значение")],
            [[value] for value in self._values],
            "zgeo-pg_nsi_{}.{}".format(self._side, suffix),
            tr("Качество по НСИ"),
            export_format=export_format,
        )


class NsiTabPage(QWidget):
    """Сверка НСИ: два набора значений, статистика и списки расхождений."""

    def __init__(self, host) -> None:
        super().__init__()
        self._host = host
        self._comparison = NsiComparison()
        self._status_kind: Tuple[str, ...] = ()
        self._status_error = ""
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        self._sides = QSplitter(Qt.Orientation.Horizontal)
        self._left = NsiSide(self, "left")
        self._right = NsiSide(self, "right")
        self._sides.addWidget(self._left)

        middle = QWidget()
        middle_layout = QVBoxLayout(middle)
        middle_layout.setContentsMargins(4, 4, 4, 4)
        middle_layout.addStretch(1)
        self._compare_button = QPushButton()
        self._compare_button.clicked.connect(self._compare)
        middle_layout.addWidget(self._compare_button)
        middle_layout.addStretch(1)
        self._sides.addWidget(middle)
        self._sides.addWidget(self._right)
        self._sides.setStretchFactor(0, 1)
        self._sides.setStretchFactor(1, 0)
        self._sides.setStretchFactor(2, 1)
        layout.addWidget(self._sides, 2)

        self._stats_table = QTableWidget(0, 2)
        self._stats_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._stats_table.verticalHeader().setVisible(False)
        self._stats_table.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self._stats_table.customContextMenuRequested.connect(self._on_menu)
        self._stats_table.cellDoubleClicked.connect(self._on_double_click)

        results = QSplitter(Qt.Orientation.Horizontal)
        results.addWidget(self._stats_table)
        self._viewer = QListWidget()
        self._viewer.setVisible(False)
        results.addWidget(self._viewer)
        results.setStretchFactor(0, 1)
        results.setStretchFactor(1, 1)
        layout.addWidget(results, 1)

        self._status_label = QLabel()
        layout.addWidget(self._status_label)

        buttons = QHBoxLayout()
        self._export_button = QPushButton()
        self._export_button.clicked.connect(self._on_export)
        self._export_button.setEnabled(False)
        buttons.addStretch(1)
        buttons.addWidget(self._export_button)
        layout.addLayout(buttons)

        self._populate_stats()

    def retranslate(self) -> None:
        self._left.retranslate()
        self._right.retranslate()
        self._compare_button.setText(tr("Сравнить"))
        self._export_button.setText(tr("Экспорт"))
        self._export_button.setToolTip(tr("Экспорт результатов сверки"))
        self._stats_table.setHorizontalHeaderLabels([tr("Категория"), tr("Количество")])
        self._populate_stats()
        self._render_status()

    # ------------------------------------------------------------ сравнение
    def _compare(self) -> None:
        left = self._left.values()
        right = self._right.values()
        if not left or not right:
            QMessageBox.information(
                self, "ZGeo-PG", tr("Загрузите значения с обеих сторон")
            )
            return
        self._status_kind = ()
        self._status_error = ""
        self._comparison = compare_values(left, right)
        self._populate_stats()
        self._export_button.setEnabled(True)
        self._render_status()
        self._viewer.setVisible(False)

    def _categories(self) -> List[Tuple[str, List[str]]]:
        """Списки значений по категориям сверки."""

        return [
            (tr("Совпало"), self._comparison.matched),
            (
                tr("Есть в левой панели, но нет в правой"),
                self._comparison.left_only,
            ),
            (
                tr("Есть в правой, но нет в левой"),
                self._comparison.right_only,
            ),
        ]

    def _verdict_label(self) -> str:
        """Название итоговой проверки: все левые значения есть справа."""

        return tr("Все из левой панели есть в правой")

    def _verdict(self) -> str:
        """Да или Нет: все значения левой панели нашлись в правой."""

        if not self._comparison.total:
            return ""
        return tr("Да") if not self._comparison.left_only else tr("Нет")

    def _verdict_values(self) -> List[str]:
        """Значения, которых не хватает в правой панели (для списка справа)."""

        return list(self._comparison.left_only)

    def _populate_stats(self) -> None:
        categories = self._categories()
        verdict = self._verdict()
        rows = len(categories) + (1 if verdict else 0)
        self._stats_table.setRowCount(rows)
        self._stats_table.setColumnCount(2)
        for row, (name, values) in enumerate(categories):
            self._stats_table.setItem(row, 0, QTableWidgetItem(name))
            count_item = QTableWidgetItem(str(len(values)))
            count_item.setData(Qt.ItemDataRole.UserRole, len(values))
            self._stats_table.setItem(row, 1, count_item)
        if verdict:
            # Итоговая строка отвечает только «Да» или «Нет».
            row = len(categories)
            self._stats_table.setItem(row, 0, QTableWidgetItem(self._verdict_label()))
            self._stats_table.setItem(row, 1, QTableWidgetItem(verdict))
        self._stats_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._stats_table.horizontalHeader().setStretchLastSection(True)

    def _render_status(self) -> None:
        """Показать состояние вкладки на текущем языке."""

        if self._status_error:
            self._status_label.setText(
                tr("Ошибка") + ": " + readable_error(self._status_error)
            )
            return
        kind = self._status_kind
        if kind:
            label = kind[0]
            if label == "connected":
                text = tr("Подключено") + ": {} ({})".format(kind[1], kind[2])
            elif label == "empty":
                text = self._empty_text(kind[1], kind[2] if len(kind) > 2 else 0)
            elif label == "none":
                text = tr("Соединение не выбрано")
            else:
                text = kind[1]
            self._status_label.setText(text)
            return
        total = self._comparison.total
        if not total:
            self._status_label.setText(tr("Сравнение не выполнялось"))
            return
        self._status_label.setText(
            tr("Всего уникальных значений в сравнении: {}").format(total)
            + " — "
            + self._verdict_label()
            + ": "
            + self._verdict()
        )

    def _empty_text(self, name: str, total: int) -> str:
        """Объяснить пустой список таблиц: нет прав или нет таблиц."""

        if total:
            return tr(
                "Подключено, но нет прав на чтение таблиц: {} (таблиц в базе: {})"
            ).format(name, total)
        return tr("Подключено, но в базе нет таблиц") + ": " + name

    # --------------------------------------------------------------- списки
    def _menu_targets(self) -> List[Tuple[str, List[str]]]:
        """Пункты меню статистики: категории и итоговая проверка."""

        targets = list(self._categories())
        if self._verdict():
            # В итоговой строке справа показываем значения, из-за которых «Нет».
            targets.append((self._verdict_label(), self._verdict_values()))
        return targets

    def _on_menu(self, position) -> None:
        row = self._stats_table.rowAt(position.y())
        targets = self._menu_targets()
        if row < 0 or row >= len(targets):
            return
        menu = QMenu(self)
        actions = {}
        for index, (name, values) in enumerate(targets):
            action = menu.addAction(name)
            action.setCheckable(True)
            action.setChecked(index == row)
            actions[action] = (name, values)
        chosen = menu.exec(self._stats_table.viewport().mapToGlobal(position))
        if chosen in actions:
            self._show_list(*actions[chosen])

    def _on_double_click(self, row: int, _column: int) -> None:
        targets = self._menu_targets()
        if 0 <= row < len(targets):
            name, values = targets[row]
            self._show_list(name, values)

    def _show_list(self, name: str, values: List[str]) -> None:
        """Открыть справа список значений выбранной категории."""

        self._viewer.clear()
        self._viewer.addItems(values)
        self._viewer.setVisible(True)
        self._host._set_status(tr(name) + ": " + str(len(values)))

    # --------------------------------------------------------------- экспорт
    def _sources_info(self) -> List[List[object]]:
        """Что выбрано в списках: соединение, таблица и поле каждой стороны."""

        return [
            [
                tr("Соединение"),
                self._left._conn_combo.currentText(),
                self._right._conn_combo.currentText(),
            ],
            [
                tr("Таблица"),
                self._left._table_combo.currentText(),
                self._right._table_combo.currentText(),
            ],
            [
                tr("Поле"),
                self._left._column_combo.currentText(),
                self._right._column_combo.currentText(),
            ],
        ]

    def _stats_rows(self) -> List[List[object]]:
        """Статистика сверки: категория и количество или «Да»/«Нет»."""

        rows: List[List[object]] = [
            [name, len(values)] for name, values in self._categories()
        ]
        verdict = self._verdict()
        if verdict:
            rows.append([self._verdict_label(), verdict])
        return rows

    def _on_export(self) -> None:
        """Экспорт сверки: листы Excel по категориям или HTML-отчёт."""

        if not self._comparison.total:
            QMessageBox.information(
                self, "ZGeo-PG", tr("Сначала выполните сравнение")
            )
            return
        export_format = ask_export_format(self, self._export_button)
        if export_format is None:
            return
        sections = [
            (name, [tr("Значение")], [[value] for value in values])
            for name, values in self._categories()
        ]
        suffix = "html" if export_format == FORMAT_HTML else "xlsx"
        export_report_with_dialog(
            self,
            self._sources_info(),
            self._stats_rows(),
            sections,
            "zgeo-pg_nsi_compare." + suffix,
            tr("Качество по НСИ"),
            export_format=export_format,
        )

    def report_error(self, message: str) -> None:
        """Показать ошибку и в строке вкладки, и в статусной строке панели."""

        self._status_error = message
        self._status_kind = ()
        text = tr("Ошибка") + ": " + readable_error(message)
        self._status_label.setText(text)
        self._host.show_status(text)

    def current_connection(self) -> Optional[PGConnection]:
        """Текущее подключение панели для выбора на стороне сверки."""

        return self._host.current_connection()

    def show_status(self, text: str) -> None:
        """Показать произвольное сообщение в статусной строке панели."""

        self._status_error = ""
        self._status_kind = ("text", text)
        self._status_label.setText(text)
        self._host.show_status(text)

    def show_connected(
        self, name: str, count: int, total: int = 0, readable: int = 0
    ) -> None:
        """Отметить успешное подключение стороны с числом таблиц."""

        if readable:
            kind = ("connected", name, count)
        else:
            kind = ("empty", name, total)
        self._status_error = ""
        self._status_kind = kind
        self._render_status()
        if count:
            self._host.show_status(
                tr("Подключено") + ": {} ({})".format(name, count)
            )
        else:
            self._host.show_status(self._status_label.text())

    def reload_connections(self) -> None:
        self._left.reload_connections()
        self._right.reload_connections()

    def shutdown(self) -> None:
        self._left.shutdown()
        self._right.shutdown()


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
        self._quality_pages: List["QualityTabPage"] = []
        self._active_page = None

        self._schema_filter: Optional[str] = None
        self._only_geometry = True
        self._build_ui()
        self._build_connection_tab()
        self._build_tables_tab()
        self._build_stats_tab()
        self._nsi_page = NsiTabPage(self)
        self._tabs.addTab(self._nsi_page, tr("Качество по НСИ"))
        self._add_quality_page(
            QUALITY_CHECKS,
            QualityTask,
            "Качество пространственных данных",
            "zgeo-pg_quality",
        )
        self._add_quality_page(
            ATTRIBUTE_CHECKS,
            AttributeTask,
            "Качество атрибутивных данных",
            "zgeo-pg_attributes",
        )
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

    def current_connection(self) -> Optional[PGConnection]:
        """Текущее подключение панели: его же можно выбрать на вкладке НСИ."""

        return self._conn

    def _add_quality_page(self, checks, task_class, title_source: str, prefix: str) -> None:
        """Добавить вкладку проверок качества с полным набором средств."""

        page = QualityTabPage(self, checks, task_class, title_source, prefix)
        self._quality_pages.append(page)
        self._tabs.addTab(page, tr(title_source))
        page.retranslate()

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

    def begin_progress(self, total: int, page) -> bool:
        """Начать показ прогресса; False — уже идут другие проверки."""

        if self._active_page is not None and self._active_page is not page:
            QMessageBox.information(
                self, "ZGeo-PG", tr("Дождитесь окончания текущих проверок")
            )
            return False
        self._active_page = page
        self._progress_bar.setRange(0, max(1, total))
        self._progress_bar.setValue(0)
        self.set_progress_visible(True)
        return True

    def progress_update(self, done: int, total: int) -> None:
        """Обновить прогресс в статусной строке."""

        self._progress_bar.setRange(0, max(1, total))
        self._progress_bar.setValue(done)

    def set_progress_text(self, text: str) -> None:
        """Показать название текущей проверки над статусной строкой."""

        self._progress_label.setText(text)

    def set_progress_visible(self, visible: bool) -> None:
        """Показать или скрыть прогресс и его подпись."""

        self._progress_bar.setVisible(visible)
        self._progress_label.setVisible(visible)

    def end_progress(self) -> None:
        """Завершить показ прогресса."""

        self._active_page = None
        self.set_progress_visible(False)

    def _set_status(self, text: str) -> None:
        self._status_label.setText(text)

    def show_status(self, text: str) -> None:
        """Открытый метод статусной строки для вложенных вкладок."""

        self._set_status(text)

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
        self._tabs.setTabText(self._tabs.indexOf(self._nsi_page), tr("Качество по НСИ"))
        self._nsi_page.retranslate()
        for page in self._quality_pages:
            self._tabs.setTabText(self._tabs.indexOf(page), tr(page.title_source))
            page.retranslate()
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
        self._nsi_page.reload_connections()
        self._retranslate()
        self._update_connection_state()
        self._reload_tables()

    def _disconnect(self) -> None:
        self._stop_task()
        for page in self._quality_pages:
            page.stop()
            page.set_available(False)
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
        self._nsi_page.reload_connections()
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
        for page in self._quality_pages:
            page.set_available(True)
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
        self._nsi_page.reload_connections()
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
        self._nsi_page.reload_connections()

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
        self._nsi_page.reload_connections()

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
        self._nsi_page.shutdown()
        self._stop_task()
        self._stop_index_task()
        for page in self._quality_pages:
            page.stop()
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