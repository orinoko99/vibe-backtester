"""
Панель инструментов рисования на главной пулбаре (над графиком).

Курсор (выбор объектов), линии, маркер, цвет и подпись для новых рисунков.
"""

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QToolButton,
    QWidget,
)


class ChartDrawingToolbar(QWidget):
    """
    Компактная панель инструментов рисования для QToolBar.

    Сигналы:
        tool_selected(str): none, horizontal_line, vertical_line, ...
        color_selected(str): HEX-цвет новых рисунков.
        label_text_changed(str): Текст подписи для новых рисунков.
    """

    tool_selected = Signal(str)
    color_selected = Signal(str)
    label_text_changed = Signal(str)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._current_color = "#1E80F0"
        self._active_tool = "none"
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        tools: list[tuple[str, str, str]] = [
            ("↖", "Курсор — выбор и перемещение объектов", "none"),
            ("━", "Горизонтальная линия", "horizontal_line"),
            ("┃", "Вертикальная линия", "vertical_line"),
            ("╱", "Трендовая линия", "trend_line"),
            ("⇢", "Луч", "ray_line"),
            ("▣", "Заливка", "vertical_span"),
            ("●", "Маркер", "marker"),
        ]
        self._tool_buttons: dict[str, QToolButton] = {}
        for label_text, tooltip, tool_name in tools:
            btn = QToolButton()
            btn.setText(label_text)
            btn.setToolTip(tooltip)
            btn.setCheckable(True)
            btn.setChecked(tool_name == "none")
            btn.clicked.connect(lambda _c=False, t=tool_name: self._on_tool_clicked(t))
            layout.addWidget(btn)
            self._tool_buttons[tool_name] = btn

        layout.addWidget(QLabel("Цвет:"))
        self.color_button = QToolButton()
        self.color_button.setFixedSize(24, 24)
        self._apply_color_style()
        self.color_button.setToolTip("Цвет новых рисунков")
        self.color_button.clicked.connect(self._on_color_clicked)
        layout.addWidget(self.color_button)

        layout.addWidget(QLabel("Текст:"))
        self.text_edit = QLineEdit()
        self.text_edit.setPlaceholderText("Подпись на рисунке")
        self.text_edit.setMaximumWidth(160)
        self.text_edit.textChanged.connect(self.label_text_changed.emit)
        layout.addWidget(self.text_edit)

        self.setLayout(layout)

    def _apply_color_style(self) -> None:
        self.color_button.setStyleSheet(
            f"background-color: {self._current_color}; border: 1px solid #555;"
        )

    def _on_tool_clicked(self, tool_name: str) -> None:
        self._active_tool = tool_name
        for name, btn in self._tool_buttons.items():
            btn.setChecked(name == tool_name)
        self.tool_selected.emit(tool_name)

    def _on_color_clicked(self) -> None:
        color = QColorDialog.getColor()
        if color.isValid():
            self._current_color = color.name()
            self._apply_color_style()
            self.color_selected.emit(self._current_color)

    def label_text(self) -> str:
        return self.text_edit.text().strip()

    def set_active_tool(self, tool_name: str) -> None:
        self._on_tool_clicked(tool_name)
