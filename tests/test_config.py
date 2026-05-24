#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тесты для модуля конфигурации src/utils/config.py.
Проверяют корректность путей, настроек и иммутабельность dataclass-ов.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Добавляем корень проекта в путь для импорта config
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.config import (
    CONFIG,
    AppConfig,
    ChartSettings,
    DatabasePaths,
    WindowSettings,
)


class TestDatabasePaths:
    """
    Тестирование путей к базам данных.
    """

    def test_futures_paths_count(self) -> None:
        """
        Проверяет, что указано ровно 3 пути к базам фьючерсов.
        """
        assert len(CONFIG.databases.futures) == 3, \
            "Должно быть 3 базы данных фьючерсов"

    def test_shares_paths_count(self) -> None:
        """
        Проверяет, что указано ровно 2 пути к базам акций.
        """
        assert len(CONFIG.databases.shares) == 2, \
            "Должно быть 2 базы данных акций"

    def test_all_databases_combined(self) -> None:
        """
        Проверяет, что all_databases возвращает все 5 баз.
        """
        assert len(CONFIG.databases.all_databases) == 5, \
            "Всего должно быть 5 баз данных"

    def test_futures_path_contains_futures_in_name(self) -> None:
        """
        Проверяет, что каждый путь фьючерсов содержит 'Futures'.
        """
        for db_path in CONFIG.databases.futures:
            assert "Futures" in db_path.name, \
                f"Имя файла {db_path.name} должно содержать 'Futures'"

    def test_shares_path_contains_shares_in_name(self) -> None:
        """
        Проверяет, что каждый путь акций содержит 'Shares'.
        """
        for db_path in CONFIG.databases.shares:
            assert "Shares" in db_path.name, \
                f"Имя файла {db_path.name} должно содержать 'Shares'"

    def test_all_paths_are_path_objects(self) -> None:
        """
        Проверяет, что все пути являются объектами Path.
        """
        for db_path in CONFIG.databases.all_databases:
            assert isinstance(db_path, Path), \
                "Каждый путь должен быть экземпляром pathlib.Path"

    def test_all_paths_have_db_extension(self) -> None:
        """
        Проверяет, что все пути имеют расширение .db.
        """
        for db_path in CONFIG.databases.all_databases:
            assert db_path.suffix == ".db", \
                f"Файл {db_path.name} должен иметь расширение .db"

    def test_frozen_dataclass_cannot_be_modified(self) -> None:
        """
        Проверяет, что DatabasePaths — frozen и не позволяет изменять поля.
        """
        with pytest.raises(AttributeError):
            DatabasePaths().futures = ()  # type: ignore


class TestChartSettings:
    """
    Тестирование настроек графика.
    """

    def test_default_width(self) -> None:
        """Проверяет ширину графика по умолчанию."""
        assert CONFIG.chart.width == 800

    def test_default_height(self) -> None:
        """Проверяет высоту графика по умолчанию."""
        assert CONFIG.chart.height == 600

    def test_visible_range_padding(self) -> None:
        """
        Проверяет значение padding для подгрузки данных.
        Должно быть 2 (экрана с каждой стороны).
        """
        assert CONFIG.chart.visible_range_padding == 2

    def test_up_color_is_valid_hex(self) -> None:
        """Проверяет, что цвет бычьей свечи — валидный hex."""
        color = CONFIG.chart.up_color
        assert color.startswith("#") and len(color) == 7

    def test_down_color_is_valid_hex(self) -> None:
        """Проверяет, что цвет медвежьей свечи — валидный hex."""
        color = CONFIG.chart.down_color
        assert color.startswith("#") and len(color) == 7

    def test_colors_are_different(self) -> None:
        """Проверяет, что цвета бычьей и медвежьей свечи различаются."""
        assert CONFIG.chart.up_color != CONFIG.chart.down_color


class TestWindowSettings:
    """
    Тестирование настроек главного окна.
    """

    def test_default_title(self) -> None:
        """Проверяет заголовок окна по умолчанию."""
        assert CONFIG.window.title == "Backtester"

    def test_default_window_size(self) -> None:
        """Проверяет размеры окна по умолчанию."""
        assert CONFIG.window.width == 1280
        assert CONFIG.window.height == 800

    def test_minimum_window_size(self) -> None:
        """Проверяет минимальные размеры окна."""
        assert CONFIG.window.min_width == 1024
        assert CONFIG.window.min_height == 600

    def test_min_size_less_than_default(self) -> None:
        """
        Проверяет, что минимальные размеры меньше или равны размерам по умолчанию.
        """
        assert CONFIG.window.min_width <= CONFIG.window.width
        assert CONFIG.window.min_height <= CONFIG.window.height


class TestAppConfig:
    """
    Тестирование главного конфигурационного объекта.
    """

    def test_config_is_singleton(self) -> None:
        """
        Проверяет, что CONFIG — это экземпляр AppConfig.
        """
        assert isinstance(CONFIG, AppConfig)

    def test_config_has_all_sections(self) -> None:
        """
        Проверяет, что CONFIG содержит все разделы настроек.
        """
        assert hasattr(CONFIG, "databases")
        assert hasattr(CONFIG, "chart")
        assert hasattr(CONFIG, "window")

    def test_config_sections_are_correct_types(self) -> None:
        """
        Проверяет типы полей конфигурации.
        """
        assert isinstance(CONFIG.databases, DatabasePaths)
        assert isinstance(CONFIG.chart, ChartSettings)
        assert isinstance(CONFIG.window, WindowSettings)

    def test_version_is_string(self) -> None:
        """Проверяет, что версия — строка."""
        assert isinstance(CONFIG.VERSION, str)

    def test_version_format(self) -> None:
        """Проверяет формат версии (semver)."""
        version = CONFIG.VERSION
        parts = version.split(".")
        assert len(parts) == 3, "Версия должна быть в формате X.Y.Z"
        assert all(p.isdigit() for p in parts), \
            "Каждая часть версии должна быть числом"
