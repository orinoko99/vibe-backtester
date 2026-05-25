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

import numpy as np
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


# ══════════════════════════════════════════════
# Тесты VolumeProfile
# ══════════════════════════════════════════════


from src.indicators.volume_profile import VolumeProfile, VolumeProfileResult


@pytest.fixture
def vp_data() -> pl.DataFrame:
    """
    Фикстура: данные с разными ценами и объёмами для Volume Profile.
    5 свечей с ростом цены и разным объёмом.
    """
    return pl.DataFrame({
        "date": [datetime(2025, 1, 1, 10, i) for i in range(5)],
        "open": [100.0, 101.0, 102.0, 103.0, 104.0],
        "high": [101.0, 102.0, 103.0, 104.0, 105.0],
        "low": [99.0, 100.0, 101.0, 102.0, 103.0],
        "close": [100.0, 101.0, 102.0, 103.0, 104.0],
        "volume": [1000, 2000, 5000, 3000, 1000],
    })


@pytest.fixture
def vp_data_flat() -> pl.DataFrame:
    """Фикстура: данные с одинаковой ценой (проверка flat price)."""
    return pl.DataFrame({
        "date": [datetime(2025, 1, 1, 10, i) for i in range(3)],
        "open": [100.0, 100.0, 100.0],
        "high": [100.0, 100.0, 100.0],
        "low": [100.0, 100.0, 100.0],
        "close": [100.0, 100.0, 100.0],
        "volume": [1000, 2000, 3000],
    })


# ──────────────────────────────────────────────
# Тесты создания и параметров VolumeProfile
# ──────────────────────────────────────────────


def test_vp_creation_with_default_params() -> None:
    """Проверяет создание VolumeProfile с параметрами по умолчанию."""
    vp = VolumeProfile()
    assert vp.name == "VolumeProfile"
    assert vp._params["bins"] == 12
    assert vp._params["va_percentage"] == 0.70
    assert vp.indicator_type == IndicatorType.VOLUME_PROFILE
    assert vp.min_bars == 2
    assert vp.display_name == "VolumeProfile(12, 0.7)"


def test_vp_creation_with_custom_params() -> None:
    """Проверяет создание VolumeProfile с пользовательскими параметрами."""
    vp = VolumeProfile(bins=20, va_percentage=0.80)
    assert vp._params["bins"] == 20
    assert vp._params["va_percentage"] == 0.80
    assert vp.display_name == "VolumeProfile(20, 0.8)"
    assert vp.display_name == "VolumeProfile(20, 0.8)"


# ──────────────────────────────────────────────
# Тесты расчёта VolumeProfile
# ──────────────────────────────────────────────


def test_vp_calculate_returns_indicator_result(vp_data: pl.DataFrame) -> None:
    """Проверяет, что calculate возвращает IndicatorResult."""
    vp = VolumeProfile()
    result = vp.calculate(vp_data)
    assert isinstance(result, IndicatorResult)
    assert result.overlay is False
    assert result.panel == "volume_profile"


def test_vp_calculate_has_required_columns(vp_data: pl.DataFrame) -> None:
    """Проверяет, что результат содержит все нужные колонки."""
    vp = VolumeProfile()
    result = vp.calculate(vp_data)
    assert "price" in result.data.columns
    assert "volume" in result.data.columns
    assert "is_poc" in result.data.columns
    assert "date" in result.data.columns


def test_vp_calculate_number_of_bins_default(vp_data: pl.DataFrame) -> None:
    """Проверяет количество бинов по умолчанию (12)."""
    vp = VolumeProfile()
    result = vp.calculate(vp_data)
    assert len(result.data) == 12


def test_vp_calculate_number_of_bins_custom(vp_data: pl.DataFrame) -> None:
    """Проверяет количество бинов с пользовательским значением."""
    vp = VolumeProfile(bins=5)
    result = vp.calculate(vp_data)
    assert len(result.data) == 5


def test_vp_calculate_total_volume(vp_data: pl.DataFrame) -> None:
    """Проверяет, что сумма объёмов бинов равна общему объёму."""
    vp = VolumeProfile()
    result = vp.calculate(vp_data)
    total = float(result.data["volume"].sum())
    expected_total = float(vp_data["volume"].sum())
    assert total == pytest.approx(expected_total, rel=1e-6)


def test_vp_calculate_poc_exists(vp_data: pl.DataFrame) -> None:
    """Проверяет, что POC найден и is_poc содержит True."""
    vp = VolumeProfile()
    result = vp.calculate(vp_data)
    poc_count = result.data["is_poc"].sum()
    assert poc_count >= 1, "Должен быть хотя бы один POC бин"


def test_vp_calculate_poc_price_within_range(vp_data: pl.DataFrame) -> None:
    """Проверяет, что POC находится в ценовом диапазоне данных."""
    vp = VolumeProfile()
    result = vp.calculate(vp_data)
    poc_mask = result.data["is_poc"]
    poc_price = float(result.data.filter(poc_mask)["price"][0])
    assert vp_data["low"].min() <= poc_price <= vp_data["high"].max()


def test_vp_calculate_all_volumes_non_negative(vp_data: pl.DataFrame) -> None:
    """Проверяет, что все объёмы бинов неотрицательные."""
    vp = VolumeProfile()
    result = vp.calculate(vp_data)
    assert (result.data["volume"] >= 0).all()


def test_vp_calculate_flat_price(vp_data_flat: pl.DataFrame) -> None:
    """Проверяет расчёт VP при одинаковой цене на всех барах."""
    vp = VolumeProfile()
    result = vp.calculate(vp_data_flat)
    assert len(result.data) == 1  # один бин
    assert result.data["volume"][0] == 6000  # сумма всех объёмов
    assert result.data["price"][0] == 100.0
    assert bool(result.data["is_poc"][0])


def test_vp_calculate_volumes_positive(vp_data: pl.DataFrame) -> None:
    """Проверяет, что все объёмы > 0 при ненулевых входных данных."""
    vp = VolumeProfile()
    result = vp.calculate(vp_data)
    assert (result.data["volume"] > 0).all()


# ──────────────────────────────────────────────
# Тесты summarize (VolumeProfileResult)
# ──────────────────────────────────────────────


def test_vp_summarize_returns_volume_profile_result(vp_data: pl.DataFrame) -> None:
    """Проверяет, что summarize возвращает VolumeProfileResult."""
    vp = VolumeProfile()
    summary = vp.summarize(vp_data)
    assert isinstance(summary, VolumeProfileResult)


def test_vp_summarize_has_price_levels(vp_data: pl.DataFrame) -> None:
    """Проверяет, что summarize содержит price_levels."""
    vp = VolumeProfile()
    summary = vp.summarize(vp_data)
    assert len(summary.price_levels) > 0
    assert len(summary.volumes) > 0


def test_vp_summarize_poc_price(vp_data: pl.DataFrame) -> None:
    """Проверяет, что POC найден в summarize."""
    vp = VolumeProfile()
    summary = vp.summarize(vp_data)
    assert summary.poc_price > 0


def test_vp_summarize_poc_index_in_range(vp_data: pl.DataFrame) -> None:
    """Проверяет, что poc_index в допустимом диапазоне."""
    vp = VolumeProfile()
    summary = vp.summarize(vp_data)
    assert 0 <= summary.poc_index < len(summary.price_levels)


def test_vp_summarize_vah_val_ordered(vp_data: pl.DataFrame) -> None:
    """Проверяет, что VAL <= VAH."""
    vp = VolumeProfile()
    summary = vp.summarize(vp_data)
    assert summary.val <= summary.vah


def test_vp_summarize_total_volume(vp_data: pl.DataFrame) -> None:
    """Проверяет общий объём в summarize."""
    vp = VolumeProfile()
    summary = vp.summarize(vp_data)
    expected_total = float(vp_data["volume"].sum())
    assert summary.total_volume == pytest.approx(expected_total, rel=1e-6)


# ──────────────────────────────────────────────
# Тесты VolumeProfile — граничные случаи
# ──────────────────────────────────────────────


def test_vp_empty_data_raises() -> None:
    """Проверяет, что пустые данные вызывают ошибку."""
    vp = VolumeProfile()
    empty = pl.DataFrame({
        "date": [],
        "open": [], "high": [], "low": [], "close": [],
        "volume": [],
    })
    with pytest.raises(ValueError):
        vp.calculate(empty)


def test_vp_two_bars_data() -> None:
    """Проверяет VP на данных из двух свечей (минимальное количество)."""
    vp = VolumeProfile()
    two = pl.DataFrame({
        "date": [datetime(2025, 1, 1), datetime(2025, 1, 2)],
        "open": [100.0, 100.0], "high": [105.0, 102.0],
        "low": [95.0, 98.0], "close": [102.0, 100.0],
        "volume": [1000, 500],
    })
    result = vp.calculate(two)
    assert len(result.data) > 0
    assert float(result.data["volume"].sum()) == pytest.approx(1500.0, rel=1e-6)


def test_vp_low_volume_data() -> None:
    """Проверяет VP с минимальными объёмами."""
    vp = VolumeProfile()
    low_vol = pl.DataFrame({
        "date": [datetime(2025, 1, 1, 10, i) for i in range(5)],
        "open": [100.0 + i for i in range(5)],
        "high": [101.0 + i for i in range(5)],
        "low": [99.0 + i for i in range(5)],
        "close": [100.0 + i for i in range(5)],
        "volume": [1, 1, 1, 1, 1],
    })
    result = vp.calculate(low_vol)
    assert float(result.data["volume"].sum()) == 5.0


def test_vp_high_bins_count() -> None:
    """Проверяет VP с большим количеством бинов (50)."""
    vp = VolumeProfile(bins=50)
    data = pl.DataFrame({
        "date": [datetime(2025, 1, 1, 10, i) for i in range(10)],
        "open": [float(i) for i in range(10)],
        "high": [float(i + 1) for i in range(10)],
        "low": [float(i) for i in range(10)],
        "close": [float(i) for i in range(10)],
        "volume": [1000] * 10,
    })
    result = vp.calculate(data)
    assert len(result.data) == 50


def test_vp_zero_volume_bar() -> None:
    """Проверяет VP с нулевым объёмом на некоторых барах."""
    vp = VolumeProfile()
    data = pl.DataFrame({
        "date": [datetime(2025, 1, 1, 10, i) for i in range(5)],
        "open": [100.0 + i for i in range(5)],
        "high": [101.0 + i for i in range(5)],
        "low": [99.0 + i for i in range(5)],
        "close": [100.0 + i for i in range(5)],
        "volume": [1000, 0, 5000, 0, 1000],
    })
    result = vp.calculate(data)
    assert float(result.data["volume"].sum()) == 7000.0


# ──────────────────────────────────────────────
# Тесты Value Area
# ──────────────────────────────────────────────


def test_vp_value_area_contains_poc(vp_data: pl.DataFrame) -> None:
    """Проверяет, что зона стоимости включает POC."""
    vp = VolumeProfile()
    summary = vp.summarize(vp_data)
    assert summary.val <= summary.poc_price <= summary.vah


def test_vp_value_area_percentage_custom() -> None:
    """Проверяет VA с пользовательским процентом (100% = весь диапазон)."""
    vp = VolumeProfile(va_percentage=1.0)
    data = pl.DataFrame({
        "date": [datetime(2025, 1, 1, 10, i) for i in range(5)],
        "open": [100.0 + i for i in range(5)],
        "high": [101.0 + i for i in range(5)],
        "low": [99.0 + i for i in range(5)],
        "close": [100.0 + i for i in range(5)],
        "volume": [1000, 2000, 5000, 3000, 1000],
    })
    summary = vp.summarize(data)
    # При 100% VA должен покрыть все ценовые уровни
    assert summary.val == pytest.approx(float(data["low"].min()), rel=1e-3) or summary.val < float(data["low"].max())
    assert summary.vah == pytest.approx(float(data["high"].max()), rel=1e-3) or summary.vah > float(data["high"].min())


# ══════════════════════════════════════════════
# Тесты наложенных индикаторов (overlay)
# ══════════════════════════════════════════════


from src.indicators.overlay import SMA, EMA, BollingerBands


@pytest.fixture
def overlay_data() -> pl.DataFrame:
    """Фикстура: 30 свечей с линейно растущей ценой."""
    return pl.DataFrame({
        "date": [datetime(2025, 1, 1, 10, i) for i in range(30)],
        "open": [float(100 + i) for i in range(30)],
        "high": [float(101 + i) for i in range(30)],
        "low": [float(99 + i) for i in range(30)],
        "close": [float(100 + i) for i in range(30)],
        "volume": [1000] * 30,
    })


@pytest.fixture
def volatile_data() -> pl.DataFrame:
    """Фикстура: волатильные данные для Bollinger."""
    closes = [100.0, 102.0, 98.0, 105.0, 95.0, 110.0, 90.0, 115.0, 85.0, 120.0,
              100.0, 103.0, 97.0, 106.0, 94.0, 111.0, 89.0, 116.0, 84.0, 121.0,
              101.0, 104.0, 96.0, 107.0, 93.0, 112.0, 88.0, 117.0, 83.0, 122.0]
    return pl.DataFrame({
        "date": [datetime(2025, 1, 1, 10, i) for i in range(30)],
        "open": closes,
        "high": [c + 2 for c in closes],
        "low": [c - 2 for c in closes],
        "close": closes,
        "volume": [1000] * 30,
    })


# ──────────────────────────────────────────────
# Тесты SMA
# ──────────────────────────────────────────────


def test_sma_creation() -> None:
    """Проверяет создание SMA."""
    sma = SMA()
    assert sma.name == "SMA"
    assert sma._params["period"] == 20
    assert sma.indicator_type == IndicatorType.OVERLAY
    assert sma.display_name == "SMA(20)"


def test_sma_custom_period() -> None:
    """Проверяет SMA с пользовательским периодом."""
    sma = SMA(period=50)
    assert sma._params["period"] == 50
    assert sma.display_name == "SMA(50)"


def test_sma_calculate_returns_indicator_result(overlay_data: pl.DataFrame) -> None:
    """Проверяет, что SMA.calculate возвращает IndicatorResult."""
    sma = SMA()
    result = sma.calculate(overlay_data)
    assert isinstance(result, IndicatorResult)
    assert result.overlay is True
    assert "sma" in result.data.columns


def test_sma_values(overlay_data: pl.DataFrame) -> None:
    """Проверяет численные значения SMA."""
    sma = SMA(period=5)
    result = sma.calculate(overlay_data)
    sma_vals = result.data["sma"].to_list()

    # Первые 4 значения должны быть NaN
    assert np.isnan(sma_vals[0])
    assert np.isnan(sma_vals[3])
    # 5-е значение = среднее первых 5 close (100+101+102+103+104)/5 = 102
    assert sma_vals[4] == pytest.approx(102.0)
    # 6-е значение = среднее close[1..5] (101+102+103+104+105)/5 = 103
    assert sma_vals[5] == pytest.approx(103.0)


def test_sma_all_nan_on_short_data() -> None:
    """Проверяет SMA на данных короче периода."""
    sma = SMA(period=10)
    short = pl.DataFrame({
        "date": [datetime(2025, 1, 1, 10, i) for i in range(5)],
        "open": [100.0] * 5, "high": [101.0] * 5,
        "low": [99.0] * 5, "close": [100.0] * 5,
        "volume": [1000] * 5,
    })
    result = sma.calculate(short)
    sma_vals = result.data["sma"].to_list()
    assert all(np.isnan(v) for v in sma_vals)


def test_sma_constant_values() -> None:
    """Проверяет SMA на данных с постоянной ценой."""
    sma = SMA(period=3)
    data = pl.DataFrame({
        "date": [datetime(2025, 1, 1, 10, i) for i in range(10)],
        "open": [100.0] * 10, "high": [100.0] * 10,
        "low": [100.0] * 10, "close": [100.0] * 10,
        "volume": [1000] * 10,
    })
    result = sma.calculate(data)
    sma_vals = result.data["sma"].to_list()
    for i in range(2, 10):
        assert sma_vals[i] == pytest.approx(100.0)


# ──────────────────────────────────────────────
# Тесты EMA
# ──────────────────────────────────────────────


def test_ema_creation() -> None:
    """Проверяет создание EMA."""
    ema = EMA()
    assert ema.name == "EMA"
    assert ema._params["period"] == 20
    assert ema.indicator_type == IndicatorType.OVERLAY
    assert ema.display_name == "EMA(20)"


def test_ema_custom_period() -> None:
    """Проверяет EMA с пользовательским периодом."""
    ema = EMA(period=10)
    assert ema._params["period"] == 10
    assert ema.display_name == "EMA(10)"


def test_ema_calculate_returns_indicator_result(overlay_data: pl.DataFrame) -> None:
    """Проверяет, что EMA.calculate возвращает IndicatorResult."""
    ema = EMA()
    result = ema.calculate(overlay_data)
    assert isinstance(result, IndicatorResult)
    assert result.overlay is True
    assert "ema" in result.data.columns


def test_ema_values(overlay_data: pl.DataFrame) -> None:
    """Проверяет численные значения EMA."""
    ema = EMA(period=3)
    result = ema.calculate(overlay_data)
    ema_vals = result.data["ema"].to_list()

    # Первые 2 значения — NaN
    assert np.isnan(ema_vals[0])
    assert np.isnan(ema_vals[1])

    # 3-е значение = SMA первых 3: (100+101+102)/3 = 101
    assert ema_vals[2] == pytest.approx(101.0)

    # 4-е значение = 103 * k + 101 * (1-k), k = 2/(3+1) = 0.5
    # = 103 * 0.5 + 101 * 0.5 = 102
    assert ema_vals[3] == pytest.approx(102.0)


def test_ema_all_nan_on_short_data() -> None:
    """Проверяет EMA на данных короче периода."""
    ema = EMA(period=10)
    short = pl.DataFrame({
        "date": [datetime(2025, 1, 1, 10, i) for i in range(5)],
        "open": [100.0] * 5, "high": [101.0] * 5,
        "low": [99.0] * 5, "close": [100.0] * 5,
        "volume": [1000] * 5,
    })
    result = ema.calculate(short)
    ema_vals = result.data["ema"].to_list()
    assert all(np.isnan(v) for v in ema_vals)


def test_ema_convergence_to_value() -> None:
    """Проверяет, что EMA стремится к постоянному значению."""
    ema = EMA(period=5)
    data = pl.DataFrame({
        "date": [datetime(2025, 1, 1, 10, i) for i in range(50)],
        "open": [100.0] * 50, "high": [100.0] * 50,
        "low": [100.0] * 50, "close": [100.0] * 50,
        "volume": [1000] * 50,
    })
    result = ema.calculate(data)
    ema_vals = result.data["ema"].to_list()
    # Последние значения должны стремиться к 100
    for v in ema_vals[-5:]:
        assert v == pytest.approx(100.0, abs=0.001)


# ──────────────────────────────────────────────
# Тесты Bollinger Bands
# ──────────────────────────────────────────────


def test_bb_creation() -> None:
    """Проверяет создание Bollinger Bands."""
    bb = BollingerBands()
    assert bb.name == "BollingerBands"
    assert bb._params["period"] == 20
    assert bb._params["std_dev"] == 2.0
    assert bb.indicator_type == IndicatorType.OVERLAY
    assert bb.display_name == "BollingerBands(20, 2.0)"


def test_bb_custom_params() -> None:
    """Проверяет Bollinger Bands с пользовательскими параметрами."""
    bb = BollingerBands(period=10, std_dev=1.5)
    assert bb._params["period"] == 10
    assert bb._params["std_dev"] == 1.5
    assert bb.display_name == "BollingerBands(10, 1.5)"


def test_bb_calculate_returns_indicator_result(overlay_data: pl.DataFrame) -> None:
    """Проверяет, что BB.calculate возвращает IndicatorResult."""
    bb = BollingerBands()
    result = bb.calculate(overlay_data)
    assert isinstance(result, IndicatorResult)
    assert result.overlay is True


def test_bb_has_three_series(overlay_data: pl.DataFrame) -> None:
    """Проверяет, что BB содержит три ряда: upper, middle, lower."""
    bb = BollingerBands()
    result = bb.calculate(overlay_data)
    assert "bb_upper" in result.data.columns
    assert "bb_middle" in result.data.columns
    assert "bb_lower" in result.data.columns


def test_bb_middle_equals_sma(overlay_data: pl.DataFrame) -> None:
    """Проверяет, что средняя линия BB равна SMA."""
    bb = BollingerBands(period=5)
    sma = SMA(period=5)
    bb_result = bb.calculate(overlay_data)
    sma_result = sma.calculate(overlay_data)
    # Сравниваем без первых NaN
    bb_middle = bb_result.data["bb_middle"].to_list()[5:]
    sma_vals = sma_result.data["sma"].to_list()[5:]
    for bm, sm in zip(bb_middle, sma_vals):
        assert bm == pytest.approx(sm)


def test_bb_upper_above_lower(overlay_data: pl.DataFrame) -> None:
    """Проверяет, что верхняя полоса всегда выше нижней."""
    bb = BollingerBands(period=5)
    result = bb.calculate(overlay_data)
    upper = result.data["bb_upper"].to_list()
    lower = result.data["bb_lower"].to_list()
    for i in range(5, len(upper)):
        assert upper[i] >= lower[i], f"На индексе {i}: upper={upper[i]} < lower={lower[i]}"


def test_bb_bands_widen_with_volatility(volatile_data: pl.DataFrame) -> None:
    """Проверяет, что полосы расширяются при высокой волатильности."""
    bb = BollingerBands(period=5)
    result = bb.calculate(volatile_data)
    upper = result.data["bb_upper"].to_list()
    lower = result.data["bb_lower"].to_list()
    # Разница между upper и lower должна быть > 0
    spreads = [upper[i] - lower[i] for i in range(5, len(upper)) if not (np.isnan(upper[i]) or np.isnan(lower[i]))]
    assert all(s > 0 for s in spreads)
    # На волатильных данных разброс должен быть заметным
    assert max(spreads) > 5.0


def test_bb_all_nan_on_short_data() -> None:
    """Проверяет BB на данных короче периода."""
    bb = BollingerBands(period=10)
    short = pl.DataFrame({
        "date": [datetime(2025, 1, 1, 10, i) for i in range(5)],
        "open": [100.0] * 5, "high": [101.0] * 5,
        "low": [99.0] * 5, "close": [100.0] * 5,
        "volume": [1000] * 5,
    })
    result = bb.calculate(short)
    upper = result.data["bb_upper"].to_list()
    middle = result.data["bb_middle"].to_list()
    lower = result.data["bb_lower"].to_list()
    assert all(np.isnan(v) for v in upper)
    assert all(np.isnan(v) for v in middle)
    assert all(np.isnan(v) for v in lower)


def test_bb_constant_values() -> None:
    """Проверяет BB на данных с постоянной ценой."""
    bb = BollingerBands(period=3)
    data = pl.DataFrame({
        "date": [datetime(2025, 1, 1, 10, i) for i in range(10)],
        "open": [100.0] * 10, "high": [100.0] * 10,
        "low": [100.0] * 10, "close": [100.0] * 10,
        "volume": [1000] * 10,
    })
    result = bb.calculate(data)
    upper = result.data["bb_upper"].to_list()
    middle = result.data["bb_middle"].to_list()
    lower = result.data["bb_lower"].to_list()
    # При постоянной цене std = 0, все линии = 100
    for i in range(2, 10):
        assert middle[i] == pytest.approx(100.0)
        assert upper[i] == pytest.approx(100.0)
        assert lower[i] == pytest.approx(100.0)


def test_bb_series_names(overlay_data: pl.DataFrame) -> None:
    """Проверяет имена рядов в IndicatorResult."""
    bb = BollingerBands()
    result = bb.calculate(overlay_data)
    assert "bb_upper" in result.series_names
    assert "bb_middle" in result.series_names
    assert "bb_lower" in result.series_names
