#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Точка входа в приложение Backtester.
Создаёт главное окно PySide6 и запускает цикл обработки событий.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from src.gui.main_window import MainWindow


def main() -> None:
    """
    Главная функция запуска приложения:
    - создаёт QApplication
    - создаёт и показывает MainWindow
    - запускает главный цикл событий
    """
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
