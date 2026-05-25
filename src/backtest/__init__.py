"""
Пакет движка бэктестинга.

Содержит:
- Strategy — базовый класс для пользовательских стратегий
- BacktestEngine — движок для прогона одиночных стратегий
- PortfolioBacktestEngine — движок для портфельного тестирования
- PortfolioData, PortfolioResult — модели данных портфеля
- BacktestResult, Trade, Order, Position — модели данных
"""

from .engine import BacktestEngine
from .models import BacktestResult, Order, PositionSide, Trade
from .portfolio import PortfolioBacktestEngine, PortfolioData, PortfolioResult
from .strategy import Strategy

__all__ = [
    "BacktestEngine",
    "BacktestResult",
    "Order",
    "PortfolioBacktestEngine",
    "PortfolioData",
    "PortfolioResult",
    "PositionSide",
    "Strategy",
    "Trade",
]
