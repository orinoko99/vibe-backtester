"""
Модуль выбора торговых инструментов и таймфреймов.

Предоставляет:
- InstrumentSelector — виджет выбора инструмента из списка доступных
- TimeframeSelector — виджет выбора таймфрейма
- Управление списком инструментов на графике
"""

from typing import Callable, Optional

from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

# Доступные таймфреймы
ТАЙМФРЕЙМЫ = [
    "1min",
    "5min",
    "15min",
    "30min",
    "1h",
    "4h",
    "1d",
]


class ВыборИнструмента(QtWidgets.QComboBox):
    """
    Выпадающий список для выбора торгового инструмента.

    Параметры
    ----------
    parent : Optional[QtWidgets.QWidget]
        Родительский виджет.
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(150)
        self.setPlaceholderText("Выберите инструмент...")
        self.setEditable(True)

    def загрузить_инструменты(self, инструменты: list[str]) -> None:
        """
        Загружает список инструментов в выпадающий список.

        Параметры
        ----------
        инструменты : list[str]
            Список кодов инструментов.
        """
        текущий = self.currentText()
        self.clear()
        self.addItems(sorted(инструменты))
        self.setCurrentText(текущий)


class ВыборТаймфрейма(QtWidgets.QComboBox):
    """
    Выпадающий список для выбора таймфрейма.

    Параметры
    ----------
    parent : Optional[QtWidgets.QWidget]
        Родительский виджет.
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(80)
        self.addItems(ТАЙМФРЕЙМЫ)


class ПанельИнструментов(QtWidgets.QWidget):
    """
    Панель управления инструментами на графике.

    Позволяет:
    - Выбрать инструмент из выпадающего списка
    - Выбрать таймфрейм
    - Добавить/удалить инструмент с графика
    - Переключить отображение объёма

    Параметры
    ----------
    parent : Optional[QtWidgets.QWidget]
        Родительский виджет.
    """

    сигнал_добавить_инструмент = QtCore.pyqtSignal(str, str)
    """Сигнал: (код_инструмента, таймфрейм) — запрос на добавление инструмента."""

    сигнал_удалить_инструмент = QtCore.pyqtSignal(str)
    """Сигнал: (код_инструмента) — запрос на удаление инструмента."""

    сигнал_изменить_таймфрейм = QtCore.pyqtSignal(str)
    """Сигнал: (таймфрейм) — изменение таймфрейма."""

    сигнал_показать_объём = QtCore.pyqtSignal(bool)
    """Сигнал: (показать) — переключение объёма."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(layout)

        # Надпись "Инструмент"
        метка_инстр = QtWidgets.QLabel("Инструмент:")
        layout.addWidget(метка_инстр)

        # Выбор инструмента
        self.выбор_инструмента = ВыборИнструмента()
        layout.addWidget(self.выбор_инструмента)

        # Кнопка "Добавить"
        self.кнопка_добавить = QtWidgets.QPushButton("+ Добавить")
        self.кнопка_добавить.setStyleSheet(
            "background-color: #2d7d2d; color: white; padding: 4px 12px;"
        )
        layout.addWidget(self.кнопка_добавить)

        # Разделитель
        разделитель = QtWidgets.QFrame()
        разделитель.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        разделитель.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        layout.addWidget(разделитель)

        # Надпись "Таймфрейм"
        метка_тф = QtWidgets.QLabel("Таймфрейм:")
        layout.addWidget(метка_тф)

        # Выбор таймфрейма
        self.выбор_таймфрейма = ВыборТаймфрейма()
        layout.addWidget(self.выбор_таймфрейма)

        # Разделитель
        разделитель2 = QtWidgets.QFrame()
        разделитель2.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        разделитель2.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        layout.addWidget(разделитель2)

        # Чекбокс "Объём"
        self.чекбокс_объём = QtWidgets.QCheckBox("Объём")
        self.чекбокс_объём.setChecked(True)
        layout.addWidget(self.чекбокс_объём)

        # Кнопка "Автомасштаб"
        self.кнопка_автомасштаб = QtWidgets.QPushButton("Автомасштаб")
        layout.addWidget(self.кнопка_автомасштаб)

        # Растягивающийся элемент
        layout.addStretch()

        # Список добавленных инструментов
        метка_активные = QtWidgets.QLabel("Активные:")
        layout.addWidget(метка_активные)

        self.список_активных = QtWidgets.QListWidget()
        self.список_активных.setMaximumWidth(150)
        self.список_активных.setMaximumHeight(60)
        layout.addWidget(self.список_активных)

        # Кнопка "Удалить"
        self.кнопка_удалить = QtWidgets.QPushButton("✕")
        self.кнопка_удалить.setMaximumWidth(30)
        self.кнопка_удалить.setStyleSheet(
            "background-color: #8b0000; color: white;"
        )
        layout.addWidget(self.кнопка_удалить)

        # Подключаем сигналы
        self.кнопка_добавить.clicked.connect(self._on_добавить)
        self.кнопка_удалить.clicked.connect(self._on_удалить)
        self.выбор_таймфрейма.currentTextChanged.connect(
            self.сигнал_изменить_таймфрейм.emit
        )
        self.чекбокс_объём.toggled.connect(self.сигнал_показать_объём.emit)

    def _on_добавить(self) -> None:
        """Обработчик нажатия кнопки 'Добавить'."""
        код = self.выбор_инструмента.currentText().strip()
        if not код:
            return
        таймфрейм = self.выбор_таймфрейма.currentText()
        self.сигнал_добавить_инструмент.emit(код, таймфрейм)

    def _on_удалить(self) -> None:
        """Обработчик нажатия кнопки 'Удалить'."""
        выбранные = self.список_активных.selectedItems()
        for элемент in выбранные:
            self.сигнал_удалить_инструмент.emit(элемент.text())

    def добавить_в_активные(self, код: str) -> None:
        """
        Добавляет код инструмента в список активных.

        Параметры
        ----------
        код : str
            Код инструмента.
        """
        # Проверяем, нет ли уже такого
        for i in range(self.список_активных.count()):
            if self.список_активных.item(i).text() == код:
                return
        self.список_активных.addItem(код)

    def удалить_из_активных(self, код: str) -> None:
        """
        Удаляет код инструмента из списка активных.

        Параметры
        ----------
        код : str
            Код инструмента.
        """
        for i in range(self.список_активных.count()):
            if self.список_активных.item(i).text() == код:
                self.список_активных.takeItem(i)
                break
