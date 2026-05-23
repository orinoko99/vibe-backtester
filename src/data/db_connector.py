"""
Модуль для подключения к SQLite базам данных QUIK со свечными данными.

Предоставляет функции для:
- Подключения к базам данных фьючерсов и акций
- Получения списка доступных торговых инструментов (таблиц)
- Поиска инструмента по всем базам данных
- Загрузки свечных данных по инструменту
"""

import sqlite3
from pathlib import Path
from typing import Optional

# Список путей к базам данных с метками типа инструмента
БАЗЫ_ДАННЫХ: list[dict] = [
    {"путь": Path(r"D:\_MARKET_TICKDATA\QUIK_DATA\allCandlesFutures.db"), "тип": "фьючерс"},
    {"путь": Path(r"D:\_MARKET_TICKDATA\QUIK_DATA\allCandlesFutures_2020.db"), "тип": "фьючерс"},
    {"путь": Path(r"D:\_MARKET_TICKDATA\QUIK_DATA\allCandlesFutures_2023.db"), "тип": "фьючерс"},
    {"путь": Path(r"D:\_MARKET_TICKDATA\QUIK_DATA\allCandlesShares.db"), "тип": "акция"},
    {"путь": Path(r"D:\_MARKET_TICKDATA\QUIK_DATA\allCandlesShares_2023.db"), "тип": "акция"},
]


def подключиться(путь_бд: Path) -> sqlite3.Connection:
    """
    Создаёт и возвращает подключение к SQLite базе данных.

    Параметры
    ----------
    путь_бд : Path
        Путь к файлу базы данных.

    Возвращает
    -------
    sqlite3.Connection
        Объект подключения к базе данных.

    Raises
    ------
    FileNotFoundError
        Если файл базы данных не найден.
    """
    if not путь_бд.exists():
        raise FileNotFoundError(f"Файл базы данных не найден: {путь_бд}")
    соединение = sqlite3.connect(str(путь_бд))
    соединение.row_factory = sqlite3.Row
    return соединение


def получить_список_таблиц(путь_бд: Path) -> list[str]:
    """
    Возвращает список всех таблиц (торговых инструментов) в указанной базе данных.

    Параметры
    ----------
    путь_бд : Path
        Путь к файлу базы данных.

    Возвращает
    -------
    list[str]
        Список имён таблиц вида 'AAH6_M1', 'SiH6_M1' и т.д.
    """
    соединение = подключиться(путь_бд)
    try:
        курсор = соединение.cursor()
        курсор.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        таблицы = [строка["name"] for строка in курсор.fetchall()]
        return таблицы
    finally:
        соединение.close()


def найти_инструмент(код: str) -> Optional[dict]:
    """
    Ищет торговый инструмент по коду во всех базах данных.

    Параметры
    ----------
    код : str
        Код инструмента, например 'AAH6', 'SiH6', 'SBER'.

    Возвращает
    -------
    Optional[dict]
        Словарь с ключами:
        - 'путь' (Path) — путь к базе данных, где найден инструмент
        - 'таблица' (str) — имя таблицы (например 'AAH6_M1')
        - 'тип' (str) — тип инструмента ('фьючерс' или 'акция')
        None, если инструмент не найден ни в одной базе.
    """
    for запись in БАЗЫ_ДАННЫХ:
        путь = запись["путь"]
        if not путь.exists():
            continue
        имя_таблицы = f"{код}_M1"
        соединение = подключиться(путь)
        try:
            курсор = соединение.cursor()
            курсор.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (имя_таблицы,),
            )
            if курсор.fetchone():
                return {
                    "путь": путь,
                    "таблица": имя_таблицы,
                    "тип": запись["тип"],
                    "код": код,
                }
        finally:
            соединение.close()
    return None


def получить_свечи(
    путь_бд: Path,
    таблица: str,
    лимит: Optional[int] = None,
    смещение: Optional[int] = None,
) -> list[sqlite3.Row]:
    """
    Загружает свечные данные из указанной таблицы.

    Параметры
    ----------
    путь_бд : Path
        Путь к файлу базы данных.
    таблица : str
        Имя таблицы (например 'AAH6_M1').
    лимит : Optional[int]
        Максимальное количество записей.
    смещение : Optional[int]
        Смещение от начала (для пагинации).

    Возвращает
    -------
    list[sqlite3.Row]
        Список строк с колонками: ID, Date, SecCode, ClassCode,
        O (open), H (high), L (low), C (close), V (volume), OpenInterest.
    """
    соединение = подключиться(путь_бд)
    try:
        курсор = соединение.cursor()
        запрос = f"SELECT * FROM [{таблица}] ORDER BY ID"
        if лимит is not None:
            запрос += f" LIMIT {лимит}"
        if смещение is not None:
            запрос += f" OFFSET {смещение}"
        курсор.execute(запрос)
        return [строка for строка in курсор.fetchall()]
    finally:
        соединение.close()


def проверить_доступность_баз() -> list[dict]:
    """
    Проверяет, какие базы данных доступны (существуют на диске).

    Возвращает
    -------
    list[dict]
        Список словарей с ключами 'путь', 'доступна', 'тип'.
    """
    результаты = []
    for запись in БАЗЫ_ДАННЫХ:
        путь = запись["путь"]
        результаты.append({
            "путь": путь,
            "доступна": путь.exists(),
            "тип": запись["тип"],
        })
    return результаты
