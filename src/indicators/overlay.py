"""
Наложенные индикаторы: SMA, EMA, Bollinger Bands.

Рисуются поверх свечного графика (IndicatorType.OVERLAY).
Используют numpy для быстрых векторных вычислений.
"""

from __future__ import annotations

from typing import ClassVar

import polars as pl
import numpy as np

from .base import BaseIndicator, IndicatorResult, IndicatorType


class SMA(BaseIndicator):
    """
    Простое скользящее среднее (Simple Moving Average).

    Рассчитывается как среднее арифметическое цены закрытия за N периодов.

    Параметры:
        period: Количество периодов для расчёта (по умолчанию 20).
    """

    name: ClassVar[str] = "SMA"
    params: ClassVar[dict] = {"period": 20}
    indicator_type: ClassVar[IndicatorType] = IndicatorType.OVERLAY
    min_bars: ClassVar[int] = 2

    def calculate(self, data: pl.DataFrame) -> IndicatorResult:
        """
        Рассчитывает SMA на основе цен закрытия.

        Параметры:
            data: Polars DataFrame с колонками date и close.

        Возвращает:
            IndicatorResult с одним рядом 'sma'.
        """
        self.validate_data(data)
        period: int = int(self._params["period"])

        close: np.ndarray = data["close"].to_numpy()
        sma_values: np.ndarray = self._compute_sma(close, period)

        result_data = pl.DataFrame({
            "date": data["date"],
            "sma": sma_values,
        })

        return IndicatorResult(
            data=result_data,
            series_names={"sma": "#FF9800"},
            overlay=True,
        )

    @staticmethod
    def _compute_sma(values: np.ndarray, period: int) -> np.ndarray:
        """
        Вычисляет SMA с помощью скользящего окна (cumsum).

        Параметры:
            values: Массив цен.
            period: Размер окна.

        Возвращает:
            Массив SMA той же длины с NaN на первых period-1 позициях.
        """
        n: int = len(values)
        result: np.ndarray = np.full(n, np.nan, dtype=np.float64)

        if n < period:
            return result

        cumsum: np.ndarray = np.cumsum(values, dtype=np.float64)
        result[period - 1] = cumsum[period - 1] / period
        for i in range(period, n):
            result[i] = (cumsum[i] - cumsum[i - period]) / period

        return result


class EMA(BaseIndicator):
    """
    Экспоненциальное скользящее среднее (Exponential Moving Average).

    Придаёт больший вес последним ценам.
    Формула: EMA = price * k + EMA_prev * (1 - k), где k = 2 / (period + 1).

    Параметры:
        period: Количество периодов для расчёта (по умолчанию 20).
    """

    name: ClassVar[str] = "EMA"
    params: ClassVar[dict] = {"period": 20}
    indicator_type: ClassVar[IndicatorType] = IndicatorType.OVERLAY
    min_bars: ClassVar[int] = 2

    def calculate(self, data: pl.DataFrame) -> IndicatorResult:
        """
        Рассчитывает EMA на основе цен закрытия.

        Параметры:
            data: Polars DataFrame с колонками date и close.

        Возвращает:
            IndicatorResult с одним рядом 'ema'.
        """
        self.validate_data(data)
        period: int = int(self._params["period"])

        close: np.ndarray = data["close"].to_numpy()
        ema_values: np.ndarray = self._compute_ema(close, period)

        result_data = pl.DataFrame({
            "date": data["date"],
            "ema": ema_values,
        })

        return IndicatorResult(
            data=result_data,
            series_names={"ema": "#26A69A"},
            overlay=True,
        )

    @staticmethod
    def _compute_ema(values: np.ndarray, period: int) -> np.ndarray:
        """
        Вычисляет EMA рекуррентно.

        Параметры:
            values: Массив цен.
            period: Размер окна.

        Возвращает:
            Массив EMA той же длины с NaN на первых period-1 позициях.
        """
        n: int = len(values)
        result: np.ndarray = np.full(n, np.nan, dtype=np.float64)

        if n < period:
            return result

        k: float = 2.0 / (period + 1)

        # Первое значение EMA = SMA за первые period баров
        result[period - 1] = float(np.mean(values[:period]))

        # Рекуррентный расчёт
        for i in range(period, n):
            result[i] = values[i] * k + result[i - 1] * (1.0 - k)

        return result


class BollingerBands(BaseIndicator):
    """
    Полосы Боллинджера (Bollinger Bands).

    Состоят из трёх линий:
    - Средняя линия: SMA за N периодов
    - Верхняя линия: SMA + K * стандартное отклонение
    - Нижняя линия: SMA - K * стандартное отклонение

    Параметры:
        period: Количество периодов для SMA (по умолчанию 20).
        std_dev: Количество стандартных отклонений (по умолчанию 2.0).
    """

    name: ClassVar[str] = "BollingerBands"
    params: ClassVar[dict] = {"period": 20, "std_dev": 2.0}
    indicator_type: ClassVar[IndicatorType] = IndicatorType.OVERLAY
    min_bars: ClassVar[int] = 2

    def calculate(self, data: pl.DataFrame) -> IndicatorResult:
        """
        Рассчитывает полосы Боллинджера.

        Параметры:
            data: Polars DataFrame с колонками date и close.

        Возвращает:
            IndicatorResult с рядами 'bb_upper', 'bb_middle', 'bb_lower'.
        """
        self.validate_data(data)
        period: int = int(self._params["period"])
        std_dev: float = float(self._params["std_dev"])

        close: np.ndarray = data["close"].to_numpy()
        middle, upper, lower = self._compute_bands(close, period, std_dev)

        result_data = pl.DataFrame({
            "date": data["date"],
            "bb_upper": upper,
            "bb_middle": middle,
            "bb_lower": lower,
        })

        return IndicatorResult(
            data=result_data,
            series_names={
                "bb_upper": "#EF5350",
                "bb_middle": "#42A5F5",
                "bb_lower": "#EF5350",
            },
            overlay=True,
        )

    @staticmethod
    def _compute_bands(
        values: np.ndarray, period: int, std_dev: float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Вычисляет три линии полос Боллинджера.

        Параметры:
            values: Массив цен.
            period: Размер окна SMA.
            std_dev: Количество стандартных отклонений.

        Возвращает:
            Кортеж (middle, upper, lower).
        """
        n: int = len(values)
        middle: np.ndarray = np.full(n, np.nan, dtype=np.float64)
        upper: np.ndarray = np.full(n, np.nan, dtype=np.float64)
        lower: np.ndarray = np.full(n, np.nan, dtype=np.float64)

        if n < period:
            return middle, upper, lower

        # SMA как средняя линия
        middle = SMA._compute_sma(values, period)

        # Стандартное отклонение и полосы
        for i in range(period - 1, n):
            window: np.ndarray = values[i - period + 1:i + 1]
            std: float = float(np.std(window, ddof=0))
            middle_val = float(middle[i])
            upper[i] = middle_val + std_dev * std
            lower[i] = middle_val - std_dev * std

        return middle, upper, lower
