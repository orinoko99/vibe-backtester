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

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)


class InstrumentPanel(QDockWidget):
    """
    Панель выбора инструментов и таймфреймов.

    Пока содержит заглушку. В дальнейшем:
    - выпадающий список инструментов
    - выбор таймфрейма
    - поиск по коду
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Инструменты", parent)

        # Содержимое панели
        container = QWidget()
        layout = QVBoxLayout(container)
        label = QLabel("Список инструментов\n(будет реализовано)")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        layout.addStretch()
        self.setWidget(container)

        # Настройки панели
        self.setMinimumWidth(200)
        self.setMaximumWidth(350)
        self.setFeatures(
            QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable
        )


class IndicatorsPanel(QDockWidget):
    """
    Панель добавления индикаторов на график.

    Пока содержит заглушку. В дальнейшем:
    - список доступных индикаторов
    - кнопка добавления на график
    - настройки параметров индикатора
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Индикаторы", parent)

        container = QWidget()
        layout = QVBoxLayout(container)
        label = QLabel("Панель индикаторов\n(будет реализовано)")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        layout.addStretch()
        self.setWidget(container)

        self.setMinimumWidth(180)
        self.setMaximumWidth(300)
        self.setFeatures(
            QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable
        )


class ChartPlaceholder(QWidget):
    """
    Заглушка для области графика.

    В дальнейшем будет заменена на lightweight-charts виджет,
    который отображает свечи, объём, volume profile
    и поддерживает интерактивное взаимодействие.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        self._label = QLabel(
            "Область графика\n\n"
            "Выберите инструмент для отображения"
        )
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setStyleSheet(
            "QLabel {"
            "  color: #888;"
            "  font-size: 16px;"
            "  background-color: #1a1a2e;"
            "  border: 1px solid #333;"
            "}"
        )
        layout.addWidget(self._label)

    def set_placeholder_text(self, text: str) -> None:
        """
        Устанавливает текст-заглушку для графика.
        """
        self._label.setText(text)


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

        # Создаём все элементы интерфейса
        self._create_menu()
        self._create_toolbar()
        self._create_central_widget()
        self._create_dock_panels()
        self._create_status_bar()

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
        view_menu.addAction(toggle_instruments)

        toggle_indicators = QAction("&Индикаторы", self)
        toggle_indicators.setCheckable(True)
        toggle_indicators.setChecked(True)
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
        self._chart_widget = ChartPlaceholder()
        self.setCentralWidget(self._chart_widget)

    def _create_dock_panels(self) -> None:
        """
        Создаёт закрепляемые боковые панели:
        - панель инструментов (слева)
        - панель индикаторов (справа)
        """
        self._instrument_panel = InstrumentPanel(self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self._instrument_panel)

        self._indicators_panel = IndicatorsPanel(self)
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
        Пока только обновляет текст в строке состояния.
        """
        self.statusBar().showMessage("Обновление данных...", 3000)

    # ------------------------------------------------------------------
    #  Свойства для доступа к дочерним виджетам
    # ------------------------------------------------------------------

    @property
    def chart_widget(self) -> ChartPlaceholder:
        """
        Возвращает виджет графика.
        """
        return self._chart_widget

    @property
    def instrument_panel(self) -> InstrumentPanel:
        """
        Возвращает панель выбора инструментов.
        """
        return self._instrument_panel

    @property
    def indicators_panel(self) -> IndicatorsPanel:
        """
        Возвращает панель индикаторов.
        """
        return self._indicators_panel
