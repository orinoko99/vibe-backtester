"""
Панель списка рисунков и действий над ними (без кнопок инструментов рисования).

Инструменты рисования и курсор — на главной панели над графиком (ChartDrawingToolbar).
"""

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class DrawingToolbar(QWidget):
    """
    Список рисунков на графике и кнопки управления ими.

    Сигналы:
        clear_requested(): Очистить все рисунки.
        delete_last_requested(): Удалить последний.
        delete_drawing_requested(int): Удалить по индексу.
        edit_drawing_requested(int, str): Изменить цвет.
        edit_drawing_text_requested(int, str): Изменить текст подписи.
    """

    clear_requested = Signal()
    delete_last_requested = Signal()
    delete_drawing_requested = Signal(int)
    edit_drawing_requested = Signal(int, str)
    edit_drawing_text_requested = Signal(int, str)

    TYPE_NAMES: dict[str, str] = {
        "horizontal_line": "Гориз. линия",
        "vertical_line": "Вертик. линия",
        "trend_line": "Тренд. линия",
        "ray_line": "Луч",
        "vertical_span": "Заливка",
        "marker": "Маркер",
    }

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        title_label = QLabel("Рисунки")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)

        self.delete_last_button = QPushButton("Удалить последний")
        self.delete_last_button.clicked.connect(self.delete_last_requested.emit)
        layout.addWidget(self.delete_last_button)

        self.clear_button = QPushButton("Очистить всё")
        self.clear_button.clicked.connect(self.clear_requested.emit)
        layout.addWidget(self.clear_button)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(separator)

        self.drawing_list = QListWidget()
        self.drawing_list.setAlternatingRowColors(True)
        self.drawing_list.setMinimumHeight(120)
        self.drawing_list.itemDoubleClicked.connect(self._on_drawing_double_clicked)
        layout.addWidget(self.drawing_list)

        item_actions = QHBoxLayout()

        self.edit_text_button = QPushButton("Текст")
        self.edit_text_button.setToolTip("Изменить подпись выбранного рисунка")
        self.edit_text_button.clicked.connect(self._on_edit_text_clicked)
        item_actions.addWidget(self.edit_text_button)

        self.edit_color_button = QPushButton("Цвет")
        self.edit_color_button.clicked.connect(self._on_edit_color_clicked)
        item_actions.addWidget(self.edit_color_button)

        self.delete_selected_button = QPushButton("Удалить")
        self.delete_selected_button.clicked.connect(self._on_delete_selected_clicked)
        item_actions.addWidget(self.delete_selected_button)

        layout.addLayout(item_actions)
        layout.addStretch()
        self.setLayout(layout)

    def update_drawing_list(self, drawings: list[dict]) -> None:
        """Обновляет список рисунков."""
        self.drawing_list.clear()
        for i, d in enumerate(drawings):
            dtype = d.get("type", "unknown")
            color = d.get("color", "#888")
            display_name = self.TYPE_NAMES.get(dtype, dtype)
            label = d.get("text", "") or ""

            details = ""
            if dtype == "horizontal_line":
                details = f" @ {d.get('price', '')}"
            elif dtype == "vertical_line":
                details = f" t={d.get('time', '')}"
            elif dtype == "trend_line":
                details = f" {d.get('start_value', '')}→{d.get('end_value', '')}"
            if label:
                details += f' «{label}»'

            item = QListWidgetItem(f"{display_name}{details}")
            item.setData(256, i)
            item.setForeground(QColor(color))
            self.drawing_list.addItem(item)

    def _on_drawing_double_clicked(self, _item: QListWidgetItem) -> None:
        self._on_edit_text_clicked()

    def _on_edit_color_clicked(self) -> None:
        current = self.drawing_list.currentItem()
        if current is None:
            return
        index = current.data(256)
        color = QColorDialog.getColor()
        if color.isValid() and index is not None:
            self.edit_drawing_requested.emit(index, color.name())

    def _on_edit_text_clicked(self) -> None:
        current = self.drawing_list.currentItem()
        if current is None:
            return
        index = current.data(256)
        if index is None:
            return
        text, ok = QInputDialog.getText(self, "Подпись", "Текст на рисунке:")
        if ok:
            self.edit_drawing_text_requested.emit(index, text)

    def _on_delete_selected_clicked(self) -> None:
        current = self.drawing_list.currentItem()
        if current is None:
            return
        index = current.data(256)
        if index is not None:
            self.delete_drawing_requested.emit(index)
