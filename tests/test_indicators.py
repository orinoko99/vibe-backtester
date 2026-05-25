"""
Тесты для базового класса индикаторов src/indicators/base.py.

Проверяет:
- Создание конкретной реализации BaseIndicator
- Валидацию данных (validate_data)
- Обработку параметров (конструктор с kwargs)
- IndicatorResult и IndicatorType
- Граничные случаи: пустые данные, неизвестные параметры
"""

from __future__ import annotations

from datetime import datetime

import polars as pl
import pytest

from src.indicators.base import (
    BaseIndicator,
    IndicatorResult,
    IndicatorType,
)


# ──────────────────────────────────────────────
# Вспомогательная конкретная реализация для тестов
# ──────────────────────────────────────────────


class DummyOverlayIndicator(BaseIndicator):
    """Тестовый индикатор, рисующийся поверх свечей."""

    name = "DummyOverlay"
    params = {"period": 14, "multiplier": 2.0}
    indicator_type = IndicatorType.OVERLAY
    min_bars = 5

    def calculate(self, data: pl.DataFrame) -> IndicatorResult:
        """Простой расчёт: возвращает close + period."""
        self.validate_data(data)
        period = self._params["period"]
        result_data = data.select([
            pl.col("date"),
            (pl.col("close") + period).alias("dummy_line"),
        ])
        return IndicatorResult(
            data=result_data,
            series_names={"dummy_line": "#FF0000"},
            overlay=True,
        )


class DummyOscillatorIndicator(BaseIndicator):
    """Тестовый индикатор-осциллятор (отдельная панель)."""

    name = "DummyOsc"
    params = {"period": 14}
    indicator_type = IndicatorType.OSCILLATOR
    min_bars = 3

    def calculate(self, data: pl.DataFrame) -> IndicatorResult:
        """Простой расчёт: возвращает нормализованную цену."""
        self.validate_data(data)
        result_data = data.select([
            pl.col("date"),
            ((pl.col("close") - pl.col("close").min()) /
             (pl.col("close").max() - pl.col("close").min()) * 100).alias("osc"),
        ])
        return IndicatorResult(
            data=result_data,
            series_names={"osc": "#00FF00"},
            panel="oscillator",
            overlay=False,
        )


class DummyVolumeProfileIndicator(BaseIndicator):
    """Тестовый индикатор Volume Profile."""

    name = "DummyVP"
    params = {"bins": 10}
    indicator_type = IndicatorType.VOLUME_PROFILE
    min_bars = 2

    def calculate(self, data: pl.DataFrame) -> IndicatorResult:
        """Простой расчёт: возвращает price_bins."""
        self.validate_data(data)
        result_data = pl.DataFrame({
            "date": [datetime(2025, 1, 1)] * 3,
            "price": [100.0, 101.0, 102.0],
            "volume": [100, 200, 300],
        })
        return IndicatorResult(
            data=result_data,
            series_names={"volume": "#0000FF"},
            panel="volume_profile",
            overlay=False,
        )


# ──────────────────────────────────────────────
# Фикстуры
# ──────────────────────────────────────────────


@pytest.fixture
def sample_data() -> pl.DataFrame:
    """Фикстура: тестовый DataFrame с 10 свечами."""
    return pl.DataFrame({
        "date": [datetime(2025, 1, 1, 10, i) for i in range(10)],
        "open": [100.0 + i for i in range(10)],
        "high": [101.0 + i for i in range(10)],
        "low": [99.0 + i for i in range(10)],
        "close": [100.0 + i for i in range(10)],
        "volume": [1000 + i * 100 for i in range(10)],
    })


@pytest.fixture
def small_data() -> pl.DataFrame:
    """Фикстура: DataFrame с 2 свечами (для проверки min_bars)."""
    return pl.DataFrame({
        "date": [datetime(2025, 1, 1, 10, 0), datetime(2025, 1, 1, 10, 1)],
        "open": [100.0, 101.0],
        "high": [101.0, 102.0],
        "low": [99.0, 100.0],
        "close": [100.0, 101.0],
        "volume": [1000, 1100],
    })


@pytest.fixture
def empty_data() -> pl.DataFrame:
    """Фикстура: пустой DataFrame."""
    return pl.DataFrame({
        "date": [],
        "open": [],
        "high": [],
        "low": [],
        "close": [],
        "volume": [],
    })


# ──────────────────────────────────────────────
# Тесты IndicatorType
# ──────────────────────────────────────────────


def test_indicator_type_values() -> None:
    """Проверяет значения перечисления IndicatorType."""
    assert IndicatorType.OVERLAY.value == 1
    assert IndicatorType.OSCILLATOR.value == 2
    assert IndicatorType.VOLUME_PROFILE.value == 3


# ──────────────────────────────────────────────
# Тесты IndicatorResult
# ──────────────────────────────────────────────


def test_indicator_result_defaults() -> None:
    """Проверяет значения по умолчанию IndicatorResult."""
    data = pl.DataFrame({"date": [datetime(2025, 1, 1)], "value": [1.0]})
    result = IndicatorResult(data=data)
    assert result.series_names == {}
    assert result.panel == ""
    assert result.overlay is True


def test_indicator_result_custom_values() -> None:
    """Проверяет пользовательские значения IndicatorResult."""
    data = pl.DataFrame({"date": [datetime(2025, 1, 1)], "value": [1.0]})
    result = IndicatorResult(
        data=data,
        series_names={"value": "#FF0000"},
        panel="custom",
        overlay=False,
    )
    assert result.series_names == {"value": "#FF0000"}
    assert result.panel == "custom"
    assert result.overlay is False


# ──────────────────────────────────────────────
# Тесты BaseIndicator — создание и параметры
# ──────────────────────────────────────────────


def test_indicator_creation_with_default_params() -> None:
    """Проверяет создание индикатора с параметрами по умолчанию."""
    ind = DummyOverlayIndicator()
    assert ind.name == "DummyOverlay"
    assert ind._params == {"period": 14, "multiplier": 2.0}
    assert ind.indicator_type == IndicatorType.OVERLAY
    assert ind.min_bars == 5


def test_indicator_creation_with_custom_params() -> None:
    """Проверяет создание индикатора с переопределёнными параметрами."""
    ind = DummyOverlayIndicator(period=20, multiplier=3.0)
    assert ind._params["period"] == 20
    assert ind._params["multiplier"] == 3.0


def test_indicator_creation_partial_params() -> None:
    """Проверяет частичное переопределение параметров."""
    ind = DummyOverlayIndicator(period=50)
    assert ind._params["period"] == 50
    assert ind._params["multiplier"] == 2.0  # остаётся по умолчанию


def test_indicator_creation_invalid_param() -> None:
    """Проверяет, что неизвестный параметр выбрасывает ValueError."""
    with pytest.raises(ValueError) as exc_info:
        DummyOverlayIndicator(invalid_param=100)

    assert "не поддерживает параметр" in str(exc_info.value).lower()


def test_indicator_display_name_default() -> None:
    """Проверяет отображаемое имя с параметрами по умолчанию."""
    ind = DummyOverlayIndicator()
    assert ind.display_name == "DummyOverlay(14, 2.0)"


def test_indicator_display_name_custom() -> None:
    """Проверяет отображаемое имя с пользовательскими параметрами."""
    ind = DummyOverlayIndicator(period=50, multiplier=1.5)
    assert ind.display_name == "DummyOverlay(50, 1.5)"


def test_indicator_repr() -> None:
    """Проверяет строковое представление индикатора."""
    ind = DummyOverlayIndicator()
    assert repr(ind) == "<DummyOverlay(14, 2.0)>"


# ──────────────────────────────────────────────
# Тесты BaseIndicator — типы индикаторов
# ──────────────────────────────────────────────


def test_indicator_type_overlay() -> None:
    """Проверяет, что OVERLAY индикатор имеет correct type."""
    ind = DummyOverlayIndicator()
    assert ind.indicator_type == IndicatorType.OVERLAY


def test_indicator_type_oscillator() -> None:
    """Проверяет, что OSCILLATOR индикатор имеет correct type."""
    ind = DummyOscillatorIndicator()
    assert ind.indicator_type == IndicatorType.OSCILLATOR


def test_indicator_type_volume_profile() -> None:
    """Проверяет, что VOLUME_PROFILE индикатор имеет correct type."""
    ind = DummyVolumeProfileIndicator()
    assert ind.indicator_type == IndicatorType.VOLUME_PROFILE


# ──────────────────────────────────────────────
# Тесты BaseIndicator — расчёт (calculate)
# ──────────────────────────────────────────────


def test_calculate_returns_indicator_result(sample_data: pl.DataFrame) -> None:
    """Проверяет, что calculate возвращает IndicatorResult."""
    ind = DummyOverlayIndicator()
    result = ind.calculate(sample_data)
    assert isinstance(result, IndicatorResult)
    assert isinstance(result.data, pl.DataFrame)
    assert "date" in result.data.columns


def test_calculate_with_custom_params(sample_data: pl.DataFrame) -> None:
    """Проверяет расчёт с пользовательскими параметрами."""
    ind = DummyOverlayIndicator(period=50)
    result = ind.calculate(sample_data)
    # close[0] = 100, + period(50) = 150
    assert result.data["dummy_line"][0] == 150.0


def test_calculate_oscillator(sample_data: pl.DataFrame) -> None:
    """Проверяет расчёт осциллятора."""
    ind = DummyOscillatorIndicator()
    result = ind.calculate(sample_data)
    assert result.overlay is False
    assert result.panel == "oscillator"
    assert "osc" in result.data.columns


def test_calculate_volume_profile(small_data: pl.DataFrame) -> None:
    """Проверяет расчёт Volume Profile."""
    ind = DummyVolumeProfileIndicator()
    result = ind.calculate(small_data)
    assert result.overlay is False
    assert result.panel == "volume_profile"
    assert "price" in result.data.columns
    assert "volume" in result.data.columns


# ──────────────────────────────────────────────
# Тесты BaseIndicator — валидация данных
# ──────────────────────────────────────────────


def test_validate_data_success(sample_data: pl.DataFrame) -> None:
    """Проверяет успешную валидацию данных."""
    ind = DummyOverlayIndicator()
    # Не должно выбросить исключение
    ind.validate_data(sample_data)


def test_validate_data_missing_column() -> None:
    """Проверяет валидацию при отсутствии обязательной колонки."""
    ind = DummyOverlayIndicator()
    bad_data = pl.DataFrame({
        "date": [datetime(2025, 1, 1)],
        "open": [100.0],
        "close": [105.0],
        # Нет high, low
    })
    with pytest.raises(ValueError) as exc_info:
        ind.validate_data(bad_data)
    assert "должен содержать колонку" in str(exc_info.value)


def test_validate_data_not_enough_rows(empty_data: pl.DataFrame) -> None:
    """Проверяет валидацию при недостаточном количестве строк."""
    ind = DummyOverlayIndicator()  # min_bars = 5
    with pytest.raises(ValueError) as exc_info:
        ind.validate_data(empty_data)
    assert "Недостаточно данных" in str(exc_info.value)


def test_validate_data_min_bars_boundary() -> None:
    """Проверяет валидацию на границе min_bars."""
    ind = DummyOverlayIndicator()  # min_bars = 5
    data_5 = pl.DataFrame({
        "date": [datetime(2025, 1, 1, 10, i) for i in range(5)],
        "open": [100.0] * 5,
        "high": [101.0] * 5,
        "low": [99.0] * 5,
        "close": [100.0] * 5,
        "volume": [1000] * 5,
    })
    # 5 строк = min_bars, не должно выбросить исключение
    ind.validate_data(data_5)

    data_4 = pl.DataFrame({
        "date": [datetime(2025, 1, 1, 10, i) for i in range(4)],
        "open": [100.0] * 4,
        "high": [101.0] * 4,
        "low": [99.0] * 4,
        "close": [100.0] * 4,
        "volume": [1000] * 4,
    })
    with pytest.raises(ValueError) as exc_info:
        ind.validate_data(data_4)
    assert "Недостаточно данных" in str(exc_info.value)


# ──────────────────────────────────────────────
# Тесты BaseIndicator — граничные случаи
# ──────────────────────────────────────────────


def test_base_indicator_abstract_cannot_instantiate() -> None:
    """Проверяет, что BaseIndicator нельзя создать напрямую."""
    with pytest.raises(TypeError):
        BaseIndicator()  # type: ignore  # noqa


def test_calculate_empty_data_raises() -> None:
    """Проверяет, что calculate на пустых данных выбрасывает ошибку."""
    ind = DummyOverlayIndicator()
    empty = pl.DataFrame({
        "date": [],
        "open": [],
        "high": [],
        "low": [],
        "close": [],
        "volume": [],
    })
    with pytest.raises(ValueError):
        ind.calculate(empty)


def test_calculate_small_data_success(small_data: pl.DataFrame) -> None:
    """Проверяет calculate на минимально допустимом количестве данных."""
    ind = DummyVolumeProfileIndicator()  # min_bars = 2
    result = ind.calculate(small_data)
    assert isinstance(result, IndicatorResult)


def test_indicator_params_not_shared() -> None:
    """Проверяет, что params разных экземпляров не влияют друг на друга."""
    ind1 = DummyOverlayIndicator(period=20)
    ind2 = DummyOverlayIndicator(period=50)

    assert ind1._params["period"] == 20
    assert ind2._params["period"] == 50

    # Меняем ind1 — ind2 не должен измениться
    ind1._params["period"] = 100
    assert ind2._params["period"] == 50


def test_indicator_class_params_not_mutated() -> None:
    """Проверяет, что изменение params экземпляра не меняет ClassVar."""
    ind = DummyOverlayIndicator(period=99)
    assert DummyOverlayIndicator.params["period"] == 14  # Осталось по умолчанию


# ──────────────────────────────────────────────
# Тесты индикатора без параметров
# ──────────────────────────────────────────────


class NoParamIndicator(BaseIndicator):
    """Индикатор без параметров."""

    name = "NoParam"
    params = {}
    indicator_type = IndicatorType.OVERLAY
    min_bars = 1

    def calculate(self, data: pl.DataFrame) -> IndicatorResult:
        self.validate_data(data)
        return IndicatorResult(data=data.select(["date", "close"]))


def test_indicator_without_params() -> None:
    """Проверяет индикатор без параметров."""
    ind = NoParamIndicator()
    assert ind._params == {}
    assert ind.display_name == "NoParam()"


def test_indicator_without_params_rejects_any_kwargs() -> None:
    """Проверяет, что индикатор без параметров не принимает kwargs."""
    with pytest.raises(ValueError):
        NoParamIndicator(something=123)


# ──────────────────────────────────────────────
# Тесты на возвращаемые данные
# ──────────────────────────────────────────────


def test_calculate_result_has_all_requested_series(sample_data: pl.DataFrame) -> None:
    """Проверяет, что результат содержит все запрошенные ряды."""
    ind = DummyOverlayIndicator()
    result = ind.calculate(sample_data)
    for series_name in result.series_names:
        assert series_name in result.data.columns


def test_calculate_result_date_column_preserved(sample_data: pl.DataFrame) -> None:
    """Проверяет, что колонка date сохраняется в результате."""
    ind = DummyOverlayIndicator()
    result = ind.calculate(sample_data)
    assert "date" in result.data.columns
    assert len(result.data) == len(sample_data)


def test_calculate_overlay_flag(sample_data: pl.DataFrame) -> None:
    """Проверяет флаг overlay в результате."""
    overlay_ind = DummyOverlayIndicator()
    result = overlay_ind.calculate(sample_data)
    assert result.overlay is True

    osc_ind = DummyOscillatorIndicator()
    result2 = osc_ind.calculate(sample_data)
    assert result2.overlay is False
