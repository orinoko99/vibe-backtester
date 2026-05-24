#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тесты для моделей данных (src/data/models.py).
Проверяют создание, валидацию и свойства свечей и инструментов.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

# Добавляем корень проекта в путь для импорта моделей
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.models import (
    Candle,
    InstrumentInfo,
    InstrumentType,
)


class TestInstrumentType:
    """
    Тестирование перечисления InstrumentType.
    """

    def test_futures_value(self) -> None:
        assert InstrumentType.FUTURES.value == "futures"

    def test_shares_value(self) -> None:
        assert InstrumentType.SHARES.value == "shares"

    def test_has_both_types(self) -> None:
        assert len(InstrumentType) == 2


class TestCandleCreation:
    """
    Тестирование создания свечей с валидными данными.
    """

    @pytest.fixture
    def sample_candle_data(self) -> dict:
        """
        Типичные данные бычьей свечи.
        """
        return {
            "timestamp": datetime(2025, 10, 28, 18, 32),
            "open": 65.0,
            "high": 66.5,
            "low": 64.5,
            "close": 66.0,
            "volume": 1000,
            "open_interest": 500,
        }

    def test_create_bullish_candle(self, sample_candle_data) -> None:
        """Проверяет создание бычьей свечи."""
        candle = Candle(**sample_candle_data)
        assert candle.open == 65.0
        assert candle.close == 66.0
        assert candle.high == 66.5
        assert candle.low == 64.5
        assert candle.volume == 1000
        assert candle.open_interest == 500
        assert candle.is_bullish
        assert not candle.is_bearish

    def test_create_bearish_candle(self) -> None:
        """Проверяет создание медвежьей свечи."""
        candle = Candle(
            timestamp=datetime(2025, 10, 28, 19, 7),
            open=65.0,
            high=65.0,
            low=64.0,
            close=64.2,
            volume=500,
        )
        assert candle.is_bearish
        assert not candle.is_bullish
        assert candle.open_interest is None

    def test_create_doji_candle(self) -> None:
        """Проверяет создание дожи (open == close)."""
        candle = Candle(
            timestamp=datetime(2025, 10, 28, 20, 0),
            open=65.0,
            high=65.5,
            low=64.5,
            close=65.0,
            volume=300,
        )
        assert not candle.is_bullish
        assert not candle.is_bearish
        assert candle.body == 0.0

    def test_minimal_required_fields(self) -> None:
        """Проверяет создание с минимальным набором полей."""
        candle = Candle(
            timestamp=datetime(2025, 10, 28, 20, 0),
            open=100.0,
            high=110.0,
            low=95.0,
            close=105.0,
            volume=1,
        )
        assert candle.open_interest is None

    def test_zero_volume_allowed(self) -> None:
        """Проверяет, что нулевой объём допустим."""
        candle = Candle(
            timestamp=datetime(2025, 10, 28, 20, 0),
            open=100.0,
            high=100.0,
            low=100.0,
            close=100.0,
            volume=0,
        )
        assert candle.volume == 0


class TestCandleValidation:
    """
    Тестирование валидации свечей (граничные случаи и ошибки).
    """

    def test_negative_open_rejected(self) -> None:
        """Проверяет, что отрицательная цена открытия запрещена."""
        with pytest.raises(ValidationError):
            Candle(
                timestamp=datetime(2025, 10, 28, 20, 0),
                open=-1.0,
                high=10.0,
                low=0.0,
                close=5.0,
                volume=100,
            )

    def test_negative_volume_rejected(self) -> None:
        """Проверяет, что отрицательный объём запрещён."""
        with pytest.raises(ValidationError):
            Candle(
                timestamp=datetime(2025, 10, 28, 20, 0),
                open=10.0,
                high=20.0,
                low=5.0,
                close=15.0,
                volume=-1,
            )

    def test_high_less_than_open_rejected(self) -> None:
        """Проверяет, что high < max(open, close) запрещён."""
        with pytest.raises(ValidationError):
            Candle(
                timestamp=datetime(2025, 10, 28, 20, 0),
                open=50.0,
                high=40.0,
                low=30.0,
                close=45.0,
                volume=100,
            )

    def test_low_greater_than_open_rejected(self) -> None:
        """Проверяет, что low > min(open, close) запрещён."""
        with pytest.raises(ValidationError):
            Candle(
                timestamp=datetime(2025, 10, 28, 20, 0),
                open=30.0,
                high=50.0,
                low=45.0,
                close=40.0,
                volume=100,
            )

    def test_close_outside_low_high_rejected(self) -> None:
        """Проверяет, что close вне [low, high] запрещён."""
        with pytest.raises(ValidationError):
            Candle(
                timestamp=datetime(2025, 10, 28, 20, 0),
                open=50.0,
                high=60.0,
                low=40.0,
                close=70.0,
                volume=100,
            )

    def test_all_prices_equal_accepted(self) -> None:
        """Проверяет, что все цены равны — допустимо."""
        candle = Candle(
            timestamp=datetime(2025, 10, 28, 20, 0),
            open=50.0,
            high=50.0,
            low=50.0,
            close=50.0,
            volume=100,
        )
        assert candle.body == 0.0
        assert candle.upper_shadow == 0.0
        assert candle.lower_shadow == 0.0


class TestCandleProperties:
    """
    Тестирование расчётных свойств свечи.
    """

    @pytest.fixture
    def bullish_candle(self) -> Candle:
        """Бычья свеча для тестов."""
        return Candle(
            timestamp=datetime(2025, 10, 28, 20, 0),
            open=50.0,
            high=60.0,
            low=45.0,
            close=55.0,
            volume=1000,
        )

    @pytest.fixture
    def bearish_candle(self) -> Candle:
        """Медвежья свеча для тестов."""
        return Candle(
            timestamp=datetime(2025, 10, 28, 20, 0),
            open=55.0,
            high=60.0,
            low=45.0,
            close=50.0,
            volume=1000,
        )

    def test_body_bullish(self, bullish_candle: Candle) -> None:
        """Проверяет тело бычьей свечи."""
        assert bullish_candle.body == 5.0

    def test_body_bearish(self, bearish_candle: Candle) -> None:
        """Проверяет тело медвежьей свечи."""
        assert bearish_candle.body == 5.0

    def test_upper_shadow_bullish(self, bullish_candle: Candle) -> None:
        """Проверяет верхнюю тень бычьей свечи."""
        # high=60, max(open=50, close=55) = 55 => upper = 5
        assert bullish_candle.upper_shadow == 5.0

    def test_upper_shadow_bearish(self, bearish_candle: Candle) -> None:
        """Проверяет верхнюю тень медвежьей свечи."""
        # high=60, max(open=55, close=50) = 55 => upper = 5
        assert bearish_candle.upper_shadow == 5.0

    def test_lower_shadow_bullish(self, bullish_candle: Candle) -> None:
        """Проверяет нижнюю тень бычьей свечи."""
        # min(open=50, close=55) = 50, low=45 => lower = 5
        assert bullish_candle.lower_shadow == 5.0

    def test_lower_shadow_bearish(self, bearish_candle: Candle) -> None:
        """Проверяет нижнюю тень медвежьей свечи."""
        # min(open=55, close=50) = 50, low=45 => lower = 5
        assert bearish_candle.lower_shadow == 5.0

    def test_no_upper_shadow(self) -> None:
        """Проверяет отсутствие верхней тени."""
        candle = Candle(
            timestamp=datetime(2025, 10, 28, 20, 0),
            open=50.0,
            high=55.0,
            low=45.0,
            close=55.0,
            volume=100,
        )
        assert candle.upper_shadow == 0.0

    def test_no_lower_shadow(self) -> None:
        """Проверяет отсутствие нижней тени."""
        candle = Candle(
            timestamp=datetime(2025, 10, 28, 20, 0),
            open=50.0,
            high=60.0,
            low=50.0,
            close=55.0,
            volume=100,
        )
        assert candle.lower_shadow == 0.0

    def test_long_lower_shadow(self) -> None:
        """Проверяет длинную нижнюю тень (молот)."""
        candle = Candle(
            timestamp=datetime(2025, 10, 28, 20, 0),
            open=50.0,
            high=52.0,
            low=40.0,
            close=51.0,
            volume=100,
        )
        assert candle.lower_shadow == 10.0
        assert candle.upper_shadow == 1.0


class TestInstrumentInfo:
    """
    Тестирование модели InstrumentInfo.
    """

    def test_create_futures_instrument(self) -> None:
        """Проверяет создание фьючерсного инструмента."""
        instrument = InstrumentInfo(
            sec_code="AAH6",
            class_code="SPBFUT",
            instrument_type=InstrumentType.FUTURES,
        )
        assert instrument.sec_code == "AAH6"
        assert instrument.class_code == "SPBFUT"
        assert instrument.instrument_type == InstrumentType.FUTURES
        assert instrument.lot_size == 1
        assert instrument.name is None
        assert instrument.min_step is None

    def test_create_shares_instrument(self) -> None:
        """Проверяет создание инструмента-акции."""
        instrument = InstrumentInfo(
            sec_code="SBER",
            class_code="TQBR",
            instrument_type=InstrumentType.SHARES,
            name="Сбербанк ПАО ао",
            lot_size=10,
            min_step=0.01,
        )
        assert instrument.sec_code == "SBER"
        assert instrument.instrument_type == InstrumentType.SHARES
        assert instrument.name == "Сбербанк ПАО ао"
        assert instrument.lot_size == 10
        assert instrument.min_step == 0.01

    def test_table_name_generation(self) -> None:
        """Проверяет генерацию имени таблицы."""
        instrument = InstrumentInfo(
            sec_code="AAH6",
            class_code="SPBFUT",
            instrument_type=InstrumentType.FUTURES,
        )
        assert instrument.table_name == "AAH6_M1"

    def test_lot_size_must_be_positive(self) -> None:
        """Проверяет, что размер лота >= 1."""
        with pytest.raises(ValidationError):
            InstrumentInfo(
                sec_code="AAH6",
                class_code="SPBFUT",
                instrument_type=InstrumentType.FUTURES,
                lot_size=0,
            )

    def test_min_step_must_be_non_negative(self) -> None:
        """Проверяет, что шаг цены >= 0."""
        with pytest.raises(ValidationError):
            InstrumentInfo(
                sec_code="AAH6",
                class_code="SPBFUT",
                instrument_type=InstrumentType.FUTURES,
                min_step=-0.01,
            )

    def test_sec_code_required(self) -> None:
        """Проверяет, что sec_code обязателен."""
        with pytest.raises(ValidationError):
            InstrumentInfo(
                class_code="SPBFUT",
                instrument_type=InstrumentType.FUTURES,
            )
