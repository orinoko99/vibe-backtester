"""
Тесты для модуля индикаторов.

Проверяют:
- SMA, EMA, RSI, MACD, Bollinger Bands, Stochastic
- Корректность расчётов
- Обработку крайних случаев
"""

import numpy as np
import pandas as pd
import pytest

from src.indicators.base import (
    SMA,
    EMA,
    RSI,
    MACD,
    BollingerBands,
    Stochastic,
)


@pytest.fixture
def восходящие_данные():
    """Восходящий тренд: 100 значений, рост с 100 до 150."""
    цены = np.linspace(100.0, 150.0, 100) + np.random.randn(100) * 2
    return pd.Series(цены, name="close")


@pytest.fixture
def данные_20_значений():
    """Ровно 20 значений для проверки границ."""
    return pd.Series([
        100.0, 101.0, 102.0, 103.0, 104.0,
        105.0, 106.0, 107.0, 108.0, 109.0,
        110.0, 111.0, 112.0, 113.0, 114.0,
        115.0, 116.0, 117.0, 118.0, 119.0,
    ], name="close")


@pytest.fixture
def постоянные_данные():
    """Постоянные цены (проверка RSI и MACD)."""
    return pd.Series([100.0] * 50, name="close")


@pytest.fixture
def данные_ohlc():
    """OHLC данные для Stochastic."""
    n = 50
    цены = 100.0 + np.cumsum(np.random.randn(n) * 0.5)
    цены = np.maximum(цены, 1.0)
    return (
        pd.Series(цены + 0.5, name="high"),
        pd.Series(цены - 0.5, name="low"),
        pd.Series(цены, name="close"),
    )


# ====================
# Тесты SMA
# ====================

class TestSMA:
    def test_создание(self):
        sma = SMA(20)
        assert sma.период == 20
        assert sma.название == "SMA(20)"

    def test_некорректный_период(self):
        with pytest.raises(ValueError, match=">= 1"):
            SMA(0)

    def test_расчёт_возвращает_series(self, восходящие_данные):
        sma = SMA(20)
        результат = sma.рассчитать(восходящие_данные)
        assert isinstance(результат, pd.Series)
        assert len(результат) == len(восходящие_данные)

    def test_первые_nan(self, восходящие_данные):
        sma = SMA(20)
        результат = sma.рассчитать(восходящие_данные)
        assert pd.isna(результат.iloc[0])
        assert not pd.isna(результат.iloc[20])

    def test_значение_sma_20(self, данные_20_значений):
        """SMA(20) на 20 значениях = среднее арифметическое."""
        sma = SMA(20)
        результат = sma.рассчитать(данные_20_значений)
        expected = данные_20_значений.mean()
        assert float(результат.iloc[-1]) == pytest.approx(expected, rel=1e-3)

    def test_sma_1_равно_цене(self, восходящие_данные):
        """SMA(1) должна быть равна исходному ряду."""
        sma = SMA(1)
        результат = sma.рассчитать(восходящие_данные)
        pd.testing.assert_series_equal(
            результат.fillna(0), восходящие_данные.fillna(0)
        )


# ====================
# Тесты EMA
# ====================

class TestEMA:
    def test_создание(self):
        ema = EMA(14)
        assert ema.период == 14
        assert ema.название == "EMA(14)"

    def test_некорректный_период(self):
        with pytest.raises(ValueError, match=">= 1"):
            EMA(0)

    def test_расчёт(self, восходящие_данные):
        ema = EMA(20)
        результат = ema.рассчитать(восходящие_данные)
        assert isinstance(результат, pd.Series)
        assert len(результат) == len(восходящие_данные)

    def test_ema_1_равно_цене(self, восходящие_данные):
        """EMA(1) должна быть равна исходному ряду."""
        ema = EMA(1)
        результат = ema.рассчитать(восходящие_данные)
        pd.testing.assert_series_equal(
            результат.fillna(0), восходящие_данные.fillna(0)
        )


# ====================
# Тесты RSI
# ====================

class TestRSI:
    def test_создание(self):
        rsi = RSI(14)
        assert rsi.период == 14
        assert rsi.название == "RSI(14)"

    def test_некорректный_период(self):
        with pytest.raises(ValueError, match=">= 1"):
            RSI(0)

    def test_расчёт(self, восходящие_данные):
        rsi = RSI(14)
        результат = rsi.рассчитать(восходящие_данные)
        assert isinstance(результат, pd.Series)

    def test_rsi_в_диапазоне(self, восходящие_данные):
        """RSI должен быть между 0 и 100."""
        rsi = RSI(14)
        результат = rsi.рассчитать(восходящие_данные)
        валидные = результат.dropna()
        assert (валидные >= 0).all()
        assert (валидные <= 100).all()

    def test_rsi_на_восходящем_тренде(self, восходящие_данные):
        """На восходящем тренде RSI должен быть > 50."""
        rsi = RSI(14)
        результат = rsi.рассчитать(восходящие_данные)
        средний_rsi = результат.dropna().mean()
        assert средний_rsi > 50

    def test_rsi_на_постоянных_данных(self, постоянные_данные):
        """На постоянных данных RSI должен быть 50 (или NaN)."""
        rsi = RSI(14)
        результат = rsi.рассчитать(постоянные_данные)
        # Если нет изменений, RSI может быть NaN или 50
        валидные = результат.dropna()
        if len(валидные) > 0:
            assert all(abs(в - 50) < 1e-6 for в in валидные)


# ====================
# Тесты MACD
# ====================

class TestMACD:
    def test_создание(self):
        macd = MACD()
        assert macd.название == "MACD(12,26,9)"

    def test_некорректные_периоды(self):
        with pytest.raises(ValueError, match=">= 1"):
            MACD(период_быстрый=0)

    def test_расчёт_возвращает_dataframe(self, восходящие_данные):
        macd = MACD()
        результат = macd.рассчитать(восходящие_данные)
        assert isinstance(результат, pd.DataFrame)
        assert list(результат.columns) == ["macd", "сигнал", "гистограмма"]

    def test_длины_совпадают(self, восходящие_данные):
        macd = MACD()
        результат = macd.рассчитать(восходящие_данные)
        assert len(результат) == len(восходящие_данные)

    def test_гистограмма_разность_macd_и_сигнала(self, восходящие_данные):
        """Гистограмма должна быть разностью MACD и сигнальной линии."""
        macd = MACD()
        результат = macd.рассчитать(восходящие_данные)
        разность = результат["гистограмма"] - (
            результат["macd"] - результат["сигнал"]
        )
        assert все_близки_к_нулю(разность.dropna())

    def test_macd_на_постоянных_данных(self, постоянные_данные):
        """На постоянных данных MACD гистограмма = 0."""
        macd = MACD()
        результат = macd.рассчитать(постоянные_данные)
        гист = результат["гистограмма"].dropna()
        if len(гист) > 0:
            assert all(abs(г) < 1e-6 for г in гист)


# ====================
# Тесты Bollinger Bands
# ====================

class TestBollingerBands:
    def test_создание(self):
        bb = BollingerBands()
        assert bb.название == "BB(20,2)"

    def test_некорректные_параметры(self):
        with pytest.raises(ValueError, match=">= 1"):
            BollingerBands(период=0)
        with pytest.raises(ValueError, match="> 0"):
            BollingerBands(множитель=0)

    def test_расчёт(self, восходящие_данные):
        bb = BollingerBands()
        результат = bb.рассчитать(восходящие_данные)
        assert isinstance(результат, pd.DataFrame)
        assert list(результат.columns) == ["средняя", "верхняя", "нижняя"]

    def test_верхняя_выше_средней(self, восходящие_данные):
        """Верхняя полоса должна быть выше средней."""
        bb = BollingerBands()
        результат = bb.рассчитать(восходящие_данные)
        assert (результат["верхняя"].dropna() >= результат["средняя"].dropna()).all()

    def test_нижняя_ниже_средней(self, восходящие_данные):
        """Нижняя полоса должна быть ниже средней."""
        bb = BollingerBands()
        результат = bb.рассчитать(восходящие_данные)
        assert (результат["нижняя"].dropna() <= результат["средняя"].dropna()).all()

    def test_полосы_шире_при_большем_множителе(self, данные_20_значений):
        """Больший множитель -> более широкие полосы."""
        bb1 = BollingerBands(период=5, множитель=1)
        bb2 = BollingerBands(период=5, множитель=3)
        r1 = bb1.рассчитать(данные_20_значений)
        r2 = bb2.рассчитать(данные_20_значений)
        ширина1 = (r1["верхняя"] - r1["нижняя"]).dropna()
        ширина2 = (r2["верхняя"] - r2["нижняя"]).dropna()
        assert (ширина2 > ширина1).all()


# ====================
# Тесты Stochastic
# ====================

class TestStochastic:
    def test_создание(self):
        stoch = Stochastic()
        assert stoch.название == "Stoch(14,3)"

    def test_некорректные_периоды(self):
        with pytest.raises(ValueError, match=">= 1"):
            Stochastic(период_k=0)

    def test_расчёт(self, данные_ohlc):
        high, low, close = данные_ohlc
        stoch = Stochastic()
        результат = stoch.рассчитать(high, low, close)
        assert isinstance(результат, pd.DataFrame)
        assert list(результат.columns) == ["k", "d"]

    def test_значения_в_диапазоне(self, данные_ohlc):
        """%K и %D должны быть между 0 и 100."""
        high, low, close = данные_ohlc
        stoch = Stochastic()
        результат = stoch.рассчитать(high, low, close)
        for колонка in ["k", "d"]:
            валидные = результат[колонка].dropna()
            assert (валидные >= 0).all(), f"{колонка} имеет значения < 0"
            assert (валидные <= 100).all(), f"{колонка} имеет значения > 100"


# ====================
# Вспомогательные функции
# ====================

def все_близки_к_нулю(series: pd.Series, eps: float = 1e-6) -> bool:
    """Проверяет, что все значения ряда близки к нулю."""
    if len(series) == 0:
        return True
    return bool((abs(series) < eps).all())
