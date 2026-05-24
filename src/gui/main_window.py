"""
Главное окно приложения бэктестера.

Построено на QMainWindow с пустым контейнером для будущего графика,
строкой меню, статус-баром и областями для док-панелей.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    """
    Главное окно приложения.

    Содержит:
    - Центральный виджет-контейнер для графика (chart_container).
    - Строку меню (File, View, Help).
    - Строку статуса.
    - Возможность добавления док-панелей в будущем.
    """

    def __init__(self) -> None:
        """Инициализирует главное окно: настройка заголовка, размеров, меню и статуса."""
        super().__init__()

        # Настройка окна
        self.setWindowTitle("Бэктестер стратегий")
        self.setMinimumSize(1280, 720)
        self.resize(1600, 900)

        # Создаём центральный виджет-контейнер для графика
        self._create_central_widget()

        # Создаём строку меню
        self._create_menu_bar()

        # Создаём строку статуса
        self._create_status_bar()

    def _create_central_widget(self) -> None:
        """
        Создаёт центральный виджет с пустым контейнером.

        chart_container — QWidget, в который в будущем будет встроен
        график lightweight-charts (через QWebEngineView).
        """
        # Главный центральный виджет
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        # Макет для размещения контейнера графика
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        central_widget.setLayout(layout)

        # Пустой контейнер под будущий график
        self.chart_container = QWidget()
        self.chart_container.setObjectName("chartContainer")
        self.chart_container.setStyleSheet(
            "background-color: #1a1a2e; border: 1px solid #333;"
        )
        layout.addWidget(self.chart_container)

    def _create_menu_bar(self) -> None:
        """Создаёт строку меню с разделами File, View и Help."""
        menu_bar = self.menuBar()

        # Меню File
        file_menu = menu_bar.addMenu("Файл")

        self.action_exit = QAction("Выход", self)
        self.action_exit.setShortcut("Ctrl+Q")
        self.action_exit.setStatusTip("Закрыть приложение")
        self.action_exit.triggered.connect(self.close)
        file_menu.addAction(self.action_exit)

        # Меню View
        view_menu = menu_bar.addMenu("Вид")
        self.action_toggle_status_bar = QAction("Строка статуса", self)
        self.action_toggle_status_bar.setCheckable(True)
        self.action_toggle_status_bar.setChecked(True)
        self.action_toggle_status_bar.setStatusTip("Показать/скрыть строку статуса")
        self.action_toggle_status_bar.triggered.connect(self._toggle_status_bar)
        view_menu.addAction(self.action_toggle_status_bar)

        # Меню Help
        help_menu = menu_bar.addMenu("Помощь")
        self.action_about = QAction("О программе", self)
        self.action_about.setStatusTip("Информация о приложении")
        self.action_about.triggered.connect(self._show_about)
        help_menu.addAction(self.action_about)

    def _create_status_bar(self) -> None:
        """Создаёт строку статуса с приветственным сообщением."""
        status_bar = QStatusBar()
        status_bar.setObjectName("statusBar")
        status_bar.showMessage("Готов к работе")
        self.setStatusBar(status_bar)

    def _toggle_status_bar(self, checked: bool) -> None:
        """
        Показывает или скрывает строку статуса.

        Параметры:
            checked: True — показать, False — скрыть.
        """
        self.statusBar().setVisible(checked)
        # Синхронизируем состояние флажка действия с видимостью
        self.action_toggle_status_bar.setChecked(checked)

    def _show_about(self) -> None:
        """Показывает диалоговое окно с информацией о приложении."""
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.about(
            self,
            "О программе",
            "Бэктестер стратегий\n\n"
            "Версия: 0.1.0\n\n"
            "Приложение для тестирования торговых стратегий "
            "на исторических данных с интерактивными графиками.",
        )

    def set_status_message(self, message: str) -> None:
        """
        Устанавливает текст в строке статуса.

        Параметры:
            message: Текст сообщения.
        """
        self.statusBar().showMessage(message)
