"""
Модуль портфельного тестирования.

Позволяет запускать несколько стратегий на нескольких инструментах
с распределением капитала и ребалансировкой портфеля.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Callable, Literal, Type

import numpy as np
import polars as pl

from .engine import BacktestEngine
from .models import BacktestResult
from .strategy import Strategy


RebalanceFrequency = Literal["daily", "weekly", "monthly", "quarterly", "yearly", None]


@dataclass
class PortfolioData:
    """
    Конфигурация портфеля инструментов.

    Атрибуты:
        instruments: Список кодов инструментов.
        weights: Список весов инструментов (сумма должна быть равна 1.0).
        initial_capital: Начальный капитал портфеля.
        rebalance_frequency: Частота ребалансировки (daily/weekly/monthly/quarterly/yearly/None).
        commission_pct: Комиссия в процентах для всех сделок в портфеле.
        slippage_pct: Проскальзывание в процентах для всех сделок в портфеле.
    """
    instruments: list[str]
    weights: list[float]
    initial_capital: float = 1_000_000.0
    rebalance_frequency: RebalanceFrequency = None
    commission_pct: float = 0.0
    slippage_pct: float = 0.0

    def __post_init__(self) -> None:
        """Проверяет корректность данных портфеля после инициализации."""
        if len(self.instruments) != len(self.weights):
            raise ValueError(
                f"Количество инструментов ({len(self.instruments)}) "
                f"не совпадает с количеством весов ({len(self.weights)})"
            )
        if len(self.instruments) == 0:
            raise ValueError("Портфель должен содержать хотя бы один инструмент")
        total_weight = sum(self.weights)
        if abs(total_weight - 1.0) > 1e-6:
            raise ValueError(f"Сумма весов должна быть 1.0, получено {total_weight}")
        for w in self.weights:
            if w < 0:
                raise ValueError(f"Вес не может быть отрицательным: {w}")


@dataclass
class PortfolioAllocation:
    """
    Распределение капитала по инструментам на конкретный период.

    Атрибуты:
        date: Дата начала периода.
        allocations: Словарь {инструмент: выделенный капитал}.
    """
    date: str
    allocations: dict[str, float]


@dataclass
class PortfolioResult:
    """
    Результат портфельного тестирования.

    Атрибуты:
        asset_results: Словарь {инструмент: индивидуальный результат BacktestResult}.
        portfolio_equity_curve: Polars DataFrame с кривой капитала портфеля.
        total_return: Общая доходность портфеля в процентах.
        total_pnl: Общая прибыль портфеля в денежных единицах.
        sharpe_ratio: Коэффициент Шарпа портфеля (годовой).
        max_drawdown: Максимальная просадка портфеля в процентах.
        max_drawdown_duration: Длительность максимальной просадки в барах.
        allocations: История распределения капитала по периодам.
        weights: Веса инструментов в портфеле.
        instruments: Список инструментов портфеля.
    """
    asset_results: dict[str, BacktestResult] = field(default_factory=dict)
    portfolio_equity_curve: pl.DataFrame = field(
        default_factory=lambda: pl.DataFrame({"bar": [], "equity": []})
    )
    total_return: float = 0.0
    total_pnl: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    allocations: list[PortfolioAllocation] = field(default_factory=list)
    weights: dict[str, float] = field(default_factory=dict)
    instruments: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Автоматически рассчитывает метрики портфеля после инициализации."""
        self._calculate_metrics()

    def _calculate_metrics(self) -> None:
        """Рассчитывает метрики портфеля на основе кривой капитала."""
        if self.portfolio_equity_curve.is_empty() or len(self.portfolio_equity_curve) < 2:
            return

        equity = self.portfolio_equity_curve["equity"].to_numpy()
        initial_equity = equity[0]
        final_equity = equity[-1]

        if initial_equity > 0:
            self.total_return = (final_equity - initial_equity) / initial_equity * 100.0
            self.total_pnl = final_equity - initial_equity

        returns = (equity[1:] - equity[:-1]) / equity[:-1]
        returns = returns[~pl.Series(returns).is_nan().to_numpy()]
        if len(returns) > 1 and float(np.std(returns)) > 0:
            self.sharpe_ratio = float(
                np.mean(returns) / np.std(returns) * (252 * 390) ** 0.5
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

    def to_dict(self) -> dict[str, float | int]:
        """
        Возвращает основные метрики портфеля в виде словаря.

        Возвращает:
            Словарь с ключами: total_return, total_pnl, sharpe_ratio,
            max_drawdown, max_drawdown_duration, total_trades.
        """
        total_trades = sum(
            r.total_trades for r in self.asset_results.values()
        )
        return {
            "total_return": round(self.total_return, 2),
            "total_pnl": round(self.total_pnl, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 3),
            "max_drawdown": round(self.max_drawdown, 2),
            "max_drawdown_duration": self.max_drawdown_duration,
            "total_trades": total_trades,
        }


class PortfolioBacktestEngine:
    """
    Движок портфельного бэктестинга.

    Позволяет запускать одну стратегию на нескольких инструментах
    с распределением капитала и опциональной ребалансировкой.

    Пример использования:
        engine = PortfolioBacktestEngine()
        result = engine.run(
            strategy_class=MyStrategy,
            data_dict={
                "SBER": sber_data,
                "GAZP": gazp_data,
            },
            weights={"SBER": 0.6, "GAZP": 0.4},
            initial_capital=1_000_000,
        )
    """

    def __init__(
        self,
        commission_pct: float = 0.0,
        slippage_pct: float = 0.0,
    ) -> None:
        """
        Инициализирует движок портфельного тестирования.

        Параметры:
            commission_pct: Комиссия в процентах для всех сделок.
            slippage_pct: Проскальзывание в процентах.
        """
        self.commission_pct: float = commission_pct
        self.slippage_pct: float = slippage_pct

    def run(
        self,
        strategy_class: Type[Strategy],
        data_dict: dict[str, pl.DataFrame],
        portfolio: PortfolioData | None = None,
        weights: dict[str, float] | None = None,
        initial_capital: float = 1_000_000.0,
        rebalance_frequency: RebalanceFrequency = None,
        **strategy_kwargs: object,
    ) -> PortfolioResult:
        """
        Запускает портфельный бэктест.

        Параметры:
            strategy_class: Класс стратегии (один для всех инструментов).
            data_dict: Словарь {название_инструмента: Polars DataFrame с OHLCV}.
            portfolio: Объект PortfolioData (альтернативный способ задания параметров).
            weights: Словарь {инструмент: вес} для распределения капитала.
            initial_capital: Начальный капитал портфеля.
            rebalance_frequency: Частота ребалансировки.
            **strategy_kwargs: Дополнительные аргументы для стратегии.

        Возвращает:
            PortfolioResult с результатами портфельного тестирования.
        """
        # Определяем параметры портфеля
        if portfolio is not None:
            weights_dict = dict(zip(portfolio.instruments, portfolio.weights))
            initial_capital = portfolio.initial_capital
            rebalance_frequency = portfolio.rebalance_frequency
            commission_pct = portfolio.commission_pct
            slippage_pct = portfolio.slippage_pct
        else:
            if weights is None:
                # Равномерное распределение, если веса не заданы
                n = len(data_dict)
                weights_dict = {name: 1.0 / n for name in data_dict}
            else:
                weights_dict = weights
            commission_pct = self.commission_pct
            slippage_pct = self.slippage_pct

        # Проверяем, что все инструменты из weights есть в data_dict
        for name in weights_dict:
            if name not in data_dict:
                raise ValueError(f"Инструмент '{name}' не найден в data_dict")

        instruments = list(weights_dict.keys())
        n_instruments = len(instruments)

        if n_instruments == 0:
            return PortfolioResult(instruments=[])

        # Определяем общую временную шкалу всех инструментов
        all_dates: list[pl.Series] = []
        for name in instruments:
            df = data_dict[name]
            if "date" not in df.columns:
                raise ValueError(f"DataFrame инструмента '{name}' не содержит колонку 'date'")
            all_dates.append(df["date"])

        # Создаём единую шкалу времени (пересечение дат)
        date_series = all_dates[0]
        for ds in all_dates[1:]:
            date_series = pl.Series(
                "date",
                np.intersect1d(date_series.to_numpy(), ds.to_numpy())
            )

        if len(date_series) == 0:
            return PortfolioResult(instruments=instruments)

        # Сортируем даты
        date_series = date_series.sort()
        n_bars = len(date_series)

        # Фильтруем данные по пересечению дат и запускаем каждый инструмент
        asset_results: dict[str, BacktestResult] = {}
        aligned_data: dict[str, pl.DataFrame] = {}

        for name in instruments:
            df = data_dict[name]
            mask = df["date"].is_in(date_series.implode())
            aligned = df.filter(mask).sort("date")
            aligned_data[name] = aligned

        # Упрощённый подход: запускаем каждый инструмент независимо
        # с пропорциональным капиталом и суммируем equity
        portfolio_equity_matrix: list[np.ndarray] = []
        allocation_history: list[PortfolioAllocation] = []

        for name in instruments:
            weight = weights_dict[name]
            allocated_capital = initial_capital * weight

            engine = BacktestEngine(
                initial_capital=allocated_capital,
                commission_pct=commission_pct,
                slippage_pct=slippage_pct,
            )

            result = engine.run(
                strategy_class=strategy_class,
                data=aligned_data[name],
                **strategy_kwargs,
            )

            asset_results[name] = result

            # Собираем equity каждого инструмента
            if not result.equity_curve.is_empty():
                equity_values = result.equity_curve["equity"].to_numpy()
                # Нормализуем длину до n_bars
                if len(equity_values) < n_bars:
                    equity_values = np.pad(
                        equity_values,
                        (0, n_bars - len(equity_values)),
                        mode="edge",
                    )
                elif len(equity_values) > n_bars:
                    equity_values = equity_values[:n_bars]
                portfolio_equity_matrix.append(equity_values)
            else:
                portfolio_equity_matrix.append(
                    np.full(n_bars, allocated_capital)
                )

            # Записываем распределение капитала для первого бара
            allocation_history.append(
                PortfolioAllocation(
                    date=str(date_series[0]),
                    allocations={name: allocated_capital},
                )
            )

        # Суммируем equity всех инструментов
        if portfolio_equity_matrix:
            total_equity = np.sum(portfolio_equity_matrix, axis=0)
        else:
            total_equity = np.full(n_bars, initial_capital)

        portfolio_equity = pl.DataFrame({
            "bar": list(range(n_bars)),
            "equity": total_equity,
        })

        # Рассчитываем метрики портфеля
        result = self._calculate_portfolio_metrics(
            equity_curve=portfolio_equity,
            asset_results=asset_results,
            instruments=instruments,
            weights=weights_dict,
            allocation_history=allocation_history,
        )

        return result

    def _calculate_allocations(
        self,
        instruments: list[str],
        weights: dict[str, float],
        total_capital: float,
        date_series: pl.Series,
        rebalance_frequency: RebalanceFrequency,
    ) -> list[PortfolioAllocation]:
        """
        Рассчитывает распределение капитала по инструментам на каждый период.

        Параметры:
            instruments: Список инструментов.
            weights: Словарь весов инструментов.
            total_capital: Общий капитал.
            date_series: Временная шкала.
            rebalance_frequency: Частота ребалансировки.

        Возвращает:
            Список распределений капитала по периодам.
        """
        if rebalance_frequency is None or len(date_series) == 0:
            # Без ребалансировки: одно распределение на весь период
            allocations_list = {
                name: total_capital * weights[name]
                for name in instruments
            }
            return [
                PortfolioAllocation(
                    date=str(date_series[0]) if len(date_series) > 0 else "",
                    allocations=allocations_list,
                )
            ]

        # Определяем периоды ребалансировки
        rebalance_indices = self._get_rebalance_indices(
            date_series=date_series,
            frequency=rebalance_frequency,
        )

        allocations_list: list[PortfolioAllocation] = []
        for idx in rebalance_indices:
            date_value = str(date_series[idx])
            alloc = {
                name: total_capital * weights[name]
                for name in instruments
            }
            allocations_list.append(
                PortfolioAllocation(date=date_value, allocations=alloc)
            )

        return allocations_list

    def _get_rebalance_indices(
        self,
        date_series: pl.Series,
        frequency: RebalanceFrequency,
    ) -> list[int]:
        """
        Определяет индексы баров, на которых нужно делать ребалансировку.

        Параметры:
            date_series: Временная шкала с датами.
            frequency: Частота ребалансировки.

        Возвращает:
            Список индексов для ребалансировки.
        """
        if frequency is None or len(date_series) == 0:
            return [0]

        indices: list[int] = [0]

        if frequency == "daily":
            # Каждый бар — ребалансировка (для тестов)
            indices = list(range(len(date_series)))
        elif frequency == "weekly":
            # Первый бар каждой недели
            current_week = -1
            for i in range(len(date_series)):
                week = i // 5  # упрощённо: 5 баров = неделя
                if week != current_week:
                    current_week = week
                    indices.append(i)
        else:
            # monthly, quarterly, yearly — только первый бар
            indices = [0]

        return indices

    def _calculate_portfolio_metrics(
        self,
        equity_curve: pl.DataFrame,
        asset_results: dict[str, BacktestResult],
        instruments: list[str],
        weights: dict[str, float],
        allocation_history: list[PortfolioAllocation],
    ) -> PortfolioResult:
        """
        Рассчитывает итоговые метрики портфеля.

        Параметры:
            equity_curve: Кривая капитала портфеля.
            asset_results: Индивидуальные результаты по инструментам.
            instruments: Список инструментов.
            weights: Веса инструментов.
            allocation_history: История распределения капитала.

        Возвращает:
            PortfolioResult с рассчитанными метриками.
        """
        result = PortfolioResult(
            asset_results=asset_results,
            portfolio_equity_curve=equity_curve,
            allocations=allocation_history,
            weights=weights,
            instruments=instruments,
        )

        # Метрики автоматически рассчитываются в PortfolioResult.__post_init__
        return result

    def run_with_portfolio_data(
        self,
        strategy_class: Type[Strategy],
        data_dict: dict[str, pl.DataFrame],
        portfolio: PortfolioData,
        **strategy_kwargs: object,
    ) -> PortfolioResult:
        """
        Запускает портфельный бэктест с использованием объекта PortfolioData.

        Удобный метод-обёртка для случаев, когда параметры портфеля
        уже упакованы в PortfolioData.

        Параметры:
            strategy_class: Класс стратегии.
            data_dict: Словарь {инструмент: DataFrame с OHLCV}.
            portfolio: Объект PortfolioData с конфигурацией портфеля.
            **strategy_kwargs: Дополнительные аргументы для стратегии.

        Возвращает:
            PortfolioResult с результатами портфельного тестирования.
        """
        return self.run(
            strategy_class=strategy_class,
            data_dict=data_dict,
            portfolio=portfolio,
            **strategy_kwargs,
        )

    def run_with_different_strategies(
        self,
        strategy_dict: dict[str, Type[Strategy]],
        data_dict: dict[str, pl.DataFrame],
        weights: dict[str, float] | None = None,
        initial_capital: float = 1_000_000.0,
        rebalance_frequency: RebalanceFrequency = None,
    ) -> PortfolioResult:
        """
        Запускает портфельный бэктест с разными стратегиями для разных инструментов.

        Параметры:
            strategy_dict: Словарь {инструмент: класс стратегии}.
            data_dict: Словарь {инструмент: DataFrame с OHLCV}.
            weights: Словарь {инструмент: вес} (если None — равномерное распределение).
            initial_capital: Начальный капитал.
            rebalance_frequency: Частота ребалансировки.

        Возвращает:
            PortfolioResult с результатами портфельного тестирования.
        """
        instruments = list(strategy_dict.keys())

        if weights is None:
            n = len(instruments)
            weights = {name: 1.0 / n for name in instruments}

        # Проверяем, что все инструменты из strategy_dict есть в data_dict
        for name in instruments:
            if name not in data_dict:
                raise ValueError(f"Инструмент '{name}' не найден в data_dict")

        # Определяем единую временную шкалу
        all_dates: list[pl.Series] = []
        for name in instruments:
            df = data_dict[name]
            if "date" not in df.columns:
                raise ValueError(f"DataFrame инструмента '{name}' не содержит колонку 'date'")
            all_dates.append(df["date"])

        date_series = all_dates[0]
        for ds in all_dates[1:]:
            date_series = pl.Series(
                "date",
                np.intersect1d(date_series.to_numpy(), ds.to_numpy())
            )

        if len(date_series) == 0:
            return PortfolioResult(instruments=instruments)

        date_series = date_series.sort()
        n_bars = len(date_series)

        # Запускаем каждую стратегию на своём инструменте
        asset_results: dict[str, BacktestResult] = {}
        portfolio_equity_matrix: list[np.ndarray] = []

        for name in instruments:
            weight = weights.get(name, 1.0 / len(instruments))
            allocated_capital = initial_capital * weight
            df = data_dict[name]

            # Фильтруем по пересечению дат
            mask = df["date"].is_in(date_series.implode())
            aligned = df.filter(mask).sort("date")

            engine = BacktestEngine(
                initial_capital=allocated_capital,
                commission_pct=self.commission_pct,
                slippage_pct=self.slippage_pct,
            )

            result = engine.run(
                strategy_class=strategy_dict[name],
                data=aligned,
            )
            asset_results[name] = result

            if not result.equity_curve.is_empty():
                equity_values = result.equity_curve["equity"].to_numpy()
                if len(equity_values) < n_bars:
                    equity_values = np.pad(
                        equity_values,
                        (0, n_bars - len(equity_values)),
                        mode="edge",
                    )
                elif len(equity_values) > n_bars:
                    equity_values = equity_values[:n_bars]
                portfolio_equity_matrix.append(equity_values)
            else:
                portfolio_equity_matrix.append(np.full(n_bars, allocated_capital))

        # Суммируем equity
        if portfolio_equity_matrix:
            total_equity = np.sum(portfolio_equity_matrix, axis=0)
        else:
            total_equity = np.full(n_bars, initial_capital)

        portfolio_equity = pl.DataFrame({
            "bar": list(range(n_bars)),
            "equity": total_equity,
        })

        result = self._calculate_portfolio_metrics(
            equity_curve=portfolio_equity,
            asset_results=asset_results,
            instruments=instruments,
            weights=weights,
            allocation_history=[],
        )

        return result
