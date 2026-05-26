"""Тесты панели рисования над графиком."""

import pytest
from PySide6.QtWidgets import QToolButton

from src.gui.chart_drawing_toolbar import ChartDrawingToolbar


@pytest.fixture
def bar(qtbot) -> ChartDrawingToolbar:
    w = ChartDrawingToolbar()
    qtbot.addWidget(w)
    return w


def test_has_drawing_tools(bar: ChartDrawingToolbar) -> None:
    for name in ("none", "horizontal_line", "vertical_line", "trend_line", "ray_line", "vertical_span", "marker"):
        assert name in bar._tool_buttons
        assert isinstance(bar._tool_buttons[name], QToolButton)


def test_cursor_default(bar: ChartDrawingToolbar) -> None:
    assert bar._active_tool == "none"
    assert bar._tool_buttons["none"].isChecked()


def test_tool_signal(bar: ChartDrawingToolbar, qtbot) -> None:
    with qtbot.waitSignal(bar.tool_selected) as blocker:
        bar._on_tool_clicked("horizontal_line")
    assert blocker.args[0] == "horizontal_line"


def test_label_text(bar: ChartDrawingToolbar) -> None:
    bar.text_edit.setText("Уровень")
    assert bar.label_text() == "Уровень"
