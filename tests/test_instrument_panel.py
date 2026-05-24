"""
Тесты для панели выбора инструмента (src/gui/instrument_panel.py).
"""

import pytest
from PySide6.QtCore import Qt

from src.gui.instrument_panel import InstrumentPanel


@pytest.fixture
def panel(qtbot) -> InstrumentPanel:
    """
    Фикстура: создаёт InstrumentPanel.
    """
    widget = InstrumentPanel()
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def sample_instruments() -> list[dict[str, str]]:
    """
    Фикстура: тестовый список инструментов.
    """
    return [
        {"db_path": "futures.db", "table": "SiH6_M1", "sec_code": "SiH6"},
        {"db_path": "futures.db", "table": "AAH6_M1", "sec_code": "AAH6"},
        {"db_path": "futures.db", "table": "BRH6_M1", "sec_code": "BRH6"},
        {"db_path": "futures.db", "table": "EUGH6_M1", "sec_code": "EUGH6"},
        {"db_path": "shares.db", "table": "SBER_M1", "sec_code": "SBER"},
        {"db_path": "shares.db", "table": "GAZP_M1", "sec_code": "GAZP"},
        {"db_path": "shares.db", "table": "LKOH_M1", "sec_code": "LKOH"},
    ]


def test_panel_creation(panel: InstrumentPanel) -> None:
    """
    Проверяет создание панели.
    """
    assert panel is not None
    assert isinstance(panel, InstrumentPanel)


def test_search_input_exists(panel: InstrumentPanel) -> None:
    """
    Проверяет наличие поля поиска.
    """
    assert panel.search_input is not None
    assert panel.search_input.placeholderText() == "Поиск инструмента..."


def test_instrument_list_exists(panel: InstrumentPanel) -> None:
    """
    Проверяет наличие списка инструментов.
    """
    assert panel.instrument_list is not None


def test_refresh_button_exists(panel: InstrumentPanel) -> None:
    """
    Проверяет наличие кнопки обновления.
    """
    assert panel.refresh_button is not None
    assert panel.refresh_button.text() == "Обновить список"


def test_set_instruments_populates_list(panel: InstrumentPanel, sample_instruments: list[dict[str, str]]) -> None:
    """
    Проверяет, что set_instruments заполняет список.
    """
    panel.set_instruments(sample_instruments)
    assert panel.instrument_list.count() == len(sample_instruments)


def test_search_filters_instruments(panel: InstrumentPanel, sample_instruments: list[dict[str, str]]) -> None:
    """
    Проверяет фильтрацию списка по тексту поиска.
    """
    panel.set_instruments(sample_instruments)

    # Фильтр по Si
    panel.search_input.setText("Si")
    assert panel.instrument_list.count() == 1  # Только SiH6

    # Фильтр по H6
    panel.search_input.setText("H6")
    assert panel.instrument_list.count() == 4  # SiH6, AAH6, BRH6, EUGH6


def test_search_case_insensitive(panel: InstrumentPanel, sample_instruments: list[dict[str, str]]) -> None:
    """
    Проверяет, что поиск не зависит от регистра.
    """
    panel.set_instruments(sample_instruments)

    panel.search_input.setText("sber")
    assert panel.instrument_list.count() == 1
    assert "SBER" in panel.instrument_list.item(0).text()


def test_search_clear_returns_all(panel: InstrumentPanel, sample_instruments: list[dict[str, str]]) -> None:
    """
    Проверяет, что очистка поиска возвращает полный список.
    """
    panel.set_instruments(sample_instruments)

    panel.search_input.setText("XYZ")
    assert panel.instrument_list.count() == 0

    panel.search_input.clear()
    assert panel.instrument_list.count() == len(sample_instruments)


def test_empty_instruments_list(panel: InstrumentPanel) -> None:
    """
    Проверяет поведение с пустым списком инструментов.
    """
    panel.set_instruments([])
    assert panel.instrument_list.count() == 0


def test_instrument_selected_signal(qtbot, panel: InstrumentPanel, sample_instruments: list[dict[str, str]]) -> None:
    """
    Проверяет, что при клике на инструмент испускается сигнал.
    """
    panel.set_instruments(sample_instruments)
    panel.show()

    # Ждём сигнал instrument_selected
    with qtbot.waitSignal(panel.instrument_selected) as blocker:
        # Эмулируем двойной клик по первому элементу списка
        item = panel.instrument_list.item(0)
        panel.instrument_list.setCurrentItem(item)
        panel.instrument_list.itemClicked.emit(item)

    # Проверяем аргументы сигнала
    db_path, sec_code = blocker.args
    assert db_path == "futures.db"
    assert sec_code == "SiH6"


def test_search_does_not_affect_data(panel: InstrumentPanel, sample_instruments: list[dict[str, str]]) -> None:
    """
    Проверяет, что фильтр поиска не удаляет данные.
    """
    panel.set_instruments(sample_instruments)

    panel.search_input.setText("AAH6")
    assert panel.instrument_list.count() == 1

    # Очищаем поиск — все инструменты должны вернуться
    panel.search_input.clear()
    assert panel.instrument_list.count() == len(sample_instruments)


def test_instrument_list_item_data(qtbot, panel: InstrumentPanel, sample_instruments: list[dict[str, str]]) -> None:
    """
    Проверяет, что в элементе списка сохранены данные инструмента.
    """
    panel.set_instruments(sample_instruments)

    item = panel.instrument_list.item(0)
    data = item.data(Qt.UserRole)
    assert data["sec_code"] == "SiH6"
    assert data["db_path"] == "futures.db"
    assert data["table"] == "SiH6_M1"


def test_refresh_button_click(panel: InstrumentPanel, qtbot) -> None:
    """
    Проверяет, что нажатие кнопки обновления не вызывает падения.
    """
    try:
        panel.refresh_button.click()
    except Exception as exc:
        pytest.fail(f"Кнопка обновления вызвала исключение: {exc}")
