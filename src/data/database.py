#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для работы с SQLite-базами данных свечных котировок.

Предоставляет:
- подключение к базам данных по путям из конфигурации
- получение списка всех доступных инструментов (таблиц)
- чтение свечей по коду инструмента и диапазону дат
- поиск базы данных по инструменту
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Generator, Iterator, List, Optional, Tuple

from src.data.models import Candle, InstrumentInfo, InstrumentType
from src.utils.config import CONFIG


@dataclass
class InstrumentEntry:
    """
    Запись об инструменте, полученная из БД.

    Содержит код инструмента, класс, тип БД и путь к файлу БД.
    """

    sec_code: str
    class_code: str = ""
    db_type: InstrumentType = InstrumentType.FUTURES
    db_path: Path = field(default_factory=Path)


class DatabaseManager:
    """
    Менеджер подключений к SQLite-базам данных.

    Позволяет:
    - получать список инструментов из всех баз
    - загружать свечи по инструменту и датам
    - определять, в какой базе находится инструмент
    """

    def __init__(
        self,
        futures_paths: Optional[Tuple[Path, ...]] = None,
        shares_paths: Optional[Tuple[Path, ...]] = None,
    ) -> None:
        """
        Инициализация менеджера с путями к базам данных.

        Если пути не указаны, используются пути из глобальной конфигурации.
        """
        self._futures_paths: Tuple[Path, ...] = (
            futures_paths if futures_paths is not None
            else CONFIG.databases.futures
        )
        self._shares_paths: Tuple[Path, ...] = (
            shares_paths if shares_paths is not None
            else CONFIG.databases.shares
        )

    @property
    def all_db_paths(self) -> List[Tuple[Path, InstrumentType]]:
        """
        Возвращает список всех путей к БД с указанием их типа.
        """
        result: List[Tuple[Path, InstrumentType]] = []
        for path in self._futures_paths:
            result.append((path, InstrumentType.FUTURES))
        for path in self._shares_paths:
            result.append((path, InstrumentType.SHARES))
        return result

    @contextmanager
    def _connect(
        self, db_path: Path
    ) -> Generator[sqlite3.Connection, None, None]:
        """
        Контекстный менеджер для подключения к SQLite-базе.

        Автоматически закрывает соединение после использования.
        """
        connection: Optional[sqlite3.Connection] = None
        try:
            connection = sqlite3.connect(str(db_path))
            connection.row_factory = sqlite3.Row
            yield connection
        finally:
            if connection is not None:
                connection.close()

    def get_instrument_tables(
        self, db_path: Path
    ) -> List[str]:
        """
        Возвращает список всех таблиц (инструментов) в указанной базе данных.

        Фильтрует системные таблицы SQLite (начинающиеся с sqlite_).
        """
        tables: List[str] = []
        try:
            with self._connect(db_path) as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                    "ORDER BY name"
                )
                tables = [row["name"] for row in cursor.fetchall()]
        except sqlite3.Error:
            pass  # База может отсутствовать — просто возвращаем пустой список
        return tables

    def get_all_instruments(self) -> List[InstrumentEntry]:
        """
        Собирает список всех инструментов из всех доступных баз данных.

        Возвращает: список InstrumentEntry с кодом, классом, типом и путём.
        """
        instruments: List[InstrumentEntry] = []

        for db_path, db_type in self.all_db_paths:
            tables = self.get_instrument_tables(db_path)
            for table_name in tables:
                # Имя таблицы вида 'AAH6_M1' -> sec_code = 'AAH6'
                sec_code = table_name.rsplit("_", 1)[0] if "_" in table_name else table_name

                # Пробуем прочитать ClassCode из первой записи таблицы
                class_code: str = ""
                try:
                    with self._connect(db_path) as conn:
                        cursor = conn.execute(
                            f"SELECT ClassCode FROM \"{table_name}\" "
                            "WHERE ClassCode IS NOT NULL "
                            "AND ClassCode != '' LIMIT 1"
                        )
                        row = cursor.fetchone()
                        if row is not None:
                            class_code = row["ClassCode"]
                except sqlite3.Error:
                    pass

                instruments.append(InstrumentEntry(
                    sec_code=sec_code,
                    class_code=class_code,
                    db_type=db_type,
                    db_path=db_path,
                ))

        return instruments

    def find_instrument(
        self, sec_code: str
    ) -> Optional[InstrumentEntry]:
        """
        Ищет инструмент по коду во всех базах данных.

        Возвращает первый найденный InstrumentEntry или None.
        """
        for db_path, db_type in self.all_db_paths:
            # Формируем ожидаемое имя таблицы
            table_name = f"{sec_code}_M1"
            tables = self.get_instrument_tables(db_path)
            if table_name in tables:
                class_code: str = ""
                try:
                    with self._connect(db_path) as conn:
                        cursor = conn.execute(
                            f"SELECT ClassCode FROM \"{table_name}\" LIMIT 1"
                        )
                        row = cursor.fetchone()
                        if row is not None:
                            class_code = row["ClassCode"]
                except sqlite3.Error:
                    pass

                return InstrumentEntry(
                    sec_code=sec_code,
                    class_code=class_code,
                    db_type=db_type,
                    db_path=db_path,
                )
        return None

    def get_candles(
        self,
        sec_code: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[Candle]:
        """
        Загружает свечи для указанного инструмента.

        Параметры:
            sec_code — код инструмента (например 'AAH6')
            start_date — начальная дата (включительно), опционально
            end_date — конечная дата (включительно), опционально
            limit — максимальное количество свечей, опционально

        Возвращает: список объектов Candle.
        """
        entry = self.find_instrument(sec_code)
        if entry is None:
            return []

        table_name = f"{sec_code}_M1"
        candles: List[Candle] = []

        try:
            with self._connect(entry.db_path) as conn:
                query_parts: List[str] = [
                    f"SELECT Date, O, H, L, C, V, OpenInterest "
                    f"FROM \"{table_name}\""
                ]
                params: List[str] = []
                conditions: List[str] = []

                if start_date is not None:
                    conditions.append("Date >= ?")
                    params.append(start_date.strftime("%Y-%m-%d %H:%M:%S"))

                if end_date is not None:
                    conditions.append("Date <= ?")
                    params.append(end_date.strftime("%Y-%m-%d %H:%M:%S"))

                if conditions:
                    query_parts.append("WHERE " + " AND ".join(conditions))

                query_parts.append("ORDER BY Date ASC")

                if limit is not None:
                    query_parts.append("LIMIT ?")
                    params.append(str(limit))

                query = " ".join(query_parts)
                cursor = conn.execute(query, params)

                for row in cursor.fetchall():
                    try:
                        timestamp = datetime.strptime(
                            row["Date"], "%Y-%m-%d %H:%M:%S"
                        )
                    except ValueError:
                        # Пробуем альтернативный формат даты
                        try:
                            timestamp = datetime.fromisoformat(row["Date"])
                        except ValueError:
                            continue

                    candle = Candle(
                        timestamp=timestamp,
                        open=float(row["O"]),
                        high=float(row["H"]),
                        low=float(row["L"]),
                        close=float(row["C"]),
                        volume=int(row["V"]),
                        open_interest=(
                            int(row["OpenInterest"])
                            if row["OpenInterest"] is not None
                            else None
                        ),
                    )
                    candles.append(candle)

        except sqlite3.Error:
            pass

        return candles
