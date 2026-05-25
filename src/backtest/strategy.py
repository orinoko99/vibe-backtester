"""
Базовый класс стратегии для бэктестинга.

Определяет интерфейс, который должны реализовывать пользовательские
торговые стратегии: методы init() и next(i).

User defined strategies should inherit from Strategy and implement:
- init() — для подготовки индикаторов и переменных
- next(i) — вызывается на каждой свече с индексом i
"""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl

from .models import Order, PositionSide, Trade


class Strategy:
    """
    Базовый класс для всех торговых стратегий.

    Пользовательские стратегии наследуются от этого класса и
    переопределяют методы init() и next(i).

    Атрибуты:
        data (pl.DataFrame): Полные свечные данные (OHLCV).
        open (np.ndarray): Массив цен открытия.
        high (np.ndarray): Массив максимальных цен.
        low (np.ndarray): Массив минимальных цен.
        close (np.ndarray): Массив цен закрытия.
        volume (np.ndarray): Массив объёмов.
        date (np.ndarray): Массив дат.
        _orders (list[Order]): Список активных ордеров.
        _trades (list[Trade]): Список завершённых сделок.
        _position_size (float): Текущий размер позиции (0 — нет позиции).
        _position_side (PositionSide | None): Текущая сторона позиции.
        _entry_price (float): Цена входа в текущую позицию.
        _entry_bar (int): Индекс бара входа в текущую позицию.
        _entry_time (str): Время входа в текущую позицию.
        _equity (list[float]): История equity для кривой капитала.
    """

    def __init__(self, data: pl.DataFrame) -> None:
        """
        Инициализирует стратегию с данными.

        Параметры:
            data: Polars DataFrame с колонками date, open, high, low, close, volume.
        """
        self.data: pl.DataFrame = data

        # Преобразуем колонки в numpy для быстрого доступа по индексу
        self.open: np.ndarray = data["open"].to_numpy()
        self.high: np.ndarray = data["high"].to_numpy()
        self.low: np.ndarray = data["low"].to_numpy()
        self.close: np.ndarray = data["close"].to_numpy()
        self.volume: np.ndarray = data["volume"].to_numpy() if "volume" in data.columns else np.zeros(len(data))
        self.date: np.ndarray = data["date"].to_numpy()

        # Состояние стратегии
        self._current_index: int = -1
        self._orders: list[Order] = []
        self._trades: list[Trade] = []
        self._position_size: float = 0.0
        self._position_side: PositionSide | None = None
        self._entry_price: float = 0.0
        self._entry_bar: int = 0
        self._entry_time: str = ""
        self._equity: list[float] = []
        self._last_sl: float | None = None
        self._last_tp: float | None = None

    def init(self) -> None:
        """
        Вызывается один раз перед началом прогона стратегии.

        Используется для расчёта индикаторов, инициализации переменных.
        """
        ...

    def next(self, i: int) -> None:
        """
        Вызывается на каждой свече (баре) после init().

        Параметры:
            i: Индекс текущей свечи в data.
        """
        ...

    def buy(
        self,
        size: float = 1.0,
        price: float | None = None,
        stop_loss: float | None = None,
        take_profit: float | None = None,
    ) -> Order | None:
        """
        Открывает длинную позицию (или увеличивает существующую).

        Параметры:
            size: Размер позиции.
            price: Цена входа (None = цена закрытия текущего бара).
            stop_loss: Цена стоп-лосса.
            take_profit: Цена тейк-профита.

        Возвращает:
            Order или None, если уже есть позиция того же направления.
        """
        if self._position_side == "long":
            return None

        self._last_sl = stop_loss
        self._last_tp = take_profit

        order = Order(
            side="buy",
            size=size,
            price=price if price is not None else self.close[self._current_index],
            bar_index=self._current_index,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        self._orders.append(order)
        return order

    def sell(
        self,
        size: float = 1.0,
        price: float | None = None,
        stop_loss: float | None = None,
        take_profit: float | None = None,
    ) -> Order | None:
        """
        Открывает короткую позицию (или увеличивает существующую).

        Параметры:
            size: Размер позиции.
            price: Цена входа (None = цена закрытия текущего бара).
            stop_loss: Цена стоп-лосса.
            take_profit: Цена тейк-профита.

        Возвращает:
            Order или None, если уже есть позиция того же направления.
        """
        if self._position_side == "short":
            return None

        self._last_sl = stop_loss
        self._last_tp = take_profit

        order = Order(
            side="sell",
            size=size,
            price=price if price is not None else self.close[self._current_index],
            bar_index=self._current_index,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        self._orders.append(order)
        return order

    def close_position(self, price: float | None = None) -> None:
        """
        Закрывает текущую открытую позицию.

        Параметры:
            price: Цена закрытия (None = цена закрытия текущего бара).
        """
        if self._position_size == 0 or self._position_side is None:
            return

        exit_price = price if price is not None else self.close[self._current_index]
        exit_time = str(self.date[self._current_index])

        # Рассчитываем P&L
        if self._position_side == "long":
            pnl = (exit_price - self._entry_price) * self._position_size
        else:
            pnl = (self._entry_price - exit_price) * self._position_size

        pnl_pct = pnl / (self._entry_price * self._position_size) * 100.0 if self._entry_price > 0 else 0.0

        trade = Trade(
            entry_bar=self._entry_bar,
            exit_bar=self._current_index,
            entry_price=self._entry_price,
            exit_price=exit_price,
            size=self._position_size,
            side=self._position_side,
            pnl=pnl,
            pnl_pct=pnl_pct,
            entry_time=self._entry_time,
            exit_time=exit_time,
        )
        self._trades.append(trade)

        # Сбрасываем позицию
        self._position_size = 0.0
        self._position_side = None
        self._entry_price = 0.0
        self._entry_bar = 0
        self._entry_time = ""

    @property
    def position_size(self) -> float:
        """Возвращает текущий размер позиции."""
        return self._position_size

    @property
    def position_side(self) -> PositionSide | None:
        """Возвращает текущую сторону позиции (long/short/None)."""
        return self._position_side

    @property
    def in_position(self) -> bool:
        """True, если есть открытая позиция."""
        return self._position_size > 0

    @property
    def trades(self) -> list[Trade]:
        """Возвращает список всех завершённых сделок."""
        return self._trades.copy()
