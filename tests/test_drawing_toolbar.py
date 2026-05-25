"""
Тесты для панели инструментов рисования (src/gui/drawing_toolbar.py).

Проверяет создание DrawingToolbar, кнопки инструментов,
выбор цвета и сигналы.
"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QToolButton, QPushButton, QWidget

from src.gui.drawing_toolbar import DrawingToolbar


@pytest.fixture
def toolbar(qtbot) -> DrawingToolbar:
    """
    Фикстура: создаёт DrawingToolbar для тестирования.
    """
    tb = DrawingToolbar()
    qtbot.addWidget(tb)
    return tb


def test_toolbar_creation(toolbar: DrawingToolbar) -> None:
    """
    Проверяет, что панель инструментов создаётся корректно.
    """
    assert toolbar is not None
    assert isinstance(toolbar, QWidget)


def test_toolbar_has_tool_buttons(toolbar: DrawingToolbar) -> None:
    """
    Проверяет наличие кнопок инструментов рисования.
    """
    expected_tools = ["none", "horizontal_line", "vertical_line",
                      "trend_line", "ray_line", "vertical_span", "marker"]
    for tool_name in expected_tools:
        assert tool_name in toolbar._tool_buttons
        assert isinstance(toolbar._tool_buttons[tool_name], QToolButton)


def test_tool_buttons_are_checkable(toolbar: DrawingToolbar) -> None:
    """
    Проверяет, что кнопки инструментов переключаемые.
    """
    for tool_name, btn in toolbar._tool_buttons.items():
        assert btn.isCheckable(), f"Кнопка {tool_name} должна быть checkable"


def test_default_active_tool_is_none(toolbar: DrawingToolbar) -> None:
    """
    Проверяет, что по умолчанию активен инструмент 'none'.
    """
    assert toolbar._active_tool == "none"
    assert toolbar._tool_buttons["none"].isChecked() is True


def test_selecting_tool_updates_active(toolbar: DrawingToolbar) -> None:
    """
    Проверяет, что выбор инструмента обновляет _active_tool.
    """
    toolbar._on_tool_clicked("horizontal_line")
    assert toolbar._active_tool == "horizontal_line"
    assert toolbar._tool_buttons["horizontal_line"].isChecked() is True
    assert toolbar._tool_buttons["none"].isChecked() is False


def test_selecting_tool_emits_signal(toolbar: DrawingToolbar, qtbot) -> None:
    """
    Проверяет, что выбор инструмента испускает сигнал tool_selected.
    """
    with qtbot.waitSignal(toolbar.tool_selected) as blocker:
        toolbar._on_tool_clicked("trend_line")

    assert blocker.args[0] == "trend_line"


def test_selecting_different_tool_deselects_previous(toolbar: DrawingToolbar) -> None:
    """
    Проверяет, что выбор нового инструмента деактивирует предыдущий.
    """
    toolbar._on_tool_clicked("horizontal_line")
    assert toolbar._tool_buttons["horizontal_line"].isChecked() is True
    assert toolbar._tool_buttons["none"].isChecked() is False

    toolbar._on_tool_clicked("vertical_line")
    assert toolbar._tool_buttons["horizontal_line"].isChecked() is False
    assert toolbar._tool_buttons["vertical_line"].isChecked() is True


def test_color_button_exists(toolbar: DrawingToolbar) -> None:
    """
    Проверяет наличие кнопки выбора цвета.
    """
    assert hasattr(toolbar, "color_button")
    assert isinstance(toolbar.color_button, QPushButton)


def test_default_color(toolbar: DrawingToolbar) -> None:
    """
    Проверяет цвет по умолчанию.
    """
    assert toolbar.current_color() == "#1E80F0"


def test_clear_button_exists(toolbar: DrawingToolbar) -> None:
    """
    Проверяет наличие кнопки очистки рисунков.
    """
    assert hasattr(toolbar, "clear_button")
    assert isinstance(toolbar.clear_button, QPushButton)


def test_clear_button_emits_signal(toolbar: DrawingToolbar, qtbot) -> None:
    """
    Проверяет, что кнопка очистки испускает сигнал clear_requested.
    """
    signal_emitted = []

    def on_clear():
        signal_emitted.append(True)

    toolbar.clear_requested.connect(on_clear)
    toolbar.clear_button.click()
    assert len(signal_emitted) == 1


def test_set_active_tool(toolbar: DrawingToolbar) -> None:
    """
    Проверяет программную установку активного инструмента.
    """
    toolbar.set_active_tool("marker")
    assert toolbar._active_tool == "marker"
    assert toolbar._tool_buttons["marker"].isChecked() is True


def test_tool_selected_signal_on_button_click(toolbar: DrawingToolbar, qtbot) -> None:
    """
    Проверяет, что клик по кнопке инструмента испускает tool_selected.
    """
    btn = toolbar._tool_buttons["ray_line"]
    with qtbot.waitSignal(toolbar.tool_selected) as blocker:
        btn.click()

    assert blocker.args[0] == "ray_line"


def test_multiple_tool_selections(toolbar: DrawingToolbar, qtbot) -> None:
    """
    Проверяет последовательный выбор нескольких инструментов.
    """
    signals = []
    toolbar.tool_selected.connect(lambda t: signals.append(t))

    toolbar._on_tool_clicked("horizontal_line")
    toolbar._on_tool_clicked("vertical_line")
    toolbar._on_tool_clicked("marker")

    assert signals == ["horizontal_line", "vertical_line", "marker"]
    assert toolbar._active_tool == "marker"
