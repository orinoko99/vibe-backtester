#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Конфигурация приложения Backtester.

Содержит:
- пути к SQLite-базам данных с минутными свечами
- настройки окна и графика по умолчанию
- константы для работы с данными
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar


@dataclass(frozen=True)
class DatabasePaths:
    """
    Пути к SQLite-базам данных с минутными свечами.

    Базы разделены на фьючерсы и акции.
    Каждая содержит таблицы вида 'AAH6_M1' — по одной на инструмент.
    """

    # Пути к файлам баз данных фьючерсов
    futures: tuple[Path, ...] = (
        Path(r"D:\_MARKET_TICKDATA\QUIK_DATA\allCandlesFutures.db"),
        Path(r"D:\_MARKET_TICKDATA\QUIK_DATA\allCandlesFutures_2020.db"),
        Path(r"D:\_MARKET_TICKDATA\QUIK_DATA\allCandlesFutures_2023.db"),
    )

    # Пути к файлам баз данных акций
    shares: tuple[Path, ...] = (
        Path(r"D:\_MARKET_TICKDATA\QUIK_DATA\allCandlesShares.db"),
        Path(r"D:\_MARKET_TICKDATA\QUIK_DATA\allCandlesShares_2023.db"),
    )

    @property
    def all_databases(self) -> tuple[Path, ...]:
        """
        Возвращает кортеж со ВСЕМИ путями к базам данных
        (фьючерсы + акции).
        """
        return self.futures + self.shares


@dataclass(frozen=True)
class ChartSettings:
    """
    Настройки графика по умолчанию.
    """

    # Ширина и высота графика в пикселях
    width: int = 800
    height: int = 600

    # Цветовая схема
    background_color: str = "#1a1a2e"
    text_color: str = "#ffffff"
    grid_color: str = "#2a2a3e"

    # Настройки свечей
    up_color: str = "#26a69a"      # Цвет бычьей свечи (зелёный)
    down_color: str = "#ef5350"    # Цвет медвежьей свечи (красный)

    # Количество свечей, подгружаемых с каждой стороны от видимой области
    visible_range_padding: int = 2


@dataclass(frozen=True)
class WindowSettings:
    """
    Настройки главного окна приложения.
    """

    # Заголовок окна
    title: str = "Backtester"

    # Начальные размеры окна в пикселях
    width: int = 1280
    height: int = 800

    # Минимальные размеры окна
    min_width: int = 1024
    min_height: int = 600


@dataclass(frozen=True)
class AppConfig:
    """
    Главный конфигурационный объект приложения.
    Объединяет все настройки в единую точку доступа.
    """

    # Версия приложения
    VERSION: ClassVar[str] = "0.1.0"

    # Составные части конфигурации
    databases: DatabasePaths = field(default_factory=DatabasePaths)
    chart: ChartSettings = field(default_factory=ChartSettings)
    window: WindowSettings = field(default_factory=WindowSettings)


# Единственный экземпляр конфигурации для всего приложения
CONFIG: AppConfig = AppConfig()
