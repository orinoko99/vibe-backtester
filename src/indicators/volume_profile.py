"""
Реализация индикатора Volume Profile.

Volume Profile — это гистограмма объёма, распределённого по ценовым уровням
за указанный период. Показывает, сколько торговалось на каждой цене.

Основные понятия:
- POC (Point of Control) — цена с максимальным объёмом
- Value Area (VA) — зона стоимости (ценовой диапазон, в котором сосредоточено ~70% объёма)
- Value Area High (VAH) — верхняя граница VA
- Value Area Low (VAL) — нижняя граница VA
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

import polars as pl
import numpy as np

from .base import BaseIndicator, IndicatorResult, IndicatorType


# Константы по умолчанию
DEFAULT_BINS: int = 12
DEFAULT_VA_PERCENTAGE: float = 0.70


@dataclass
class VolumeProfileResult:
    """
    Результат расчёта Volume Profile.

    Атрибуты:
        price_levels: Массив ценовых уровней (центры бинов).
        volumes: Массив объёмов для каждого уровня.
        poc_index: Индекс POC (точки контроля) в массивах.
        poc_price: Цена POC.
        vah: Верхняя граница зоны стоимости.
        val: Нижняя граница зоны стоимости.
        total_volume: Суммарный объём.
    """

    price_levels: np.ndarray
    volumes: np.ndarray
    poc_index: int = 0
    poc_price: float = 0.0
    vah: float = 0.0
    val: float = 0.0
    total_volume: float = 0.0


class VolumeProfile(BaseIndicator):
    """
    Индикатор Volume Profile.

    Разбивает ценовой диапазон на N равных интервалов (bins),
    суммирует объём в каждом интервале и определяет POC и зону стоимости.

    Параметры:
        bins: Количество ценовых интервалов (по умолчанию 12).
        va_percentage: Доля объёма для зоны стоимости (по умолчанию 0.70).
    """

    name: ClassVar[str] = "VolumeProfile"
    params: ClassVar[dict] = {
        "bins": DEFAULT_BINS,
        "va_percentage": DEFAULT_VA_PERCENTAGE,
    }
    indicator_type: ClassVar[IndicatorType] = IndicatorType.VOLUME_PROFILE
    min_bars: ClassVar[int] = 2

    def calculate(self, data: pl.DataFrame) -> IndicatorResult:
        """
        Рассчитывает Volume Profile по переданным свечным данным.

        Параметры:
            data: Polars DataFrame с колонками date, high, low, volume.

        Возвращает:
            IndicatorResult с расчётными профилями.
        """
        self.validate_data(data)

        bins: int = int(self._params["bins"])
        va_percentage: float = float(self._params["va_percentage"])

        # Извлекаем данные как numpy массивы для быстрых расчётов
        highs: np.ndarray = data["high"].to_numpy()
        lows: np.ndarray = data["low"].to_numpy()
        volumes: np.ndarray = data["volume"].to_numpy()

        # Определяем общий ценовой диапазон
        price_min: float = float(lows.min())
        price_max: float = float(highs.max())
        price_range: float = price_max - price_min

        # Если цена не менялась — все объёмы в один бин
        if price_range == 0.0:
            bin_centers = np.array([price_min], dtype=np.float64)
            bin_volumes = np.array([float(volumes.sum())], dtype=np.float64)
        else:
            # Создаём границы бинов
            bin_edges: np.ndarray = np.linspace(price_min, price_max, bins + 1)
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0
            bin_volumes = np.zeros(bins, dtype=np.float64)

            # Распределяем объём каждого бара по бинам
            for i in range(len(highs)):
                bar_high: float = float(highs[i])
                bar_low: float = float(lows[i])
                bar_volume: float = float(volumes[i])
                bar_range: float = bar_high - bar_low

                if bar_range == 0.0:
                    # Если бар без диапазона — весь объём в соответствующий бин
                    idx = int(np.searchsorted(bin_edges, bar_high, side="right") - 1)
                    idx = np.clip(idx, 0, bins - 1)
                    bin_volumes[idx] += bar_volume
                else:
                    # Распределяем объём пропорционально перекрытию с каждым бином
                    for j in range(bins):
                        bin_low = bin_edges[j]
                        bin_high = bin_edges[j + 1]
                        overlap_low = max(bar_low, bin_low)
                        overlap_high = min(bar_high, bin_high)
                        overlap = max(0.0, overlap_high - overlap_low)
                        if overlap > 0:
                            bin_volumes[j] += bar_volume * (overlap / bar_range)

        # Находим POC (точку контроля) — индекс с максимальным объёмом
        poc_index = int(np.argmax(bin_volumes))
        poc_price = float(bin_centers[poc_index])
        total_volume = float(bin_volumes.sum())

        # Рассчитываем зону стоимости (Value Area)
        vah, val = self._calculate_value_area(
            bin_centers, bin_volumes, poc_index, va_percentage, total_volume,
        )

        # Строим результирующий DataFrame для отрисовки
        profile_data = pl.DataFrame({
            "date": [data["date"][0]] * len(bin_centers),
            "price": bin_centers,
            "volume": bin_volumes,
            "is_poc": np.arange(len(bin_centers)) == poc_index,
        })

        return IndicatorResult(
            data=profile_data,
            series_names={
                "volume": "#26A69A",
                "poc_line": "#FF9800",
                "vah_line": "#FF5252",
                "val_line": "#FF5252",
            },
            panel="volume_profile",
            overlay=False,
        )

    def _calculate_value_area(
        self,
        bin_centers: np.ndarray,
        bin_volumes: np.ndarray,
        poc_index: int,
        va_percentage: float,
        total_volume: float,
    ) -> tuple[float, float]:
        """
        Рассчитывает зону стоимости (Value Area).

        Начиная от POC, расширяет диапазон вверх/вниз, добавляя бины
        с наибольшим объёмом, пока не будет накоплено va_percentage от всего объёма.

        Параметры:
            bin_centers: Центры ценовых интервалов.
            bin_volumes: Объёмы в каждом интервале.
            poc_index: Индекс POC.
            va_percentage: Доля объёма для VA (0.0-1.0).
            total_volume: Суммарный объём.

        Возвращает:
            Кортеж (vah, val) — верхняя и нижняя границы VA.
        """
        if total_volume == 0:
            return float(bin_centers[poc_index]), float(bin_centers[poc_index])

        n_bins = len(bin_centers)
        target_volume = total_volume * va_percentage
        accumulated = float(bin_volumes[poc_index])

        # Начинаем от POC и расширяемся в обе стороны
        left_idx = poc_index
        right_idx = poc_index

        while accumulated < target_volume and (left_idx > 0 or right_idx < n_bins - 1):
            # Выбираем следующую сторону с бОльшим объёмом
            left_volume = bin_volumes[left_idx - 1] if left_idx > 0 else -1.0
            right_volume = bin_volumes[right_idx + 1] if right_idx < n_bins - 1 else -1.0

            if left_volume >= right_volume and left_idx > 0:
                left_idx -= 1
                accumulated += float(left_volume)
            elif right_idx < n_bins - 1:
                right_idx += 1
                accumulated += float(right_volume)
            else:
                break

        vah = float(bin_centers[right_idx])
        val = float(bin_centers[left_idx])

        return vah, val

    def summarize(self, data: pl.DataFrame) -> VolumeProfileResult:
        """
        Возвращает структурированный результат Volume Profile.

        Параметры:
            data: Polars DataFrame со свечными данными.

        Возвращает:
            VolumeProfileResult с полями price_levels, volumes, poc, vah, val.
        """
        result = self.calculate(data)
        prices = result.data["price"].to_numpy()
        volumes_arr = result.data["volume"].to_numpy()
        poc_mask = result.data["is_poc"].to_numpy()

        poc_indices = np.where(poc_mask)[0]
        poc_idx = int(poc_indices[0]) if len(poc_indices) > 0 else 0

        vah, val = self._calculate_value_area(
            prices, volumes_arr, poc_idx,
            float(self._params["va_percentage"]),
            float(volumes_arr.sum()),
        )

        return VolumeProfileResult(
            price_levels=prices,
            volumes=volumes_arr,
            poc_index=poc_idx,
            poc_price=float(prices[poc_idx]),
            vah=vah,
            val=val,
            total_volume=float(volumes_arr.sum()),
        )
