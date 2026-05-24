"""
Панель выбора торгового инструмента.

Содержит строку поиска и список инструментов из доступных БД.
Позволяет фильтровать по коду инструмента и выбирать нужный.
"""

from typing import Callable

from PySide6.QtCore import Qt, Signal
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


class InstrumentPanel(QWidget):
    """
    Панель выбора торгового инструмента.

    Содержит поле поиска/фильтрации и список доступных инструментов.
    При выборе инструмента испускает сигнал instrument_selected.

    Сигналы:
        instrument_selected(str, str): db_path, sec_code — выбран инструмент.
    """

    instrument_selected = Signal(str, str)  # (db_path, sec_code)

    def __init__(self, parent: QWidget = None) -> None:
        """
        Инициализирует панель выбора инструментов.

        Параметры:
            parent: Родительский виджет.
        """
        super().__init__(parent)

        # Список всех инструментов: список словарей с ключами db_path, sec_code, table
        self._instruments: list[dict[str, str]] = []

        # Создаём интерфейс
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Создаёт элементы интерфейса панели."""
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Заголовок панели
        title_label = QLabel("Инструменты")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)

        # Строка поиска
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск инструмента...")
        self.search_input.textChanged.connect(self._filter_instruments)
        layout.addWidget(self.search_input)

        # Кнопка загрузки списка инструментов
        self.refresh_button = QPushButton("Обновить список")
        self.refresh_button.clicked.connect(self._request_refresh)
        layout.addWidget(self.refresh_button)

        # Список инструментов
        self.instrument_list = QListWidget()
        self.instrument_list.setAlternatingRowColors(True)
        self.instrument_list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.instrument_list)

        self.setLayout(layout)

    def set_instruments(self, instruments: list[dict[str, str]]) -> None:
        """
        Устанавливает список инструментов для отображения.

        Параметры:
            instruments: список словарей с ключами db_path, sec_code, table.
        """
        self._instruments = instruments
        self._filter_instruments(self.search_input.text())

    def _filter_instruments(self, filter_text: str) -> None:
        """
        Фильтрует список инструментов по введённому тексту.

        Параметры:
            filter_text: Текст для фильтрации (по sec_code).
        """
        self.instrument_list.clear()
        filter_lower = filter_text.lower()

        for instr in self._instruments:
            sec_code = instr.get("sec_code", "")
            if filter_lower in sec_code.lower():
                item = QListWidgetItem(f"{sec_code}  ({instr.get('table', '')})")
                # Сохраняем данные инструмента в item
                item.setData(Qt.UserRole, instr)
                self.instrument_list.addItem(item)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """
        Обрабатывает щелчок по инструменту в списке.

        Параметры:
            item: Выбранный элемент списка.
        """
        instr_data = item.data(Qt.UserRole)
        if instr_data:
            self.instrument_selected.emit(
                instr_data.get("db_path", ""),
                instr_data.get("sec_code", ""),
            )

    def _request_refresh(self) -> None:
        """Запрашивает обновление списка инструментов."""
        from src.data.loader import get_available_instruments

        try:
            result = get_available_instruments()
            all_instruments = result.get("futures", []) + result.get("shares", [])
            self.set_instruments(all_instruments)
        except Exception:
            # Если БД недоступны — список остаётся пустым
            self.instrument_list.clear()
