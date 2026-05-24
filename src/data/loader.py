#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль динамической загрузки свечных данных.

Реализует пагинацию с паддингом:
- загружается только видимая область + padding экранов с каждой стороны
- при смещении видимой области данные догружаются автоматически
- минимизируются повторные запросы к БД
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from src.data.database import DatabaseManager
from src.data.models import Candle
from src.utils.config import CONFIG


class DataLoader:
    """
    Загрузчик свечных данных с динамической пагинацией.

    Управляет видимым временным окном и автоматически подгружает
    данные с запасом (padding) с каждой стороны.

    Атрибуты:
        sec_code — код инструмента
        visible_start — начало видимого окна
        visible_end — конец видимого окна
        _candles — все загруженные свечи (отсортированы)
        _padding_factor — количество экранов запаса с каждой стороны
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        sec_code: str,
        padding_factor: int = 2,
    ) -> None:
        """
        Инициализация загрузчика.

        Параметры:
            db_manager — менеджер подключений к БД
            sec_code — код инструмента (например 'AAH6')
            padding_factor — сколько видимых окон загружать
                             с каждой стороны (по умолчанию 2)
        """
        self._db: DatabaseManager = db_manager
        self.sec_code: str = sec_code
        self._padding_factor: int = padding_factor

        # Текущее видимое окно (временной диапазон)
        self.visible_start: Optional[datetime] = None
        self.visible_end: Optional[datetime] = None

        # Все загруженные свечи (включая padding)
        self._candles: List[Candle] = []

        # Границы загруженных данных (с учётом padding)
        self._loaded_start: Optional[datetime] = None
        self._loaded_end: Optional[datetime] = None

    @property
    def visible_duration(self) -> Optional[timedelta]:
        """
        Длительность видимого окна.

        Возвращает None, если окно не задано.
        """
        if self.visible_start is None or self.visible_end is None:
            return None
        return self.visible_end - self.visible_start

    @property
    def loaded_candles(self) -> List[Candle]:
        """
        Возвращает все загруженные свечи (с паддингом).
        """
        return self._candles.copy()

    @property
    def visible_candles(self) -> List[Candle]:
        """
        Возвращает свечи только в пределах видимого окна.
        """
        if (
            self.visible_start is None
            or self.visible_end is None
            or not self._candles
        ):
            return []

        return [
            c
            for c in self._candles
            if self.visible_start <= c.timestamp <= self.visible_end
        ]

    @property
    def has_data(self) -> bool:
        """
        Проверяет, загружены ли какие-либо данные.
        """
        return len(self._candles) > 0

    def _calculate_padded_range(
        self,
    ) -> Optional[Tuple[datetime, datetime]]:
        """
        Рассчитывает диапазон загрузки с учётом padding.

        Берёт видимое окно и расширяет его на padding_factor
        с каждой стороны.

        Возвращает (start, end) или None, если окно не задано.
        """
        if self.visible_start is None or self.visible_end is None:
            return None

        duration = self.visible_end - self.visible_start
        pad = duration * self._padding_factor

        return (self.visible_start - pad, self.visible_end + pad)

    def _needs_reload(
        self, padded_start: datetime, padded_end: datetime
    ) -> bool:
        """
        Проверяет, нужно ли перезагружать данные.

        Возвращает True, если загруженные данные не покрывают
        запрошенный padded-диапазон.
        """
        if not self._candles:
            return True
        if self._loaded_start is None or self._loaded_end is None:
            return True

        return (
            padded_start < self._loaded_start
            or padded_end > self._loaded_end
        )

    def set_visible_range(
        self,
        start: datetime,
        end: datetime,
    ) -> List[Candle]:
        """
        Устанавливает видимое окно и загружает данные с паддингом.

        Параметры:
            start — начало видимого окна
            end — конец видимого окна

        Возвращает: список загруженных свечей (с паддингом).
        """
        if start >= end:
            raise ValueError(
                "Начало видимого окна должно быть раньше конца"
            )

        self.visible_start = start
        self.visible_end = end

        padded_range = self._calculate_padded_range()
        if padded_range is None:
            return []

        padded_start, padded_end = padded_range

        # Загружаем, если нужно
        if self._needs_reload(padded_start, padded_end):
            self._candles = self._db.get_candles(
                self.sec_code,
                start_date=padded_start,
                end_date=padded_end,
            )
            self._loaded_start = padded_start
            self._loaded_end = padded_end
        else:
            # Уже загружено, ничего не делаем
            pass

        return self.loaded_candles

    def shift_visible_range(
        self,
        delta: timedelta,
    ) -> List[Candle]:
        """
        Смещает видимое окно на указанную величину.

        Параметры:
            delta — величина смещения (положительная = вправо/будущее,
                    отрицательная = влево/прошлое)

        Возвращает: список загруженных свечей (с паддингом).
        """
        if self.visible_start is None or self.visible_end is None:
            raise RuntimeError(
                "Видимое окно не задано. "
                "Сначала вызовите set_visible_range."
            )

        new_start = self.visible_start + delta
        new_end = self.visible_end + delta

        return self.set_visible_range(new_start, new_end)

    def zoom_visible_range(self, factor: float) -> List[Candle]:
        """
        Изменяет масштаб видимого окна (зум).

        Параметры:
            factor — коэффициент масштаба:
                     > 1 — увеличить окно (отдалить)
                     < 1 — уменьшить окно (приблизить)
                     Центр окна остаётся неизменным.

        Возвращает: список загруженных свечей (с паддингом).
        """
        if self.visible_start is None or self.visible_end is None:
            raise RuntimeError(
                "Видимое окно не задано. "
                "Сначала вызовите set_visible_range."
            )

        if factor <= 0:
            raise ValueError(
                "Коэффициент масштаба должен быть положительным"
            )

        center = self.visible_start + (self.visible_end - self.visible_start) / 2
        half_duration = (self.visible_end - self.visible_start) * factor / 2

        new_start = center - half_duration
        new_end = center + half_duration

        return self.set_visible_range(new_start, new_end)

    def reload(self) -> List[Candle]:
        """
        Принудительно перезагружает все данные для текущего видимого окна.

        Возвращает список загруженных свечей.
        """
        if self.visible_start is None or self.visible_end is None:
            return []

        # Сбрасываем кэш загруженных границ
        self._loaded_start = None
        self._loaded_end = None

        # Перезагружаем
        return self.set_visible_range(
            self.visible_start, self.visible_end
        )

    def clear(self) -> None:
        """
        Очищает все загруженные данные и сбрасывает видимое окно.
        """
        self.visible_start = None
        self.visible_end = None
        self._candles = []
        self._loaded_start = None
        self._loaded_end = None
