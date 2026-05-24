#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Точка входа в приложение Backtester.
Создаёт главное окно PySide6 и запускает цикл обработки событий.
"""

import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QLabel
from PySide6.QtCore import Qt


class MainWindow(QMainWindow):
    """
    Главное окно приложения-бэктестера.
    Пока что содержит заглушку, в дальнейшем будет заменено
    полноценным интерфейсом с графиками и панелями управления.
    """

    def __init__(self) -> None:
        """
        Инициализация главного окна:
        - устанавливается заголовок
        - задаётся начальный размер
        - размещается приветственная метка
        """
        super().__init__(None)

        # Настройка окна
        self.setWindowTitle("Backtester v0.1")
        self.resize(1280, 800)

        # Центральная метка-заглушка
        label = QLabel("Добро пожаловать в Backtester!\nЗагрузка данных и графиков...")
        label.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(label)


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
