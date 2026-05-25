"""
Базовый класс для всех индикаторов бэктестера.

Определяет единый интерфейс для расчёта индикаторов:
- BaseIndicator — абстрактный базовый класс
- IndicatorType — перечисление типов индикаторов
- IndicatorResult — датакласс результата расчёта
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, ClassVar, Optional

import polars as pl


class IndicatorType(Enum):
    """Перечисление типов индикаторов по способу отображения."""

    OVERLAY = auto()       # Рисуется поверх свечей (SMA, EMA, Bollinger)
    OSCILLATOR = auto()    # Рисуется на отдельной панели (RSI, MACD)
    VOLUME_PROFILE = auto() # Гистограмма объёма по ценовым уровням


@dataclass
class IndicatorResult:
    """
    Результат расчёта индикатора.

    Содержит один или несколько рядов данных для отображения на графике.

    Атрибуты:
        data: Polars DataFrame с колонкой date и одним/несколькими рядами значений.
        series_names: Словарь {имя_ряда: цвет_линии} для отрисовки.
        panel: Название панели (для осцилляторов — отдельная панель под графиком).
        overlay: Флаг — рисовать поверх свечей (True) или на отдельной панели (False).
    """

    data: pl.DataFrame
    series_names: dict[str, str] = field(default_factory=dict)
    panel: str = ""
    overlay: bool = True


class BaseIndicator(ABC):
    """
    Абстрактный базовый класс для всех индикаторов.

    Каждый индикатор должен реализовать:
    - name — уникальное имя индикатора
    - params — словарь параметров с их значениями
    - indicator_type — тип индикатора (OVERLAY / OSCILLATOR / VOLUME_PROFILE)
    - calculate(data) — метод расчёта, возвращающий IndicatorResult

    Пример использования:
        class SMA(BaseIndicator):
            name = "SMA"
            params = {"period": 20}
            indicator_type = IndicatorType.OVERLAY

            def calculate(self, data: pl.DataFrame) -> IndicatorResult:
                ...
    """

    # Уникальное имя индикатора (переопределяется в наследниках)
    name: ClassVar[str] = ""
    # Параметры индикатора со значениями по умолчанию
    params: ClassVar[dict[str, Any]] = {}
    # Тип индикатора (способ отображения)
    indicator_type: ClassVar[IndicatorType] = IndicatorType.OVERLAY

    # Минимальное количество баров, необходимое для расчёта
    min_bars: ClassVar[int] = 1

    def __init__(self, **kwargs: Any) -> None:
        """
        Инициализирует индикатор с переопределёнными параметрами.

        Параметры:
            **kwargs: Параметры для переопределения значений по умолчанию.
                      Например: SMA(period=50) переопределит period=20 на period=50.

        Исключения:
            ValueError: Если передан неизвестный параметр.
        """
        # Создаём копию параметров по умолчанию для экземпляра
        self._params: dict[str, Any] = dict(self.__class__.params)

        for key, value in kwargs.items():
            if key not in self._params:
                raise ValueError(
                    f"Индикатор '{self.name}' не поддерживает параметр '{key}'. "
                    f"Доступные параметры: {list(self._params.keys())}"
                )
            self._params[key] = value

    @property
    def display_name(self) -> str:
        """
        Возвращает отображаемое имя индикатора с текущими параметрами.

        Например: "SMA(20)", "EMA(50)", "RSI(14)".
        """
        params_str = ", ".join(str(v) for v in self._params.values())
        return f"{self.name}({params_str})"

    @abstractmethod
    def calculate(self, data: pl.DataFrame) -> IndicatorResult:
        """
        Рассчитывает значения индикатора на переданных свечных данных.

        Параметры:
            data: Polars DataFrame с колонками date, open, high, low, close, volume.

        Возвращает:
            IndicatorResult с рассчитанными значениями.

        Исключения:
            ValueError: Если данных недостаточно для расчёта.
        """
        ...

    def validate_data(self, data: pl.DataFrame) -> None:
        """
        Проверяет, что данные содержат необходимые колонки и достаточно строк.

        Параметры:
            data: Polars DataFrame для проверки.

        Исключения:
            ValueError: Если данных недостаточно или отсутствуют колонки.
        """
        required_cols = ["date", "open", "high", "low", "close"]
        for col in required_cols:
            if col not in data.columns:
                raise ValueError(
                    f"DataFrame должен содержать колонку '{col}' для расчёта "
                    f"индикатора '{self.name}'"
                )

        if len(data) < self.min_bars:
            raise ValueError(
                f"Недостаточно данных для расчёта индикатора '{self.name}': "
                f"требуется минимум {self.min_bars} баров, получено {len(data)}"
            )

    def __repr__(self) -> str:
        """Строковое представление индикатора."""
        return f"<{self.display_name}>"
