#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тесты для главного окна приложения (src/gui/main_window.py).
Проверяют создание окна, меню, панелей, строки состояния.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDockWidget, QStatusBar

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.gui.main_window import (
    ChartPlaceholder,
    IndicatorsPanel,
    InstrumentPanel,
    MainWindow,
)


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
        """
        Проверяет, что MainWindow создаётся без ошибок.
        """
        window = MainWindow()
        assert window is not None
        assert window.windowTitle() == "Backtester v0.1"
        window.close()

    def test_window_default_size(self, app: QApplication) -> None:
        """
        Проверяет размеры окна по умолчанию.
        """
        window = MainWindow()
        assert window.width() == 1280
        assert window.height() == 800
        window.close()

    def test_window_minimum_size(self, app: QApplication) -> None:
        """
        Проверяет минимальные размеры окна.
        """
        window = MainWindow()
        assert window.minimumWidth() == 1024
        assert window.minimumHeight() == 600
        window.close()


class TestMainWindowComponents:
    """
    Тестирование наличия и корректности компонентов окна.
    """

    def test_has_instrument_panel(self, app: QApplication) -> None:
        """
        Проверяет наличие панели инструментов.
        """
        window = MainWindow()
        panel = window.instrument_panel
        assert isinstance(panel, InstrumentPanel)
        assert panel.windowTitle() == "Инструменты"
        # Должна быть слева
        assert window.dockWidgetArea(panel) == Qt.LeftDockWidgetArea
        window.close()

    def test_has_indicators_panel(self, app: QApplication) -> None:
        """
        Проверяет наличие панели индикаторов.
        """
        window = MainWindow()
        panel = window.indicators_panel
        assert isinstance(panel, IndicatorsPanel)
        assert panel.windowTitle() == "Индикаторы"
        # Должна быть справа
        assert window.dockWidgetArea(panel) == Qt.RightDockWidgetArea
        window.close()

    def test_has_chart_widget(self, app: QApplication) -> None:
        """
        Проверяет наличие центрального виджета графика.
        """
        window = MainWindow()
        chart = window.chart_widget
        assert isinstance(chart, ChartPlaceholder)
        assert window.centralWidget() is chart
        window.close()

    def test_has_status_bar(self, app: QApplication) -> None:
        """
        Проверяет наличие строки состояния.
        """
        window = MainWindow()
        status = window.statusBar()
        assert isinstance(status, QStatusBar)
        assert "Готов к работе" in status.currentMessage()
        window.close()

    def test_has_menu_bar(self, app: QApplication) -> None:
        """
        Проверяет наличие строки меню.
        """
        window = MainWindow()
        menu_bar = window.menuBar()
        # Проверяем, что меню не пустое
        actions = menu_bar.actions()
        assert len(actions) > 0, "Строка меню должна содержать пункты"
        # Проверяем названия меню
        menu_titles = [a.text() for a in actions if a.text()]
        assert "&Файл" in menu_titles
        assert "&Вид" in menu_titles
        assert "&Справка" in menu_titles
        window.close()


class TestChartPlaceholder:
    """
    Тестирование заглушки графика.
    """

    def test_default_text(self, app: QApplication) -> None:
        """
        Проверяет текст по умолчанию.
        """
        placeholder = ChartPlaceholder()
        assert "Выберите инструмент" in placeholder._label.text()
        placeholder.close()

    def test_set_placeholder_text(self, app: QApplication) -> None:
        """
        Проверяет смену текста заглушки.
        """
        placeholder = ChartPlaceholder()
        placeholder.set_placeholder_text("Новый текст")
        assert placeholder._label.text() == "Новый текст"
        placeholder.close()


class TestMainWindowShowHide:
    """
    Тестирование отображения и скрытия окна.
    """

    def test_window_show_and_hide(self, app: QApplication) -> None:
        """
        Проверяет, что окно отображается и скрывается без ошибок.
        """
        window = MainWindow()
        window.show()
        assert window.isVisible()
        window.hide()
        assert not window.isVisible()
        window.close()

    def test_dock_panels_visible_by_default(
        self, app: QApplication
    ) -> None:
        """
        Проверяет, что боковые панели видны по умолчанию.
        """
        window = MainWindow()
        window.show()
        assert window.instrument_panel.isVisible()
        assert window.indicators_panel.isVisible()
        window.close()
