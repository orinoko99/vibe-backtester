"""
Тесты для движка бэктестинга (src/backtest/).

Проверяет Strategy, BacktestEngine, модели данных и метрики.
"""

from __future__ import annotations

from datetime import datetime

import polars as pl
import pytest

from src.backtest import BacktestEngine, BacktestResult, Strategy, Trade
from src.backtest.models import Order


# ──────────────────────────────────────────────
# Фикстуры
# ──────────────────────────────────────────────


@pytest.fixture
def sample_data() -> pl.DataFrame:
    """
    Фикстура: создаёт тестовый DataFrame с 10 свечами.

    Цена растёт с 100 до 109.
    """
    return pl.DataFrame({
        "date": [datetime(2025, 1, 1, 10, i) for i in range(10)],
        "open": [100.0 + i for i in range(10)],
        "high": [101.0 + i for i in range(10)],
        "low": [99.0 + i for i in range(10)],
        "close": [100.0 + i for i in range(10)],
        "volume": [1000 + i * 100 for i in range(10)],
    })


@pytest.fixture
def data_with_volatility() -> pl.DataFrame:
    """
    Фикстура: волатильные данные для теста SL/TP.

    Цена: 100, 105, 95, 110, 90, 115, 85, 120, 80, 125
    """
    closes = [100.0, 105.0, 95.0, 110.0, 90.0, 115.0, 85.0, 120.0, 80.0, 125.0]
    return pl.DataFrame({
        "date": [datetime(2025, 1, 1, 10, i) for i in range(10)],
        "open": closes,
        "high": [c + 2.0 for c in closes],
        "low": [c - 2.0 for c in closes],
        "close": closes,
        "volume": [1000] * 10,
    })


# ──────────────────────────────────────────────
# Тест стратегии — всегда покупаем на первом баре
# ──────────────────────────────────────────────


class BuyAndHoldStrategy(Strategy):
    """Стратегия: покупаем на первой свече, держим до конца."""

    def next(self, i: int) -> None:
        if i == 0:
            self.buy(size=1.0)
        if i == len(self.close) - 1:
            self.close_position()


class BuyAndSellStrategy(Strategy):
    """Стратегия: покупаем на баре 1, продаём на баре 5."""

    def next(self, i: int) -> None:
        if i == 1:
            self.buy(size=1.0)
        if i == 5:
            self.close_position()


class ShortStrategy(Strategy):
    """Стратегия: продаём на первом баре, закрываем в конце."""

    def next(self, i: int) -> None:
        if i == 0:
            self.sell(size=1.0)
        if i == len(self.close) - 1:
            self.close_position()


class MultiTradeStrategy(Strategy):
    """Стратегия: несколько сделок подряд (long, short, long)."""

    def next(self, i: int) -> None:
        if i == 0:
            self.buy(size=1.0)
        if i == 2:
            self.close_position()
        if i == 4:
            self.sell(size=1.0)
        if i == 6:
            self.close_position()
        if i == 8:
            self.buy(size=1.0)
        if i == 9:
            self.close_position()


class NoTradeStrategy(Strategy):
    """Стратегия: не совершает сделок."""

    def next(self, i: int) -> None:
        pass


# ──────────────────────────────────────────────
# Тесты моделей
# ──────────────────────────────────────────────


def test_order_creation() -> None:
    """Проверяет создание ордера."""
    order = Order(side="buy", size=10.0, price=100.0, bar_index=5)
    assert order.side == "buy"
    assert order.size == 10.0
    assert order.price == 100.0
    assert order.bar_index == 5
    assert order.order_type == "market"


def test_order_with_sl_tp() -> None:
    """Проверяет ордер с стоп-лоссом и тейк-профитом."""
    order = Order(side="buy", size=1.0, stop_loss=95.0, take_profit=110.0)
    assert order.stop_loss == 95.0
    assert order.take_profit == 110.0


def test_trade_creation() -> None:
    """Проверяет создание сделки."""
    trade = Trade(
        entry_bar=1, exit_bar=10,
        entry_price=100.0, exit_price=110.0,
        size=1.0, side="long",
        pnl=10.0, pnl_pct=10.0,
    )
    assert trade.entry_bar == 1
    assert trade.exit_bar == 10
    assert trade.pnl == 10.0
    assert trade.pnl_pct == 10.0
    assert trade.side == "long"


def test_backtest_result_empty() -> None:
    """Проверяет пустой результат бэктеста."""
    result = BacktestResult()
    assert result.total_trades == 0
    assert result.trades == []
    assert result.equity_curve.is_empty()


def test_backtest_result_with_trades() -> None:
    """Проверяет результат с одной сделкой."""
    trades = [
        Trade(entry_bar=0, exit_bar=5, entry_price=100.0, exit_price=110.0,
              size=1.0, side="long", pnl=10.0, pnl_pct=10.0),
    ]
    equity = pl.DataFrame({"bar": [0, 1, 2, 3, 4, 5], "equity": [100000.0, 100002.0, 100005.0, 100008.0, 100009.0, 100010.0]})
    result = BacktestResult(trades=trades, equity_curve=equity)
    assert result.total_trades == 1
    assert result.win_rate == 100.0
    assert result.total_pnl == 10.0


def test_backtest_result_with_losing_trade() -> None:
    """Проверяет результат с убыточной сделкой."""
    trades = [
        Trade(entry_bar=0, exit_bar=5, entry_price=100.0, exit_price=90.0,
              size=1.0, side="long", pnl=-10.0, pnl_pct=-10.0),
    ]
    equity = pl.DataFrame({"bar": [0, 5], "equity": [100000.0, 99990.0]})
    result = BacktestResult(trades=trades, equity_curve=equity)
    assert result.total_trades == 1
    assert result.win_rate == 0.0
    assert result.total_pnl == -10.0


def test_backtest_result_to_dict() -> None:
    """Проверяет преобразование результата в словарь."""
    result = BacktestResult()
    d = result.to_dict()
    assert isinstance(d, dict)
    assert "total_return" in d
    assert "sharpe_ratio" in d
    assert "max_drawdown" in d


# ──────────────────────────────────────────────
# Тесты стратегии
# ──────────────────────────────────────────────


def test_strategy_creation(sample_data: pl.DataFrame) -> None:
    """Проверяет создание стратегии с данными."""
    strat = BuyAndHoldStrategy(sample_data)
    assert strat.data is not None
    assert len(strat.close) == 10
    assert not strat.in_position
    assert strat.position_size == 0.0


def test_strategy_buy(sample_data: pl.DataFrame) -> None:
    """Проверяет создание ордера на покупку."""
    strat = BuyAndHoldStrategy(sample_data)
    order = strat.buy(size=2.0)
    assert order is not None
    assert order.side == "buy"
    assert order.size == 2.0


def test_strategy_buy_when_in_position(sample_data: pl.DataFrame) -> None:
    """Проверяет, что повторный buy не создаёт ордер."""
    strat = BuyAndHoldStrategy(sample_data)
    strat._position_side = "long"
    strat._position_size = 1.0
    order = strat.buy(size=1.0)
    assert order is None


def test_strategy_sell(sample_data: pl.DataFrame) -> None:
    """Проверяет создание ордера на продажу."""
    strat = BuyAndHoldStrategy(sample_data)
    order = strat.sell(size=1.0)
    assert order is not None
    assert order.side == "sell"


def test_strategy_sell_when_in_position(sample_data: pl.DataFrame) -> None:
    """Проверяет, что повторный sell не создаёт ордер."""
    strat = BuyAndHoldStrategy(sample_data)
    strat._position_side = "short"
    strat._position_size = 1.0
    order = strat.sell(size=1.0)
    assert order is None


def test_strategy_close_position(sample_data: pl.DataFrame) -> None:
    """Проверяет закрытие позиции."""
    strat = BuyAndHoldStrategy(sample_data)
    strat._current_index = 5
    strat._position_side = "long"
    strat._position_size = 1.0
    strat._entry_price = 100.0
    strat._entry_bar = 0

    strat.close_position()
    assert not strat.in_position
    assert len(strat.trades) == 1
    assert strat.trades[0].pnl == pytest.approx(105.0 - 100.0)


def test_strategy_close_position_without_position(sample_data: pl.DataFrame) -> None:
    """Проверяет, что close_position без позиции не создаёт сделку."""
    strat = BuyAndHoldStrategy(sample_data)
    strat.close_position()
    assert len(strat.trades) == 0


def test_strategy_close_position_short(sample_data: pl.DataFrame) -> None:
    """Проверяет закрытие короткой позиции."""
    strat = BuyAndHoldStrategy(sample_data)
    strat._current_index = 5
    strat._position_side = "short"
    strat._position_size = 1.0
    strat._entry_price = 105.0
    strat._entry_bar = 3

    strat.close_position()
    assert len(strat.trades) == 1
    assert strat.trades[0].side == "short"
    assert strat.trades[0].pnl == pytest.approx(105.0 - 105.0)  # close[5] = 105


def test_strategy_properties(sample_data: pl.DataFrame) -> None:
    """Проверяет свойства стратегии."""
    strat = BuyAndHoldStrategy(sample_data)
    assert strat.position_size == 0.0
    assert strat.position_side is None
    assert not strat.in_position

    strat._position_side = "long"
    strat._position_size = 1.0
    assert strat.position_size == 1.0
    assert strat.position_side == "long"
    assert strat.in_position


# ──────────────────────────────────────────────
# Тесты движка
# ──────────────────────────────────────────────


def test_engine_creation() -> None:
    """Проверяет создание движка."""
    engine = BacktestEngine()
    assert engine.initial_capital == 100_000.0
    assert engine.commission_pct == 0.0
    assert engine.slippage_pct == 0.0


def test_engine_with_custom_params() -> None:
    """Проверяет создание движка с пользовательскими параметрами."""
    engine = BacktestEngine(initial_capital=50_000.0, commission_pct=0.1, slippage_pct=0.05)
    assert engine.initial_capital == 50_000.0
    assert engine.commission_pct == 0.1
    assert engine.slippage_pct == 0.05


def test_engine_run_empty_data() -> None:
    """Проверяет запуск с пустыми данными."""
    engine = BacktestEngine()
    empty_data = pl.DataFrame({"date": [], "open": [], "high": [], "low": [], "close": []})
    result = engine.run(NoTradeStrategy, empty_data)
    assert isinstance(result, BacktestResult)
    assert result.total_trades == 0


def test_engine_run_no_trades(sample_data: pl.DataFrame) -> None:
    """Проверяет запуск стратегии без сделок."""
    engine = BacktestEngine()
    result = engine.run(NoTradeStrategy, sample_data)
    assert result.total_trades == 0
    assert result.total_pnl == 0.0


def test_engine_run_buy_and_hold(sample_data: pl.DataFrame) -> None:
    """Проверяет стратегию buy-and-hold."""
    engine = BacktestEngine()
    result = engine.run(BuyAndHoldStrategy, sample_data)
    assert result.total_trades == 1
    trade = result.trades[0]
    assert trade.side == "long"
    assert trade.entry_price == 100.0
    assert trade.exit_price == 109.0
    assert trade.pnl == 9.0


def test_engine_run_buy_and_sell(sample_data: pl.DataFrame) -> None:
    """Проверяет стратегию с покупкой и продажей."""
    engine = BacktestEngine()
    result = engine.run(BuyAndSellStrategy, sample_data)
    assert result.total_trades == 1
    trade = result.trades[0]
    assert trade.entry_bar == 1
    assert trade.exit_bar == 5
    assert trade.entry_price == 101.0
    assert trade.exit_price == 105.0
    assert trade.pnl == 4.0


def test_engine_run_short(sample_data: pl.DataFrame) -> None:
    """Проверяет короткую стратегию на растущем рынке (убыток)."""
    engine = BacktestEngine()
    result = engine.run(ShortStrategy, sample_data)
    assert result.total_trades == 1
    trade = result.trades[0]
    assert trade.side == "short"
    assert trade.pnl == pytest.approx(-9.0)


def test_engine_run_multi_trade(sample_data: pl.DataFrame) -> None:
    """Проверяет стратегию с несколькими сделками."""
    engine = BacktestEngine()
    result = engine.run(MultiTradeStrategy, sample_data)
    assert result.total_trades == 3


def test_engine_equity_curve(sample_data: pl.DataFrame) -> None:
    """Проверяет, что equity_curve не пустая после прогона."""
    engine = BacktestEngine()
    result = engine.run(BuyAndHoldStrategy, sample_data)
    assert not result.equity_curve.is_empty()
    assert "bar" in result.equity_curve.columns
    assert "equity" in result.equity_curve.columns


def test_engine_commission_affects_equity(sample_data: pl.DataFrame) -> None:
    """Проверяет, что комиссия уменьшает equity."""
    engine_no_comm = BacktestEngine(commission_pct=0.0)
    engine_comm = BacktestEngine(commission_pct=5.0)  # 5% комиссия

    result_no_comm = engine_no_comm.run(BuyAndHoldStrategy, sample_data)
    result_comm = engine_comm.run(BuyAndHoldStrategy, sample_data)

    # С комиссией финальная equity должна быть меньше
    final_no_comm = float(result_no_comm.equity_curve["equity"][-1])
    final_comm = float(result_comm.equity_curve["equity"][-1])
    assert final_no_comm > final_comm, f"{final_no_comm} should be > {final_comm}"


def test_engine_raises_on_missing_column() -> None:
    """Проверяет, что движок выбрасывает ошибку при отсутствии колонки."""
    engine = BacktestEngine()
    bad_data = pl.DataFrame({"date": [], "open": [], "close": []})
    with pytest.raises(ValueError):
        engine.run(NoTradeStrategy, bad_data)


# ──────────────────────────────────────────────
# Тесты стоп-лосса и тейк-профита
# ──────────────────────────────────────────────


class StrategyWithSL(Strategy):
    """Стратегия: покупает и устанавливает стоп-лосс."""

    def next(self, i: int) -> None:
        if i == 0:
            self.buy(size=1.0, stop_loss=98.0)


class StrategyWithTP(Strategy):
    """Стратегия: покупает и устанавливает тейк-профит."""

    def next(self, i: int) -> None:
        if i == 0:
            self.buy(size=1.0, take_profit=107.0)


class StrategyWithSLTP(Strategy):
    """Стратегия: покупает с SL и TP, TP должен сработать раньше."""

    def next(self, i: int) -> None:
        if i == 0:
            self.buy(size=1.0, stop_loss=90.0, take_profit=108.0)


def test_stop_loss_triggers(data_with_volatility: pl.DataFrame) -> None:
    """Проверяет, что стоп-лосс срабатывает при падении цены."""
    engine = BacktestEngine()
    result = engine.run(StrategyWithSL, data_with_volatility)
    assert result.total_trades == 1
    trade = result.trades[0]
    # SL на 98, цена падает до 95 на баре 2 → должен сработать SL
    assert trade.exit_price == pytest.approx(98.0)


def test_take_profit_triggers(data_with_volatility: pl.DataFrame) -> None:
    """Проверяет, что тейк-профит срабатывает при росте цены."""
    engine = BacktestEngine()
    result = engine.run(StrategyWithTP, data_with_volatility)
    assert result.total_trades == 1
    trade = result.trades[0]
    # TP на 107, цена растёт до 110 на баре 3 → должен сработать TP
    assert trade.exit_price == pytest.approx(107.0)


# ──────────────────────────────────────────────
# Тесты метрик производительности
# ──────────────────────────────────────────────


def test_metrics_total_return(sample_data: pl.DataFrame) -> None:
    """Проверяет расчёт общей доходности."""
    engine = BacktestEngine()
    result = engine.run(BuyAndHoldStrategy, sample_data)
    # Купили по 100, продали по 109, 1 единица = 9 прибыли на 100K капитала
    assert result.total_return > 0
    assert result.total_pnl == 9.0


def test_metrics_win_rate() -> None:
    """Проверяет расчёт процента прибыльных сделок."""
    trades = [
        Trade(entry_bar=0, exit_bar=5, entry_price=100.0, exit_price=110.0,
              size=1.0, side="long", pnl=10.0, pnl_pct=10.0),
        Trade(entry_bar=6, exit_bar=10, entry_price=110.0, exit_price=105.0,
              size=1.0, side="long", pnl=-5.0, pnl_pct=-4.55),
    ]
    result = BacktestResult(trades=trades)
    assert result.total_trades == 2
    assert result.win_rate == 50.0


def test_metrics_avg_holding_bars() -> None:
    """Проверяет расчёт средней длительности сделки."""
    trades = [
        Trade(entry_bar=0, exit_bar=5, entry_price=100.0, exit_price=110.0,
              size=1.0, side="long", pnl=10.0, pnl_pct=10.0),
        Trade(entry_bar=10, exit_bar=20, entry_price=110.0, exit_price=105.0,
              size=1.0, side="long", pnl=-5.0, pnl_pct=-4.55),
    ]
    result = BacktestResult(trades=trades)
    assert result.avg_holding_bars == 7.5  # (5 + 10) / 2


def test_metrics_max_drawdown() -> None:
    """Проверяет расчёт максимальной просадки."""
    equity = pl.DataFrame({
        "bar": [0, 1, 2, 3, 4, 5],
        "equity": [100000.0, 105000.0, 95000.0, 90000.0, 110000.0, 108000.0],
    })
    result = BacktestResult(trades=[], equity_curve=equity)
    # Пик 105000, просадка до 90000 = (105000-90000)/105000 = 14.29%
    assert result.max_drawdown > 0
    assert result.max_drawdown < 20.0


def test_metrics_sharpe_ratio() -> None:
    """Проверяет, что Sharpe ratio рассчитывается (положительный для растущей кривой)."""
    equity = pl.DataFrame({
        "bar": list(range(100)),
        "equity": [100000.0 + i * 100 for i in range(100)],
    })
    result = BacktestResult(trades=[], equity_curve=equity)
    assert result.sharpe_ratio > 0


def test_strategy_realistic_usage(data_with_volatility: pl.DataFrame) -> None:
    """
    Интеграционный тест: полный цикл стратегии с проверкой
   , что движок возвращает корректные метрики.
    """

    class SmaCrossStrategy(Strategy):
        """Простая стратегия на пересечении SMA."""

        def init(self) -> None:
            # Рассчитываем SMA в init
            close_series = pl.Series("close", self.close)
            self.sma_fast = close_series.to_numpy().copy()
            self.sma_slow = close_series.to_numpy().copy()

        def next(self, i: int) -> None:
            if i < 3:
                return

            # Простейшее пересечение SMA (эмуляция)
            if i == 3:  # сигнал на покупку
                if not self.in_position:
                    self.buy(size=1.0)
            if i == 6:  # сигнал на продажу
                if self.in_position:
                    self.close_position()

    engine = BacktestEngine()
    result = engine.run(SmaCrossStrategy, data_with_volatility)
    assert result.total_trades >= 1
    assert isinstance(result.to_dict(), dict)


def test_trade_list_is_not_shared(sample_data: pl.DataFrame) -> None:
    """Проверяет, что trades возвращает копию, а не ссылку."""
    strat = BuyAndHoldStrategy(sample_data)
    trades1 = strat.trades
    trades2 = strat.trades
    assert trades1 is not trades2
