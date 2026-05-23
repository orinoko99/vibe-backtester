"""
Модуль загрузки и обработки свечных данных.

Предоставляет:
- Загрузку свечей из БД в pandas DataFrame
- Ресемплинг (агрегацию) в произвольный таймфрейм
- Поиск инструмента по коду во всех базах
"""

from typing import Optional

import pandas as pd

from src.data.db_connector import (
    найти_инструмент,
    получить_свечи,
)

# Словарь соответствия таймфреймов для ресемплинга pandas
ТАЙМФРЕЙМЫ_PANDAS = {
    "1min": "1min",
    "5min": "5min",
    "15min": "15min",
    "30min": "30min",
    "1h": "1h",
    "4h": "4h",
    "1d": "1D",
}

# Колонки, которые будут в итоговом DataFrame
КОЛОНКИ_СВЕЧЕЙ = ["open", "high", "low", "close", "volume", "open_interest"]
КОЛОНКИ_РЕСЕМПЛИНГА = {
    "open": "first",
    "high": "max",
    "low": "min",
    "close": "last",
    "volume": "sum",
    "open_interest": "last",
}


def загрузить_инструмент(
    код: str,
    таймфрейм: str = "1min",
    лимит: Optional[int] = None,
) -> Optional[pd.DataFrame]:
    """
    Загружает свечные данные для указанного инструмента.

    Ищет инструмент по коду во всех доступных базах данных,
    загружает минутные свечи и при необходимости агрегирует
    в указанный таймфрейм.

    Параметры
    ----------
    код : str
        Код инструмента (например 'AAH6', 'SiH6', 'SBER').
    таймфрейм : str, optional
        Таймфрейм для агрегации: '1min', '5min', '15min',
        '30min', '1h', '4h', '1d' (по умолчанию '1min').
    лимит : Optional[int]
        Максимальное количество загружаемых минутных свечей.

    Возвращает
    -------
    Optional[pd.DataFrame]
        DataFrame с колонками:
        - datetime (datetime64[ns], индекс)
        - open, high, low, close (float64)
        - volume (int64)
        - open_interest (int64)
        - sec_code (str)
        - class_code (str)

        None, если инструмент не найден.
    """
    # Ищем инструмент в базах
    информация = найти_инструмент(код)
    if информация is None:
        return None

    # Загружаем сырые данные
    строки = получить_свечи(
        информация["путь"],
        информация["таблица"],
        лимит=лимит,
    )

    if not строки:
        return None

    # Преобразуем в DataFrame
    записи = []
    for строка in строки:
        записи.append({
            "datetime": строка["Date"],
            "open": float(строка["O"]),
            "high": float(строка["H"]),
            "low": float(строка["L"]),
            "close": float(строка["C"]),
            "volume": int(строка["V"]),
            "open_interest": int(строка["OpenInterest"]),
            "sec_code": строка["SecCode"],
            "class_code": строка["ClassCode"],
        })

    df = pd.DataFrame(записи)

    # Преобразуем datetime
    df["datetime"] = pd.to_datetime(df["datetime"])
    df.set_index("datetime", inplace=True)
    df.sort_index(inplace=True)

    # Если нужен не минутный таймфрейм — агрегируем
    if таймфрейм != "1min":
        правило = ТАЙМФРЕЙМЫ_PANDAS.get(таймфрейм)
        if правило is None:
            допустимые = ", ".join(ТАЙМФРЕЙМЫ_PANDAS.keys())
            raise ValueError(
                f"Неподдерживаемый таймфрейм '{таймфрейм}'. "
                f"Допустимые: {допустимые}"
            )
        df = df.resample(правило).agg(КОЛОНКИ_РЕСЕМПЛИНГА)
        # Убираем строки с NaN (первая строка после ресемплинга)
        df.dropna(subset=["open"], inplace=True)
        # Преобразуем объём обратно в int
        df["volume"] = df["volume"].astype(int)
        df["open_interest"] = df["open_interest"].astype(int)

    return df


def получить_доступные_инструменты() -> list[dict]:
    """
    Возвращает список всех доступных инструментов из всех баз данных.

    Выполняет полный перебор всех таблиц во всех базах.

    Возвращает
    -------
    list[dict]
        Список словарей с ключами: код, таблица, тип, путь.
    """
    from src.data.db_connector import БАЗЫ_ДАННЫХ, получить_список_таблиц

    инструменты = []
    for запись in БАЗЫ_ДАННЫХ:
        if not запись["путь"].exists():
            continue
        try:
            таблицы = получить_список_таблиц(запись["путь"])
        except Exception:
            continue
        for имя_таблицы in таблицы:
            if имя_таблицы.endswith("_M1"):
                код = имя_таблицы[:-3]  # Убираем суффикс '_M1'
                инструменты.append({
                    "код": код,
                    "таблица": имя_таблицы,
                    "тип": запись["тип"],
                    "путь": запись["путь"],
                })
    return инструменты


def загрузить_диапазон(
    код: str,
    таймфрейм: str = "1min",
    дата_начала: Optional[str] = None,
    дата_конца: Optional[str] = None,
) -> Optional[pd.DataFrame]:
    """
    Загружает свечные данные для инструмента в указанном диапазоне дат.

    Параметры
    ----------
    код : str
        Код инструмента.
    таймфрейм : str
        Таймфрейм для агрегации.
    дата_начала : Optional[str]
        Начальная дата в формате 'YYYY-MM-DD HH:MM:SS' или 'YYYY-MM-DD'.
    дата_конца : Optional[str]
        Конечная дата в формате 'YYYY-MM-DD HH:MM:SS' или 'YYYY-MM-DD'.

    Возвращает
    -------
    Optional[pd.DataFrame]
        DataFrame с данными или None, если инструмент не найден.
    """
    df = загрузить_инструмент(код, таймфрейм=таймфрейм)
    if df is None:
        return None

    if дата_начала:
        df = df[df.index >= pd.to_datetime(дата_начала)]
    if дата_конца:
        df = df[df.index <= pd.to_datetime(дата_конца)]

    return df
