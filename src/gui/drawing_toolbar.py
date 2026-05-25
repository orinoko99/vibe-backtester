"""
Панель инструментов рисования на графике.

Содержит кнопки для выбора инструментов рисования:
горизонтальная линия, вертикальная линия, трендовая линия,
луч, вертикальная заливка, маркер, а также выбор цвета.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QColorDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class DrawingToolbar(QWidget):
    """
    Панель инструментов рисования.

    Позволяет выбирать инструмент рисования (линия, маркер и т.д.),
    цвет линий и очищать все рисунки.

    Сигналы:
        tool_selected(str): Выбран инструмент ('horizontal_line', 'vertical_line',
            'trend_line', 'ray_line', 'vertical_span', 'marker', 'none').
        color_selected(str): Выбран цвет в HEX-формате.
        clear_requested(): Запрос на очистку всех рисунков.
    """

    tool_selected = Signal(str)
    color_selected = Signal(str)
    clear_requested = Signal()
    delete_last_requested = Signal()

    def __init__(self, parent: QWidget = None) -> None:
        """
        Инициализирует панель инструментов рисования.

        Параметры:
            parent: Родительский виджет.
        """
        super().__init__(parent)

        # Текущие настройки
        self._current_color: str = "#1E80F0"
        self._active_tool: str = "none"

        # Создаём интерфейс
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Создаёт элементы интерфейса панели."""
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Заголовок панели
        title_label = QLabel("Рисование")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)

        # Контейнер для кнопок инструментов
        tools_layout = QVBoxLayout()
        tools_layout.setSpacing(2)

        # Определяем инструменты: (метка, подсказка)
        tools: list[tuple[str, str, str]] = [
            ("cursor", "Указатель", "none"),
            ("━ H", "Горизонтальная линия", "horizontal_line"),
            ("┃ V", "Вертикальная линия", "vertical_line"),
            ("╱ T", "Трендовая линия", "trend_line"),
            ("╱ R", "Луч", "ray_line"),
            ("▣ S", "Вертикальная заливка", "vertical_span"),
            ("● M", "Маркер", "marker"),
        ]

        self._tool_buttons: dict[str, QToolButton] = {}

        for label_text, tooltip, tool_name in tools:
            btn = QToolButton()
            btn.setText(label_text)
            btn.setToolTip(tooltip)
            btn.setCheckable(True)
            btn.setChecked(tool_name == self._active_tool)
            btn.setMinimumWidth(60)
            btn.clicked.connect(lambda checked, t=tool_name: self._on_tool_clicked(t))
            tools_layout.addWidget(btn)
            self._tool_buttons[tool_name] = btn

        # Кнопка выбора цвета
        color_layout = QHBoxLayout()
        color_label = QLabel("Цвет:")
        self.color_button = QPushButton()
        self.color_button.setFixedSize(28, 28)
        self.color_button.setStyleSheet(
            f"background-color: {self._current_color}; border: 1px solid #555; border-radius: 4px;"
        )
        self.color_button.setToolTip("Выбрать цвет")
        self.color_button.clicked.connect(self._on_color_clicked)
        color_layout.addWidget(color_label)
        color_layout.addWidget(self.color_button)
        color_layout.addStretch()
        tools_layout.addLayout(color_layout)

        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        tools_layout.addWidget(separator)

        # Кнопка удаления последнего рисунка
        self.delete_last_button = QPushButton("Удалить последний")
        self.delete_last_button.setToolTip("Удалить последний добавленный рисунок")
        self.delete_last_button.clicked.connect(self.delete_last_requested.emit)
        tools_layout.addWidget(self.delete_last_button)

        # Кнопка очистки всех рисунков
        self.clear_button = QPushButton("Очистить всё")
        self.clear_button.setToolTip("Удалить все рисунки и маркеры с графика")
        self.clear_button.clicked.connect(self.clear_requested.emit)
        tools_layout.addWidget(self.clear_button)

        layout.addLayout(tools_layout)
        layout.addStretch()
        self.setLayout(layout)

    def _on_tool_clicked(self, tool_name: str) -> None:
        """
        Обрабатывает выбор инструмента рисования.

        Переключает состояние кнопок: выбранная становится активной,
        остальные сбрасываются.

        Параметры:
            tool_name: Имя выбранного инструмента.
        """
        self._active_tool = tool_name

        # Обновляем состояние всех кнопок
        for name, btn in self._tool_buttons.items():
            btn.setChecked(name == tool_name)

        self.tool_selected.emit(tool_name)

    def _on_color_clicked(self) -> None:
        """Открывает диалог выбора цвета и применяет выбранный цвет."""
        color = QColorDialog.getColor()
        if color.isValid():
            self._current_color = color.name()
            self.color_button.setStyleSheet(
                f"background-color: {self._current_color}; border: 1px solid #555; border-radius: 4px;"
            )
            self.color_selected.emit(self._current_color)

    def set_active_tool(self, tool_name: str) -> None:
        """
        Программно устанавливает активный инструмент.

        Параметры:
            tool_name: Имя инструмента.
        """
        self._on_tool_clicked(tool_name)

    def current_color(self) -> str:
        """
        Возвращает текущий выбранный цвет.

        Возвращает:
            Цвет в HEX-формате (например '#1E80F0').
        """
        return self._current_color
