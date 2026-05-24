from __future__ import annotations

import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Generator
import sqlite3

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.database import DatabaseManager
from src.gui.instrument_panel import InstrumentPanel


@pytest.fixture(scope="module")
def app() -> QApplication:
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def temp_db_path() -> Generator[Path, None, None]:
    with NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    conn = sqlite3.connect(str(tmp_path))
    conn.execute(
        "CREATE TABLE 'AAH6_M1' ("
        "ID INTEGER PRIMARY KEY, "
        "Date TEXT, SecCode TEXT, ClassCode TEXT, "
        "O TEXT, H TEXT, L TEXT, C TEXT, "
        "V INTEGER, OpenInterest INTEGER)"
    )
    conn.execute(
        "CREATE TABLE 'SiH6_M1' ("
        "ID INTEGER PRIMARY KEY, "
        "Date TEXT, SecCode TEXT, ClassCode TEXT, "
        "O TEXT, H TEXT, L TEXT, C TEXT, "
        "V INTEGER, OpenInterest INTEGER)"
    )
    conn.execute(
        "CREATE TABLE 'GAZP_M5' ("
        "ID INTEGER PRIMARY KEY, "
        "Date TEXT, SecCode TEXT, ClassCode TEXT, "
        "O TEXT, H TEXT, L TEXT, C TEXT, "
        "V INTEGER, OpenInterest INTEGER)"
    )

    test_data = [
        (1, "2025-10-28 18:32:00", "AAH6", "SPBFUT", "65.91", "66.22", "65.91", "66.22", 2, 0),
        (2, "2025-10-28 19:07:00", "AAH6", "SPBFUT", "64.35", "64.35", "64.35", "64.35", 1, 0),
    ]
    conn.executemany(
        "INSERT INTO 'AAH6_M1' (ID, Date, SecCode, ClassCode, O, H, L, C, V, OpenInterest) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        test_data,
    )
    conn.commit()
    conn.close()
    yield tmp_path
    tmp_path.unlink(missing_ok=True)


@pytest.fixture
def db_manager(temp_db_path: Path) -> DatabaseManager:
    dm = DatabaseManager(
        futures_paths=(temp_db_path,),
        shares_paths=(),
    )
    return dm


@pytest.fixture
def panel(app: QApplication, db_manager: DatabaseManager) -> Generator[InstrumentPanel, None, None]:
    p = InstrumentPanel(
        db_manager=db_manager,
        parent=None,
    )
    yield p
    p.deleteLater()


class TestInstrumentPanelCreation:
    def test_panel_created(self, panel: InstrumentPanel) -> None:
        assert panel is not None
        assert isinstance(panel, QWidget)

    def test_panel_has_list_widget(self, panel: InstrumentPanel) -> None:
        assert hasattr(panel, "_list_widget")
        assert panel._list_widget is not None

    def test_panel_has_search_input(self, panel: InstrumentPanel) -> None:
        assert hasattr(panel, "_search_input")
        assert panel._search_input is not None

    def test_panel_has_load_button(self, panel: InstrumentPanel) -> None:
        assert hasattr(panel, "_load_button")
        assert panel._load_button is not None
        assert not panel._load_button.isEnabled()


class TestInstrumentPanelLoading:
    def test_instruments_loaded_from_db(
        self, panel: InstrumentPanel
    ) -> None:
        assert len(panel._instruments) == 3  # AAH6, GAZP, SiH6
        assert "AAH6" in panel._instruments
        assert "SiH6" in panel._instruments
        assert "GAZP" in panel._instruments

    def test_list_widget_populated(self, panel: InstrumentPanel) -> None:
        assert panel._list_widget.count() == 3

    def test_list_items_text(self, panel: InstrumentPanel) -> None:
        items = [
            panel._list_widget.item(i).text()
            for i in range(panel._list_widget.count())
        ]
        assert "AAH6" in items
        assert "SiH6" in items
        assert "GAZP" in items


class TestInstrumentPanelFiltering:
    def test_filter_show_all_by_default(
        self, panel: InstrumentPanel
    ) -> None:
        assert panel._list_widget.count() == 3

    def test_filter_empty_gives_all(
        self, panel: InstrumentPanel
    ) -> None:
        panel._search_input.setText("")
        panel._filter_instruments("")
        assert panel._list_widget.count() == 3

    def test_filter_by_partial_code(
        self, panel: InstrumentPanel
    ) -> None:
        panel._search_input.setText("AA")
        panel._filter_instruments("AA")
        assert panel._list_widget.count() == 1
        assert panel._list_widget.item(0).text() == "AAH6"

    def test_filter_case_insensitive(
        self, panel: InstrumentPanel
    ) -> None:
        panel._search_input.setText("aah")
        panel._filter_instruments("aah")
        assert panel._list_widget.count() == 1
        assert panel._list_widget.item(0).text() == "AAH6"

    def test_filter_no_matches(self, panel: InstrumentPanel) -> None:
        panel._search_input.setText("ZZZZ")
        panel._filter_instruments("ZZZZ")
        assert panel._list_widget.count() == 0

    def test_filter_restores_after_clear(
        self, panel: InstrumentPanel
    ) -> None:
        panel._search_input.setText("ZZZZ")
        panel._filter_instruments("ZZZZ")
        assert panel._list_widget.count() == 0
        panel._search_input.setText("")
        panel._filter_instruments("")
        assert panel._list_widget.count() == 3


class TestInstrumentPanelSelection:
    def test_load_button_disabled_initially(
        self, panel: InstrumentPanel
    ) -> None:
        assert not panel._load_button.isEnabled()

    def test_select_item_enables_load_button(
        self, panel: InstrumentPanel
    ) -> None:
        item = panel._list_widget.item(0)
        panel._list_widget.setCurrentItem(item)
        panel._on_item_clicked(item)
        assert panel._load_button.isEnabled()
        assert hasattr(panel, "_selected_sec_code")
        assert panel._selected_sec_code == item.text()

    def test_load_button_emits_signal(
        self, panel: InstrumentPanel
    ) -> None:
        emitted_codes: list[str] = []

        def handler(code: str) -> None:
            emitted_codes.append(code)

        panel.instrument_selected.connect(handler)
        item = panel._list_widget.item(0)
        panel._list_widget.setCurrentItem(item)
        panel._on_item_clicked(item)
        panel._on_load_clicked()
        assert len(emitted_codes) == 1
        assert emitted_codes[0] == item.text()

    def test_different_selection_different_signal(
        self, panel: InstrumentPanel
    ) -> None:
        emitted_codes: list[str] = []

        def handler(code: str) -> None:
            emitted_codes.append(code)

        panel.instrument_selected.connect(handler)

        # Выбираем первый
        item0 = panel._list_widget.item(0)
        panel._list_widget.setCurrentItem(item0)
        panel._on_item_clicked(item0)
        panel._on_load_clicked()
        assert emitted_codes[-1] == item0.text()

        # Выбираем второй
        item1 = panel._list_widget.item(1)
        panel._list_widget.setCurrentItem(item1)
        panel._on_item_clicked(item1)
        panel._on_load_clicked()
        assert emitted_codes[-1] == item1.text()
        assert len(emitted_codes) == 2


class TestInstrumentPanelSignal:
    def test_signal_is_pyqt_signal(self, panel: InstrumentPanel) -> None:
        from PySide6.QtCore import SignalInstance
        assert isinstance(
            panel.instrument_selected, SignalInstance
        )

    def test_signal_connected_when_wired(
        self, panel: InstrumentPanel
    ) -> None:
        called = False

        def handler(code: str) -> None:
            nonlocal called
            called = True

        panel.instrument_selected.connect(handler)
        panel.instrument_selected.emit("TEST")
        assert called


class TestInstrumentPanelRefresh:
    def test_refresh_reloads_instruments(
        self, panel: InstrumentPanel,
        db_manager: DatabaseManager,
        temp_db_path: Path,
    ) -> None:
        assert len(panel._instruments) == 3
        # Добавляем новый инструмент напрямую в БД
        conn = sqlite3.connect(str(temp_db_path))
        conn.execute(
            "CREATE TABLE 'NEW_M1' ("
            "ID INTEGER PRIMARY KEY, "
            "Date TEXT, SecCode TEXT, ClassCode TEXT, "
            "O TEXT, H TEXT, L TEXT, C TEXT, "
            "V INTEGER, OpenInterest INTEGER)"
        )
        conn.commit()
        conn.close()

        panel.refresh()
        assert len(panel._instruments) == 4
        assert "NEW" in panel._instruments
