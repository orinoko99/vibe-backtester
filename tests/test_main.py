#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тесты для главного окна приложения (src/gui/main_window.py).
Проверяют создание окна, меню, панелей, строки состояния,
а также виджета графика (ChartWidget).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QStatusBar

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QDockWidget

from src.gui.chart_widget import ChartWidget
from src.gui.instrument_panel import InstrumentPanel
from src.gui.main_window import MainWindow


@pytest.fixture(scope="module")
def app() -> QApplication:
    """
    Фикстура: создаёт QApplication один раз на весь модуль тестов.
    """
    application = QApplication.instance() or QApplication(sys.argv)
    yield application


class TestMainWindowCreation:
    """
    Тестирование создания главного окна.
    """

    def test_window_created(self, app: QApplication) -> None:
        window = MainWindow()
        assert window is not None
        assert window.windowTitle() == "Backtester v0.1"
        window.close()

    def test_window_default_size(self, app: QApplication) -> None:
        window = MainWindow()
        assert window.width() == 1280
        assert window.height() == 800
        window.close()

    def test_window_minimum_size(self, app: QApplication) -> None:
        window = MainWindow()
        assert window.minimumWidth() == 1024
        assert window.minimumHeight() == 600
        window.close()


class TestMainWindowComponents:
    """
    Тестирование наличия и корректности компонентов окна.
    """

    def test_has_instrument_panel(self, app: QApplication) -> None:
        window = MainWindow()
        panel = window.instrument_panel
        assert isinstance(panel, QDockWidget)
        assert panel.windowTitle() == "Инструменты"
        assert window.dockWidgetArea(panel) == Qt.LeftDockWidgetArea
        window.close()

    def test_has_indicators_panel(self, app: QApplication) -> None:
        window = MainWindow()
        panel = window.indicators_panel
        assert isinstance(panel, QDockWidget)
        assert panel.windowTitle() == "Индикаторы"
        assert window.dockWidgetArea(panel) == Qt.RightDockWidgetArea
        window.close()

    def test_has_chart_widget(self, app: QApplication) -> None:
        window = MainWindow()
        chart = window.chart_widget
        assert isinstance(chart, ChartWidget)
        assert window.centralWidget() is chart
        window.close()

    def test_has_status_bar(self, app: QApplication) -> None:
        window = MainWindow()
        status = window.statusBar()
        assert isinstance(status, QStatusBar)
        assert "Готов к работе" in status.currentMessage()
        window.close()

    def test_has_menu_bar(self, app: QApplication) -> None:
        window = MainWindow()
        menu_bar = window.menuBar()
        actions = menu_bar.actions()
        assert len(actions) > 0, "Строка меню должна содержать пункты"
        menu_titles = [a.text() for a in actions if a.text()]
        assert "&Файл" in menu_titles
        assert "&Вид" in menu_titles
        assert "&Справка" in menu_titles
        window.close()


class TestChartWidget:
    """
    Тестирование ChartWidget (создание, настройка, получение данных).
    """

    def test_chart_widget_created(self, app: QApplication) -> None:
        chart = ChartWidget()
        assert chart is not None
        assert chart._webview is not None
        chart.close()

    def test_chart_widget_set_candles_no_crash(
        self, app: QApplication
    ) -> None:
        """
        Проверяет, что set_candles не вызывает исключений.
        Данные ставятся в очередь, если страница не загружена.
        """
        chart = ChartWidget()
        from datetime import datetime
        from src.data.models import Candle
        candles = [
            Candle(
                timestamp=datetime(2025, 10, 28, 10, 0),
                open=100.0, high=105.0,
                low=95.0, close=102.0,
                volume=1000,
            ),
        ]
        # Не должно быть исключений — скрипт уходит в очередь
        chart.set_candles(candles)
        assert len(chart._pending_scripts) > 0
        chart.close()

    def test_chart_widget_set_theme(self, app: QApplication) -> None:
        chart = ChartWidget()
        # Не должно быть исключений
        chart.set_theme("#000000", "#ffffff", "#333333")
        assert len(chart._pending_scripts) > 0
        chart.close()

    def test_chart_widget_fit_content(self, app: QApplication) -> None:
        chart = ChartWidget()
        chart.fit_content()
        assert len(chart._pending_scripts) > 0
        chart.close()

    def test_chart_widget_clear(self, app: QApplication) -> None:
        chart = ChartWidget()
        chart.clear()
        assert len(chart._pending_scripts) > 0
        chart.close()


class TestMainWindowShowHide:
    """
    Тестирование отображения и скрытия окна.
    """

    def test_window_show_and_hide(self, app: QApplication) -> None:
        window = MainWindow()
        window.show()
        assert window.isVisible()
        window.hide()
        assert not window.isVisible()
        window.close()

    def test_dock_panels_visible_by_default(
        self, app: QApplication
    ) -> None:
        window = MainWindow()
        window.show()
        assert window.instrument_panel.isVisible()
        assert window.indicators_panel.isVisible()
        window.close()
