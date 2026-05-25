"""
Осцилляторы: RSI, MACD.

Рисуются на отдельной панели под свечным графиком (IndicatorType.OSCILLATOR).
Используют numpy для векторных вычислений.
"""

from __future__ import annotations

from typing import ClassVar

import polars as pl
import numpy as np

from .base import BaseIndicator, IndicatorResult, IndicatorType
from .overlay import EMA  # для расчёта MACD


class RSI(BaseIndicator):
    """
    Индекс относительной силы (Relative Strength Index).

    Измеряет скорость и изменение ценовых движений.
    Значения выше 70 считаются перекупленностью, ниже 30 — перепроданностью.

    Формула:
        RSI = 100 - (100 / (1 + RS))
        RS = средний_прирост / средняя_потеря

    Параметры:
        period: Количество периодов для расчёта (по умолчанию 14).
    """

    name: ClassVar[str] = "RSI"
    params: ClassVar[dict] = {"period": 14}
    indicator_type: ClassVar[IndicatorType] = IndicatorType.OSCILLATOR
    min_bars: ClassVar[int] = 2

    def calculate(self, data: pl.DataFrame) -> IndicatorResult:
        """
        Рассчитывает RSI на основе цен закрытия.

        Параметры:
            data: Polars DataFrame с колонками date и close.

        Возвращает:
            IndicatorResult с рядом 'rsi' (0-100).
        """
        self.validate_data(data)
        period: int = int(self._params["period"])

        close: np.ndarray = data["close"].to_numpy()
        rsi_values: np.ndarray = self._compute_rsi(close, period)

        result_data = pl.DataFrame({
            "date": data["date"],
            "rsi": rsi_values,
        })

        return IndicatorResult(
            data=result_data,
            series_names={"rsi": "#7B1FA2"},
            panel="rsi",
            overlay=False,
        )

    @staticmethod
    def _compute_rsi(values: np.ndarray, period: int) -> np.ndarray:
        """
        Вычисляет RSI с использованием EMA для сглаживания приростов/потерь.

        Параметры:
            values: Массив цен закрытия.
            period: Период RSI.

        Возвращает:
            Массив RSI (0-100) с NaN на первых period позициях.
        """
        n: int = len(values)
        result: np.ndarray = np.full(n, np.nan, dtype=np.float64)

        if n < period + 1:
            return result

        # Разницы между последовательными ценами
        deltas: np.ndarray = np.diff(values)

        # Приросты (положительные изменения) и потери (отрицательные, взятые по модулю)
        gains: np.ndarray = np.where(deltas > 0, deltas, 0.0).astype(np.float64)
        losses: np.ndarray = np.where(deltas < 0, -deltas, 0.0).astype(np.float64)

        # Первые средние — простые средние за period баров
        avg_gain: float = float(np.mean(gains[:period]))
        avg_loss: float = float(np.mean(losses[:period]))

        if avg_loss == 0.0:
            result[period] = 100.0
        else:
            rs: float = avg_gain / avg_loss
            result[period] = 100.0 - 100.0 / (1.0 + rs)

        # Рекуррентный расчёт для остальных баров (сглаживание Wilder)
        k: float = 1.0 / period
        for i in range(period + 1, n):
            avg_gain = gains[i - 1] * k + avg_gain * (1.0 - k)
            avg_loss = losses[i - 1] * k + avg_loss * (1.0 - k)

            if avg_loss == 0.0:
                result[i] = 100.0
            else:
                rs = avg_gain / avg_loss
                result[i] = 100.0 - 100.0 / (1.0 + rs)

        return result


class MACD(BaseIndicator):
    """
    Схождение/расхождение скользящих средних (MACD).

    Состоит из трёх линий:
    - MACD line: EMA(12) - EMA(26)
    - Signal line: EMA(9) от MACD line
    - Histogram: MACD line - Signal line

    Параметры:
        fast_period: Период быстрой EMA (по умолчанию 12).
        slow_period: Период медленной EMA (по умолчанию 26).
        signal_period: Период сигнальной линии (по умолчанию 9).
    """

    name: ClassVar[str] = "MACD"
    params: ClassVar[dict] = {
        "fast_period": 12,
        "slow_period": 26,
        "signal_period": 9,
    }
    indicator_type: ClassVar[IndicatorType] = IndicatorType.OSCILLATOR
    min_bars: ClassVar[int] = 2

    def calculate(self, data: pl.DataFrame) -> IndicatorResult:
        """
        Рассчитывает MACD на основе цен закрытия.

        Параметры:
            data: Polars DataFrame с колонками date и close.

        Возвращает:
            IndicatorResult с рядами 'macd', 'signal', 'histogram'.
        """
        self.validate_data(data)

        fast_period: int = int(self._params["fast_period"])
        slow_period: int = int(self._params["slow_period"])
        signal_period: int = int(self._params["signal_period"])

        close: np.ndarray = data["close"].to_numpy()
        macd_line, signal_line, histogram = self._compute_macd(
            close, fast_period, slow_period, signal_period,
        )

        result_data = pl.DataFrame({
            "date": data["date"],
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram,
        })

        return IndicatorResult(
            data=result_data,
            series_names={
                "macd": "#2962FF",
                "signal": "#FF6D00",
                "histogram": "#4CAF50",
            },
            panel="macd",
            overlay=False,
        )

    @staticmethod
    def _compute_macd(
        values: np.ndarray,
        fast_period: int,
        slow_period: int,
        signal_period: int,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Вычисляет все три линии MACD.

        Параметры:
            values: Массив цен закрытия.
            fast_period: Период быстрой EMA.
            slow_period: Период медленной EMA.
            signal_period: Период сигнальной линии.

        Возвращает:
            Кортеж (macd_line, signal_line, histogram).
        """
        n: int = len(values)
        macd_line: np.ndarray = np.full(n, np.nan, dtype=np.float64)
        signal_line: np.ndarray = np.full(n, np.nan, dtype=np.float64)
        histogram: np.ndarray = np.full(n, np.nan, dtype=np.float64)

        if n < slow_period:
            return macd_line, signal_line, histogram

        # Рассчитываем быструю и медленную EMA
        fast_ema: np.ndarray = EMA._compute_ema(values, fast_period)
        slow_ema: np.ndarray = EMA._compute_ema(values, slow_period)

        # MACD line = fast_ema - slow_ema (начиная с slow_period - 1)
        for i in range(slow_period - 1, n):
            if not (np.isnan(fast_ema[i]) or np.isnan(slow_ema[i])):
                macd_line[i] = fast_ema[i] - slow_ema[i]

        # Signal line = EMA(MACD, signal_period)
        macd_valid: np.ndarray = macd_line[slow_period - 1:]
        signal_valid: np.ndarray = EMA._compute_ema(macd_valid, signal_period)
        for i in range(len(signal_valid)):
            if not np.isnan(signal_valid[i]):
                signal_line[slow_period - 1 + i] = signal_valid[i]

        # Histogram = MACD line - Signal line
        for i in range(n):
            if not (np.isnan(macd_line[i]) or np.isnan(signal_line[i])):
                histogram[i] = macd_line[i] - signal_line[i]

        return macd_line, signal_line, histogram
