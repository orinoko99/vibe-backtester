"""Тесты агрегации минутных свечей в старшие таймфреймы."""

from datetime import datetime

import polars as pl

from src.data.resample import resample_candles


def _sample_m1(n: int = 10) -> pl.DataFrame:
    dates = [
        datetime(2025, 1, 1, 10, i) for i in range(n)
    ]
    return pl.DataFrame({
        "date": dates,
        "open": [100.0 + i for i in range(n)],
        "high": [101.0 + i for i in range(n)],
        "low": [99.0 + i for i in range(n)],
        "close": [100.5 + i for i in range(n)],
        "volume": [10] * n,
    })


def test_resample_m1_unchanged() -> None:
    df = _sample_m1(5)
    out = resample_candles(df, "M1")
    assert len(out) == 5


def test_resample_m5_reduces_bars() -> None:
    df = _sample_m1(10)
    out = resample_candles(df, "M5")
    assert len(out) <= len(df)
    assert len(out) >= 2


def test_resample_ohlc_logic() -> None:
    """Проверяет open=first, close=last, high=max, low=min в одном интервале M5."""
    df = pl.DataFrame({
        "date": [
            datetime(2025, 1, 1, 10, 0),
            datetime(2025, 1, 1, 10, 1),
            datetime(2025, 1, 1, 10, 2),
            datetime(2025, 1, 1, 10, 3),
            datetime(2025, 1, 1, 10, 4),
        ],
        "open": [10.0, 11.0, 12.0, 13.0, 14.0],
        "high": [15.0, 16.0, 17.0, 18.0, 19.0],
        "low": [5.0, 6.0, 7.0, 8.0, 9.0],
        "close": [10.5, 11.5, 12.5, 13.5, 14.5],
        "volume": [1, 2, 3, 4, 5],
    })
    out = resample_candles(df, "M5")
    assert len(out) == 1
    row = out.row(0, named=True)
    assert row["open"] == 10.0
    assert row["close"] == 14.5
    assert row["high"] == 19.0
    assert row["low"] == 5.0
    assert row["volume"] == 15


def test_resample_empty() -> None:
    empty = pl.DataFrame({
        "date": [], "open": [], "high": [], "low": [], "close": [],
    })
    assert resample_candles(empty, "M5").is_empty()
