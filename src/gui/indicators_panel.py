"""
Панель выбора и настройки индикаторов на графике.

Содержит список доступных индикаторов, кнопку добавления с настройкой
параметров и список активных индикаторов с возможностью удаления.
"""

from __future__ import annotations

from typing import Any, ClassVar

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QDoubleSpinBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.indicators.base import BaseIndicator, IndicatorType
from src.indicators.overlay import SMA, EMA, BollingerBands
from src.indicators.oscillators import RSI, MACD
from src.indicators.volume_profile import VolumeProfile


# Реестр доступных индикаторов: имя → класс
INDICATOR_REGISTRY: dict[str, type[BaseIndicator]] = {
    "SMA": SMA,
    "EMA": EMA,
    "Bollinger Bands": BollingerBands,
    "RSI": RSI,
    "MACD": MACD,
    "Volume Profile": VolumeProfile,
}

# Типы параметров для динамического создания полей ввода
PARAM_TYPE_MAP: dict[type, type[QSpinBox | QDoubleSpinBox]] = {
    int: QSpinBox,
    float: QDoubleSpinBox,
}


class IndicatorConfigDialog(QDialog):
    """
    Диалог настройки параметров индикатора перед добавлением.

    Автоматически создаёт поля ввода на основе params класса индикатора.
    """

    def __init__(
        self,
        indicator_class: type[BaseIndicator],
        parent: QWidget = None,
    ) -> None:
        """
        Инициализирует диалог настройки.

        Параметры:
            indicator_class: Класс индикатора для настройки.
            parent: Родительский виджет.
        """
        super().__init__(parent)
        self.indicator_class = indicator_class
        self._param_widgets: dict[str, QSpinBox | QDoubleSpinBox] = {}

        self.setWindowTitle(f"Настройка: {indicator_class.name}")
        self.setMinimumWidth(300)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Создаёт элементы интерфейса диалога."""
        layout = QVBoxLayout()
        form_layout = QFormLayout()

        # Создаём поля для каждого параметра индикатора
        for param_name, default_value in self.indicator_class.params.items():
            param_type = type(default_value)
            widget_class = PARAM_TYPE_MAP.get(param_type)

            if widget_class is None:
                continue

            spinbox = widget_class()
            spinbox.setMinimum(1)
            spinbox.setMaximum(999999)

            if isinstance(spinbox, QDoubleSpinBox):
                spinbox.setDecimals(2)
                spinbox.setSingleStep(0.5)

            spinbox.setValue(default_value)
            form_layout.addRow(f"{param_name}:", spinbox)
            self._param_widgets[param_name] = spinbox

        layout.addLayout(form_layout)

        # Кнопки OK/Отмена
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def get_params(self) -> dict[str, Any]:
        """
        Возвращает словарь параметров, введённых пользователем.

        Возвращает:
            Словарь {имя_параметра: значение}.
        """
        return {
            name: widget.value()
            for name, widget in self._param_widgets.items()
        }


class IndicatorsPanel(QWidget):
    """
    Панель выбора и управления индикаторами.

    Позволяет добавлять индикаторы из списка, настраивать их параметры,
    просматривать активные индикаторы и удалять их.

    Сигналы:
        indicator_added(BaseIndicator): Добавлен новый индикатор.
        indicator_removed(str): Удалён индикатор (передаётся display_name).
    """

    indicator_added = Signal(BaseIndicator)
    indicator_removed = Signal(str)

    def __init__(self, parent: QWidget = None) -> None:
        """
        Инициализирует панель индикаторов.

        Параметры:
            parent: Родительский виджет.
        """
        super().__init__(parent)

        # Список активных индикаторов
        self._active_indicators: list[BaseIndicator] = []

        # Создаём интерфейс
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Создаёт элементы интерфейса панели."""
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Заголовок панели
        title_label = QLabel("Индикаторы")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)

        # Выпадающий список индикаторов
        self.indicator_combo = QComboBox()
        self.indicator_combo.addItems(sorted(INDICATOR_REGISTRY.keys()))
        self.indicator_combo.setToolTip("Выберите индикатор для добавления")
        layout.addWidget(self.indicator_combo)

        # Кнопка добавления индикатора
        add_layout = QHBoxLayout()
        self.add_button = QPushButton("Добавить индикатор")
        self.add_button.clicked.connect(self._on_add_clicked)
        add_layout.addWidget(self.add_button)
        layout.addLayout(add_layout)

        # Разделитель
        section_label = QLabel("Активные индикаторы:")
        section_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        layout.addWidget(section_label)

        # Список активных индикаторов
        self.active_list = QListWidget()
        self.active_list.setAlternatingRowColors(True)
        layout.addWidget(self.active_list)

        # Кнопка удаления выбранного индикатора
        self.remove_button = QPushButton("Удалить выбранный")
        self.remove_button.setEnabled(False)
        self.remove_button.clicked.connect(self._on_remove_clicked)
        self.active_list.itemSelectionChanged.connect(
            lambda: self.remove_button.setEnabled(
                len(self.active_list.selectedItems()) > 0
            )
        )
        layout.addWidget(self.remove_button)

        # Кнопка удаления всех индикаторов
        self.clear_button = QPushButton("Удалить все")
        self.clear_button.clicked.connect(self._on_clear_clicked)
        layout.addWidget(self.clear_button)

        layout.addStretch()
        self.setLayout(layout)

    def _on_add_clicked(self) -> None:
        """Открывает диалог настройки и добавляет индикатор."""
        indicator_name: str = self.indicator_combo.currentText()
        indicator_class = INDICATOR_REGISTRY.get(indicator_name)

        if indicator_class is None:
            return

        # Если у индикатора есть параметры — открываем диалог настройки
        if indicator_class.params:
            dialog = IndicatorConfigDialog(indicator_class, self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            params = dialog.get_params()
            indicator_instance = indicator_class(**params)
        else:
            indicator_instance = indicator_class()

        # Добавляем в список активных
        self._active_indicators.append(indicator_instance)
        self._update_list()

        # Испускаем сигнал
        self.indicator_added.emit(indicator_instance)

    def _on_remove_clicked(self) -> None:
        """Удаляет выбранный индикатор из списка."""
        selected = self.active_list.selectedItems()
        if not selected:
            return

        for item in selected:
            display_name = item.text()
            # Находим и удаляем индикатор
            for i, ind in enumerate(self._active_indicators):
                if ind.display_name == display_name:
                    self._active_indicators.pop(i)
                    self.indicator_removed.emit(display_name)
                    break

        self._update_list()

    def _on_clear_clicked(self) -> None:
        """Удаляет все активные индикаторы."""
        for ind in self._active_indicators[:]:
            self.indicator_removed.emit(ind.display_name)

        self._active_indicators.clear()
        self._update_list()

    def _update_list(self) -> None:
        """Обновляет отображение списка активных индикаторов."""
        self.active_list.clear()
        for ind in self._active_indicators:
            item = QListWidgetItem(ind.display_name)
            item.setData(Qt.UserRole, ind.display_name)
            self.active_list.addItem(item)

    def get_active_indicators(self) -> list[BaseIndicator]:
        """
        Возвращает список активных индикаторов.

        Возвращает:
            Список экземпляров BaseIndicator.
        """
        return self._active_indicators.copy()

    def clear_all(self) -> None:
        """Программно очищает все индикаторы."""
        self._on_clear_clicked()
