"""
Тесты для модуля загрузки данных src/data/loader.py.

Создаёт временную SQLite БД с тестовыми данными для изоляции тестов.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

import polars as pl
import pytest

from src.data.loader import (
    get_table_list,
    get_available_instruments,
    load_candles,
)


@pytest.fixture
def temp_db_path(tmp_path: Path) -> str:
    """
    Фикстура: создаёт временную SQLite БД с тестовыми свечными данными.
    Возвращает путь к созданному файлу .db.
    """
    db_file = tmp_path / "test_candles.db"
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()

    # Создаём таблицу, повторяющую структуру реальной БД QUIK
    cursor.execute("""
        CREATE TABLE 'TEST_M1' (
            'ID' INTEGER PRIMARY KEY,
            'Date' TEXT,
            'SecCode' TEXT,
            'ClassCode' TEXT,
            'O' TEXT,
            'H' TEXT,
            'L' TEXT,
            'C' TEXT,
            'V' INTEGER,
            'OpenInterest' INTEGER
        )
    """)

    # Вставляем тестовые данные (10 свечей с разными датами)
    test_data = [
        (1, "2025-10-28 09:00:00", "TEST", "SPBFUT", "100.0", "105.0", "99.0", "104.0", 1000, 500),
        (2, "2025-10-28 09:01:00", "TEST", "SPBFUT", "104.0", "106.0", "103.0", "105.5", 800, 520),
        (3, "2025-10-28 09:02:00", "TEST", "SPBFUT", "105.5", "107.0", "105.0", "106.0", 1200, 530),
        (4, "2025-10-29 10:00:00", "TEST", "SPBFUT", "106.0", "108.0", "105.5", "107.5", 1500, 540),
        (5, "2025-10-29 10:01:00", "TEST", "SPBFUT", "107.5", "109.0", "107.0", "108.0", 900, 550),
        (6, "2025-10-30 11:00:00", "TEST", "SPBFUT", "108.0", "110.0", "107.5", "109.5", 2000, 560),
        (7, "2025-10-30 11:01:00", "TEST", "SPBFUT", "109.5", "111.0", "109.0", "110.0", 1100, 570),
        (8, "2025-10-30 11:02:00", "TEST", "SPBFUT", "110.0", "112.0", "109.5", "111.5", 1300, 580),
        (9, "2025-10-31 12:00:00", "TEST", "SPBFUT", "111.5", "113.0", "111.0", "112.0", 700, 590),
        (10, "2025-10-31 12:01:00", "TEST", "SPBFUT", "112.0", "114.0", "111.5", "113.5", 1600, 600),
    ]

    cursor.executemany(
        """INSERT INTO 'TEST_M1' ("ID", "Date", "SecCode", "ClassCode", "O", "H", "L", "C", "V", "OpenInterest")
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        test_data,
    )

    # Создаём вторую таблицу для теста множественных инструментов
    cursor.execute("""
        CREATE TABLE 'TEST2_M1' (
            'ID' INTEGER PRIMARY KEY,
            'Date' TEXT,
            'SecCode' TEXT,
            'ClassCode' TEXT,
            'O' TEXT,
            'H' TEXT,
            'L' TEXT,
            'C' TEXT,
            'V' INTEGER,
            'OpenInterest' INTEGER
        )
    """)

    cursor.execute(
        """INSERT INTO 'TEST2_M1' ("ID", "Date", "SecCode", "ClassCode", "O", "H", "L", "C", "V", "OpenInterest")
           VALUES (1, '2025-10-28 09:00:00', 'TEST2', 'SPBFUT', '50.0', '52.0', '49.0', '51.0', 500, 200)"""
    )

    conn.commit()
    conn.close()
    return str(db_file)


def test_get_table_list_returns_tables(temp_db_path: str) -> None:
    """
    Проверяет, что get_table_list возвращает правильные имена таблиц.
    """
    tables = get_table_list(temp_db_path)

    assert "TEST_M1" in tables
    assert "TEST2_M1" in tables
    assert len(tables) == 2


def test_get_table_list_file_not_found() -> None:
    """
    Проверяет, что выбрасывается FileNotFoundError для несуществующего файла.
    """
    with pytest.raises(FileNotFoundError) as exc_info:
        get_table_list("C:\\nonexistent\\path\\database.db")

    assert "Файл базы данных не найден" in str(exc_info.value)


def test_load_candles_returns_all_data(temp_db_path: str) -> None:
    """
    Проверяет загрузку всех свечей инструмента без фильтрации.
    """
    df = load_candles(temp_db_path, "TEST")

    assert isinstance(df, pl.DataFrame)
    assert len(df) == 10
    assert df.columns == [
        "id", "date", "sec_code", "class_code",
        "open", "high", "low", "close", "volume", "open_interest",
    ]


def test_load_candles_data_types(temp_db_path: str) -> None:
    """
    Проверяет корректность типов данных в загруженном DataFrame.
    """
    df = load_candles(temp_db_path, "TEST")

    # Проверяем типы колонок
    assert df.schema["id"] == pl.Int64
    assert df.schema["date"] == pl.Datetime
    assert df.schema["sec_code"] == pl.String
    assert df.schema["class_code"] == pl.String
    assert df.schema["open"] == pl.Float64
    assert df.schema["high"] == pl.Float64
    assert df.schema["low"] == pl.Float64
    assert df.schema["close"] == pl.Float64
    assert df.schema["volume"] == pl.Int64
    assert df.schema["open_interest"] == pl.Int64


def test_load_candles_data_correctness(temp_db_path: str) -> None:
    """
    Проверяет корректность загруженных значений.
    """
    df = load_candles(temp_db_path, "TEST")

    # Проверяем первую свечу
    first_row = df.row(0)
    assert first_row[df.columns.index("id")] == 1
    assert first_row[df.columns.index("sec_code")] == "TEST"
    assert first_row[df.columns.index("class_code")] == "SPBFUT"
    assert first_row[df.columns.index("open")] == 100.0
    assert first_row[df.columns.index("high")] == 105.0
    assert first_row[df.columns.index("low")] == 99.0
    assert first_row[df.columns.index("close")] == 104.0
    assert first_row[df.columns.index("volume")] == 1000
    assert first_row[df.columns.index("open_interest")] == 500


def test_load_candles_with_date_filter(temp_db_path: str) -> None:
    """
    Проверяет фильтрацию свечей по диапазону дат.
    """
    # Фильтр по одной дате
    df = load_candles(
        temp_db_path, "TEST",
        start_date="2025-10-29 00:00:00",
        end_date="2025-10-29 23:59:59",
    )

    assert len(df) == 2
    # Все свечи должны быть от 2025-10-29
    assert all(
        datetime(2025, 10, 29) <= row[df.columns.index("date")] <= datetime(2025, 10, 29, 23, 59, 59)
        for row in df.iter_rows()
    )


def test_load_candles_with_start_date_only(temp_db_path: str) -> None:
    """
    Проверяет фильтрацию только по начальной дате.
    """
    df = load_candles(temp_db_path, "TEST", start_date="2025-10-30 00:00:00")

    # Должны быть только свечи с 2025-10-30 и позже (3 с 30.10 + 2 с 31.10 = 5 штук)
    assert len(df) == 5
    assert all(
        row[df.columns.index("date")] >= datetime(2025, 10, 30)
        for row in df.iter_rows()
    )


def test_load_candles_with_end_date_only(temp_db_path: str) -> None:
    """
    Проверяет фильтрацию только по конечной дате.
    """
    df = load_candles(temp_db_path, "TEST", end_date="2025-10-28 23:59:59")

    # Должны быть только свечи до 2025-10-28 (3 штуки)
    assert len(df) == 3
    assert all(
        row[df.columns.index("date")] <= datetime(2025, 10, 28, 23, 59, 59)
        for row in df.iter_rows()
    )


def test_load_candles_empty_filter(temp_db_path: str) -> None:
    """
    Проверяет, что фильтр по несуществующей дате возвращает пустой DataFrame.
    """
    df = load_candles(
        temp_db_path, "TEST",
        start_date="2026-01-01 00:00:00",
        end_date="2026-01-02 00:00:00",
    )

    assert isinstance(df, pl.DataFrame)
    assert df.is_empty()


def test_load_candles_table_not_found(temp_db_path: str) -> None:
    """
    Проверяет, что выбрасывается ValueError для несуществующего инструмента.
    """
    with pytest.raises(ValueError) as exc_info:
        load_candles(temp_db_path, "NONEXISTENT")

    assert "не найдена в базе" in str(exc_info.value)


def test_load_candles_file_not_found() -> None:
    """
    Проверяет, что выбрасывается FileNotFoundError если БД не существует.
    """
    with pytest.raises(FileNotFoundError) as exc_info:
        load_candles("C:\\missing.db", "TEST")

    assert "Файл базы данных не найден" in str(exc_info.value)


def test_get_table_list_empty_db(tmp_path: Path) -> None:
    """
    Проверяет, что для пустой БД возвращается пустой список.
    """
    db_file = tmp_path / "empty.db"
    conn = sqlite3.connect(str(db_file))
    conn.close()

    tables = get_table_list(str(db_file))
    assert tables == []


def test_load_candles_orders_by_date(temp_db_path: str) -> None:
    """
    Проверяет, что данные отсортированы по дате по возрастанию.
    """
    df = load_candles(temp_db_path, "TEST")
    dates = df["date"].to_list()

    # Каждая следующая дата должна быть >= предыдущей
    for i in range(len(dates) - 1):
        assert dates[i] <= dates[i + 1], f"Сортировка нарушена на индексе {i}: {dates[i]} > {dates[i + 1]}"


def test_get_available_instruments_skips_missing_dbs(tmp_path: Path) -> None:
    """
    Проверяет, что get_available_instruments пропускает несуществующие БД.
    """
    result = get_available_instruments(
        futures_paths=[str(tmp_path / "nonexistent.db")],
        shares_paths=[],
    )

    assert result == {"futures": [], "shares": []}


def test_get_available_instruments_with_real_db(temp_db_path: str) -> None:
    """
    Проверяет сбор инструментов из реальной (тестовой) БД.
    """
    result = get_available_instruments(
        futures_paths=[temp_db_path],
        shares_paths=[],
    )

    assert len(result["futures"]) == 2
    # Таблицы сортируются по алфавиту: TEST2_M1 раньше TEST_M1
    assert result["futures"][0]["sec_code"] == "TEST2"
    assert result["futures"][1]["sec_code"] == "TEST"


def test_load_candles_custom_timeframe(temp_db_path: str) -> None:
    """
    Проверяет загрузку с кастомным таймфреймом.
    """
    # Пытаемся загрузить данные с таймфреймом M5 — таблицы нет
    with pytest.raises(ValueError) as exc_info:
        load_candles(temp_db_path, "TEST", timeframe="M5")

    assert "не найдена в базе" in str(exc_info.value)


def test_load_candles_sec_code_case_sensitivity(temp_db_path: str) -> None:
    """
    Проверяет, что поиск таблицы регистрозависим (как в SQLite по умолчанию).
    """
    with pytest.raises(ValueError):
        load_candles(temp_db_path, "test")


def test_load_candles_volume_and_open_interest_types(temp_db_path: str) -> None:
    """
    Проверяет, что volume и open_interest — целые числа.
    """
    df = load_candles(temp_db_path, "TEST")

    assert df["volume"].dtype == pl.Int64
    assert df["open_interest"].dtype == pl.Int64
    assert df["volume"].sum() > 0
    assert df["open_interest"].sum() > 0
