#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Главное окно приложения Backtester.

Содержит:
- строку меню и панель инструментов
- боковые панели для выбора инструментов и индикаторов
- центральную область для графика
- строку состояния
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QDockWidget,
    QLabel,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from src.data.database import DatabaseManager
from src.data.loader import DataLoader
from src.gui.chart_widget import ChartWidget
from src.gui.instrument_panel import InstrumentPanel as InstrumentPanelWidget

class MainWindow(QMainWindow):
    """
    Главное окно приложения-бэктестера.

    Содержит полноценный интерфейс с:
    - меню и панелью инструментов
    - док-панелями инструментов и индикаторов
    - центральной областью графика
    - строкой состояния
    """

    def __init__(self) -> None:
        """
        Инициализация главного окна:
        создаёт меню, панели, центральный виджет.
        """
        super().__init__(None)

        # Настройка окна
        self.setWindowTitle("Backtester v0.1")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 600)

        # Компоненты данных
        self._db_manager: DatabaseManager = DatabaseManager()
        self._data_loader: Optional[DataLoader] = None

        # Создаём все элементы интерфейса
        # Панели должны быть созданы до меню (меню ссылается на них)
        self._create_dock_panels()
        self._create_menu()
        self._create_toolbar()
        self._create_central_widget()
        self._create_status_bar()

        # Настраиваем тему графика при загрузке
        self._chart_widget.set_theme()

    # ------------------------------------------------------------------
    #  Создание элементов интерфейса
    # ------------------------------------------------------------------

    def _create_menu(self) -> None:
        """
        Создаёт строку меню с разделами:
        Файл, Вид, Справка.
        """
        menu_bar: QMenuBar = self.menuBar()

        # --- Меню "Файл" ---
        file_menu = menu_bar.addMenu("&Файл")

        exit_action = QAction("&Выход", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # --- Меню "Вид" ---
        view_menu = menu_bar.addMenu("&Вид")

        toggle_instruments = QAction("&Инструменты", self)
        toggle_instruments.setCheckable(True)
        toggle_instruments.setChecked(True)
        toggle_instruments.triggered.connect(
            self._instrument_panel.setVisible
        )
        view_menu.addAction(toggle_instruments)

        toggle_indicators = QAction("&Индикаторы", self)
        toggle_indicators.setCheckable(True)
        toggle_indicators.setChecked(True)
        toggle_indicators.triggered.connect(
            self._indicators_panel.setVisible
        )
        view_menu.addAction(toggle_indicators)

        # --- Меню "Справка" ---
        help_menu = menu_bar.addMenu("&Справка")

        about_action = QAction("&О программе", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _create_toolbar(self) -> None:
        """
        Создаёт панель инструментов с базовыми кнопками.
        """
        toolbar: QToolBar = self.addToolBar("Основная")
        toolbar.setMovable(False)

        # Кнопка обновления данных (заглушка)
        refresh_action = QAction("🔄 Обновить", self)
        refresh_action.setStatusTip("Обновить данные")
        refresh_action.triggered.connect(self._on_refresh)
        toolbar.addAction(refresh_action)

    def _create_central_widget(self) -> None:
        """
        Создаёт центральную область с графиком.
        """
        self._chart_widget = ChartWidget()
        self.setCentralWidget(self._chart_widget)

    def _create_dock_panels(self) -> None:
        """
        Создаёт закрепляемые боковые панели:
        - панель инструментов (слева)
        - панель индикаторов (справа)
        """
        # Панель инструментов (QWidget из instrument_panel.py, обёрнутый в QDockWidget)
        self._instrument_panel = QDockWidget("Инструменты", self)
        self._instrument_widget = InstrumentPanelWidget(
            self._db_manager, self
        )
        self._instrument_panel.setWidget(self._instrument_widget)
        self._instrument_panel.setMinimumWidth(220)
        self._instrument_panel.setMaximumWidth(350)
        self._instrument_panel.setFeatures(
            QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable
        )
        self.addDockWidget(Qt.LeftDockWidgetArea, self._instrument_panel)

        # Подключаем сигнал выбора инструмента
        self._instrument_widget.instrument_selected.connect(
            self.load_instrument
        )

        # Панель индикаторов (заглушка)
        self._indicators_panel = QDockWidget("Индикаторы", self)
        indicators_container = QWidget()
        indicators_layout = QVBoxLayout(indicators_container)
        indicators_label = QLabel("Панель индикаторов\n(будет реализовано)")
        indicators_label.setAlignment(Qt.AlignCenter)
        indicators_layout.addWidget(indicators_label)
        indicators_layout.addStretch()
        self._indicators_panel.setWidget(indicators_container)
        self._indicators_panel.setMinimumWidth(180)
        self._indicators_panel.setMaximumWidth(300)
        self._indicators_panel.setFeatures(
            QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable
        )
        self.addDockWidget(
            Qt.RightDockWidgetArea, self._indicators_panel
        )

    def _create_status_bar(self) -> None:
        """
        Создаёт строку состояния с приветствием.
        """
        status: QStatusBar = self.statusBar()
        status.showMessage("Готов к работе. Выберите инструмент.")

    # ------------------------------------------------------------------
    #  Слоты (обработчики событий)
    # ------------------------------------------------------------------

    @Slot()
    def _show_about(self) -> None:
        """
        Показывает диалог "О программе".
        """
        QMessageBox.about(
            self,
            "О программе Backtester",
            "Backtester v0.1\n\n"
            "Приложение для бэктестинга торговых стратегий\n"
            "с интерактивными графиками.\n\n"
            "Стек: Python 3.14, PySide6, lightweight-charts",
        )

    @Slot()
    def _on_refresh(self) -> None:
        """
        Обработчик кнопки обновления данных.
        Перезагружает данные для текущего инструмента.
        """
        if self._data_loader is None:
            self.statusBar().showMessage(
                "Нет загруженного инструмента", 3000
            )
            return

        loaded = self._data_loader.reload()
        if loaded:
            self._chart_widget.set_candles(loaded)

        self.statusBar().showMessage(
            f"Данные обновлены: {len(loaded)} свечей", 3000
        )

    # ------------------------------------------------------------------
    #  Загрузка инструмента и интеграция с DataLoader
    # ------------------------------------------------------------------

    def load_instrument(
        self,
        sec_code: str,
        days_back: int = 30,
    ) -> None:
        """
        Загружает инструмент и отображает его свечи на графике.

        Параметры:
            sec_code — код инструмента (например 'AAH6')
            days_back — количество дней от текущей даты для начального окна
        """
        # Ищем инструмент в БД
        entry = self._db_manager.find_instrument(sec_code)
        if entry is None:
            self.statusBar().showMessage(
                f"Инструмент {sec_code} не найден", 5000
            )
            return

        # Создаём DataLoader
        self._data_loader = DataLoader(
            self._db_manager, sec_code, padding_factor=2
        )

        # Устанавливаем видимое окно: последние N дней
        now = datetime.now()
        start = now - timedelta(days=days_back)

        # Загружаем данные через DataLoader
        loaded = self._data_loader.set_visible_range(start, now)

        if not loaded:
            self.statusBar().showMessage(
                f"Нет данных для {sec_code}", 5000
            )
            return

        # Отображаем на графике
        self._chart_widget.set_candles(loaded)
        self._chart_widget.set_visible_range(
            self._data_loader.visible_start,
            self._data_loader.visible_end,
        )

        # Регистрируем callback на изменение видимого диапазона
        self._chart_widget.set_on_visible_range_changed(
            self._on_chart_visible_range_changed,
        )

        self.statusBar().showMessage(
            f"Загружен {sec_code}: "
            f"{len(self._data_loader.visible_candles)} свечей в окне, "
            f"{len(loaded)} всего загружено",
            5000,
        )

    def _on_chart_visible_range_changed(
        self, start: datetime, end: datetime
    ) -> None:
        """
        Обрабатывает изменение видимого диапазона на графике.

        Обновляет DataLoader и при необходимости догружает данные.
        """
        if self._data_loader is None:
            return

        # Обновляем видимое окно в DataLoader
        loaded = self._data_loader.set_visible_range(start, end)

        # Если данные изменились — обновляем график
        if loaded:
            self._chart_widget.set_candles(loaded)

        self.statusBar().showMessage(
            f"Диапазон: {start.strftime('%d.%m %H:%M')} — "
            f"{end.strftime('%d.%m %H:%M')}, "
            f"загружено {len(loaded)} свечей",
            5000,
        )

    # ------------------------------------------------------------------
    #  Свойства для доступа к дочерним виджетам
    # ------------------------------------------------------------------

    @property
    def chart_widget(self) -> ChartWidget:
        """
        Возвращает виджет графика (lightweight-charts).
        """
        return self._chart_widget

    @property
    def instrument_panel(self) -> QDockWidget:
        """
        Возвращает док-панель выбора инструментов.
        """
        return self._instrument_panel

    @property
    def indicators_panel(self) -> QDockWidget:
        """
        Возвращает док-панель индикаторов.
        """
        return self._indicators_panel
