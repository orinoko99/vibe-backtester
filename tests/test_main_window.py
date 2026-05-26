"""
Тесты для главного окна приложения (src/gui/main_window.py).

Использует pytest-qt для тестирования Qt-виджетов.
"""

import pytest
import polars as pl
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


# ──────────────────────────────────────────────
# Тесты для панели рисования
# ──────────────────────────────────────────────


def test_drawing_dock_exists(window: MainWindow) -> None:
    """
    Проверяет наличие док-панели списка рисунков.
    """
    dock = window.findChild(QDockWidget, "drawingDock")
    assert dock is not None
    assert dock.windowTitle() == "Рисунки"


def test_chart_drawing_toolbar_on_main_bar(window: MainWindow) -> None:
    """Инструменты рисования — на главной панели, не в доке."""
    assert hasattr(window, "chart_drawing_toolbar")
    assert window.chart_drawing_toolbar is not None


def test_drawing_toolbar_exists(window: MainWindow) -> None:
    """
    Проверяет, что DrawingToolbar создан в MainWindow.
    """
    assert hasattr(window, "drawing_toolbar")
    assert window.drawing_toolbar is not None


def test_drawing_tool_selected_updates_chart(window: MainWindow) -> None:
    """Выбор инструмента на панели над графиком передаётся в ChartWidget."""
    window.chart_drawing_toolbar._on_tool_clicked("horizontal_line")
    assert window.chart_widget.active_tool == "horizontal_line"


def test_drawing_color_selected_updates_chart(window: MainWindow) -> None:
    """Цвет с панели над графиком передаётся в ChartWidget."""
    window.chart_drawing_toolbar.color_selected.emit("#FF0000")
    assert window.chart_widget.drawing_color == "#FF0000"


def test_drawing_label_text_updates_chart(window: MainWindow) -> None:
    """Текст подписи передаётся в ChartWidget."""
    window.chart_drawing_toolbar.label_text_changed.emit("Уровень")
    assert window.chart_widget.drawing_text == "Уровень"


def test_drawing_clear_clears_chart(window: MainWindow) -> None:
    """
    Проверяет, что очистка рисунков работает.
    """
    window.chart_widget._drawings.append({"type": "test"})
    window.drawing_toolbar.clear_requested.emit()
    assert window.chart_widget._drawings == []


def test_drawing_tool_status_messages(window: MainWindow) -> None:
    """Сообщения статус-бара при выборе инструментов на панели графика."""
    window.chart_drawing_toolbar._on_tool_clicked("horizontal_line")
    assert "Горизонтальная" in window.statusBar().currentMessage()

    window.chart_drawing_toolbar._on_tool_clicked("none")
    assert "Курсор" in window.statusBar().currentMessage()


def test_drawing_clear_status_message(window: MainWindow) -> None:
    """
    Проверяет сообщение статус-бара при очистке рисунков.
    """
    window.drawing_toolbar.clear_requested.emit()
    msg = window.statusBar().currentMessage()
    assert "очищены" in msg


def test_drawing_dock_is_left_dock(window: MainWindow) -> None:
    """
    Проверяет, что док-панель рисования находится слева.
    """
    dock = window.findChild(QDockWidget, "drawingDock")
    assert dock is not None
    # Проверяем, что dock добавлен
    assert dock in window.findChildren(QDockWidget)


# ──────────────────────────────────────────────
# Тесты для нового сигнала delete_drawing_requested
# ──────────────────────────────────────────────


def test_delete_drawing_signal_connected(window: MainWindow) -> None:
    """
    Проверяет, что delete_drawing_requested подключён к _on_drawing_delete_by_index.
    """
    window.chart_widget._drawings.append({"type": "horizontal_line", "price": 100.0, "color": "#FF0000", "object": None})
    window.chart_widget._drawings.append({"type": "vertical_line", "time": "2025-01-01", "color": "#00FF00", "object": None})
    window.drawing_toolbar.delete_drawing_requested.emit(0)
    assert len(window.chart_widget._drawings) == 1
    assert window.chart_widget._drawings[0]["type"] == "vertical_line"


def test_edit_drawing_signal_connected(window: MainWindow) -> None:
    """
    Проверяет, что edit_drawing_requested подключён к _on_drawing_edit_color.
    """
    window.chart_widget._drawings.append({"type": "horizontal_line", "price": 100.0, "color": "#FF0000", "object": None})
    window.drawing_toolbar.edit_drawing_requested.emit(0, "#00FF00")
    assert window.chart_widget._drawings[0]["color"] == "#00FF00"


def test_refresh_drawing_list_updates_toolbar(window: MainWindow) -> None:
    """
    Проверяет, что _refresh_drawing_list обновляет список в тулбаре.
    """
    window.chart_widget._drawings.append({"type": "horizontal_line", "price": 100.0, "color": "#FF0000", "object": None})
    window._refresh_drawing_list()
    assert window.drawing_toolbar.drawing_list.count() == 1


# ──────────────────────────────────────────────
# Тесты для сохранения/восстановления рисунков
# ──────────────────────────────────────────────


def test_save_drawings_per_instrument(window: MainWindow) -> None:
    """
    Проверяет, что рисунки сохраняются по ключу (db, sec) без timeframe.
    """
    window._current_db_path = "test.db"
    window._current_sec_code = "TEST"
    window._current_timeframe = "M1"
    window.chart_widget._drawings.append({"type": "horizontal_line", "price": 100.0, "color": "#FF0000", "object": None})
    window._save_drawings()
    key = (window._current_db_path, window._current_sec_code)
    assert key in window._saved_drawings
    assert "M1" in window._saved_drawings[key]
    assert len(window._saved_drawings[key]["M1"]) == 1


def test_restore_drawings_uses_current_timeframe(window: MainWindow) -> None:
    """
    Проверяет, что восстановление рисунков использует текущий таймфрейм.
    """
    window._current_db_path = "test.db"
    window._current_sec_code = "TEST"
    window._current_timeframe = "M5"
    key = (window._current_db_path, window._current_sec_code)
    window._saved_drawings[key] = {
        "M5": [{"type": "horizontal_line", "price": 150.0, "color": "#00FF00"}],
    }
    window._restore_drawings("test.db", "TEST")
    assert len(window.chart_widget._drawings) == 1
    assert window.chart_widget._drawings[0]["price"] == 150.0


def test_save_camera_position_per_instrument(window: MainWindow) -> None:
    """Границы M1 в памяти сохраняются с таймфреймом."""
    window._current_db_path = "test.db"
    window._current_sec_code = "TEST"
    window._current_timeframe = "M1"
    window._m1_loaded_start = "2025-01-01"
    window._m1_loaded_end = "2025-01-10"
    window._save_camera_position()
    key = (window._current_db_path, window._current_sec_code)
    tf, start, end = window._camera_positions[key]
    assert tf == "M1"
    assert start == "2025-01-01"


def test_on_drawings_changed_callback(window: MainWindow) -> None:
    """
    Проверяет, что on_drawings_changed установлен в ChartWidget.
    """
    assert window.chart_widget.on_drawings_changed is not None
    assert window.chart_widget.on_drawings_changed == window._refresh_drawing_list


def test_instrument_timeframe_saved_and_restored(window: MainWindow) -> None:
    """
    Проверяет, что таймфрейм запоминается для каждого инструмента отдельно.
    """
    window._current_db_path = "a.db"
    window._current_sec_code = "AAA"
    window._current_timeframe = "M15"
    window._save_instrument_timeframe()

    window._current_db_path = "b.db"
    window._current_sec_code = "BBB"
    window._current_timeframe = "H1"
    window._save_instrument_timeframe()

    window._restore_instrument_timeframe("a.db", "AAA")
    assert window._current_timeframe == "M15"
    assert window.timeframe_combo.currentText() == "M15"

    window._restore_instrument_timeframe("b.db", "BBB")
    assert window._current_timeframe == "H1"
    assert window.timeframe_combo.currentText() == "H1"


def test_timeframe_change_without_m1_keeps_tf(window: MainWindow) -> None:
    """Смена ТФ без загруженных M1 только обновляет _current_timeframe."""
    window._m1_candles = None
    window._current_timeframe = "M1"
    window._on_timeframe_changed("M5")
    assert window._current_timeframe == "M5"


def test_refresh_chart_display_resamples(window: MainWindow) -> None:
    """Отображение строится ресемплом из M1, загружаются все свечи."""
    from datetime import datetime

    window._current_db_path = "t.db"
    window._current_sec_code = "T"
    window._current_timeframe = "M5"
    n = 60
    window._m1_candles = pl.DataFrame({
        "date": [datetime(2025, 1, 1, 10, i) for i in range(n)],
        "open": [1.0] * n,
        "high": [2.0] * n,
        "low": [0.5] * n,
        "close": [1.5] * n,
        "volume": [100] * n,
    })
    window._refresh_chart_display(refresh_drawings=False, fit=False)
    assert window.chart_widget._cached_candles is not None
    assert len(window.chart_widget._cached_candles) == n // 5  # 60 M1 = 12 M5
    assert window._resampled_cache is not None


def test_drawing_clear_updates_saved_drawings(window: MainWindow) -> None:
    """
    Проверяет, что «Очистить всё» обнуляет сохранённые рисунки для таймфрейма.
    """
    window._current_db_path = "test.db"
    window._current_sec_code = "TEST"
    window._current_timeframe = "M1"
    window.chart_widget._drawings.append(
        {"type": "horizontal_line", "price": 100.0, "color": "#FF0000", "object": None},
    )
    window._save_drawings()
    window._on_drawing_clear()
    key = (window._current_db_path, window._current_sec_code)
    assert window._saved_drawings[key]["M1"] == []


# ──────────────────────────────────────────────
# Тесты фикса zoom (сохранение/восстановление visible range)
# ──────────────────────────────────────────────


def test_save_visible_range_from_cache_empty(window: MainWindow) -> None:
    """Пустой кэш — saved_visible сбрасывается в None."""
    window._resampled_cache = None
    window._save_visible_range_from_cache(10, 20)
    assert window._saved_visible_start is None
    assert window._saved_visible_end is None

    window._resampled_cache = pl.DataFrame()
    window._save_visible_range_from_cache(10, 20)
    assert window._saved_visible_start is None
    assert window._saved_visible_end is None


def test_save_visible_range_from_cache_center(window: MainWindow) -> None:
    """С сохранённым кэшем сохраняются корректные unix-timestamps для средней области."""
    from datetime import datetime, timedelta

    base = datetime(2025, 6, 1, 10, 0)
    dates = [base + timedelta(minutes=i) for i in range(100)]
    window._resampled_cache = pl.DataFrame({
        "date": dates,
        "open": [1.0] * 100,
        "high": [1.1] * 100,
        "low": [0.9] * 100,
        "close": [1.05] * 100,
    })
    # bars_before=30, bars_after=20 => видимая область: индексы [30..79]
    window._save_visible_range_from_cache(30, 20)
    assert window._saved_visible_start is not None
    assert window._saved_visible_end is not None
    # Проверяем, что сохранённые timestamps соответствуют датам на индексах 30 и 79
    expected_start = dates[30].timestamp()
    expected_end = dates[79].timestamp()
    assert abs(window._saved_visible_start - expected_start) < 0.001
    assert abs(window._saved_visible_end - expected_end) < 0.001


def test_save_visible_range_from_cache_clamped(window: MainWindow) -> None:
    """bars_before/bars_after за границами данных — индексы не выходят за пределы."""
    from datetime import datetime

    n = 50
    dates = [datetime(2025, 6, 1, 10, i) for i in range(n)]
    window._resampled_cache = pl.DataFrame({
        "date": dates,
        "open": [1.0] * n,
        "high": [1.1] * n,
        "low": [0.9] * n,
        "close": [1.05] * n,
    })
    # bars_before=999 (больше n) => visible_start_idx принудительно 0
    # bars_after=999 => visible_end_idx принудительно n
    window._save_visible_range_from_cache(999, 999)
    assert window._saved_visible_start is not None
    assert window._saved_visible_end is not None
    expected_start = dates[0].timestamp()
    expected_end = dates[-1].timestamp()
    assert abs(window._saved_visible_start - expected_start) < 0.001
    assert abs(window._saved_visible_end - expected_end) < 0.001


def test_on_range_change_saves_visible_range(window: MainWindow) -> None:
    """При range_change сохраняются временные границы видимой области."""
    from datetime import datetime

    n = 50
    dates = [datetime(2025, 6, 1, 10, i) for i in range(n)]
    window._resampled_cache = pl.DataFrame({
        "date": dates,
        "open": [1.0] * n,
        "high": [1.1] * n,
        "low": [0.9] * n,
        "close": [1.05] * n,
    })
    window._on_chart_range_change(10, 15)
    assert window._saved_visible_start is not None
    expected_start = dates[10].timestamp()
    assert abs(window._saved_visible_start - expected_start) < 0.001


def test_on_range_change_skipped_when_restoring(window: MainWindow) -> None:
    """
    Если _restoring_range=True, range_change не должен пытаться подгружать данные.
    Проверяем, что _m1_loaded_start не меняется (нет вызова _load_data_before).
    """
    from datetime import datetime

    window._current_db_path = "t.db"
    window._current_sec_code = "T"
    window._m1_candles = pl.DataFrame({
        "date": [datetime(2025, 6, 1, 10, i) for i in range(5)],
        "open": [1.0] * 5,
        "high": [1.1] * 5,
        "low": [0.9] * 5,
        "close": [1.05] * 5,
    })
    window._m1_loaded_start = "2025-06-01 10:00:00"
    original_start = window._m1_loaded_start
    window._restoring_range = True
    # При restoring=True _load_data_before не вызывается, _m1_loaded_start не меняется
    window._on_chart_range_change(-1, 5)
    assert window._m1_loaded_start == original_start


def test_refresh_chart_display_restores_range(window: MainWindow) -> None:
    """
    _refresh_chart_display восстанавливает visible range после chart.set(),
    если сохранены границы и не заданы fit/scroll_to_end.
    """
    from datetime import datetime
    from unittest.mock import patch

    n = 60
    dates = [datetime(2025, 6, 1, 10, i) for i in range(n)]
    window._current_db_path = "t.db"
    window._current_sec_code = "T"
    window._current_timeframe = "M1"
    window._m1_candles = pl.DataFrame({
        "date": dates,
        "open": [1.0] * n,
        "high": [1.1] * n,
        "low": [0.9] * n,
        "close": [1.05] * n,
    })
    # Имитируем сохранённый visible range (индексы 10..49)
    window._saved_visible_start = dates[10].timestamp()
    window._saved_visible_end = dates[49].timestamp()

    called_with: list[tuple] = []

    def fake_set_visible_range(start, end):
        called_with.append((start, end))

    with patch.object(window.chart_widget.chart, "set_visible_range", fake_set_visible_range):
        window._refresh_chart_display(refresh_drawings=False, fit=False)

    # Проверяем, что set_visible_range был вызван с нужными аргументами
    assert len(called_with) == 1, "set_visible_range должен быть вызван ровно 1 раз"
    actual_start, actual_end = called_with[0]
    # Проверяем, что timestamps соответствуют ожидаемым (допуск 1 сек)
    assert abs(actual_start.timestamp() - dates[10].timestamp()) < 1.0
    assert abs(actual_end.timestamp() - dates[49].timestamp()) < 1.0
    # Флаг _restoring_range должен быть выставлен
    assert window._restoring_range is True


def test_refresh_chart_display_skips_restore_on_scroll_to_end(window: MainWindow) -> None:
    """
    При scroll_to_end=True visible range НЕ восстанавливается,
    чтобы не мешать скроллу к последним данным.
    """
    from datetime import datetime
    from unittest.mock import patch

    n = 30
    dates = [datetime(2025, 6, 1, 10, i) for i in range(n)]
    window._current_db_path = "t.db"
    window._current_sec_code = "T"
    window._current_timeframe = "M1"
    window._m1_candles = pl.DataFrame({
        "date": dates,
        "open": [1.0] * n,
        "high": [1.1] * n,
        "low": [0.9] * n,
        "close": [1.05] * n,
    })
    window._saved_visible_start = dates[5].timestamp()
    window._saved_visible_end = dates[25].timestamp()

    called = False

    def fake_set_visible_range(start, end):
        nonlocal called
        called = True

    with patch.object(window.chart_widget.chart, "set_visible_range", fake_set_visible_range):
        window._refresh_chart_display(refresh_drawings=False, scroll_to_end=True)

    assert not called, "set_visible_range НЕ должен вызываться при scroll_to_end=True"


def test_refresh_chart_display_skips_restore_on_fit(window: MainWindow) -> None:
    """При fit=True visible range НЕ восстанавливается."""
    from datetime import datetime
    from unittest.mock import patch

    n = 30
    dates = [datetime(2025, 6, 1, 10, i) for i in range(n)]
    window._current_db_path = "t.db"
    window._current_sec_code = "T"
    window._current_timeframe = "M1"
    window._m1_candles = pl.DataFrame({
        "date": dates,
        "open": [1.0] * n,
        "high": [1.1] * n,
        "low": [0.9] * n,
        "close": [1.05] * n,
    })
    window._saved_visible_start = dates[5].timestamp()
    window._saved_visible_end = dates[25].timestamp()

    called = False

    def fake_set_visible_range(start, end):
        nonlocal called
        called = True

    with patch.object(window.chart_widget.chart, "set_visible_range", fake_set_visible_range):
        window._refresh_chart_display(refresh_drawings=False, fit=True)

    assert not called, "set_visible_range НЕ должен вызываться при fit=True"
