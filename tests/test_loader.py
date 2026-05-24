#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тесты для модуля динамической загрузки данных (src/data/loader.py).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Generator

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.database import DatabaseManager
from src.data.loader import DataLoader
from src.data.models import Candle


@pytest.fixture
def temp_db_path() -> Generator[Path, None, None]:
    """
    Фикстура: временная SQLite-БД с тестовыми свечами.
    Содержит 100 свечей AAH6 с интервалом 1 минута.
    """
    with NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    conn = sqlite3.connect(str(tmp_path))
    conn.execute(
        "CREATE TABLE 'AAH6_M1' ("
        "ID INTEGER PRIMARY KEY, "
        "Date TEXT, SecCode TEXT, ClassCode TEXT, "
        "O TEXT, H TEXT, L TEXT, C TEXT, "
        "V INTEGER, OpenInterest INTEGER)"
    )

    base_time = datetime(2025, 10, 28, 10, 0)
    test_data = []
    for i in range(100):
        ts = base_time + timedelta(minutes=i)
        price = 100.0 + i * 0.1
        test_data.append((
            i + 1,
            ts.strftime("%Y-%m-%d %H:%M:%S"),
            "AAH6",
            "SPBFUT",
            str(price),
            str(price + 0.5),
            str(price - 0.3),
            str(price + 0.2),
            100 + i,
            i * 10,
        ))

    conn.executemany(
        "INSERT INTO 'AAH6_M1' "
        "(ID, Date, SecCode, ClassCode, O, H, L, C, V, OpenInterest) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        test_data,
    )
    conn.commit()
    conn.close()

    yield tmp_path
    tmp_path.unlink(missing_ok=True)


@pytest.fixture
def db_manager(temp_db_path: Path) -> DatabaseManager:
    """Фикстура: DatabaseManager с тестовой БД."""
    return DatabaseManager(futures_paths=(temp_db_path,), shares_paths=())


@pytest.fixture
def loader(db_manager: DatabaseManager) -> DataLoader:
    """Фикстура: DataLoader для AAH6."""
    return DataLoader(db_manager, "AAH6", padding_factor=2)


class TestDataLoaderCreation:
    """
    Тестирование создания DataLoader.
    """

    def test_creation_default_padding(
        self, db_manager: DatabaseManager
    ) -> None:
        """Проверяет создание с padding по умолчанию."""
        loader = DataLoader(db_manager, "AAH6")
        assert loader.sec_code == "AAH6"
        assert loader.has_data is False

    def test_creation_custom_padding(
        self, db_manager: DatabaseManager
    ) -> None:
        """Проверяет создание с пользовательским padding."""
        loader = DataLoader(db_manager, "AAH6", padding_factor=3)
        assert loader._padding_factor == 3

    def test_initial_state(self, loader: DataLoader) -> None:
        """Проверяет начальное состояние загрузчика."""
        assert loader.visible_start is None
        assert loader.visible_end is None
        assert loader.loaded_candles == []
        assert loader.visible_candles == []
        assert loader.has_data is False
        assert loader.visible_duration is None


class TestSetVisibleRange:
    """
    Тестирование установки видимого диапазона.
    """

    def test_set_visible_range_loads_data(
        self, loader: DataLoader
    ) -> None:
        """
        Проверяет, что после установки видимого окна
        данные загружаются.
        """
        start = datetime(2025, 10, 28, 10, 0)
        end = datetime(2025, 10, 28, 10, 10)
        candles = loader.set_visible_range(start, end)
        assert len(candles) > 0
        assert loader.has_data

    def test_visible_candles_count(self, loader: DataLoader) -> None:
        """
        Проверяет, что visible_candles возвращает
        свечи только в видимом диапазоне.
        """
        start = datetime(2025, 10, 28, 10, 0)
        end = datetime(2025, 10, 28, 10, 9)  # 10 свечей
        loader.set_visible_range(start, end)

        visible = loader.visible_candles
        # Видимое окно: 10 минут -> 10 свечей
        assert len(visible) == 10

    def test_loaded_candles_more_than_visible(
        self, loader: DataLoader
    ) -> None:
        """
        Проверяет, что loaded_candles содержит больше свечей,
        чем visible_candles (за счёт padding).
        """
        start = datetime(2025, 10, 28, 10, 0)
        end = datetime(2025, 10, 28, 10, 9)
        loader.set_visible_range(start, end)

        loaded = loader.loaded_candles
        visible = loader.visible_candles

        assert len(loaded) > len(visible)

    def test_set_visible_range_rejects_invalid(
        self, loader: DataLoader
    ) -> None:
        """
        Проверяет, что start >= end вызывает ошибку.
        """
        start = datetime(2025, 10, 28, 10, 10)
        end = datetime(2025, 10, 28, 10, 0)

        with pytest.raises(ValueError):
            loader.set_visible_range(start, end)

    def test_set_visible_range_without_data(self, loader: DataLoader) -> None:
        """
        Проверяет, что загрузка за пределами данных
        возвращает пустой список.
        """
        start = datetime(2020, 1, 1)
        end = datetime(2020, 1, 2)
        candles = loader.set_visible_range(start, end)
        assert candles == []

    def test_repeat_set_same_range_does_not_reload(
        self, loader: DataLoader
    ) -> None:
        """
        Проверяет, что повторная установка того же диапазона
        не вызывает новую загрузку из БД (кэширование).
        """
        start = datetime(2025, 10, 28, 10, 0)
        end = datetime(2025, 10, 28, 10, 9)

        # Первая загрузка
        candles_first = loader.set_visible_range(start, end)
        id_first = id(loader._candles)
        start_loaded = loader._loaded_start

        # Вторая загрузка того же диапазона
        candles_second = loader.set_visible_range(start, end)

        # Объект свечей не должен измениться (тот же id)
        # или, как минимум, loaded_start остаётся тем же
        assert loader._loaded_start == start_loaded
        assert len(candles_first) == len(candles_second)


class TestShiftVisibleRange:
    """
    Тестирование смещения видимого окна.
    """

    def test_shift_forward(self, loader: DataLoader) -> None:
        """
        Проверяет смещение вправо (в будущее).
        """
        start = datetime(2025, 10, 28, 10, 0)
        end = datetime(2025, 10, 28, 10, 9)
        loader.set_visible_range(start, end)

        delta = timedelta(minutes=10)
        loader.shift_visible_range(delta)

        assert loader.visible_start == start + delta
        assert loader.visible_end == end + delta

    def test_shift_backward(self, loader: DataLoader) -> None:
        """
        Проверяет смещение влево (в прошлое).
        """
        start = datetime(2025, 10, 28, 10, 10)
        end = datetime(2025, 10, 28, 10, 19)
        loader.set_visible_range(start, end)

        delta = timedelta(minutes=-10)
        loader.shift_visible_range(delta)

        assert loader.visible_start == start + delta
        assert loader.visible_end == end + delta

    def test_shift_without_window_raises(
        self, loader: DataLoader
    ) -> None:
        """
        Проверяет, что shift без установленного окна
        вызывает RuntimeError.
        """
        with pytest.raises(RuntimeError):
            loader.shift_visible_range(timedelta(minutes=5))


class TestZoomVisibleRange:
    """
    Тестирование изменения масштаба.
    """

    def test_zoom_in(self, loader: DataLoader) -> None:
        """
        Проверяет уменьшение окна (приближение).
        """
        start = datetime(2025, 10, 28, 10, 0)
        end = datetime(2025, 10, 28, 10, 19)
        loader.set_visible_range(start, end)

        loader.zoom_visible_range(0.5)

        # Окно должно уменьшиться вдвое
        new_duration = loader.visible_end - loader.visible_start
        old_duration = end - start
        assert abs(new_duration.total_seconds() - old_duration.total_seconds() * 0.5) < 1

    def test_zoom_out(self, loader: DataLoader) -> None:
        """
        Проверяет увеличение окна (отдаление).
        """
        start = datetime(2025, 10, 28, 10, 0)
        end = datetime(2025, 10, 28, 10, 9)
        loader.set_visible_range(start, end)

        loader.zoom_visible_range(2.0)

        # Окно должно увеличиться вдвое
        new_duration = loader.visible_end - loader.visible_start
        old_duration = end - start
        assert abs(new_duration.total_seconds() - old_duration.total_seconds() * 2.0) < 1

    def test_zoom_invalid_factor(self, loader: DataLoader) -> None:
        """
        Проверяет, что нулевой или отрицательный factor
        вызывает ошибку.
        """
        start = datetime(2025, 10, 28, 10, 0)
        end = datetime(2025, 10, 28, 10, 9)
        loader.set_visible_range(start, end)

        with pytest.raises(ValueError):
            loader.zoom_visible_range(0)

        with pytest.raises(ValueError):
            loader.zoom_visible_range(-1)

    def test_zoom_without_window_raises(
        self, loader: DataLoader
    ) -> None:
        """Проверяет zoom без установленного окна."""
        with pytest.raises(RuntimeError):
            loader.zoom_visible_range(1.5)


class TestReloadAndClear:
    """
    Тестирование перезагрузки и очистки.
    """

    def test_reload_returns_data(
        self, loader: DataLoader
    ) -> None:
        """
        Проверяет, что reload возвращает данные.
        """
        start = datetime(2025, 10, 28, 10, 0)
        end = datetime(2025, 10, 28, 10, 9)
        loader.set_visible_range(start, end)

        candles = loader.reload()
        assert len(candles) > 0

    def test_reload_without_window(
        self, loader: DataLoader
    ) -> None:
        """
        Проверяет reload без установленного окна.
        """
        candles = loader.reload()
        assert candles == []

    def test_clear_resets_state(self, loader: DataLoader) -> None:
        """
        Проверяет, что clear полностью сбрасывает состояние.
        """
        start = datetime(2025, 10, 28, 10, 0)
        end = datetime(2025, 10, 28, 10, 9)
        loader.set_visible_range(start, end)
        assert loader.has_data

        loader.clear()

        assert loader.visible_start is None
        assert loader.visible_end is None
        assert loader.loaded_candles == []
        assert loader.visible_candles == []
        assert loader.has_data is False


class TestDataIntegrity:
    """
    Тестирование целостности загруженных данных.
    """

    def test_visible_candles_within_window(
        self, loader: DataLoader
    ) -> None:
        """
        Проверяет, что все visible_candles
        находятся внутри видимого окна.
        """
        start = datetime(2025, 10, 28, 10, 5)
        end = datetime(2025, 10, 28, 10, 14)
        loader.set_visible_range(start, end)

        for candle in loader.visible_candles:
            assert start <= candle.timestamp <= end

    def test_loaded_candles_sorted(
        self, loader: DataLoader
    ) -> None:
        """
        Проверяет, что loaded_candles отсортированы по времени.
        """
        start = datetime(2025, 10, 28, 10, 0)
        end = datetime(2025, 10, 28, 10, 9)
        loader.set_visible_range(start, end)

        candles = loader.loaded_candles
        timestamps = [c.timestamp for c in candles]
        assert timestamps == sorted(timestamps)

    def test_visible_duration_calculation(
        self, loader: DataLoader
    ) -> None:
        """
        Проверяет расчёт длительности видимого окна.
        """
        start = datetime(2025, 10, 28, 10, 0)
        end = datetime(2025, 10, 28, 10, 9)
        loader.set_visible_range(start, end)

        duration = loader.visible_duration
        assert duration is not None
        assert duration.total_seconds() == 9 * 60  # 9 минут
