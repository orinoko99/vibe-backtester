"""
Модуль базовых технических индикаторов.

Реализует:
- SMA (Simple Moving Average)
- EMA (Exponential Moving Average)
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
"""

from typing import Optional

import numpy as np
import pandas as pd


class SMA:
    """
    Простая скользящая средняя (Simple Moving Average).

    Параметры
    ----------
    период : int
        Период расчёта SMA (по умолчанию 20).
    """

    def __init__(self, период: int = 20) -> None:
        if период < 1:
            raise ValueError(f"Период SMA должен быть >= 1, получен {период}")
        self.период = период
        self.название = f"SMA({период})"

    def рассчитать(self, данные: pd.Series) -> pd.Series:
        """
        Рассчитывает SMA для указанного ряда данных.

        Параметры
        ----------
        данные : pd.Series
            Временной ряд цен (close).

        Возвращает
        -------
        pd.Series
            SMA с NaN в начале (период-1 первых значений).
        """
        return данные.rolling(window=self.период).mean()


class EMA:
    """
    Экспоненциальная скользящая средняя (Exponential Moving Average).

    Параметры
    ----------
    период : int
        Период расчёта EMA (по умолчанию 20).
    """

    def __init__(self, период: int = 20) -> None:
        if период < 1:
            raise ValueError(f"Период EMA должен быть >= 1, получен {период}")
        self.период = период
        self.название = f"EMA({период})"

    def рассчитать(self, данные: pd.Series) -> pd.Series:
        """
        Рассчитывает EMA для указанного ряда данных.

        Параметры
        ----------
        данные : pd.Series
            Временной ряд цен (close).

        Возвращает
        -------
        pd.Series
            EMA.
        """
        return данные.ewm(span=self.период, adjust=False).mean()


class RSI:
    """
    Индекс относительной силы (Relative Strength Index).

    Параметры
    ----------
    период : int
        Период расчёта RSI (по умолчанию 14).
    """

    def __init__(self, период: int = 14) -> None:
        if период < 1:
            raise ValueError(f"Период RSI должен быть >= 1, получен {период}")
        self.период = период
        self.название = f"RSI({период})"

    def рассчитать(self, данные: pd.Series) -> pd.Series:
        """
        Рассчитывает RSI для указанного ряда данных.

        Параметры
        ----------
        данные : pd.Series
            Временной ряд цен (close).

        Возвращает
        -------
        pd.Series
            RSI (0-100).
        """
        дельта = данные.diff()
        прибыль = дельта.clip(lower=0)
        убыток = (-дельта).clip(lower=0)

        средняя_прибыль = прибыль.rolling(window=self.период).mean()
        средний_убыток = убыток.rolling(window=self.период).mean()

        rs = средняя_прибыль / средний_убыток.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi


class MACD:
    """
    Схождение/расхождение скользящих средних (MACD).

    Параметры
    ----------
    период_быстрый : int
        Период быстрой EMA (по умолчанию 12).
    период_медленный : int
        Период медленной EMA (по умолчанию 26).
    период_сигнальный : int
        Период сигнальной линии (по умолчанию 9).
    """

    def __init__(
        self,
        период_быстрый: int = 12,
        период_медленный: int = 26,
        период_сигнальный: int = 9,
    ) -> None:
        if период_быстрый < 1 or период_медленный < 1 or период_сигнальный < 1:
            raise ValueError("Все периоды MACD должны быть >= 1")
        self.период_быстрый = период_быстрый
        self.период_медленный = период_медленный
        self.период_сигнальный = период_сигнальный
        self.название = f"MACD({период_быстрый},{период_медленный},{период_сигнальный})"

    def рассчитать(self, данные: pd.Series) -> pd.DataFrame:
        """
        Рассчитывает MACD: линию MACD, сигнальную линию и гистограмму.

        Параметры
        ----------
        данные : pd.Series
            Временной ряд цен (close).

        Возвращает
        -------
        pd.DataFrame
            С колонками: macd, сигнал, гистограмма.
        """
        ema_быстрый = данные.ewm(span=self.период_быстрый, adjust=False).mean()
        ema_медленный = данные.ewm(span=self.период_медленный, adjust=False).mean()

        macd_линия = ema_быстрый - ema_медленный
        сигнал = macd_линия.ewm(span=self.период_сигнальный, adjust=False).mean()
        гистограмма = macd_линия - сигнал

        return pd.DataFrame({
            "macd": macd_линия,
            "сигнал": сигнал,
            "гистограмма": гистограмма,
        })


class BollingerBands:
    """
    Полосы Боллинджера (Bollinger Bands).

    Параметры
    ----------
    период : int
        Период расчёта средней (по умолчанию 20).
    множитель : float
        Количество стандартных отклонений (по умолчанию 2.0).
    """

    def __init__(self, период: int = 20, множитель: float = 2.0) -> None:
        if период < 1:
            raise ValueError(f"Период Bollinger Bands должен быть >= 1, получен {период}")
        if множитель <= 0:
            raise ValueError(f"Множитель Bollinger Bands должен быть > 0, получен {множитель}")
        self.период = период
        self.множитель = множитель
        self.название = f"BB({период},{множитель:g})"

    def рассчитать(self, данные: pd.Series) -> pd.DataFrame:
        """
        Рассчитывает полосы Боллинджера.

        Параметры
        ----------
        данные : pd.Series
            Временной ряд цен (close).

        Возвращает
        -------
        pd.DataFrame
            С колонками: средняя, верхняя, нижняя.
        """
        средняя = данные.rolling(window=self.период).mean()
        std = данные.rolling(window=self.период).std()
        верхняя = средняя + self.множитель * std
        нижняя = средняя - self.множитель * std

        return pd.DataFrame({
            "средняя": средняя,
            "верхняя": верхняя,
            "нижняя": нижняя,
        })


class Stochastic:
    """
    Стохастический осциллятор (Stochastic Oscillator).

    Параметры
    ----------
    период_k : int
        Период %K (по умолчанию 14).
    период_d : int
        Период %D (по умолчанию 3).
    """

    def __init__(self, период_k: int = 14, период_d: int = 3) -> None:
        if период_k < 1 or период_d < 1:
            raise ValueError("Все периоды Stochastic должны быть >= 1")
        self.период_k = период_k
        self.период_d = период_d
        self.название = f"Stoch({период_k},{период_d})"

    def рассчитать(
        self, high: pd.Series, low: pd.Series, close: pd.Series
    ) -> pd.DataFrame:
        """
        Рассчитывает стохастический осциллятор.

        Параметры
        ----------
        high : pd.Series
            Максимальные цены.
        low : pd.Series
            Минимальные цены.
        close : pd.Series
            Цены закрытия.

        Возвращает
        -------
        pd.DataFrame
            С колонками: k, d.
        """
        низкий_минимум = low.rolling(window=self.период_k).min()
        высокий_максимум = high.rolling(window=self.период_k).max()

        k = 100 * (close - низкий_минимум) / (
            высокий_максимум - низкий_минимум
        ).replace(0, np.nan)
        d = k.rolling(window=self.период_d).mean()

        return pd.DataFrame({"k": k, "d": d})
