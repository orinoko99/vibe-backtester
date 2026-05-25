"""
Движок бэктестинга для одиночных стратегий.

Прогоняет стратегию по историческим данным, исполняет ордера,
отслеживает позиции и рассчитывает метрики производительности.
"""

from __future__ import annotations

from typing import Type

import polars as pl

from .models import BacktestResult, Order, PositionSide, Trade
from .strategy import Strategy


class BacktestEngine:
    """
    Движок для прогона стратегии по историческим данным.

    Принимает класс стратегии (не экземпляр) и свечные данные,
    создаёт экземпляр стратегии, прогоняет её по всем барам,
    исполняет ордера и возвращает результат.

    Атрибуты:
        initial_capital (float): Начальный капитал.
        commission_pct (float): Комиссия в процентах от объёма сделки.
        slippage_pct (float): Проскальзывание в процентах от цены.
    """

    def __init__(
        self,
        initial_capital: float = 100_000.0,
        commission_pct: float = 0.0,
        slippage_pct: float = 0.0,
    ) -> None:
        """
        Инициализирует движок бэктестинга.

        Параметры:
            initial_capital: Начальный капитал в денежных единицах.
            commission_pct: Комиссия в процентах (0.1 = 0.1%).
            slippage_pct: Проскальзывание в процентах (0.05 = 0.05%).
        """
        self.initial_capital: float = initial_capital
        self.commission_pct: float = commission_pct
        self.slippage_pct: float = slippage_pct
        self._total_commission: float = 0.0

    def run(
        self,
        strategy_class: Type[Strategy],
        data: pl.DataFrame,
        **strategy_kwargs: object,
    ) -> BacktestResult:
        """
        Запускает бэктест стратегии на исторических данных.

        Параметры:
            strategy_class: Класс стратегии (наследник Strategy).
            data: Polars DataFrame с колонками date, open, high, low, close, volume.
            **strategy_kwargs: Дополнительные аргументы для конструктора стратегии.

        Возвращает:
            BacktestResult с метриками и списком сделок.
        """
        # Проверяем наличие необходимых колонок
        required_cols = ["date", "open", "high", "low", "close"]
        for col in required_cols:
            if col not in data.columns:
                raise ValueError(f"DataFrame должен содержать колонку '{col}'")

        if data.is_empty():
            return BacktestResult()

        # Создаём экземпляр стратегии
        strategy = strategy_class(data, **strategy_kwargs)

        # Сохраняем ссылку на стратегию для доступа к equity
        self._strategy = strategy
        self._equity: list[float] = [self.initial_capital]

        # Вызываем init() — подготовка индикаторов
        strategy.init()

        n_bars = len(data)

        # Основной цикл по барам
        for i in range(n_bars):
            strategy._current_index = i

            # Проверяем стоп-лосс и тейк-профит для открытой позиции
            if strategy.in_position:
                self._check_sl_tp(strategy, i)

            # Исполняем накопленные ордера на открытие
            self._execute_pending_orders(strategy, i)

            # Вызываем next() стратегии
            strategy.next(i)

            # Исполняем новые ордера, созданные в next()
            self._execute_pending_orders(strategy, i)

            # Рассчитываем текущую equity
            self._update_equity(strategy, i)

        # Закрываем позицию в конце, если она ещё открыта
        if strategy.in_position:
            strategy._current_index = n_bars - 1
            strategy.close_position()

        # Формируем результат
        equity_curve = pl.DataFrame({
            "bar": list(range(len(self._equity))),
            "equity": self._equity,
        })

        # Переносим сделки из стратегии
        trades = strategy.trades

        result = BacktestResult(
            trades=trades,
            equity_curve=equity_curve,
        )

        return result

    def _execute_pending_orders(self, strategy: Strategy, bar_index: int) -> None:
        """
        Исполняет накопленные ордера стратегии.

        Рыночные ордера исполняются по цене закрытия текущего бара
        (или следующего открытия для более реалистичного моделирования).

        Параметры:
            strategy: Экземпляр стратегии.
            bar_index: Индекс текущего бара.
        """
        if not strategy._orders:
            return

        for order in strategy._orders:
            if order.order_type != "market":
                continue

            # Определяем цену исполнения с учётом проскальзывания
            execution_price = strategy.close[bar_index]
            if self.slippage_pct > 0:
                slippage = execution_price * self.slippage_pct / 100.0
                if order.side == "buy":
                    execution_price += slippage
                else:
                    execution_price -= slippage

            order.price = execution_price

            # Если есть открытая позиция противоположного направления — закрываем её
            if strategy.in_position:
                opposite = (
                    (strategy._position_side == "long" and order.side == "sell") or
                    (strategy._position_side == "short" and order.side == "buy")
                )
                if opposite:
                    strategy.close_position(price=execution_price)

            # Открываем новую позицию
            if not strategy.in_position:
                strategy._position_size = order.size
                strategy._position_side = "long" if order.side == "buy" else "short"
                strategy._entry_price = execution_price
                strategy._entry_bar = bar_index
                strategy._entry_time = str(strategy.date[bar_index])

                # Накопливаем комиссию
                trade_commission = execution_price * order.size * self.commission_pct / 100.0
                self._total_commission += trade_commission

        # Очищаем ордера после исполнения
        strategy._orders.clear()

    def _check_sl_tp(self, strategy: Strategy, bar_index: int) -> None:
        """
        Проверяет условия стоп-лосса и тейк-профита для открытой позиции.

        Параметры:
            strategy: Экземпляр стратегии.
            bar_index: Индекс текущего бара.
        """
        if not strategy.in_position:
            return

        sl = strategy._last_sl
        tp = strategy._last_tp

        if sl is None and tp is None:
            return

        current_low = strategy.low[bar_index]
        current_high = strategy.high[bar_index]

        if strategy._position_side == "long":
            if sl is not None and current_low <= sl:
                strategy.close_position(price=sl)
            elif tp is not None and current_high >= tp:
                strategy.close_position(price=tp)
        elif strategy._position_side == "short":
            if sl is not None and current_high >= sl:
                strategy.close_position(price=sl)
            elif tp is not None and current_low <= tp:
                strategy.close_position(price=tp)

    def _update_equity(self, strategy: Strategy, bar_index: int) -> None:
        """
        Рассчитывает текущую стоимость портфеля (equity).

        Equity = начальный капитал + P&L по открытой позиции.

        Параметры:
            strategy: Экземпляр стратегии.
            bar_index: Индекс текущего бара.
        """
        current_price = strategy.close[bar_index]
        unrealized_pnl = 0.0

        if strategy.in_position:
            if strategy._position_side == "long":
                unrealized_pnl = (current_price - strategy._entry_price) * strategy._position_size
            else:
                unrealized_pnl = (strategy._entry_price - current_price) * strategy._position_size

        # Суммируем P&L по закрытым сделкам
        realized_pnl = sum(t.pnl for t in strategy.trades)
        total_equity = self.initial_capital + realized_pnl + unrealized_pnl - self._total_commission

        self._equity.append(total_equity)
