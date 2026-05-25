"""
Модели данных для движка бэктестинга.

Содержит структуры данных для ордеров, позиций, сделок
и результатов бэктестинга.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import polars as pl


OrderSide = Literal["buy", "sell"]
OrderType = Literal["market", "limit", "stop"]
PositionSide = Literal["long", "short"]


@dataclass
class Order:
    """
    Ордер на покупку или продажу.

    Атрибуты:
        side: Сторона сделки (buy/sell).
        size: Размер позиции в единицах.
        price: Цена исполнения (для market — цена следующего бара).
        order_type: Тип ордера (market/limit/stop).
        bar_index: Индекс бара, на котором создан ордер.
        stop_loss: Цена стоп-лосса (опционально).
        take_profit: Цена тейк-профита (опционально).
    """
    side: OrderSide
    size: float
    price: float | None = None
    order_type: OrderType = "market"
    bar_index: int = 0
    stop_loss: float | None = None
    take_profit: float | None = None


@dataclass
class Trade:
    """
    Завершённая сделка (открытие + закрытие позиции).

    Атрибуты:
        entry_bar: Индекс бара входа.
        exit_bar: Индекс бара выхода.
        entry_price: Цена входа.
        exit_price: Цена выхода.
        size: Размер позиции.
        side: Сторона (long/short).
        pnl: Прибыль/убыток в пунктах.
        pnl_pct: Прибыль/убыток в процентах.
        entry_time: Время входа.
        exit_time: Время выхода.
    """
    entry_bar: int = 0
    exit_bar: int = 0
    entry_price: float = 0.0
    exit_price: float = 0.0
    size: float = 0.0
    side: PositionSide = "long"
    pnl: float = 0.0
    pnl_pct: float = 0.0
    entry_time: str = ""
    exit_time: str = ""


@dataclass
class BacktestResult:
    """
    Результат прогона бэктеста.

    Атрибуты:
        trades: Список всех совершённых сделок.
        equity_curve: DataFrame с кривой капитала (bar, equity).
        total_return: Общая доходность в процентах.
        total_pnl: Общая прибыль в пунктах.
        sharpe_ratio: Коэффициент Шарпа (годовой).
        max_drawdown: Максимальная просадка в процентах.
        max_drawdown_duration: Длительность макс. просадки в барах.
        win_rate: Процент прибыльных сделок.
        total_trades: Общее количество сделок.
        avg_holding_bars: Средняя длительность сделки в барах.
    """
    trades: list[Trade] = field(default_factory=list)
    equity_curve: pl.DataFrame = field(default_factory=lambda: pl.DataFrame({"bar": [], "equity": []}))
    total_return: float = 0.0
    total_pnl: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    win_rate: float = 0.0
    total_trades: int = 0
    avg_holding_bars: float = 0.0

    def __post_init__(self) -> None:
        """Автоматически рассчитывает метрики после инициализации."""
        self._calculate_metrics()

    def _calculate_equity_metrics(self) -> None:
        """Рассчитывает метрики на основе кривой капитала."""
        if self.equity_curve.is_empty():
            return

        equity = self.equity_curve["equity"].to_numpy()
        if len(equity) < 2:
            return

        initial_equity = equity[0]
        final_equity = equity[-1]
        if initial_equity > 0:
            self.total_return = (final_equity - initial_equity) / initial_equity * 100.0

        returns = (equity[1:] - equity[:-1]) / equity[:-1]
        returns = returns[np.isfinite(returns)]
        if len(returns) > 1 and returns.std() > 0:
            self.sharpe_ratio = float(
                returns.mean() / returns.std() * (252 * 390) ** 0.5
            )

        peak = equity[0]
        max_dd = 0.0
        max_dd_duration = 0
        current_duration = 0

        for value in equity:
            if value > peak:
                peak = value
                current_duration = 0
            else:
                dd = (peak - value) / peak * 100.0
                if dd > max_dd:
                    max_dd = dd
                    max_dd_duration = current_duration
                current_duration += 1

        self.max_drawdown = max_dd
        self.max_drawdown_duration = max_dd_duration

    def _calculate_metrics(self) -> None:
        """Рассчитывает метрики производительности на основе списка сделок."""
        self.total_trades = len(self.trades)

        if self.total_trades == 0:
            self._calculate_equity_metrics()
            return

        winning_trades = [t for t in self.trades if t.pnl > 0]
        self.win_rate = len(winning_trades) / self.total_trades * 100.0

        self.total_pnl = sum(t.pnl for t in self.trades)

        self._calculate_equity_metrics()

        if self.total_trades > 0:
            total_bars = sum(t.exit_bar - t.entry_bar for t in self.trades)
            self.avg_holding_bars = total_bars / self.total_trades

    def to_dict(self) -> dict[str, float | int]:
        """
        Возвращает основные метрики в виде словаря.

        Возвращает:
            Словарь с ключами: total_return, total_pnl, sharpe_ratio,
            max_drawdown, win_rate, total_trades, avg_holding_bars.
        """
        return {
            "total_return": round(self.total_return, 2),
            "total_pnl": round(self.total_pnl, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 3),
            "max_drawdown": round(self.max_drawdown, 2),
            "max_drawdown_duration": self.max_drawdown_duration,
            "win_rate": round(self.win_rate, 1),
            "total_trades": self.total_trades,
            "avg_holding_bars": round(self.avg_holding_bars, 1),
        }
