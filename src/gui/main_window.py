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
from datetime import timedelta

import polars as pl

logger = logging.getLogger(__name__)

from src.data.loader import load_candles
from src.gui.chart_widget import ChartWidget
from src.gui.drawing_toolbar import DrawingToolbar
from src.gui.instrument_panel import InstrumentPanel


# Поддерживаемые таймфреймы
TIMEFRAMES: list[str] = ["M1", "M5", "M10", "M15", "M30", "H1", "H4", "D1"]

# Количество экранов для подгрузки данных с каждой стороны
PADDING_SCREENS: int = 2


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

        # Сохранённые позиции камеры по инструментам: ключ (db_path, sec_code, timeframe) -> (start_date, end_date)
        self._camera_positions: dict[tuple[str, str, str], tuple[str, str]] = {}

        # Сохранённые рисунки по инструментам: ключ (db_path, sec_code, timeframe) -> list[dict]
        self._saved_drawings: dict[tuple[str, str, str], list[dict[str, Any]]] = {}

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
        """Создаёт панель инструментов с выбором таймфрейма."""
        toolbar = QToolBar("Панель инструментов")
        toolbar.setObjectName("mainToolBar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Метка выбора таймфрейма
        tf_label = QLabel("Таймфрейм:")
        toolbar.addWidget(tf_label)

        # Комбобокс выбора таймфрейма
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
        """Создаёт док-панель инструментов рисования."""
        self.drawing_dock = QDockWidget("Рисование", self)
        self.drawing_dock.setObjectName("drawingDock")
        self.drawing_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )

        # Панель инструментов рисования
        self.drawing_toolbar = DrawingToolbar()
        self.drawing_toolbar.tool_selected.connect(self._on_drawing_tool_selected)
        self.drawing_toolbar.color_selected.connect(self._on_drawing_color_selected)
        self.drawing_toolbar.clear_requested.connect(self._on_drawing_clear)
        self.drawing_toolbar.delete_last_requested.connect(self._on_drawing_delete_last)
        self.drawing_dock.setWidget(self.drawing_toolbar)

        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.drawing_dock)

    def _on_drawing_tool_selected(self, tool_name: str) -> None:
        """
        Обрабатывает выбор инструмента рисования.

        Параметры:
            tool_name: Имя инструмента ('horizontal_line', 'vertical_line' и т.д.).
        """
        self.chart_widget.set_drawing_tool(tool_name)
        status_text = {
            "none": "Рисование отключено",
            "horizontal_line": "Горизонтальная линия — кликните на график",
            "vertical_line": "Вертикальная линия — кликните на график",
            "trend_line": "Трендовая линия — кликните первую точку, затем вторую",
            "ray_line": "Луч — кликните начальную точку",
            "vertical_span": "Вертикальная заливка — кликните начало, затем конец",
            "marker": "Маркер — кликните на свечу",
        }
        self.set_status_message(status_text.get(tool_name, f"Инструмент: {tool_name}"))

    def _on_drawing_color_selected(self, color: str) -> None:
        """
        Обрабатывает выбор цвета для рисования.

        Параметры:
            color: HEX-код цвета.
        """
        self.chart_widget.set_drawing_color(color)

    def _on_drawing_clear(self) -> None:
        """Очищает все рисунки и маркеры с графика."""
        self.chart_widget.clear_drawings()
        self.set_status_message("Все рисунки очищены")

    def _on_drawing_delete_last(self) -> None:
        """Удаляет последний добавленный рисунок."""
        drawings = self.chart_widget.get_drawings()
        if not drawings:
            self.set_status_message("Нет рисунков для удаления")
            return
        if self.chart_widget.delete_drawing(len(drawings) - 1):
            self.set_status_message("Последний рисунок удалён")

    def _on_instrument_selected(self, db_path: str, sec_code: str) -> None:
        """
        Обрабатывает выбор инструмента в панели.

        Сохраняет позицию камеры текущего инструмента, загружает данные
        нового инструмента и восстанавливает его позицию камеры.

        Параметры:
            db_path: Путь к БД инструмента.
            sec_code: Код инструмента.
        """
        # Сохраняем позицию камеры и рисунки для текущего инструмента
        self._save_camera_position()
        self._save_drawings()

        self._current_db_path = db_path
        self._current_sec_code = sec_code

        self.set_status_message(f"Выбран инструмент: {sec_code}")
        self.load_and_display(db_path, sec_code)

    def _save_camera_position(self) -> None:
        """Сохраняет текущую видимую область графика для текущего инструмента."""
        if self._current_db_path and self._current_sec_code and self._loaded_start and self._loaded_end:
            key = (self._current_db_path, self._current_sec_code, self._current_timeframe)
            self._camera_positions[key] = (self._loaded_start, self._loaded_end)

    def _save_drawings(self) -> None:
        """Сохраняет рисунки текущего инструмента."""
        if self._current_db_path and self._current_sec_code and hasattr(self, 'chart_widget'):
            key = (self._current_db_path, self._current_sec_code, self._current_timeframe)
            self._saved_drawings[key] = self.chart_widget.serialize_drawings()

    def _restore_drawings(self, db_path: str, sec_code: str) -> None:
        """Восстанавливает рисунки для инструмента, если они были сохранены."""
        key = (db_path, sec_code, self._current_timeframe)
        drawings = self._saved_drawings.get(key, [])
        if drawings:
            self.chart_widget.restore_drawings(drawings)

    def _restore_camera_position(self, db_path: str, sec_code: str) -> bool:
        """
        Восстанавливает сохранённую позицию камеры для инструмента.

        Параметры:
            db_path: Путь к БД.
            sec_code: Код инструмента.

        Возвращает:
            True, если позиция восстановлена, иначе False.
        """
        key = (db_path, sec_code, self._current_timeframe)
        if key in self._camera_positions:
            start, end = self._camera_positions[key]
            self._loaded_start = start
            self._loaded_end = end
            return True
        return False

    def _on_timeframe_changed(self, timeframe: str) -> None:
        """
        Обрабатывает изменение таймфрейма.

        Если инструмент уже выбран — перезагружает данные с новым таймфреймом.

        Параметры:
            timeframe: Новый таймфрейм (например 'M5', 'H1').
        """
        # Сохраняем рисунки для старого таймфрейма
        self._save_drawings()

        self._current_timeframe = timeframe
        self.set_status_message(f"Таймфрейм изменён: {timeframe}")

        # Если инструмент выбран — перезагружаем с новым таймфреймом
        if self._current_db_path and self._current_sec_code:
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

    def _on_chart_range_change(self, bars_before: float, bars_after: float) -> None:
        """
        Обрабатывает изменение видимого диапазона графика.

        Если данных с одной из сторон меньше порога (PADDING_SCREENS),
        загружает дополнительный блок данных.

        Параметры:
            bars_before: Количество свечей до видимой области.
            bars_after: Количество свечей после видимой области.
        """
        # Сохраняем последние значения для оценки размера видимой области
        self._last_visible_range = (int(bars_before), int(bars_after))

        # Сохраняем позицию камеры при изменении видимого диапазона
        self._save_camera_position()

        # Если инструмент не выбран — игнорируем
        if not self._current_db_path or not self._current_sec_code:
            return

        # Оцениваем размер видимой области в свечах
        # (примерно bars_before + bars_after изменилось с прошлого раза)
        visible_bars = max(50, int(bars_before + bars_after) // 4)
        padding_bars = visible_bars * PADDING_SCREENS

        # Проверяем, нужно ли подгрузить данные слева
        if bars_before < padding_bars and bars_before >= 0:
            self._load_data_before(bars_before, visible_bars)

        # Проверяем, нужно ли подгрузить данные справа
        if bars_after < padding_bars and bars_after >= 0:
            self._load_data_after(bars_after, visible_bars)

    def _load_data_before(self, bars_before: float, visible_bars: int) -> None:
        """
        Загружает дополнительный блок данных перед видимой областью.

        Параметры:
            bars_before: Количество свечей до видимой области.
            visible_bars: Размер видимой области в свечах.
        """
        if not self._current_db_path or not self._current_sec_code or not self._loaded_start:
            return

        try:
            # Загружаем данные на PADDING_SCREENS экранов раньше
            # Конвертируем количество свечей во временной интервал
            minutes_per_bar = self._get_minutes_per_bar()
            load_minutes = visible_bars * minutes_per_bar * PADDING_SCREENS

            start_dt = pl.Series([self._loaded_start]).str.to_datetime("%Y-%m-%d %H:%M:%S")[0]
            new_start = start_dt - timedelta(minutes=load_minutes)
            new_start_str = new_start.strftime("%Y-%m-%d %H:%M:%S")

            df = load_candles(
                db_path=self._current_db_path,
                sec_code=self._current_sec_code,
                start_date=new_start_str,
                end_date=self._loaded_start,
                timeframe=self._current_timeframe,
            )

            if not df.is_empty():
                self.chart_widget.load_candles(df, replace=False)
                self._loaded_start = new_start_str
                self.set_status_message(
                    f"Подгружено {len(df)} свечей слева для {self._current_sec_code}"
                )

        except Exception as exc:
            logger.warning("Не удалось подгрузить данные слева: %s", exc)

    def _load_data_after(self, bars_after: float, visible_bars: int) -> None:
        """
        Загружает дополнительный блок данных после видимой области.

        Параметры:
            bars_after: Количество свечей после видимой области.
            visible_bars: Размер видимой области в свечах.
        """
        if not self._current_db_path or not self._current_sec_code or not self._loaded_end:
            return

        try:
            minutes_per_bar = self._get_minutes_per_bar()
            load_minutes = visible_bars * minutes_per_bar * PADDING_SCREENS

            end_dt = pl.Series([self._loaded_end]).str.to_datetime("%Y-%m-%d %H:%M:%S")[0]
            new_end = end_dt + timedelta(minutes=load_minutes)
            new_end_str = new_end.strftime("%Y-%m-%d %H:%M:%S")

            df = load_candles(
                db_path=self._current_db_path,
                sec_code=self._current_sec_code,
                start_date=self._loaded_end,
                end_date=new_end_str,
                timeframe=self._current_timeframe,
            )

            if not df.is_empty():
                self.chart_widget.load_candles(df, replace=False)
                self._loaded_end = new_end_str
                self.set_status_message(
                    f"Подгружено {len(df)} свечей справа для {self._current_sec_code}"
                )

        except Exception as exc:
            logger.warning("Не удалось подгрузить данные справа: %s", exc)

    def _get_minutes_per_bar(self) -> int:
        """
        Возвращает количество минут в одной свече для текущего таймфрейма.
        """
        tf = self._current_timeframe
        if tf == "M1":
            return 1
        elif tf == "M5":
            return 5
        elif tf == "M10":
            return 10
        elif tf == "M15":
            return 15
        elif tf == "M30":
            return 30
        elif tf == "H1":
            return 60
        elif tf == "H4":
            return 240
        elif tf == "D1":
            return 1440
        return 1

    def load_and_display(
        self,
        db_path: str,
        sec_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
        timeframe: str | None = None,
    ) -> None:
        """
        Загружает свечные данные из SQLite БД и отображает их на графике.

        Параметры:
            db_path: Путь к файлу SQLite базы данных.
            sec_code: Код инструмента (например 'AAH6', 'SiH6').
            start_date: Начальная дата фильтрации (включительно).
            end_date: Конечная дата фильтрации (включительно).
            timeframe: Таймфрейм (M1, M5, H1 и т.д.). Если None — используется текущий.
        """
        try:
            self.set_status_message(f"Загрузка данных {sec_code}...")

            # Используем переданный таймфрейм или текущий
            if timeframe is None:
                timeframe = self._current_timeframe

            # Восстанавливаем сохранённую позицию камеры, если есть
            has_saved = self._restore_camera_position(db_path, sec_code)

            # Если есть сохранённая позиция — грузим только её диапазон с запасом
            load_start = start_date
            load_end = end_date
            if has_saved and self._loaded_start and self._loaded_end:
                start_dt = pl.Series([self._loaded_start]).str.to_datetime("%Y-%m-%d %H:%M:%S")[0]
                end_dt = pl.Series([self._loaded_end]).str.to_datetime("%Y-%m-%d %H:%M:%S")[0]
                load_start = (start_dt - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
                load_end = (end_dt + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")

            # Загружаем данные через loader
            df = load_candles(
                db_path=db_path,
                sec_code=sec_code,
                start_date=load_start,
                end_date=load_end,
                timeframe=timeframe,
            )

            if df.is_empty():
                self.set_status_message(f"Нет данных для {sec_code}")
                return

            # Отображаем данные на графике
            self.chart_widget.load_candles(df)

            # Сохраняем диапазон загруженных данных
            dates = df["date"]
            if len(dates) > 0:
                self._loaded_start = str(dates[0])
                self._loaded_end = str(dates[-1])

            # Восстанавливаем рисунки для этого инструмента
            self._restore_drawings(db_path, sec_code)

            # Подгоняем масштаб с микро-задержкой, чтобы WebEngine успел отрисовать данные
            QTimer.singleShot(50, self.chart_widget.fit)

            # Обновляем заголовок и статус
            self.chart_widget.set_title(sec_code)
            count = len(df)
            self.set_status_message(
                f"Загружено {count} свечей для {sec_code}"
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
