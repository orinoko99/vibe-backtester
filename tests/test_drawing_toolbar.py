"""
Тесты для панели списка рисунков (src/gui/drawing_toolbar.py).
"""

import pytest
from PySide6.QtWidgets import QPushButton, QListWidget, QWidget

from src.gui.drawing_toolbar import DrawingToolbar


@pytest.fixture
def toolbar(qtbot) -> DrawingToolbar:
    tb = DrawingToolbar()
    qtbot.addWidget(tb)
    return tb


def test_toolbar_creation(toolbar: DrawingToolbar) -> None:
    assert toolbar is not None
    assert isinstance(toolbar, QWidget)


def test_clear_button_exists(toolbar: DrawingToolbar) -> None:
    assert isinstance(toolbar.clear_button, QPushButton)


def test_clear_button_emits_signal(toolbar: DrawingToolbar) -> None:
    signal_emitted = []
    toolbar.clear_requested.connect(lambda: signal_emitted.append(True))
    toolbar.clear_button.click()
    assert len(signal_emitted) == 1


def test_drawing_list_exists(toolbar: DrawingToolbar) -> None:
    assert isinstance(toolbar.drawing_list, QListWidget)


def test_update_drawing_list_shows_items(toolbar: DrawingToolbar) -> None:
    drawings = [
        {"type": "horizontal_line", "price": 100.0, "color": "#FF0000", "text": "A"},
        {"type": "vertical_line", "time": 1740.0, "color": "#00FF00"},
    ]
    toolbar.update_drawing_list(drawings)
    assert toolbar.drawing_list.count() == 2


def test_delete_selected_emits_index(toolbar: DrawingToolbar, qtbot) -> None:
    toolbar.update_drawing_list([
        {"type": "horizontal_line", "color": "#FF0000"},
        {"type": "vertical_line", "color": "#00FF00"},
    ])
    toolbar.drawing_list.setCurrentRow(1)
    with qtbot.waitSignal(toolbar.delete_drawing_requested) as blocker:
        toolbar.delete_selected_button.click()
    assert blocker.args[0] == 1


def test_edit_text_button_exists(toolbar: DrawingToolbar) -> None:
    assert hasattr(toolbar, "edit_text_button")
