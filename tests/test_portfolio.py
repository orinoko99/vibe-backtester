"""
Тесты для модуля портфельного тестирования (src/backtest/portfolio.py).

Проверяет PortfolioData, PortfolioBacktestEngine, PortfolioResult,
распределение капитала, ребалансировку и метрики портфеля.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import polars as pl
import pytest

from src.backtest import (
    PortfolioBacktestEngine,
    PortfolioData,
    PortfolioResult,
    Strategy,
)
from src.backtest.models import Trade


# ──────────────────────────────────────────────
# Вспомогательные стратегии
# ──────────────────────────────────────────────


class BuyAndHoldStrategy(Strategy):
    """
    Тестовая стратегия: покупает на первом баре, держит до конца.

    Используется для проверки базового функционала портфеля.
    """

    def next(self, i: int) -> None:
        if i == 0:
            self.buy(size=1.0)
        if i == len(self.close) - 1:
            self.close_position()


class NoTradeStrategy(Strategy):
    """Тестовая стратегия: не совершает сделок."""

    def next(self, i: int) -> None:
        pass


class AlternateTradeStrategy(Strategy):
    """
    Тестовая стратегия: вход/выход на каждом баре.

    Создаёт много сделок для проверки накопления комиссий.
    """

    def next(self, i: int) -> None:
        if i == 0:
            self.buy(size=1.0)
        elif i % 2 == 0:
            if self.in_position:
                self.close_position()
            else:
                self.buy(size=1.0)


# ──────────────────────────────────────────────
# Фикстуры
# ──────────────────────────────────────────────


@pytest.fixture
def single_instrument_data() -> dict[str, pl.DataFrame]:
    """
    Фикстура: данные одного инструмента (10 свечей, цена растёт).

    Возвращает:
        Словарь с одним инструментом 'ASSET1'.
    """
    return {
        "ASSET1": pl.DataFrame({
            "date": [datetime(2025, 1, 1, 10, i) for i in range(10)],
            "open": [100.0 + i for i in range(10)],
            "high": [101.0 + i for i in range(10)],
            "low": [99.0 + i for i in range(10)],
            "close": [100.0 + i for i in range(10)],
            "volume": [1000 + i * 100 for i in range(10)],
        }),
    }


@pytest.fixture
def two_instruments_data() -> dict[str, pl.DataFrame]:
    """
    Фикстура: данные двух инструментов с одинаковой временной шкалой.

    ASSET1: цена растёт 100→109
    ASSET2: цена падает 200→191

    Возвращает:
        Словарь с инструментами 'ASSET1' и 'ASSET2'.
    """
    return {
        "ASSET1": pl.DataFrame({
            "date": [datetime(2025, 1, 1, 10, i) for i in range(10)],
            "open": [100.0 + i for i in range(10)],
            "high": [101.0 + i for i in range(10)],
            "low": [99.0 + i for i in range(10)],
            "close": [100.0 + i for i in range(10)],
            "volume": [1000 + i * 100 for i in range(10)],
        }),
        "ASSET2": pl.DataFrame({
            "date": [datetime(2025, 1, 1, 10, i) for i in range(10)],
            "open": [200.0 - i for i in range(10)],
            "high": [201.0 - i for i in range(10)],
            "low": [199.0 - i for i in range(10)],
            "close": [200.0 - i for i in range(10)],
            "volume": [2000 + i * 50 for i in range(10)],
        }),
    }


@pytest.fixture
def instruments_different_dates() -> dict[str, pl.DataFrame]:
    """
    Фикстура: два инструмента с разными временными шкалами (пересечение = 5 баров).

    Возвращает:
        Словарь с инструментами, имеющими частичное пересечение дат.
    """
    return {
        "ASSET1": pl.DataFrame({
            "date": [
                datetime(2025, 1, 1, 10, i) for i in range(10)
            ],
            "open": [100.0 + i for i in range(10)],
            "high": [101.0 + i for i in range(10)],
            "low": [99.0 + i for i in range(10)],
            "close": [100.0 + i for i in range(10)],
            "volume": [1000] * 10,
        }),
        "ASSET2": pl.DataFrame({
            "date": [
                datetime(2025, 1, 1, 10, i) for i in range(2, 8)
            ],
            "open": [200.0 - i for i in range(2, 8)],
            "high": [201.0 - i for i in range(2, 8)],
            "low": [199.0 - i for i in range(2, 8)],
            "close": [200.0 - i for i in range(2, 8)],
            "volume": [2000] * 6,
        }),
    }


# ──────────────────────────────────────────────
# Тесты PortfolioData
# ──────────────────────────────────────────────


def test_portfolio_data_creation() -> None:
    """Проверяет создание PortfolioData с корректными параметрами."""
    portfolio = PortfolioData(
        instruments=["ASSET1", "ASSET2"],
        weights=[0.6, 0.4],
        initial_capital=1_000_000.0,
    )
    assert portfolio.instruments == ["ASSET1", "ASSET2"]
    assert portfolio.weights == [0.6, 0.4]
    assert portfolio.initial_capital == 1_000_000.0
    assert portfolio.rebalance_frequency is None


def test_portfolio_data_weights_sum_to_one() -> None:
    """Проверяет, что сумма весов должна быть равна 1.0."""
    with pytest.raises(ValueError, match="Сумма весов"):
        PortfolioData(
            instruments=["ASSET1", "ASSET2"],
            weights=[0.6, 0.3],
        )


def test_portfolio_data_empty_instruments() -> None:
    """Проверяет, что портфель не может быть пустым."""
    with pytest.raises(ValueError, match="хотя бы один инструмент"):
        PortfolioData(
            instruments=[],
            weights=[],
        )


def test_portfolio_data_length_mismatch() -> None:
    """Проверяет, что количество инструментов и весов совпадает."""
    with pytest.raises(ValueError, match="не совпадает"):
        PortfolioData(
            instruments=["ASSET1", "ASSET2"],
            weights=[1.0],
        )


def test_portfolio_data_negative_weight() -> None:
    """Проверяет, что вес не может быть отрицательным."""
    with pytest.raises(ValueError, match="отрицательным"):
        PortfolioData(
            instruments=["ASSET1", "ASSET2"],
            weights=[1.5, -0.5],
        )


def test_portfolio_data_single_instrument() -> None:
    """Проверяет портфель с одним инструментом."""
    portfolio = PortfolioData(
        instruments=["ASSET1"],
        weights=[1.0],
        initial_capital=500_000.0,
    )
    assert len(portfolio.instruments) == 1
    assert portfolio.weights[0] == 1.0


# ──────────────────────────────────────────────
# Тесты PortfolioResult
# ──────────────────────────────────────────────


def test_portfolio_result_empty() -> None:
    """Проверяет пустой результат портфеля."""
    result = PortfolioResult()
    assert result.total_return == 0.0
    assert result.total_pnl == 0.0
    assert result.sharpe_ratio == 0.0
    assert result.max_drawdown == 0.0
    assert result.asset_results == {}


def test_portfolio_result_to_dict() -> None:
    """Проверяет преобразование результата в словарь."""
    result = PortfolioResult()
    d = result.to_dict()
    assert isinstance(d, dict)
    assert "total_return" in d
    assert "sharpe_ratio" in d
    assert "max_drawdown" in d
    assert "total_trades" in d


# ──────────────────────────────────────────────
# Тесты PortfolioBacktestEngine
# ──────────────────────────────────────────────


def test_engine_creation() -> None:
    """Проверяет создание движка портфельного тестирования."""
    engine = PortfolioBacktestEngine()
    assert engine.commission_pct == 0.0
    assert engine.slippage_pct == 0.0


def test_engine_with_custom_params() -> None:
    """Проверяет создание движка с пользовательскими параметрами."""
    engine = PortfolioBacktestEngine(commission_pct=0.1, slippage_pct=0.05)
    assert engine.commission_pct == 0.1
    assert engine.slippage_pct == 0.05


def test_engine_run_single_instrument(
    single_instrument_data: dict[str, pl.DataFrame],
) -> None:
    """Проверяет запуск портфеля с одним инструментом."""
    engine = PortfolioBacktestEngine()
    result = engine.run(
        strategy_class=BuyAndHoldStrategy,
        data_dict=single_instrument_data,
        initial_capital=100_000.0,
    )
    assert isinstance(result, PortfolioResult)
    assert "ASSET1" in result.asset_results
    assert result.total_return > 0  # Цена росла, прибыль должна быть


def test_engine_run_two_instruments(
    two_instruments_data: dict[str, pl.DataFrame],
) -> None:
    """Проверяет запуск портфеля с двумя инструментами."""
    engine = PortfolioBacktestEngine()
    result = engine.run(
        strategy_class=BuyAndHoldStrategy,
        data_dict=two_instruments_data,
        weights={"ASSET1": 0.5, "ASSET2": 0.5},
        initial_capital=100_000.0,
    )
    assert isinstance(result, PortfolioResult)
    assert "ASSET1" in result.asset_results
    assert "ASSET2" in result.asset_results
    # ASSET1 растёт, ASSET2 падает — в каждой сделке по трейду
    assert len(result.asset_results["ASSET1"].trades) == 1
    assert len(result.asset_results["ASSET2"].trades) == 1


def test_engine_run_no_trades(
    two_instruments_data: dict[str, pl.DataFrame],
) -> None:
    """Проверяет портфель со стратегией без сделок."""
    engine = PortfolioBacktestEngine()
    result = engine.run(
        strategy_class=NoTradeStrategy,
        data_dict=two_instruments_data,
        weights={"ASSET1": 0.5, "ASSET2": 0.5},
        initial_capital=100_000.0,
    )
    assert result.total_pnl == 0.0


def test_engine_run_with_portfolio_data(
    two_instruments_data: dict[str, pl.DataFrame],
) -> None:
    """Проверяет запуск с использованием PortfolioData."""
    portfolio = PortfolioData(
        instruments=["ASSET1", "ASSET2"],
        weights=[0.7, 0.3],
        initial_capital=500_000.0,
    )
    engine = PortfolioBacktestEngine()
    result = engine.run(
        strategy_class=BuyAndHoldStrategy,
        data_dict=two_instruments_data,
        portfolio=portfolio,
    )
    assert isinstance(result, PortfolioResult)
    # ASSET1 с весом 0.7, ASSET2 с весом 0.3
    assert result.instruments == ["ASSET1", "ASSET2"]
    assert result.weights == {"ASSET1": 0.7, "ASSET2": 0.3}


def test_engine_run_with_portfolio_data_method(
    two_instruments_data: dict[str, pl.DataFrame],
) -> None:
    """Проверяет метод run_with_portfolio_data."""
    portfolio = PortfolioData(
        instruments=["ASSET1", "ASSET2"],
        weights=[0.5, 0.5],
        initial_capital=200_000.0,
    )
    engine = PortfolioBacktestEngine()
    result = engine.run_with_portfolio_data(
        strategy_class=BuyAndHoldStrategy,
        data_dict=two_instruments_data,
        portfolio=portfolio,
    )
    assert isinstance(result, PortfolioResult)
    # ASSET1 вырос на 9, ASSET2 упал на 9 (равные веса) → портфель в нуле
    assert result.total_return == 0.0


def test_engine_run_equal_weights(
    two_instruments_data: dict[str, pl.DataFrame],
) -> None:
    """Проверяет равномерное распределение весов (weights=None)."""
    engine = PortfolioBacktestEngine()
    result = engine.run(
        strategy_class=BuyAndHoldStrategy,
        data_dict=two_instruments_data,
        initial_capital=100_000.0,
    )
    assert isinstance(result, PortfolioResult)
    assert "ASSET1" in result.asset_results
    assert "ASSET2" in result.asset_results


def test_engine_missing_instrument_in_data() -> None:
    """Проверяет ошибку при отсутствии инструмента в data_dict."""
    engine = PortfolioBacktestEngine()
    with pytest.raises(ValueError, match="не найден"):
        empty_data = pl.DataFrame({
            "date": [], "open": [], "high": [], "low": [], "close": [],
        })
        engine.run(
            strategy_class=NoTradeStrategy,
            data_dict={"ASSET1": empty_data},
            weights={"ASSET1": 0.5, "MISSING": 0.5},
            initial_capital=100_000.0,
        )


def test_engine_missing_date_column() -> None:
    """Проверяет ошибку при отсутствии колонки date."""
    engine = PortfolioBacktestEngine()
    with pytest.raises(ValueError, match="не содержит колонку 'date'"):
        bad_data = pl.DataFrame({"open": [], "close": []})
        engine.run(
            strategy_class=NoTradeStrategy,
            data_dict={"ASSET1": bad_data},
            initial_capital=100_000.0,
        )


def test_engine_equity_curve(
    two_instruments_data: dict[str, pl.DataFrame],
) -> None:
    """Проверяет, что кривая капитала портфеля не пустая."""
    engine = PortfolioBacktestEngine()
    result = engine.run(
        strategy_class=BuyAndHoldStrategy,
        data_dict=two_instruments_data,
        weights={"ASSET1": 0.5, "ASSET2": 0.5},
        initial_capital=100_000.0,
    )
    assert not result.portfolio_equity_curve.is_empty()
    assert "equity" in result.portfolio_equity_curve.columns


def test_engine_empty_data_dict() -> None:
    """Проверяет запуск с пустым словарём данных."""
    engine = PortfolioBacktestEngine()
    result = engine.run(
        strategy_class=NoTradeStrategy,
        data_dict={},
        initial_capital=100_000.0,
    )
    assert isinstance(result, PortfolioResult)
    assert result.instruments == []


def test_engine_portfolio_metrics(
    two_instruments_data: dict[str, pl.DataFrame],
) -> None:
    """Проверяет, что метрики портфеля рассчитываются корректно."""
    engine = PortfolioBacktestEngine()
    result = engine.run(
        strategy_class=BuyAndHoldStrategy,
        data_dict=two_instruments_data,
        weights={"ASSET1": 0.5, "ASSET2": 0.5},
        initial_capital=100_000.0,
    )
    # Проверяем, что метрики не None и имеют правильный тип
    assert isinstance(result.total_return, float)
    assert isinstance(result.sharpe_ratio, float)
    assert isinstance(result.max_drawdown, float)
    assert result.max_drawdown >= 0.0


def test_engine_return_value(
    single_instrument_data: dict[str, pl.DataFrame],
) -> None:
    """
    Проверяет доходность портфеля из одного растущего инструмента.

    BuyAndHold на растущем рынке (100→109) с 1 единицей = 9 прибыли.
    """
    engine = PortfolioBacktestEngine()
    result = engine.run(
        strategy_class=BuyAndHoldStrategy,
        data_dict=single_instrument_data,
        initial_capital=100_000.0,
    )
    # Купили 1 единицу по 100, продали по 109 → P&L = 9
    # Доходность = 9 / 100000 * 100% = 0.009%
    assert result.total_pnl > 0
    # ASSET1 вырос, значит и портфель должен быть в плюсе
    assert result.total_return > 0
    assert list(result.weights.keys()) == ["ASSET1"]


# ──────────────────────────────────────────────
# Тесты с разными временными шкалами
# ──────────────────────────────────────────────


def test_engine_different_date_ranges(
    instruments_different_dates: dict[str, pl.DataFrame],
) -> None:
    """
    Проверяет портфель, когда инструменты имеют разную длину данных.

    ASSET1 = 10 баров, ASSET2 = 6 баров (пересечение = бары 2-7)
    """
    engine = PortfolioBacktestEngine()
    result = engine.run(
        strategy_class=BuyAndHoldStrategy,
        data_dict=instruments_different_dates,
        weights={"ASSET1": 0.5, "ASSET2": 0.5},
        initial_capital=100_000.0,
    )
    assert isinstance(result, PortfolioResult)
    # Должны быть сделки по обоим инструментам
    assert "ASSET1" in result.asset_results
    assert "ASSET2" in result.asset_results


def test_engine_non_overlapping_dates() -> None:
    """Проверяет портфель с непересекающимися датами (должен вернуть пустой результат)."""
    data = {
        "ASSET1": pl.DataFrame({
            "date": [datetime(2025, 1, 1, 10, i) for i in range(5)],
            "open": [100.0] * 5,
            "high": [101.0] * 5,
            "low": [99.0] * 5,
            "close": [100.0] * 5,
            "volume": [1000] * 5,
        }),
        "ASSET2": pl.DataFrame({
            "date": [datetime(2026, 1, 1, 10, i) for i in range(5)],
            "open": [200.0] * 5,
            "high": [201.0] * 5,
            "low": [199.0] * 5,
            "close": [200.0] * 5,
            "volume": [2000] * 5,
        }),
    }
    engine = PortfolioBacktestEngine()
    result = engine.run(
        strategy_class=NoTradeStrategy,
        data_dict=data,
        weights={"ASSET1": 0.5, "ASSET2": 0.5},
        initial_capital=100_000.0,
    )
    assert isinstance(result, PortfolioResult)
    assert result.total_pnl == 0.0


# ──────────────────────────────────────────────
# Тесты run_with_different_strategies
# ──────────────────────────────────────────────


def test_run_with_different_strategies(
    two_instruments_data: dict[str, pl.DataFrame],
) -> None:
    """Проверяет запуск разных стратегий для разных инструментов."""
    engine = PortfolioBacktestEngine()
    result = engine.run_with_different_strategies(
        strategy_dict={
            "ASSET1": BuyAndHoldStrategy,
            "ASSET2": NoTradeStrategy,
        },
        data_dict=two_instruments_data,
        weights={"ASSET1": 0.5, "ASSET2": 0.5},
        initial_capital=100_000.0,
    )
    assert isinstance(result, PortfolioResult)
    assert "ASSET1" in result.asset_results
    assert "ASSET2" in result.asset_results
    # ASSET1 торгует, ASSET2 — нет
    asset1_result = result.asset_results["ASSET1"]
    asset2_result = result.asset_results["ASSET2"]
    assert asset1_result.total_trades > 0
    assert asset2_result.total_trades == 0


def test_run_with_different_strategies_missing_data() -> None:
    """Проверяет ошибку при отсутствии инструмента в data_dict."""
    engine = PortfolioBacktestEngine()
    empty_data = pl.DataFrame({
        "date": [], "open": [], "high": [], "low": [], "close": [],
    })
    with pytest.raises(ValueError, match="не найден"):
        engine.run_with_different_strategies(
            strategy_dict={
                "ASSET1": NoTradeStrategy,
                "MISSING": NoTradeStrategy,
            },
            data_dict={"ASSET1": empty_data},
            initial_capital=100_000.0,
        )


# ──────────────────────────────────────────────
# Тесты распределения капитала
# ──────────────────────────────────────────────


def test_capital_allocation_equal_weights() -> None:
    """Проверяет равномерное распределение капитала."""
    engine = PortfolioBacktestEngine()
    # data_dict с двумя инструментами, без weights → равные веса
    data = {
        "A": pl.DataFrame({
            "date": [datetime(2025, 1, 1, 10, 0)],
            "open": [100.0], "high": [101.0], "low": [99.0],
            "close": [100.0], "volume": [1000],
        }),
        "B": pl.DataFrame({
            "date": [datetime(2025, 1, 1, 10, 0)],
            "open": [200.0], "high": [201.0], "low": [199.0],
            "close": [200.0], "volume": [2000],
        }),
    }
    result = engine.run(
        strategy_class=NoTradeStrategy,
        data_dict=data,
        initial_capital=100_000.0,
    )
    # Оба инструмента должны быть в результате
    assert "A" in result.asset_results
    assert "B" in result.asset_results


# ──────────────────────────────────────────────
# Тесты метрик портфеля
# ──────────────────────────────────────────────


def test_portfolio_metrics_detailed() -> None:
    """Проверяет детальный расчёт метрик портфеля через PortfolioResult."""
    # Создаём результат с известными значениями
    equity = pl.DataFrame({
        "bar": [0, 1, 2, 3, 4, 5],
        "equity": [100000.0, 105000.0, 95000.0, 90000.0, 110000.0, 108000.0],
    })

    trades = [
        Trade(
            entry_bar=0, exit_bar=5, entry_price=100.0, exit_price=110.0,
            size=1.0, side="long", pnl=10.0, pnl_pct=10.0,
        ),
    ]

    asset_result = type("MockResult", (), {
        "total_return": 8.0,
        "total_pnl": 10.0,
        "sharpe_ratio": 1.5,
        "max_drawdown": 14.29,
        "total_trades": 1,
        "trades": trades,
    })()

    result = PortfolioResult(
        asset_results={"ASSET1": asset_result},  # type: ignore[assignment]
        portfolio_equity_curve=equity,
        instruments=["ASSET1"],
        weights={"ASSET1": 1.0},
    )

    # Проверяем метрики
    assert result.total_return > 0
    assert result.total_pnl > 0
    d = result.to_dict()
    assert d["total_trades"] == 1


def test_portfolio_equity_curve_shape(
    two_instruments_data: dict[str, pl.DataFrame],
) -> None:
    """Проверяет, что кривая капитала портфеля имеет правильную длину."""
    engine = PortfolioBacktestEngine()
    result = engine.run(
        strategy_class=BuyAndHoldStrategy,
        data_dict=two_instruments_data,
        weights={"ASSET1": 0.5, "ASSET2": 0.5},
        initial_capital=100_000.0,
    )
    n_bars = len(two_instruments_data["ASSET1"])
    assert len(result.portfolio_equity_curve) == n_bars


def test_portfolio_weights_are_preserved(
    two_instruments_data: dict[str, pl.DataFrame],
) -> None:
    """Проверяет, что веса портфеля сохраняются в результате."""
    engine = PortfolioBacktestEngine()
    result = engine.run(
        strategy_class=BuyAndHoldStrategy,
        data_dict=two_instruments_data,
        weights={"ASSET1": 0.8, "ASSET2": 0.2},
        initial_capital=100_000.0,
    )
    assert result.weights == {"ASSET1": 0.8, "ASSET2": 0.2}


def test_portfolio_instruments_list(
    two_instruments_data: dict[str, pl.DataFrame],
) -> None:
    """Проверяет, что список инструментов сохраняется в результате."""
    engine = PortfolioBacktestEngine()
    result = engine.run(
        strategy_class=NoTradeStrategy,
        data_dict=two_instruments_data,
        weights={"ASSET1": 0.5, "ASSET2": 0.5},
        initial_capital=100_000.0,
    )
    assert set(result.instruments) == {"ASSET1", "ASSET2"}
