"""
Модуль загрузки данных из SQLite-баз QUIK.

Предоставляет функции для подключения к базам данных фьючерсов и акций,
получения списка доступных инструментов и загрузки свечных данных.
"""

import sqlite3
from pathlib import Path
from typing import Optional

import polars as pl


# Пути к базам данных по умолчанию (из project.md)
DEFAULT_FUTURES_DB_PATHS: list[str] = [
    r"D:\_MARKET_TICKDATA\QUIK_DATA\allCandlesFutures.db",
    r"D:\_MARKET_TICKDATA\QUIK_DATA\allCandlesFutures_2020.db",
    r"D:\_MARKET_TICKDATA\QUIK_DATA\allCandlesFutures_2023.db",
]

DEFAULT_SHARES_DB_PATHS: list[str] = [
    r"D:\_MARKET_TICKDATA\QUIK_DATA\allCandlesShares.db",
    r"D:\_MARKET_TICKDATA\QUIK_DATA\allCandlesShares_2023.db",
]


def get_table_list(db_path: str) -> list[str]:
    """
    Возвращает список всех таблиц (торговых инструментов) в указанной БД.

    Параметры:
        db_path: Путь к файлу SQLite базы данных.

    Возвращает:
        Список имён таблиц в формате ['AAH6_M1', 'SiH6_M1', ...].

    Исключения:
        FileNotFoundError: Если файл БД не существует.
        sqlite3.DatabaseError: Если файл не является SQLite БД.
    """
    db_file = Path(db_path)
    if not db_file.exists():
        raise FileNotFoundError(f"Файл базы данных не найден: {db_path}")

    with sqlite3.connect(str(db_file)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]

    return tables


def load_candles(
    db_path: str,
    sec_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    timeframe: str = "M1",
) -> pl.DataFrame:
    """
    Загружает свечные данные для указанного инструмента из SQLite БД.

    Имя таблицы формируется по шаблону: {sec_code}_{timeframe}.
    Пример: для sec_code='AAH6' и timeframe='M1' таблица будет 'AAH6_M1'.

    Параметры:
        db_path: Путь к файлу SQLite базы данных.
        sec_code: Код инструмента (например 'AAH6', 'SiH6').
        start_date: Начальная дата фильтрации (включительно, формат 'YYYY-MM-DD HH:MM:SS').
                    Если None — без фильтра по началу.
        end_date: Конечная дата фильтрации (включительно, формат 'YYYY-MM-DD HH:MM:SS').
                  Если None — без фильтра по концу.
        timeframe: Таймфрейм (по умолчанию 'M1' — 1 минута).

    Возвращает:
        Polars DataFrame с колонками:
        - id (Int64) — первичный ключ
        - date (Datetime) — дата и время свечи
        - sec_code (String) — код инструмента
        - class_code (String) — класс инструмента
        - open (Float64) — цена открытия
        - high (Float64) — максимальная цена
        - low (Float64) — минимальная цена
        - close (Float64) — цена закрытия
        - volume (Int64) — объём
        - open_interest (Int64) — открытый интерес

    Исключения:
        FileNotFoundError: Если файл БД не существует.
        ValueError: Если таблица для указанного инструмента не найдена.
    """
    db_file = Path(db_path)
    if not db_file.exists():
        raise FileNotFoundError(f"Файл базы данных не найден: {db_path}")

    table_name = f"{sec_code}_{timeframe}"

    with sqlite3.connect(str(db_file)) as conn:
        # Проверяем существование таблицы
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        if cursor.fetchone() is None:
            raise ValueError(
                f"Таблица '{table_name}' не найдена в базе '{db_path}'. "
                f"Доступные инструменты: {get_table_list(db_path)}"
            )

        # Строим SQL запрос с опциональной фильтрацией по дате
        query = f"""
            SELECT
                "ID" AS id,
                "Date" AS date,
                "SecCode" AS sec_code,
                "ClassCode" AS class_code,
                CAST("O" AS REAL) AS open,
                CAST("H" AS REAL) AS high,
                CAST("L" AS REAL) AS low,
                CAST("C" AS REAL) AS close,
                "V" AS volume,
                "OpenInterest" AS open_interest
            FROM "{table_name}"
        """
        params: list[str] = []

        # Добавляем WHERE условия если указаны даты
        where_clauses: list[str] = []
        if start_date is not None:
            where_clauses.append("\"Date\" >= ?")
            params.append(start_date)
        if end_date is not None:
            where_clauses.append("\"Date\" <= ?")
            params.append(end_date)

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        query += " ORDER BY \"Date\" ASC"

        # Загружаем данные в Polars DataFrame
        df = pl.read_database(query, connection=conn, execute_options={"parameters": params})

    # Приводим колонку date к типу Datetime
    if not df.is_empty():
        df = df.with_columns(
            pl.col("date").str.to_datetime("%Y-%m-%d %H:%M:%S")
        )

    return df


def get_available_instruments(
    futures_paths: Optional[list[str]] = None,
    shares_paths: Optional[list[str]] = None,
) -> dict[str, list[dict[str, str]]]:
    """
    Собирает список всех доступных инструментов из всех БД.

    Параметры:
        futures_paths: Список путей к БД фьючерсов.
                       Если None — используются пути по умолчанию.
        shares_paths: Список путей к БД акций.
                      Если None — используются пути по умолчанию.

    Возвращает:
        Словарь с категориями:
        {
            "futures": [
                {"db_path": "...", "table": "AAH6_M1", "sec_code": "AAH6"},
                ...
            ],
            "shares": [...]
        }

    Примечание:
        Если файл БД не существует — он пропускается, ошибка не выбрасывается.
    """
    if futures_paths is None:
        futures_paths = DEFAULT_FUTURES_DB_PATHS
    if shares_paths is None:
        shares_paths = DEFAULT_SHARES_DB_PATHS

    result: dict[str, list[dict[str, str]]] = {
        "futures": [],
        "shares": [],
    }

    # Вспомогательная функция для сбора инструментов из списка БД
    def _collect_from_paths(paths: list[str], category_key: str) -> None:
        for db_path in paths:
            try:
                tables = get_table_list(db_path)
                for table in tables:
                    sec_code = table.split("_")[0] if "_" in table else table
                    result[category_key].append({
                        "db_path": db_path,
                        "table": table,
                        "sec_code": sec_code,
                    })
            except (FileNotFoundError, sqlite3.DatabaseError):
                continue

    _collect_from_paths(futures_paths, "futures")
    _collect_from_paths(shares_paths, "shares")

    return result
