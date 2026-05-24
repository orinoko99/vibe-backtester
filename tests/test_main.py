#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тесты для точки входа приложения (main.py).
Проверяют корректное создание главного окна и его базовые атрибуты.
"""

import sys

import pytest
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtCore import Qt

# Добавляем корень проекта в путь для импорта main
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from main import MainWindow


@pytest.fixture(scope="module")
def app() -> QApplication:
    """
    Фикстура: создаёт QApplication один раз на весь модуль тестов.
    """
    application = QApplication.instance() or QApplication(sys.argv)
    yield application


def test_main_window_creation(app: QApplication) -> None:
    """
    Проверяет, что MainWindow создаётся без ошибок
    и имеет корректные начальные параметры.
    """
    window = MainWindow()
    assert window is not None, "MainWindow не должен быть None"
    assert window.windowTitle() == "Backtester v0.1", \
        "Заголовок окна должен быть 'Backtester v0.1'"
    assert window.width() == 1280, "Ширина окна должна быть 1280"
    assert window.height() == 800, "Высота окна должна быть 800"
    window.close()


def test_main_window_has_label(app: QApplication) -> None:
    """
    Проверяет, что в центральном виджете находится QLabel
    с корректным текстом-приветствием.
    """
    window = MainWindow()
    central = window.centralWidget()

    # Проверяем, что центральный виджет — это QLabel
    assert isinstance(central, QLabel), \
        "Центральный виджет должен быть QLabel"

    label: QLabel = central
    assert "Добро пожаловать" in label.text(), \
        "Текст метки должен содержать приветствие"

    # Проверяем выравнивание по центру
    assert label.alignment() == Qt.AlignCenter, \
        "Текст должен быть выровнен по центру"

    window.close()


def test_main_window_show_and_hide(app: QApplication) -> None:
    """
    Проверяет, что окно корректно отображается и скрывается
    без исключений (имитация жизненного цикла окна).
    """
    window = MainWindow()
    window.show()
    assert window.isVisible(), "Окно должно быть видимым после show()"
    window.hide()
    assert not window.isVisible(), "Окно должно быть скрыто после hide()"
    window.close()
