"""
Пакет движка бэктестинга.

Содержит:
- Strategy — базовый класс для пользовательских стратегий
- BacktestEngine — движок для прогона стратегий
- BacktestResult, Trade, Order, Position — модели данных
"""

from .engine import BacktestEngine
from .models import BacktestResult, Order, PositionSide, Trade
from .strategy import Strategy

__all__ = [
    "BacktestEngine",
    "BacktestResult",
    "Order",
    "PositionSide",
    "Strategy",
    "Trade",
]
