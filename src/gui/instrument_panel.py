#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Панель выбора торговых инструментов.

Отображает список инструментов из SQLite-баз данных,
предоставляет поиск по коду и выбор для отображения на графике.
"""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.data.database import DatabaseManager


class InstrumentPanel(QWidget):
    """
    Панель для выбора торгового инструмента.

    Содержит:
    - поле поиска по коду инструмента
    - список найденных инструментов
    - кнопка загрузки выбранного инструмента на график
    """

    # Сигнал: испускается при выборе инструмента
    instrument_selected = Signal(str)  # sec_code

    def __init__(
        self,
        db_manager: DatabaseManager,
        parent: Optional[QWidget] = None,
    ) -> None:
        """
        Инициализация панели инструментов.

        Параметры:
            db_manager — менеджер подключений к БД для получения списка
        """
        super().__init__(parent)

        self._db_manager: DatabaseManager = db_manager
        self._instruments: List[str] = []  # список sec_code

        # Создаём элементы интерфейса
        self._setup_ui()

        # Загружаем список инструментов из БД
        self._load_instruments()

    def _setup_ui(self) -> None:
        """
        Создаёт визуальные компоненты панели.
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Заголовок
        title = QLabel("Инструменты")
        title.setStyleSheet(
            "QLabel { font-weight: bold; font-size: 14px; "
            "padding: 4px; }"
        )
        layout.addWidget(title)

        # Поле поиска
        search_layout = QHBoxLayout()
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Поиск по коду...")
        self._search_input.textChanged.connect(self._filter_instruments)
        search_layout.addWidget(self._search_input)
        layout.addLayout(search_layout)

        # Список инструментов
        self._list_widget = QListWidget()
        self._list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list_widget)

        # Кнопка загрузки
        self._load_button = QPushButton("Загрузить на график")
        self._load_button.clicked.connect(self._on_load_clicked)
        self._load_button.setEnabled(False)
        layout.addWidget(self._load_button)

    def _load_instruments(self) -> None:
        """
        Загружает список всех инструментов из БД
        и заполняет список.
        """
        entries = self._db_manager.get_all_instruments()
        self._instruments = sorted(
            {e.sec_code for e in entries}
        )
        self._update_list()

    def _update_list(self, filter_text: str = "") -> None:
        """
        Обновляет отображение списка с учётом фильтра.
        """
        self._list_widget.clear()
        for sec_code in self._instruments:
            if filter_text.lower() in sec_code.lower():
                item = QListWidgetItem(sec_code)
                self._list_widget.addItem(item)

    def _filter_instruments(self, text: str) -> None:
        """
        Фильтрует список инструментов по введённому тексту.
        """
        self._update_list(text)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """
        Обрабатывает клик по элементу списка.
        """
        self._load_button.setEnabled(True)
        self._selected_sec_code = item.text()

    def _on_load_clicked(self) -> None:
        """
        Обрабатывает нажатие кнопки загрузки.
        Испускает сигнал instrument_selected.
        """
        if hasattr(self, "_selected_sec_code"):
            self.instrument_selected.emit(self._selected_sec_code)

    def refresh(self) -> None:
        """
        Обновляет список инструментов (перечитывает из БД).
        """
        self._load_instruments()
