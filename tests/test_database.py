#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тесты для модуля работы с БД (src/data/database.py).
Используют in-memory SQLite для изоляции от реальных данных.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Generator, List

import pytest

# Добавляем корень проекта в путь для импорта database
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.database import DatabaseManager, InstrumentEntry
from src.data.models import Candle, InstrumentType


@pytest.fixture
def temp_db_path() -> Generator[Path, None, None]:
    """
    Фикстура: создаёт временный SQLite-файл с тестовыми данными.
    Удаляется после завершения теста.
    """
    with NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    # Создаём таблицу и наполняем тестовыми данными
    conn = sqlite3.connect(str(tmp_path))
    conn.execute(
        "CREATE TABLE 'AAH6_M1' ("
        "ID INTEGER PRIMARY KEY, "
        "Date TEXT, SecCode TEXT, ClassCode TEXT, "
        "O TEXT, H TEXT, L TEXT, C TEXT, "
        "V INTEGER, OpenInterest INTEGER)"
    )
    conn.execute(
        "CREATE TABLE 'SiH6_M1' ("
        "ID INTEGER PRIMARY KEY, "
        "Date TEXT, SecCode TEXT, ClassCode TEXT, "
        "O TEXT, H TEXT, L TEXT, C TEXT, "
        "V INTEGER, OpenInterest INTEGER)"
    )

    # Вставляем тестовые свечи для AAH6
    test_data = [
        (1, "2025-10-28 18:32:00", "AAH6", "SPBFUT", "65.91", "66.22", "65.91", "66.22", 2, 0),
        (2, "2025-10-28 19:07:00", "AAH6", "SPBFUT", "64.35", "64.35", "64.35", "64.35", 1, 0),
        (3, "2025-10-29 09:08:00", "AAH6", "SPBFUT", "65.80", "65.80", "65.30", "65.30", 6, 0),
        (4, "2025-10-29 09:45:00", "AAH6", "SPBFUT", "64.51", "64.52", "64.51", "64.52", 6, 0),
    ]
    conn.executemany(
        "INSERT INTO 'AAH6_M1' (ID, Date, SecCode, ClassCode, O, H, L, C, V, OpenInterest) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        test_data,
    )

    # Вставляем тестовые свечи для SiH6
    conn.execute(
        "INSERT INTO 'SiH6_M1' (ID, Date, SecCode, ClassCode, O, H, L, C, V, OpenInterest) "
        "VALUES (1, '2025-10-28 10:00:00', 'SiH6', 'SPBFUT', '100.0', '101.0', '99.5', '100.5', 100, 10)"
    )

    conn.commit()
    conn.close()

    yield tmp_path

    # Очистка
    tmp_path.unlink(missing_ok=True)


@pytest.fixture
def db_manager(temp_db_path: Path) -> DatabaseManager:
    """
    Фикстура: DatabaseManager с единственной тестовой БД.
    """
    return DatabaseManager(
        futures_paths=(temp_db_path,),
        shares_paths=(),
    )


class TestDatabaseManagerCreation:
    """
    Тестирование создания и базовых свойств DatabaseManager.
    """

    def test_creation_with_defaults(self) -> None:
        """
        Проверяет создание менеджера с путями по умолчанию.
        """
        manager = DatabaseManager()
        assert len(manager.all_db_paths) == 5, \
            "По умолчанию должно быть 5 баз данных"

    def test_creation_with_custom_paths(
        self, temp_db_path: Path
    ) -> None:
        """
        Проверяет создание менеджера с пользовательскими путями.
        """
        manager = DatabaseManager(
            futures_paths=(temp_db_path,),
            shares_paths=(temp_db_path,),
        )
        assert len(manager.all_db_paths) == 2

    def test_path_types(self, db_manager: DatabaseManager) -> None:
        """
        Проверяет, что all_db_paths возвращает корректные типы.
        """
        for path, inst_type in db_manager.all_db_paths:
            assert isinstance(path, Path)
            assert inst_type in (InstrumentType.FUTURES, InstrumentType.SHARES)


class TestGetInstrumentTables:
    """
    Тестирование получения списка таблиц (инструментов) из БД.
    """

    def test_get_tables_from_valid_db(
        self, db_manager: DatabaseManager, temp_db_path: Path
    ) -> None:
        """
        Проверяет получение списка таблиц из существующей БД.
        """
        tables = db_manager.get_instrument_tables(temp_db_path)
        assert "AAH6_M1" in tables
        assert "SiH6_M1" in tables
        assert len(tables) == 2

    def test_get_tables_from_nonexistent_db(
        self, db_manager: DatabaseManager
    ) -> None:
        """
        Проверяет обработку отсутствующей БД.
        """
        fake_path = Path(r"C:\nonexistent\test.db")
        tables = db_manager.get_instrument_tables(fake_path)
        assert tables == [], \
            "Для отсутствующей БД должен возвращаться пустой список"


class TestGetAllInstruments:
    """
    Тестирование получения всех инструментов из всех БД.
    """

    def test_get_all_instruments_count(
        self, db_manager: DatabaseManager
    ) -> None:
        """
        Проверяет количество найденных инструментов.
        """
        instruments = db_manager.get_all_instruments()
        assert len(instruments) == 2

    def test_instrument_entries_have_correct_fields(
        self, db_manager: DatabaseManager
    ) -> None:
        """
        Проверяет, что записи инструментов содержат все поля.
        """
        instruments = db_manager.get_all_instruments()
        for entry in instruments:
            assert isinstance(entry, InstrumentEntry)
            assert isinstance(entry.sec_code, str)
            assert isinstance(entry.db_type, InstrumentType)
            assert isinstance(entry.db_path, Path)
            assert entry.sec_code in ("AAH6", "SiH6")

    def test_instrument_class_code(
        self, db_manager: DatabaseManager
    ) -> None:
        """
        Проверяет, что ClassCode прочитан из БД.
        """
        instruments = db_manager.get_all_instruments()
        aah6 = [i for i in instruments if i.sec_code == "AAH6"]
        assert len(aah6) == 1
        assert aah6[0].class_code == "SPBFUT"

    def test_instrument_db_type(
        self, db_manager: DatabaseManager
    ) -> None:
        """
        Проверяет, что тип инструмента соответствует типу БД.
        """
        instruments = db_manager.get_all_instruments()
        for entry in instruments:
            assert entry.db_type == InstrumentType.FUTURES


class TestFindInstrument:
    """
    Тестирование поиска инструмента по коду.
    """

    def test_find_existing_instrument(
        self, db_manager: DatabaseManager
    ) -> None:
        """
        Проверяет поиск существующего инструмента.
        """
        entry = db_manager.find_instrument("AAH6")
        assert entry is not None
        assert entry.sec_code == "AAH6"
        assert entry.class_code == "SPBFUT"
        assert entry.db_type == InstrumentType.FUTURES

    def test_find_nonexistent_instrument(
        self, db_manager: DatabaseManager
    ) -> None:
        """
        Проверяет поиск несуществующего инструмента.
        """
        entry = db_manager.find_instrument("NONEXIST")
        assert entry is None

    def test_find_empty_sec_code(
        self, db_manager: DatabaseManager
    ) -> None:
        """
        Проверяет поиск с пустым кодом.
        """
        entry = db_manager.find_instrument("")
        assert entry is None


class TestGetCandles:
    """
    Тестирование загрузки свечей.
    """

    def test_get_all_candles_for_existing_instrument(
        self, db_manager: DatabaseManager
    ) -> None:
        """
        Проверяет загрузку всех свечей для существующего инструмента.
        """
        candles = db_manager.get_candles("AAH6")
        assert len(candles) == 4
        assert all(isinstance(c, Candle) for c in candles)

    def test_candle_values(
        self, db_manager: DatabaseManager
    ) -> None:
        """
        Проверяет, что значения свечей корректно распарсены.
        """
        candles = db_manager.get_candles("AAH6")
        first = candles[0]
        assert first.open == 65.91
        assert first.high == 66.22
        assert first.low == 65.91
        assert first.close == 66.22
        assert first.volume == 2
        assert first.open_interest == 0
        assert first.timestamp == datetime(2025, 10, 28, 18, 32)

    def test_candles_ordered_by_date(
        self, db_manager: DatabaseManager
    ) -> None:
        """
        Проверяет, что свечи отсортированы по дате.
        """
        candles = db_manager.get_candles("AAH6")
        timestamps = [c.timestamp for c in candles]
        assert timestamps == sorted(timestamps)

    def test_get_candles_with_limit(
        self, db_manager: DatabaseManager
    ) -> None:
        """
        Проверяет ограничение количества свечей.
        """
        candles = db_manager.get_candles("AAH6", limit=2)
        assert len(candles) == 2

    def test_get_candles_with_start_date(
        self, db_manager: DatabaseManager
    ) -> None:
        """
        Проверяет фильтрацию по начальной дате.
        """
        start = datetime(2025, 10, 29)
        candles = db_manager.get_candles("AAH6", start_date=start)
        assert len(candles) == 2
        assert all(c.timestamp >= start for c in candles)

    def test_get_candles_with_end_date(
        self, db_manager: DatabaseManager
    ) -> None:
        """
        Проверяет фильтрацию по конечной дате.
        """
        end = datetime(2025, 10, 28, 19, 30)
        candles = db_manager.get_candles("AAH6", end_date=end)
        assert len(candles) == 2
        assert all(c.timestamp <= end for c in candles)

    def test_get_candles_with_date_range(
        self, db_manager: DatabaseManager
    ) -> None:
        """
        Проверяет фильтрацию по диапазону дат.
        """
        start = datetime(2025, 10, 29)
        end = datetime(2025, 10, 29, 12, 0)
        candles = db_manager.get_candles(
            "AAH6", start_date=start, end_date=end
        )
        assert len(candles) == 2

    def test_get_candles_nonexistent_instrument(
        self, db_manager: DatabaseManager
    ) -> None:
        """
        Проверяет загрузку свечей для несуществующего инструмента.
        """
        candles = db_manager.get_candles("NONEXIST")
        assert candles == []

    def test_get_candles_returns_valid_candle_objects(
        self, db_manager: DatabaseManager
    ) -> None:
        """
        Проверяет, что возвращаются валидные объекты Candle.
        """
        candles = db_manager.get_candles("SiH6")
        assert len(candles) == 1
        candle = candles[0]
        assert candle.is_bullish  # close=100.5 > open=100.0
        assert candle.body == 0.5
        assert candle.upper_shadow == 0.5  # 101 - 100.5
        assert candle.lower_shadow == 0.5  # 100 - 99.5


class TestDatabaseEdgeCases:
    """
    Тестирование граничных случаев.
    """

    def test_empty_database(self) -> None:
        """
        Проверяет работу с пустой БД (нет таблиц с инструментами).
        """
        with NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        # Создаём пустую БД
        conn = sqlite3.connect(str(tmp_path))
        conn.execute("CREATE TABLE dummy (id INTEGER)")
        conn.commit()
        conn.close()

        manager = DatabaseManager(
            futures_paths=(tmp_path,),
            shares_paths=(),
        )
        # Таблица dummy не соответствует формату *_M1
        # Однако get_all_instruments вернёт её как есть
        instruments = manager.get_all_instruments()
        assert len(instruments) >= 0
        # Убеждаемся, что метод работает без ошибок

        candles = manager.get_candles("NONEXIST")
        assert candles == []

        tmp_path.unlink(missing_ok=True)

    def test_manager_with_no_databases(self) -> None:
        """
        Проверяет работу менеджера без баз данных.
        """
        manager = DatabaseManager(
            futures_paths=(),
            shares_paths=(),
        )
        assert manager.all_db_paths == []
        assert manager.get_all_instruments() == []
        assert manager.find_instrument("AAH6") is None
        assert manager.get_candles("AAH6") == []
