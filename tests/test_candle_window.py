"""Тесты скользящего окна свечей."""

from datetime import datetime, timedelta

import polars as pl
import pytest

from src.data.resample import TIMEFRAME_MINUTES, resample_candles
from src.gui.main_window import MAX_M1_ROWS_IN_MEMORY, M1_TRIM_TARGET_ROWS, MainWindow


@pytest.fixture
def window(qtbot) -> MainWindow:
    w = MainWindow()
    qtbot.addWidget(w)
    return w


def _make_m1(n: int = 1000) -> pl.DataFrame:
    return pl.DataFrame({
        "date": [datetime(2025, 1, 1, 10, i % 60) for i in range(n)],
        "open": [1.0] * n,
        "high": [2.0] * n,
        "low": [0.5] * n,
        "close": [1.5] * n,
        "volume": [10] * n,
    })


def test_refresh_chart_display_loads_all_data(window: MainWindow) -> None:
    """На график загружаются все ресемплированные свечи."""
    window._current_db_path = "t.db"
    window._current_sec_code = "T"
    window._current_timeframe = "M5"
    window._m1_candles = _make_m1(3000)
    window._refresh_chart_display(refresh_drawings=False, fit=False)
    cached = window.chart_widget._cached_candles
    assert cached is not None
    # Все 3000 M1 -> ~600 M5 свечей
    # 3000 M1 с минутой = i % 60 -> 12 интервалов M5 внутри часа
    assert len(cached) == 12
    assert window._resampled_cache is not None
    assert not window._resampled_cache.is_empty()


def test_refresh_chart_display_skips_no_m1(window: MainWindow) -> None:
    """Без M1 вызов не падает."""
    window._current_db_path = "t.db"
    window._current_sec_code = "T"
    window._current_timeframe = "M5"
    window._m1_candles = None
    window._refresh_chart_display()  # не должно быть ошибки


def test_trim_m1_cache_keeps_center(window: MainWindow) -> None:
    """Обрезка M1 оставляет данные вокруг видимой зоны."""
    window._current_db_path = "t.db"
    window._current_sec_code = "T"
    window._current_timeframe = "M5"
    window._m1_candles = _make_m1(MAX_M1_ROWS_IN_MEMORY + 1000)
    window._resampled_cache = resample_candles(window._m1_candles, "M5")
    n_before = len(window._m1_candles)
    window._trim_m1_cache(bars_before=5000, bars_after=5000)
    assert len(window._m1_candles) < n_before
    assert len(window._m1_candles) <= M1_TRIM_TARGET_ROWS
