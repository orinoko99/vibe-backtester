#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модели данных для торговых инструментов и свечей.

Используется Pydantic v2 для валидации и сериализации.
Структуры соответствуют схеме таблиц SQLite-баз проекта.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class InstrumentType(str, Enum):
    """
    Тип торгового инструмента.
    """
    FUTURES = "futures"
    SHARES = "shares"


class Candle(BaseModel):
    """
    Модель одной минутной свечи.

    Соответствует строкам таблиц вида 'AAH6_M1' в SQLite-базах.
    Все числовые поля хранятся как float для единообразия расчётов.

    Поля:
        timestamp — время свечи (datetime)
        open — цена открытия
        high — максимальная цена
        low — минимальная цена
        close — цена закрытия
        volume — объём торгов
        open_interest — количество открытых позиций (опционально)
    """

    timestamp: datetime = Field(
        description="Время свечи (datetime)"
    )
    open: float = Field(
        ge=0.0, description="Цена открытия"
    )
    high: float = Field(
        ge=0.0, description="Максимальная цена"
    )
    low: float = Field(
        ge=0.0, description="Минимальная цена"
    )
    close: float = Field(
        ge=0.0, description="Цена закрытия"
    )
    volume: int = Field(
        ge=0, description="Объём торгов"
    )
    open_interest: Optional[int] = Field(
        default=None, ge=0, description="Количество открытых позиций"
    )

    @field_validator("high")
    @classmethod
    def high_must_be_ge_open_and_close(
        cls, value: float, info
    ) -> float:
        """
        Проверяет, что high >= max(open, close).
        """
        data = info.data
        if "open" in data and "close" in data:
            if value < max(data["open"], data["close"]):
                raise ValueError(
                    "high должен быть >= max(open, close)"
                )
        return value

    @field_validator("low")
    @classmethod
    def low_must_be_le_open_and_close(
        cls, value: float, info
    ) -> float:
        """
        Проверяет, что low <= min(open, close).
        """
        data = info.data
        if "open" in data and "close" in data:
            if value > min(data["open"], data["close"]):
                raise ValueError(
                    "low должен быть <= min(open, close)"
                )
        return value

    @field_validator("close")
    @classmethod
    def close_must_be_between_low_and_high(
        cls, value: float, info
    ) -> float:
        """
        Проверяет, что close находится между low и high.
        """
        data = info.data
        if "low" in data and "high" in data:
            if not (data["low"] <= value <= data["high"]):
                raise ValueError(
                    "close должен быть между low и high"
                )
        return value

    @property
    def body(self) -> float:
        """
        Тело свечи: |close - open|.
        """
        return abs(self.close - self.open)

    @property
    def upper_shadow(self) -> float:
        """
        Верхняя тень: high - max(open, close).
        """
        return self.high - max(self.open, self.close)

    @property
    def lower_shadow(self) -> float:
        """
        Нижняя тень: min(open, close) - low.
        """
        return min(self.open, self.close) - self.low

    @property
    def is_bullish(self) -> bool:
        """
        True, если свеча бычья (close > open).
        """
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        """
        True, если свеча медвежья (close < open).
        """
        return self.close < self.open


class InstrumentInfo(BaseModel):
    """
    Информация о торговом инструменте.

    Поля:
        sec_code — код инструмента (например 'AAH6')
        class_code — класс (например 'SPBFUT')
        instrument_type — тип инструмента (фьючерс/акция)
        name — человекочитаемое название (опционально)
        lot_size — размер лота (по умолчанию 1)
        min_step — минимальный шаг цены (опционально)
    """

    sec_code: str = Field(
        description="Код инструмента, напр. 'AAH6'"
    )
    class_code: str = Field(
        description="Код класса, напр. 'SPBFUT'"
    )
    instrument_type: InstrumentType = Field(
        description="Тип инструмента"
    )
    name: Optional[str] = Field(
        default=None, description="Человекочитаемое название"
    )
    lot_size: int = Field(
        default=1, ge=1, description="Размер лота"
    )
    min_step: Optional[float] = Field(
        default=None, ge=0.0, description="Минимальный шаг цены"
    )

    @property
    def table_name(self) -> str:
        """
        Имя таблицы в SQLite для минутных данных: 'SECCODE_M1'.
        """
        return f"{self.sec_code}_M1"
