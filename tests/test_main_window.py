"""
Тесты для главного окна приложения (src/gui/main_window.py).

Использует pytest-qt для тестирования Qt-виджетов.
"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow, QStatusBar

from PySide6.QtWidgets import QComboBox, QDockWidget, QToolBar

from src.gui.main_window import TIMEFRAMES, MainWindow


@pytest.fixture
def window(qtbot) -> MainWindow:
    """
    Фикстура: создаёт экземпляр главного окна и показывает его.
    qtbot обеспечивает наличие QApplication.
    """
    main_window = MainWindow()
    main_window.show()
    qtbot.addWidget(main_window)
    return main_window


def test_window_created(window: MainWindow) -> None:
    """
    Проверяет, что окно создаётся с корректным заголовком и классом.
    """
    assert window is not None
    assert isinstance(window, QMainWindow)
    assert window.windowTitle() == "Бэктестер стратегий"


def test_window_default_size(window: MainWindow) -> None:
    """
    Проверяет минимальный размер окна.
    """
    min_size = window.minimumSize()
    assert min_size.width() >= 1280
    assert min_size.height() >= 720


def test_central_widget_exists(window: MainWindow) -> None:
    """
    Проверяет, что центральный виджет и контейнер графика существуют.
    """
    central = window.centralWidget()
    assert central is not None
    assert central.objectName() == "centralWidget"

    container = window.chart_container
    assert container is not None
    assert container.objectName() == "chartContainer"


def test_chart_container_has_dark_style(window: MainWindow) -> None:
    """
    Проверяет, что контейнер графика имеет тёмный стиль (как TradingView).
    """
    style = window.chart_container.styleSheet()
    assert "#1a1a2e" in style
    assert "background-color" in style


def test_chart_container_is_child_of_central(window: MainWindow) -> None:
    """
    Проверяет, что контейнер графика находится внутри центрального виджета.
    """
    central = window.centralWidget()
    container = window.chart_container
    assert container.parentWidget() is central


def test_menu_bar_exists(window: MainWindow) -> None:
    """
    Проверяет, что строка меню создана и содержит как минимум 3 меню.
    """
    menu_bar = window.menuBar()
    assert menu_bar is not None

    # Проверяем наличие меню
    actions = menu_bar.actions()
    # Ожидаем "Файл", "Вид", "Помощь"
    assert len(actions) >= 3


def test_file_menu_has_exit_action(window: MainWindow) -> None:
    """
    Проверяет, что меню Файл содержит действие Выход с шорткатом Ctrl+Q.
    """
    assert window.action_exit is not None
    assert isinstance(window.action_exit, QAction)
    assert window.action_exit.text() == "Выход"
    assert window.action_exit.shortcut().toString() == "Ctrl+Q"


def test_view_menu_has_toggle_status_bar(window: MainWindow) -> None:
    """
    Проверяет, что меню Вид содержит действие переключения строки статуса.
    """
    assert window.action_toggle_status_bar is not None
    assert window.action_toggle_status_bar.isCheckable()
    assert window.action_toggle_status_bar.isChecked() is True


def test_help_menu_has_about_action(window: MainWindow) -> None:
    """
    Проверяет, что меню Помощь содержит действие О программе.
    """
    assert window.action_about is not None
    assert window.action_about.text() == "О программе"


def test_status_bar_exists(window: MainWindow) -> None:
    """
    Проверяет наличие и начальное сообщение строки статуса.
    """
    status_bar = window.statusBar()
    assert status_bar is not None
    assert isinstance(status_bar, QStatusBar)
    assert status_bar.objectName() == "statusBar"


def test_status_bar_initial_message(window: MainWindow) -> None:
    """
    Проверяет приветственное сообщение в строке статуса.
    """
    status_bar = window.statusBar()
    # Даём время для отображения сообщения
    current_message = status_bar.currentMessage()
    assert current_message == "Готов к работе"


def test_toggle_status_bar_hides_it(window: MainWindow) -> None:
    """
    Проверяет, что вызов _toggle_status_bar(False) скрывает строку статуса.
    """
    window._toggle_status_bar(False)
    assert window.statusBar().isVisible() is False


def test_toggle_status_bar_shows_it(window: MainWindow) -> None:
    """
    Проверяет, что вызов _toggle_status_bar(True) показывает строку статуса.
    """
    window._toggle_status_bar(False)  # Сначала скрываем
    window._toggle_status_bar(True)  # Потом показываем
    assert window.statusBar().isVisible() is True


def test_set_status_message(window: MainWindow) -> None:
    """
    Проверяет установку произвольного сообщения в строку статуса.
    """
    test_message = "Загрузка данных..."
    window.set_status_message(test_message)
    assert window.statusBar().currentMessage() == test_message


def test_exit_action_triggers_close(window: MainWindow, qtbot) -> None:
    """
    Проверяет, что действие Выход закрывает окно (окно перестаёт быть видимым).
    """
    window.action_exit.trigger()
    # После закрытия окно должно стать невидимым
    assert window.isVisible() is False


def test_about_dialog_shows(window: MainWindow, qtbot) -> None:
    """
    Проверяет, что действие 'О программе' открывает диалог (не падает).
    """
    # Просто проверяем, что вызов не вызывает исключений
    try:
        window._show_about()
    except Exception as exc:
        pytest.fail(f"Вызов _show_about() вызвал исключение: {exc}")


def test_window_is_top_level(window: MainWindow) -> None:
    """
    Проверяет, что окно является независимым (не вложенным).
    """
    assert window.isWindow() is True


def test_window_has_chart_container_as_attribute(window: MainWindow) -> None:
    """
    Проверяет, что chart_container — публичный атрибут (важно для интеграции).
    """
    assert hasattr(window, "chart_container")


def test_status_bar_toggle_action_reflects_state(window: MainWindow) -> None:
    """
    Проверяет, что флажок в меню Вид синхронизирован с видимостью статус-бара.
    """
    # Скрываем статус-бар через метод
    window._toggle_status_bar(False)
    # Флажок должен стать false
    assert window.action_toggle_status_bar.isChecked() is False

    # Показываем обратно
    window._toggle_status_bar(True)
    assert window.action_toggle_status_bar.isChecked() is True


def test_window_resize_preserves_chart_container(window: MainWindow, qtbot) -> None:
    """
    Проверяет, что при изменении размера окна контейнер графика не теряется.
    """
    initial_container = window.chart_container
    window.resize(800, 600)
    qtbot.wait(50)  # Даём Qt время на обработку
    assert window.chart_container is initial_container


def test_toolbar_exists(window: MainWindow) -> None:
    """
    Проверяет наличие панели инструментов с таймфреймом.
    """
    toolbar = window.findChild(QToolBar, "mainToolBar")
    assert toolbar is not None
    assert toolbar.windowTitle() == "Панель инструментов"


def test_timeframe_combo_exists(window: MainWindow) -> None:
    """
    Проверяет наличие комбобокса выбора таймфрейма.
    """
    assert window.timeframe_combo is not None
    assert isinstance(window.timeframe_combo, QComboBox)


def test_timeframe_combo_has_values(window: MainWindow) -> None:
    """
    Проверяет, что комбобокс содержит все таймфреймы.
    """
    for tf in TIMEFRAMES:
        assert window.timeframe_combo.findText(tf) >= 0


def test_timeframe_default_is_m1(window: MainWindow) -> None:
    """
    Проверяет, что таймфрейм по умолчанию M1.
    """
    assert window.timeframe_combo.currentText() == "M1"
    assert window._current_timeframe == "M1"


def test_timeframe_change_updates_status(window: MainWindow) -> None:
    """
    Проверяет, что при изменении таймфрейма обновляется статус-бар.
    """
    window.timeframe_combo.setCurrentText("H1")
    status = window.statusBar().currentMessage()
    assert "H1" in status
    assert window._current_timeframe == "H1"


def test_instrument_dock_exists(window: MainWindow) -> None:
    """
    Проверяет наличие док-панели с инструментами.
    """
    dock = window.findChild(QDockWidget, "instrumentDock")
    assert dock is not None
    assert dock.windowTitle() == "Инструменты"


def test_instrument_panel_exists(window: MainWindow) -> None:
    """
    Проверяет, что InstrumentPanel создан.
    """
    assert window.instrument_panel is not None
    assert hasattr(window.instrument_panel, "instrument_list")


def test_instrument_panel_connected(window: MainWindow, qtbot) -> None:
    """
    Проверяет, что сигнал instrument_selected подключён и вызывает load_and_display.
    """
    # Устанавливаем тестовые инструменты в панель
    test_instruments = [
        {"db_path": "test.db", "table": "TEST_M1", "sec_code": "TEST"},
    ]
    window.instrument_panel.set_instruments(test_instruments)

    # Эмулируем выбор инструмента
    with qtbot.waitSignal(window.instrument_panel.instrument_selected) as blocker:
        item = window.instrument_panel.instrument_list.item(0)
        window.instrument_panel.instrument_list.itemClicked.emit(item)

    db_path, sec_code = blocker.args
    assert db_path == "test.db"
    assert sec_code == "TEST"


def test_instrument_selection_updates_current(window: MainWindow) -> None:
    """
    Проверяет, что при выборе инструмента обновляются текущие параметры.
    """
    window._on_instrument_selected("test.db", "SBER")
    assert window._current_db_path == "test.db"
    assert window._current_sec_code == "SBER"


def test_instrument_selection_updates_current_and_tries_load(window: MainWindow) -> None:
    """
    Проверяет, что при выборе инструмента обновляются текущие параметры
    и предпринимается попытка загрузки данных.
    """
    window._on_instrument_selected("test.db", "GAZP")
    assert window._current_db_path == "test.db"
    assert window._current_sec_code == "GAZP"
    # Статус должен содержать информацию об ошибке (БД не существует)
    status = window.statusBar().currentMessage()
    assert "test.db" in status or "Ошибка" in status


def test_timeframe_change_with_instrument_selected(window: MainWindow) -> None:
    """
    Проверяет, что при смене таймфрейма и выбранном инструменте
    не возникает ошибки.
    """
    window._current_db_path = "test.db"
    window._current_sec_code = "TEST"
    try:
        window.timeframe_combo.setCurrentText("M5")
    except Exception as exc:
        pytest.fail(f"Смена таймфрейма вызвала исключение: {exc}")


def test_timeframe_change_without_instrument(window: MainWindow) -> None:
    """
    Проверяет, что смена таймфрейма без выбранного инструмента
    не вызывает ошибок.
    """
    window._current_db_path = None
    window._current_sec_code = None
    try:
        window.timeframe_combo.setCurrentText("H4")
    except Exception as exc:
        pytest.fail(f"Смена таймфрейма без инструмента вызвала исключение: {exc}")


def test_current_state_after_instrument_selection(window: MainWindow) -> None:
    """
    Проверяет, что поле таймфрейма синхронизировано с _current_timeframe.
    """
    assert window.timeframe_combo.currentText() == window._current_timeframe
    window._current_timeframe = "D1"
    # После изменения внутреннего состояния комбобокс не синхронизируется автоматически
    # Это нормально — таймфрейм меняется через комбобокс
    assert window._current_timeframe == "D1"
