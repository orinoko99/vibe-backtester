"""
Главное окно приложения бэктестера.

Построено на QMainWindow с пустым контейнером для будущего графика,
строкой меню, статус-баром и областями для док-панелей.
"""

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QComboBox,
    QDockWidget,
    QLabel,
    QMainWindow,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

import logging
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import polars as pl

logger = logging.getLogger(__name__)

from src.data.loader import load_candles, load_candles_tail
from src.data.resample import TIMEFRAME_MINUTES, resample_candles
from src.gui.chart_drawing_toolbar import ChartDrawingToolbar
from src.gui.chart_widget import ChartWidget
from src.gui.drawing_toolbar import DrawingToolbar
from src.gui.instrument_panel import InstrumentPanel


# Поддерживаемые таймфреймы
TIMEFRAMES: list[str] = ["M1", "M5", "M10", "M15", "M30", "H1", "H4", "D1"]

# Количество свечей целевого ТФ для подгрузки за раз
LOAD_CHUNK_BARS: int = 300

# Если до края данных осталось меньше этого — подгружаем
LOAD_THRESHOLD_BARS: int = 100

# Стартовая загрузка M1 при открытии инструмента (последние N минутных свечей)
INITIAL_M1_BARS: int = 25_000

# Свечей старшего ТФ вокруг видимой области на графике (скользящее окно отображения)
DISPLAY_PADDING_BARS: int = 200

# Лимит минутных свечей в RAM; при превышении — обрезка дальних от видимой зоны
MAX_M1_ROWS_IN_MEMORY: int = 60_000
M1_TRIM_TARGET_ROWS: int = 40_000


class MainWindow(QMainWindow):
    """
    Главное окно приложения.

    Содержит:
    - Центральный виджет-контейнер для графика (chart_container).
    - ChartWidget с интерактивным графиком.
    - InstrumentPanel в док-виджете слева (выбор инструмента).
    - Панель инструментов с выбором таймфрейма.
    - Строку меню (File, View, Help).
    - Строку статуса.
    """

    def __init__(self) -> None:
        """Инициализирует главное окно: настройка заголовка, размеров, меню и статуса."""
        super().__init__()

        # Настройка окна
        self.setWindowTitle("Бэктестер стратегий")
        self.setMinimumSize(1280, 720)
        self.resize(1600, 900)

        # Текущие параметры
        self._current_db_path: str | None = None
        self._current_sec_code: str | None = None
        self._current_timeframe: str = "M1"

        # Параметры динамической подгрузки данных
        self._loaded_start: str | None = None  # минимальная загруженная дата
        self._loaded_end: str | None = None    # максимальная загруженная дата
        self._last_visible_range: tuple[int, int] | None = None  # bars_before, bars_after

        # Сохранённые позиции камеры по инструментам: ключ (db_path, sec_code) -> tuple[timeframe, start_date, end_date]
        self._camera_positions: dict[tuple[str, str], tuple[str, str, str]] = {}

        # Сохранённые рисунки по инструментам: ключ (db_path, sec_code) -> dict[timeframe, list[dict]]
        self._saved_drawings: dict[tuple[str, str], dict[str, list[dict[str, Any]]]] = {}

        # Последний выбранный таймфрейм для каждого инструмента
        self._instrument_timeframes: dict[tuple[str, str], str] = {}

        # Минутные свечи в RAM (скользящее окно вокруг просмотра)
        self._m1_candles: pl.DataFrame | None = None
        # Границы уже загруженного из БД диапазона M1 (не даты с графика!)
        self._m1_loaded_start: str | None = None
        self._m1_loaded_end: str | None = None
        # Защита от частых подгрузок при прокрутке
        self._range_load_busy: bool = False
        # Кэш ресемплированных данных (чтобы не ресемплировать на каждый range_change)
        self._resampled_cache: pl.DataFrame | None = None

        # Сохранённые временные границы видимой области (для восстановления zoom после chart.set())
        self._saved_visible_start: float | None = None
        self._saved_visible_end: float | None = None
        # Флаг: идёт восстановление диапазона — временно не обрабатываем range_change
        self._restoring_range: bool = False

        # Создаём центральный виджет-контейнер для графика
        self._create_central_widget()

        # Создаём строку меню
        self._create_menu_bar()

        # Создаём панель инструментов
        self._create_toolbar()

        # Создаём док-панель выбора инструмента
        self._create_instrument_dock()

        # Создаём док-панель инструментов рисования
        self._create_drawing_dock()

        # Создаём строку статуса
        self._create_status_bar()

        # Инициализируем график
        self._init_chart()

    def _create_central_widget(self) -> None:
        """
        Создаёт центральный виджет с пустым контейнером.

        chart_container — QWidget, в который в будущем будет встроен
        график lightweight-charts (через QWebEngineView).
        """
        # Главный центральный виджет
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        # Макет для размещения контейнера графика
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        central_widget.setLayout(layout)

        # Пустой контейнер под будущий график
        self.chart_container = QWidget()
        self.chart_container.setObjectName("chartContainer")
        self.chart_container.setStyleSheet(
            "background-color: #1a1a2e; border: 1px solid #333;"
        )
        layout.addWidget(self.chart_container)

    def _create_menu_bar(self) -> None:
        """Создаёт строку меню с разделами File, View и Help."""
        menu_bar = self.menuBar()

        # Меню File
        file_menu = menu_bar.addMenu("Файл")

        self.action_exit = QAction("Выход", self)
        self.action_exit.setShortcut("Ctrl+Q")
        self.action_exit.setStatusTip("Закрыть приложение")
        self.action_exit.triggered.connect(self.close)
        file_menu.addAction(self.action_exit)

        # Меню View
        view_menu = menu_bar.addMenu("Вид")
        self.action_toggle_status_bar = QAction("Строка статуса", self)
        self.action_toggle_status_bar.setCheckable(True)
        self.action_toggle_status_bar.setChecked(True)
        self.action_toggle_status_bar.setStatusTip("Показать/скрыть строку статуса")
        self.action_toggle_status_bar.triggered.connect(self._toggle_status_bar)
        view_menu.addAction(self.action_toggle_status_bar)

        # Меню Help
        help_menu = menu_bar.addMenu("Помощь")
        self.action_about = QAction("О программе", self)
        self.action_about.setStatusTip("Информация о приложении")
        self.action_about.triggered.connect(self._show_about)
        help_menu.addAction(self.action_about)

    def _create_toolbar(self) -> None:
        """Создаёт панель: рисование на графике + выбор таймфрейма."""
        toolbar = QToolBar("Панель инструментов")
        toolbar.setObjectName("mainToolBar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.chart_drawing_toolbar = ChartDrawingToolbar()
        self.chart_drawing_toolbar.tool_selected.connect(self._on_drawing_tool_selected)
        self.chart_drawing_toolbar.color_selected.connect(self._on_drawing_color_selected)
        self.chart_drawing_toolbar.label_text_changed.connect(self._on_drawing_label_text)
        toolbar.addWidget(self.chart_drawing_toolbar)

        toolbar.addSeparator()

        tf_label = QLabel("Таймфрейм:")
        toolbar.addWidget(tf_label)

        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(TIMEFRAMES)
        self.timeframe_combo.setCurrentText(self._current_timeframe)
        self.timeframe_combo.currentTextChanged.connect(self._on_timeframe_changed)
        toolbar.addWidget(self.timeframe_combo)

    def _create_instrument_dock(self) -> None:
        """Создаёт док-панель со списком инструментов."""
        self.instrument_dock = QDockWidget("Инструменты", self)
        self.instrument_dock.setObjectName("instrumentDock")
        self.instrument_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)

        # Панель выбора инструментов
        self.instrument_panel = InstrumentPanel()
        self.instrument_panel.instrument_selected.connect(self._on_instrument_selected)
        self.instrument_dock.setWidget(self.instrument_panel)

        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.instrument_dock)

    def _create_drawing_dock(self) -> None:
        """Док-панель: список рисунков и действия (без кнопок инструментов)."""
        self.drawing_dock = QDockWidget("Рисунки", self)
        self.drawing_dock.setObjectName("drawingDock")
        self.drawing_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )

        self.drawing_toolbar = DrawingToolbar()
        self.drawing_toolbar.clear_requested.connect(self._on_drawing_clear)
        self.drawing_toolbar.delete_last_requested.connect(self._on_drawing_delete_last)
        self.drawing_toolbar.delete_drawing_requested.connect(self._on_drawing_delete_by_index)
        self.drawing_toolbar.edit_drawing_requested.connect(self._on_drawing_edit_color)
        self.drawing_toolbar.edit_drawing_text_requested.connect(self._on_drawing_edit_text)
        self.drawing_dock.setWidget(self.drawing_toolbar)

        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.drawing_dock)

    def _on_drawing_tool_selected(self, tool_name: str) -> None:
        """
        Обрабатывает выбор инструмента рисования.

        Параметры:
            tool_name: Имя инструмента ('horizontal_line', 'vertical_line' и т.д.).
        """
        self.chart_widget.set_drawing_tool(tool_name)
        status_text = {
            "none": "Курсор — выберите или перетащите объект на графике",
            "horizontal_line": "Горизонтальная линия — кликните на график",
            "vertical_line": "Вертикальная линия — кликните на график",
            "trend_line": "Трендовая линия — кликните первую точку, затем вторую",
            "ray_line": "Луч — кликните начальную точку",
            "vertical_span": "Вертикальная заливка — кликните начало, затем конец",
            "marker": "Маркер — кликните на свечу",
        }
        self.set_status_message(status_text.get(tool_name, f"Инструмент: {tool_name}"))

    def _on_drawing_color_selected(self, color: str) -> None:
        """Применяет цвет к новым рисункам."""
        self.chart_widget.set_drawing_color(color)

    def _on_drawing_label_text(self, text: str) -> None:
        """Применяет подпись к новым рисункам."""
        self.chart_widget.set_drawing_text(text)

    def _on_drawing_edit_text(self, index: int, text: str) -> None:
        """Изменяет текст выбранного рисунка."""
        if self.chart_widget.update_drawing(index, text=text):
            self.set_status_message("Подпись обновлена")
            self._refresh_drawing_list()

    def _on_drawing_clear(self) -> None:
        """Очищает все рисунки и маркеры с графика."""
        self.chart_widget.clear_drawings()
        self._save_drawings()
        self._refresh_drawing_list()
        self.set_status_message("Все рисунки очищены")

    def _on_drawing_delete_last(self) -> None:
        """Удаляет последний добавленный рисунок."""
        drawings = self.chart_widget.get_drawings()
        if not drawings:
            self.set_status_message("Нет рисунков для удаления")
            return
        if self.chart_widget.delete_drawing(len(drawings) - 1):
            self.set_status_message("Последний рисунок удалён")
            self._refresh_drawing_list()

    def _on_drawing_delete_by_index(self, index: int) -> None:
        """Удаляет рисунок по индексу."""
        if self.chart_widget.delete_drawing(index):
            self.set_status_message("Рисунок удалён")
            self._refresh_drawing_list()

    def _on_drawing_edit_color(self, index: int, color: str) -> None:
        """Изменяет цвет рисунка по индексу."""
        if self.chart_widget.update_drawing(index, color=color):
            self.set_status_message("Цвет рисунка изменён")
            self._refresh_drawing_list()

    def _refresh_drawing_list(self) -> None:
        """Обновляет список рисунков в панели рисования."""
        drawings = self.chart_widget.get_drawings()
        self.drawing_toolbar.update_drawing_list(drawings)

    def _on_instrument_selected(self, db_path: str, sec_code: str) -> None:
        """
        Обрабатывает выбор инструмента в панели.

        Сохраняет позицию камеры текущего инструмента, загружает данные
        нового инструмента и восстанавливает его позицию камеры.

        Параметры:
            db_path: Путь к БД инструмента.
            sec_code: Код инструмента.
        """
        # Сохраняем позицию камеры, рисунки и таймфрейм для текущего инструмента
        self._save_camera_position()
        self._save_drawings()
        self._save_instrument_timeframe()

        self._current_db_path = db_path
        self._current_sec_code = sec_code

        # Восстанавливаем таймфрейм, который был у этого инструмента
        self._restore_instrument_timeframe(db_path, sec_code)

        self.set_status_message(f"Выбран инструмент: {sec_code}")
        self.load_and_display(db_path, sec_code)

    def _save_camera_position(self) -> None:
        """Сохраняет диапазон M1 в памяти для инструмента (для последующей подгрузки)."""
        if (
            self._current_db_path
            and self._current_sec_code
            and self._m1_loaded_start
            and self._m1_loaded_end
        ):
            key = (self._current_db_path, self._current_sec_code)
            self._camera_positions[key] = (
                self._current_timeframe,
                self._m1_loaded_start,
                self._m1_loaded_end,
            )

    def _save_drawings(self) -> None:
        """Сохраняет рисунки текущего инструмента и таймфрейма."""
        if self._current_db_path and self._current_sec_code and hasattr(self, 'chart_widget'):
            key = (self._current_db_path, self._current_sec_code)
            tf = self._current_timeframe
            if key not in self._saved_drawings:
                self._saved_drawings[key] = {}
            self._saved_drawings[key][tf] = self.chart_widget.serialize_drawings()

    def _restore_drawings(self, db_path: str, sec_code: str) -> None:
        """Восстанавливает рисунки для инструмента и текущего таймфрейма."""
        key = (db_path, sec_code)
        tf = self._current_timeframe
        by_tf = self._saved_drawings.get(key, {})
        drawings = by_tf.get(tf, [])
        self.chart_widget.restore_drawings(drawings)

    def _save_instrument_timeframe(self) -> None:
        """Запоминает текущий таймфрейм для выбранного инструмента."""
        if self._current_db_path and self._current_sec_code:
            key = (self._current_db_path, self._current_sec_code)
            self._instrument_timeframes[key] = self._current_timeframe

    def _restore_instrument_timeframe(self, db_path: str, sec_code: str) -> None:
        """
        Восстанавливает сохранённый таймфрейм при переключении на инструмент.

        Если для инструмента таймфрейм ещё не задавали — остаётся M1.
        """
        key = (db_path, sec_code)
        tf = self._instrument_timeframes.get(key, "M1")
        if tf == self._current_timeframe:
            return
        self.timeframe_combo.blockSignals(True)
        self.timeframe_combo.setCurrentText(tf)
        self.timeframe_combo.blockSignals(False)
        self._current_timeframe = tf

    def _restore_m1_bounds(self, db_path: str, sec_code: str) -> bool:
        """
        Восстанавливает границы загруженного M1 для инструмента (тот же таймфрейм UI).
        """
        key = (db_path, sec_code)
        if key in self._camera_positions:
            tf, start, end = self._camera_positions[key]
            if tf == self._current_timeframe:
                self._m1_loaded_start = start
                self._m1_loaded_end = end
                return True
        return False

    def _on_timeframe_changed(self, timeframe: str) -> None:
        """
        Обрабатывает изменение таймфрейма.

        Если инструмент уже выбран — перезагружает данные с новым таймфреймом.

        Параметры:
            timeframe: Новый таймфрейм (например 'M5', 'H1').
        """
        if not timeframe or timeframe == self._current_timeframe:
            return

        # Сохраняем рисунки для старого таймфрейма (пока _current_timeframe ещё старый)
        self._save_drawings()

        self._current_timeframe = timeframe
        self._save_instrument_timeframe()

        self.set_status_message(f"Таймфрейм: {timeframe} (из M1)")

        if self._m1_candles is not None and not self._m1_candles.is_empty():
            # При смене ТФ перегружаем все данные — лайтвес сам восстановит видимую зону
            self._refresh_chart_display(
                refresh_drawings=True,
                fit=False,
                scroll_to_end=True,
            )
        elif self._current_db_path and self._current_sec_code:
            self.load_and_display(self._current_db_path, self._current_sec_code)

    def _create_status_bar(self) -> None:
        """Создаёт строку статуса с приветственным сообщением."""
        status_bar = QStatusBar()
        status_bar.setObjectName("statusBar")
        status_bar.showMessage("Готов к работе")
        self.setStatusBar(status_bar)

    def _toggle_status_bar(self, checked: bool) -> None:
        """
        Показывает или скрывает строку статуса.

        Параметры:
            checked: True — показать, False — скрыть.
        """
        self.statusBar().setVisible(checked)
        # Синхронизируем состояние флажка действия с видимостью
        self.action_toggle_status_bar.setChecked(checked)

    def _show_about(self) -> None:
        """Показывает диалоговое окно с информацией о приложении."""
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.about(
            self,
            "О программе",
            "Бэктестер стратегий\n\n"
            "Версия: 0.1.0\n\n"
            "Приложение для тестирования торговых стратегий "
            "на исторических данных с интерактивными графиками.",
        )

    def _init_chart(self) -> None:
        """
        Создаёт ChartWidget и встраивает его в chart_container.

        ChartWidget использует lightweight-charts (через QtChart и QWebEngineView)
        для отображения интерактивного свечного графика.
        """
        # Создаём виджет графика с родительским контейнером
        self.chart_widget = ChartWidget(parent=self.chart_container)

        # Заменяем содержимое chart_container на ChartWidget
        # (удаляем старый layout контейнера и создаём новый)
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Если у контейнера уже есть layout, удаляем его
        old_layout = self.chart_container.layout()
        if old_layout is not None:
            # Очищаем старый layout
            while old_layout.count():
                item = old_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)

        self.chart_container.setLayout(container_layout)
        container_layout.addWidget(self.chart_widget)

        # Подписываемся на событие изменения видимого диапазона
        self.chart_widget.on_range_change(self._on_chart_range_change)

        # Подписываемся на изменения списка рисунков для обновления UI
        self.chart_widget.on_drawings_changed = self._refresh_drawing_list

    def _save_visible_range_from_cache(self, bars_before: int, bars_after: int) -> None:
        """
        Вычисляет и сохраняет временные границы видимой области из _resampled_cache.

        Эти границы используются для восстановления zoom после chart.set().
        """
        rc = self._resampled_cache
        if rc is None or rc.is_empty():
            self._saved_visible_start = None
            self._saved_visible_end = None
            return

        n = len(rc)
        visible_start_idx = max(0, bars_before)
        visible_end_idx = max(visible_start_idx + 1, n - bars_after)
        if visible_start_idx >= n:
            visible_start_idx = 0
        if visible_end_idx > n:
            visible_end_idx = n

        if visible_start_idx < n and visible_end_idx > visible_start_idx:
            # Сохраняем unix-timestamp для совместимости с set_visible_range
            self._saved_visible_start = rc["date"][visible_start_idx].timestamp()
            self._saved_visible_end = rc["date"][visible_end_idx - 1].timestamp()
        else:
            self._saved_visible_start = None
            self._saved_visible_end = None

    def _on_chart_range_change(self, bars_before: float, bars_after: float) -> None:
        """
        Скользящее окно: подгрузка M1 при прокрутке.
        НЕ вызывает chart.set() — это делает только _refresh_chart_display.
        """
        bb = int(bars_before)
        ba = int(bars_after)
        self._last_visible_range = (bb, ba)
        self._save_camera_position()

        # Сохраняем временные границы видимой области для восстановления zoom
        self._save_visible_range_from_cache(bb, ba)

        # Если идёт восстановление диапазона после chart.set() — пропускаем
        if self._restoring_range:
            return

        if not self._current_db_path or not self._current_sec_code:
            return
        if self._m1_candles is None or self._m1_candles.is_empty():
            return
        if self._range_load_busy:
            return

        need_load = False
        if bb < LOAD_THRESHOLD_BARS and bars_before >= 0:
            self._load_data_before()
            need_load = True
        if ba < LOAD_THRESHOLD_BARS and bars_after >= 0:
            self._load_data_after()
            need_load = True

        if need_load:
            # Обновляем график только когда реально подгрузили данные
            self._refresh_chart_display(scroll_to_end=(bars_after < 5))
            self._trim_m1_cache(bb, ba)

    def _get_load_minutes(self) -> int:
        """Сколько минут M1 запросить из БД за раз (с запасом на таймфрейм)."""
        tf_min = self._get_minutes_per_bar()
        return LOAD_CHUNK_BARS * tf_min

    def _load_data_before(self) -> None:
        """Подгружает более ранние минутные свечи из БД."""
        if not self._current_db_path or not self._current_sec_code or not self._m1_loaded_start:
            return

        try:
            self._range_load_busy = True
            load_minutes = self._get_load_minutes()
            fmt = "%Y-%m-%d %H:%M:%S"

            start_dt = datetime.strptime(self._m1_loaded_start, fmt)
            new_start = start_dt - timedelta(minutes=load_minutes)
            new_start_str = new_start.strftime(fmt)

            # Защита от повторной загрузки того же диапазона
            if new_start_str >= self._m1_loaded_start:
                return

            df = load_candles(
                db_path=self._current_db_path,
                sec_code=self._current_sec_code,
                start_date=new_start_str,
                end_date=self._m1_loaded_start,
                timeframe="M1",
            )

            if not df.is_empty():
                self._merge_m1_candles(df)
                self._m1_loaded_start = new_start_str
                self.set_status_message(
                    f"+{len(df)} M1 слева (в памяти {len(self._m1_candles)})"
                )
        except Exception as exc:
            logger.warning("Не удалось подгрузить данные слева: %s", exc)
        finally:
            self._range_load_busy = False

    def _load_data_after(self) -> None:
        """Подгружает более поздние минутные свечи из БД."""
        if not self._current_db_path or not self._current_sec_code or not self._m1_loaded_end:
            return

        try:
            self._range_load_busy = True
            load_minutes = self._get_load_minutes()
            fmt = "%Y-%m-%d %H:%M:%S"

            end_dt = datetime.strptime(self._m1_loaded_end, fmt)
            new_end = end_dt + timedelta(minutes=load_minutes)
            new_end_str = new_end.strftime(fmt)

            # Защита от повторной загрузки того же диапазона
            if new_end_str <= self._m1_loaded_end:
                return

            df = load_candles(
                db_path=self._current_db_path,
                sec_code=self._current_sec_code,
                start_date=self._m1_loaded_end,
                end_date=new_end_str,
                timeframe="M1",
            )

            if not df.is_empty():
                self._merge_m1_candles(df)
                self._m1_loaded_end = new_end_str
                self.set_status_message(
                    f"+{len(df)} M1 справа (в памяти {len(self._m1_candles)})"
                )
        except Exception as exc:
            logger.warning("Не удалось подгрузить данные справа: %s", exc)
        finally:
            self._range_load_busy = False

    def _get_minutes_per_bar(self) -> int:
        """Минут в одной свече текущего таймфрейма."""
        return TIMEFRAME_MINUTES.get(self._current_timeframe, 1)

    def _trim_m1_cache(self, bars_before: int, bars_after: int) -> None:
        """
        Удаляет из RAM минутные свечи, далёкие от видимой зоны.
        Использует _resampled_cache для определения центральной области.
        """
        if self._m1_candles is None or len(self._m1_candles) <= MAX_M1_ROWS_IN_MEMORY:
            return

        rc = self._resampled_cache
        if rc is None or rc.is_empty():
            return

        n = len(rc)
        # Определяем временной диапазон видимой области через индексы в ресемпле
        visible_start_idx = max(0, bars_before)
        visible_end_idx = max(visible_start_idx + 1, n - bars_after)

        # Валидация индексов
        if visible_start_idx >= n:
            visible_start_idx = 0
        if visible_end_idx > n:
            visible_end_idx = n

        center_start = rc["date"][visible_start_idx]
        center_end = rc["date"][min(visible_end_idx, n - 1)]

        tf_min = self._get_minutes_per_bar()
        # Запас: 500 свечей текущего ТФ в каждую сторону
        margin_minutes = tf_min * 500
        margin = timedelta(minutes=margin_minutes)

        keep_from = center_start - margin
        keep_to = center_end + margin

        trimmed = self._m1_candles.filter(
            (pl.col("date") >= keep_from) & (pl.col("date") <= keep_to),
        )
        if len(trimmed) > M1_TRIM_TARGET_ROWS:
            excess = len(trimmed) - M1_TRIM_TARGET_ROWS
            drop_each = excess // 2
            trimmed = trimmed.sort("date").slice(drop_each, M1_TRIM_TARGET_ROWS)

        self._m1_candles = trimmed
        if not trimmed.is_empty():
            self._m1_loaded_start = str(trimmed["date"].min())
            self._m1_loaded_end = str(trimmed["date"].max())

    def _merge_m1_candles(self, new_df: pl.DataFrame) -> None:
        """Добавляет минутные свечи в кэш _m1_candles без дубликатов по date."""
        if new_df.is_empty():
            return
        if self._m1_candles is None or self._m1_candles.is_empty():
            self._m1_candles = new_df
        else:
            self._m1_candles = pl.concat([self._m1_candles, new_df]).unique(
                subset=["date"], keep="first",
            ).sort("date")

    def _refresh_chart_display(
        self,
        *,
        refresh_drawings: bool = False,
        fit: bool = False,
        scroll_to_end: bool = False,
    ) -> None:
        """
        Пересчитывает таймфрейм из M1 и загружает ВСЕ данные на график.
        Вызывается только когда M1-кэш изменился (подгрузка, смена ТФ, инициализация).
        """
        if self._m1_candles is None or self._m1_candles.is_empty():
            return

        df_full = resample_candles(self._m1_candles, self._current_timeframe)
        self._resampled_cache = df_full

        if df_full.is_empty():
            return

        if refresh_drawings:
            self.chart_widget.clear_drawings()

        # Сохраняем видимый диапазон ДО chart.set() — после setData он сбросится
        saved_start = self._saved_visible_start
        saved_end = self._saved_visible_end

        self.chart_widget.load_candles(df_full, replace=True)

        if not self._m1_candles.is_empty():
            self._m1_loaded_start = str(self._m1_candles["date"].min())
            self._m1_loaded_end = str(self._m1_candles["date"].max())

        if refresh_drawings:
            self._restore_drawings(self._current_db_path, self._current_sec_code)

        # Восстанавливаем zoom после chart.set(), если не было явного fit/scroll_to_end
        if saved_start is not None and saved_end is not None and not fit and not scroll_to_end:
            self._restoring_range = True
            try:
                self.chart_widget.chart.set_visible_range(
                    pd.Timestamp(saved_start, unit="s"),
                    pd.Timestamp(saved_end, unit="s"),
                )
            except Exception:
                logger.warning("Не удалось восстановить visible range", exc_info=True)
            # Снимаем флаг через 100мс — достаточно, чтобы JS обработал setVisibleRange
            QTimer.singleShot(100, lambda: setattr(self, "_restoring_range", False))

        self.chart_widget.set_title(self._current_sec_code)
        self.set_status_message(
            f"{self._current_sec_code}: {len(df_full)} {self._current_timeframe}, "
            f"M1 в памяти {len(self._m1_candles)}"
        )
        if fit:
            QTimer.singleShot(50, self.chart_widget.fit)
        elif scroll_to_end:
            QTimer.singleShot(80, self.chart_widget.scroll_to_last)

    def load_and_display(
        self,
        db_path: str,
        sec_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
        timeframe: str | None = None,
        use_saved_camera: bool = False,
    ) -> None:
        """
        Загружает последние M1 из БД и показывает выбранный таймфрейм (resample).

        Не использует узкое «окно камеры» по датам отображения — это ломало видимость.
        """
        try:
            display_tf = timeframe or self._current_timeframe
            self.set_status_message(f"Загрузка {sec_code} (M1 → {display_tf})...")

            if timeframe is not None:
                self._current_timeframe = timeframe
                if self.timeframe_combo.currentText() != timeframe:
                    self.timeframe_combo.blockSignals(True)
                    self.timeframe_combo.setCurrentText(timeframe)
                    self.timeframe_combo.blockSignals(False)

            self._current_db_path = db_path
            self._current_sec_code = sec_code
            self._m1_candles = None
            self._m1_loaded_start = None
            self._m1_loaded_end = None
            self._loaded_start = None
            self._loaded_end = None
            self.chart_widget._cached_candles = None
            self.chart_widget._last_data_hash = 0
            self._resampled_cache = None
            self._last_visible_range = None
            self._saved_visible_start = None
            self._saved_visible_end = None
            self._restoring_range = False

            df_m1: pl.DataFrame
            if start_date or end_date:
                df_m1 = load_candles(
                    db_path=db_path,
                    sec_code=sec_code,
                    start_date=start_date,
                    end_date=end_date,
                    timeframe="M1",
                )
            else:
                try:
                    df_m1 = load_candles_tail(
                        db_path=db_path,
                        sec_code=sec_code,
                        limit=INITIAL_M1_BARS,
                        timeframe="M1",
                    )
                except ValueError:
                    df_m1 = load_candles(
                        db_path=db_path, sec_code=sec_code, timeframe="M1",
                    )
                    if len(df_m1) > INITIAL_M1_BARS:
                        df_m1 = df_m1.tail(INITIAL_M1_BARS)

            if df_m1.is_empty():
                self.chart_widget.clear()
                self.set_status_message(f"Нет минутных данных для {sec_code}")
                return

            self._m1_candles = df_m1
            self._m1_loaded_start = str(df_m1["date"].min())
            self._m1_loaded_end = str(df_m1["date"].max())

            self._refresh_chart_display(
                refresh_drawings=True,
                fit=False,
                scroll_to_end=True,
            )

        except FileNotFoundError as exc:
            self.set_status_message(f"Ошибка: {exc}")
        except ValueError as exc:
            self.set_status_message(f"Ошибка: {exc}")

    def set_status_message(self, message: str) -> None:
        """
        Устанавливает текст в строке статуса.

        Параметры:
            message: Текст сообщения.
        """
        self.statusBar().showMessage(message)
