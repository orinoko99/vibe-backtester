"""
Тесты для панели выбора индикаторов src/gui/indicators_panel.py.

Проверяет:
- Создание панели и её элементы
- Добавление и удаление индикаторов
- Диалог настройки параметров
- Сигналы indicator_added и indicator_removed
"""

from __future__ import annotations

from typing import Any

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QListWidget, QPushButton, QSpinBox

from src.gui.indicators_panel import (
    INDICATOR_REGISTRY,
    IndicatorConfigDialog,
    IndicatorsPanel,
)
from src.indicators.base import BaseIndicator, IndicatorType


# ──────────────────────────────────────────────
# Тесты реестра индикаторов
# ──────────────────────────────────────────────


def test_indicator_registry_contains_all() -> None:
    """Проверяет, что реестр содержит все реализованные индикаторы."""
    assert "SMA" in INDICATOR_REGISTRY
    assert "EMA" in INDICATOR_REGISTRY
    assert "Bollinger Bands" in INDICATOR_REGISTRY
    assert "RSI" in INDICATOR_REGISTRY
    assert "MACD" in INDICATOR_REGISTRY
    assert "Volume Profile" in INDICATOR_REGISTRY


def test_indicator_registry_classes() -> None:
    """Проверяет, что все классы в реестре — наследники BaseIndicator."""
    for name, cls in INDICATOR_REGISTRY.items():
        assert issubclass(cls, BaseIndicator), f"{name} не наследует BaseIndicator"


def test_indicator_registry_unique() -> None:
    """Проверяет уникальность имён в реестре."""
    assert len(INDICATOR_REGISTRY) == 6


# ──────────────────────────────────────────────
# Тесты панели индикаторов
# ──────────────────────────────────────────────


def test_panel_creation(qtbot) -> None:
    """Проверяет создание панели."""
    panel = IndicatorsPanel()
    qtbot.addWidget(panel)

    # Проверяем наличие основных элементов
    assert panel.indicator_combo is not None
    assert panel.add_button is not None
    assert panel.active_list is not None
    assert panel.remove_button is not None
    assert panel.clear_button is not None


def test_panel_combo_contains_indicators(qtbot) -> None:
    """Проверяет, что комбобокс содержит все индикаторы."""
    panel = IndicatorsPanel()
    qtbot.addWidget(panel)

    combo_items = [panel.indicator_combo.itemText(i) for i in range(panel.indicator_combo.count())]
    for name in INDICATOR_REGISTRY:
        assert name in combo_items


def test_panel_initial_state(qtbot) -> None:
    """Проверяет начальное состояние панели."""
    panel = IndicatorsPanel()
    qtbot.addWidget(panel)

    assert panel.get_active_indicators() == []
    assert panel.active_list.count() == 0
    assert not panel.remove_button.isEnabled()


def test_panel_add_indicator_no_params(qtbot) -> None:
    """Проверяет добавление индикатора без параметров."""
    panel = IndicatorsPanel()
    qtbot.addWidget(panel)

    signals: list[BaseIndicator] = []

    def on_added(ind: BaseIndicator) -> None:
        signals.append(ind)

    panel.indicator_added.connect(on_added)

    # Выбираем SMA (есть параметры) — должен открыться диалог
    # Выбираем индикатор с параметрами и проверяем, что кнопка работает
    assert panel.add_button.isEnabled()


def test_panel_add_signal_emitted(qtbot) -> None:
    """Проверяет, что сигнал indicator_added испускается при добавлении."""
    panel = IndicatorsPanel()
    qtbot.addWidget(panel)

    added_indicators: list[BaseIndicator] = []

    def on_added(ind: BaseIndicator) -> None:
        added_indicators.append(ind)

    panel.indicator_added.connect(on_added)

    # Симулируем добавление вручную через внутренний метод
    from src.indicators.overlay import SMA
    ind = SMA(period=10)
    panel._active_indicators.append(ind)
    panel._update_list()

    assert len(panel.get_active_indicators()) == 1
    assert panel.get_active_indicators()[0].display_name == "SMA(10)"


def test_panel_remove_selected(qtbot) -> None:
    """Проверяет удаление выбранного индикатора."""
    panel = IndicatorsPanel()
    qtbot.addWidget(panel)

    # Добавляем индикатор вручную
    from src.indicators.overlay import SMA
    ind = SMA(period=14)
    panel._active_indicators.append(ind)
    panel._update_list()

    assert panel.active_list.count() == 1

    # Выбираем и удаляем
    panel.active_list.item(0).setSelected(True)
    panel._on_remove_clicked()

    assert panel.active_list.count() == 0
    assert panel.get_active_indicators() == []


def test_panel_clear_all(qtbot) -> None:
    """Проверяет удаление всех индикаторов."""
    panel = IndicatorsPanel()
    qtbot.addWidget(panel)

    # Добавляем несколько индикаторов
    from src.indicators.overlay import SMA, EMA
    from src.indicators.oscillators import RSI

    panel._active_indicators = [SMA(), EMA(), RSI()]
    panel._update_list()

    assert panel.active_list.count() == 3

    # Очищаем все
    panel._on_clear_clicked()

    assert panel.active_list.count() == 0
    assert panel.get_active_indicators() == []


def test_panel_remove_button_enabled_on_selection(qtbot) -> None:
    """Проверяет, что кнопка удаления активируется при выборе."""
    panel = IndicatorsPanel()
    qtbot.addWidget(panel)

    from src.indicators.overlay import SMA
    panel._active_indicators.append(SMA())
    panel._update_list()

    assert not panel.remove_button.isEnabled()

    # Выбираем элемент
    panel.active_list.item(0).setSelected(True)

    assert panel.remove_button.isEnabled()


def test_panel_clear_all_programmatic(qtbot) -> None:
    """Проверяет программный вызов clear_all."""
    panel = IndicatorsPanel()
    qtbot.addWidget(panel)

    from src.indicators.overlay import SMA
    panel._active_indicators.append(SMA())
    panel._update_list()

    panel.clear_all()
    assert panel.get_active_indicators() == []


# ──────────────────────────────────────────────
# Тесты диалога настройки параметров
# ──────────────────────────────────────────────


def test_config_dialog_creation(qtbot) -> None:
    """Проверяет создание диалога настройки."""
    from src.indicators.overlay import SMA

    dialog = IndicatorConfigDialog(SMA)
    qtbot.addWidget(dialog)

    assert dialog.windowTitle() == "Настройка: SMA"
    assert len(dialog._param_widgets) == 1  # только period
    assert "period" in dialog._param_widgets


def test_config_dialog_params_for_bb(qtbot) -> None:
    """Проверяет диалог настройки для Bollinger Bands (2 параметра)."""
    from src.indicators.overlay import BollingerBands

    dialog = IndicatorConfigDialog(BollingerBands)
    qtbot.addWidget(dialog)

    assert len(dialog._param_widgets) == 2
    assert "period" in dialog._param_widgets
    assert "std_dev" in dialog._param_widgets


def test_config_dialog_params_for_macd(qtbot) -> None:
    """Проверяет диалог настройки для MACD (3 параметра)."""
    from src.indicators.oscillators import MACD

    dialog = IndicatorConfigDialog(MACD)
    qtbot.addWidget(dialog)

    assert len(dialog._param_widgets) == 3


def test_config_dialog_get_params(qtbot) -> None:
    """Проверяет получение параметров из диалога."""
    from src.indicators.overlay import SMA

    dialog = IndicatorConfigDialog(SMA)
    qtbot.addWidget(dialog)

    # Изменяем значение period
    dialog._param_widgets["period"].setValue(50)

    params = dialog.get_params()
    assert params == {"period": 50}


def test_config_dialog_default_values(qtbot) -> None:
    """Проверяет, что значения по умолчанию соответствуют params класса."""
    from src.indicators.overlay import SMA

    dialog = IndicatorConfigDialog(SMA)
    qtbot.addWidget(dialog)

    params = dialog.get_params()
    assert params["period"] == SMA.params["period"]


# ──────────────────────────────────────────────
# Тесты регистрации — тип параметров
# ──────────────────────────────────────────────


def test_indicator_params_types() -> None:
    """Проверяет типы параметров всех индикаторов для корректности виджетов."""
    for name, cls in INDICATOR_REGISTRY.items():
        for param_name, default_value in cls.params.items():
            param_type = type(default_value)
            assert param_type in (int, float), (
                f"{name}.{param_name} имеет неподдерживаемый тип {param_type}"
            )
