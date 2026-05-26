"""
Агрегация минутных свечей (M1) в старшие таймфреймы.

В БД хранятся только M1; M5, H1 и т.д. строятся программно из минутных данных.
"""

from __future__ import annotations

import polars as pl

# Минут в одной свече таймфрейма
TIMEFRAME_MINUTES: dict[str, int] = {
    "M1": 1,
    "M5": 5,
    "M10": 10,
    "M15": 15,
    "M30": 30,
    "H1": 60,
    "H4": 240,
    "D1": 1440,
}


def resample_candles(df: pl.DataFrame, timeframe: str) -> pl.DataFrame:
    """
    Пересчитывает OHLCV из минутных свечей в указанный таймфрейм.

    Параметры:
        df: DataFrame с колонкой date и OHLCV (минутные данные).
        timeframe: Целевой таймфрейм (M1, M5, H1, ...).

    Возвращает:
        DataFrame с теми же колонками, агрегированный по интервалу.
    """
    if df.is_empty():
        return df

    minutes = TIMEFRAME_MINUTES.get(timeframe, 1)
    if minutes <= 1:
        return df.sort("date")

    sorted_df = df.sort("date")

    # Базовые агрегаты OHLCV
    agg: list[pl.Expr] = [
        pl.col("open").first().alias("open"),
        pl.col("high").max().alias("high"),
        pl.col("low").min().alias("low"),
        pl.col("close").last().alias("close"),
    ]
    if "volume" in sorted_df.columns:
        agg.append(pl.col("volume").sum().alias("volume"))
    if "open_interest" in sorted_df.columns:
        agg.append(pl.col("open_interest").last().alias("open_interest"))
    if "id" in sorted_df.columns:
        agg.append(pl.col("id").first().alias("id"))
    if "sec_code" in sorted_df.columns:
        agg.append(pl.col("sec_code").first().alias("sec_code"))
    if "class_code" in sorted_df.columns:
        agg.append(pl.col("class_code").first().alias("class_code"))

    resampled = sorted_df.group_by_dynamic(
        "date",
        every=f"{minutes}m",
        closed="left",
        label="left",
    ).agg(agg)

    return resampled.sort("date")
