"""
Тесты для модуля data_loader.py

Проверяют:
- Загрузку инструмента в DataFrame
- Ресемплинг в различные таймфреймы
- Фильтрацию по диапазону дат
- Обработку отсутствующих инструментов
- Некорректные таймфреймы
"""

import sqlite3
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.data.data_loader import (
    загрузить_инструмент,
    загрузить_диапазон,
    ТАЙМФРЕЙМЫ_PANDAS,
)


@pytest.fixture
def временная_бд():
    """
    Фикстура: создаёт временную SQLite БД с минутными данными
    инструмента 'TEST' за несколько часов.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        путь = Path(tmp.name)

    соединение = sqlite3.connect(str(путь))
    курсор = соединение.cursor()
    курсор.execute("""
        CREATE TABLE 'TEST_M1' (
            ID INTEGER PRIMARY KEY,
            Date TEXT,
            SecCode TEXT,
            ClassCode TEXT,
            O TEXT,
            H TEXT,
            L TEXT,
            C TEXT,
            V INTEGER,
            OpenInterest INTEGER
        )
    """)

    # Генерируем данные за 3 часа с 10:00 до 12:59 (180 минутных свечей)
    # Цена плавно растёт с 100 до 105
    тестовые_данные = []
    from datetime import datetime, timedelta

    базовое_время = datetime(2025, 10, 28, 10, 0, 0)
    for i in range(180):
        время = базовое_время + timedelta(minutes=i)
        цена_базовая = 100.0 + (i * 5.0 / 180)  # плавный рост
        цена_open = round(цена_базовая + (i % 10) * 0.1, 2)
        цена_high = round(цена_open + 0.3, 2)
        цена_low = round(цена_open - 0.2, 2)
        цена_close = round(цена_open + 0.1, 2)
        объём = 100 + (i % 50) * 10

        тестовые_данные.append((
            i + 1,
            время.strftime("%Y-%m-%d %H:%M:%S"),
            "TEST",
            "SPBFUT",
            str(цена_open),
            str(цена_high),
            str(цена_low),
            str(цена_close),
            объём,
            0,
        ))

    курсор.executemany(
        "INSERT INTO 'TEST_M1' (ID, Date, SecCode, ClassCode, O, H, L, C, V, OpenInterest) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        тестовые_данные,
    )
    соединение.commit()
    соединение.close()

    yield путь
    путь.unlink(missing_ok=True)


@pytest.fixture
def бд_с_пустой_таблицей():
    """Фикстура: БД с существующей, но пустой таблицей."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        путь = Path(tmp.name)

    соединение = sqlite3.connect(str(путь))
    курсор = соединение.cursor()
    курсор.execute("""
        CREATE TABLE 'EMPTY_M1' (
            ID INTEGER PRIMARY KEY,
            Date TEXT,
            SecCode TEXT,
            ClassCode TEXT,
            O TEXT,
            H TEXT,
            L TEXT,
            C TEXT,
            V INTEGER,
            OpenInterest INTEGER
        )
    """)
    соединение.commit()
    соединение.close()

    yield путь
    путь.unlink(missing_ok=True)


def _подменить_базы(monkeypatch, временная_бд):
    """
    Подменяет БАЗЫ_ДАННЫХ в db_connector на временную БД,
    чтобы тесты не зависели от реальных файлов.
    """
    from src.data import db_connector

    monkeypatch.setattr(db_connector, "БАЗЫ_ДАННЫХ", [
        {"путь": временная_бд, "тип": "фьючерс"},
    ])


# ==================================
# Тесты для загрузить_инструмент()
# ==================================

class TestЗагрузитьИнструмент:
    """Тесты функции загрузить_инструмент."""

    def test_загружает_данные_в_dataframe(self, monkeypatch, временная_бд):
        """Должен вернуть DataFrame с данными."""
        _подменить_базы(monkeypatch, временная_бд)

        df = загрузить_инструмент("TEST")
        assert df is not None
        assert isinstance(df, pd.DataFrame)

    def test_правильное_количество_записей(self, monkeypatch, временная_бд):
        """Должен загрузить все 180 записей для минутного таймфрейма."""
        _подменить_базы(monkeypatch, временная_бд)

        df = загрузить_инструмент("TEST")
        assert len(df) == 180

    def test_правильные_колонки(self, monkeypatch, временная_бд):
        """DataFrame должен содержать все необходимые колонки."""
        _подменить_базы(monkeypatch, временная_бд)

        df = загрузить_инструмент("TEST")
        assert list(df.columns) == [
            "open", "high", "low", "close",
            "volume", "open_interest", "sec_code", "class_code",
        ]

    def test_типы_данных_корректны(self, monkeypatch, временная_бд):
        """Типы колонок должны быть правильными."""
        _подменить_базы(monkeypatch, временная_бд)

        df = загрузить_инструмент("TEST")
        assert isinstance(df.index, pd.DatetimeIndex)
        assert df["open"].dtype == "float64"
        assert df["high"].dtype == "float64"
        assert df["low"].dtype == "float64"
        assert df["close"].dtype == "float64"
        assert df["volume"].dtype == "int64"
        assert df["open_interest"].dtype == "int64"
        assert pd.api.types.is_string_dtype(df["sec_code"])
        assert pd.api.types.is_string_dtype(df["class_code"])

    def test_индекс_отсортирован_по_времени(self, monkeypatch, временная_бд):
        """Индекс должен быть монотонно возрастающим."""
        _подменить_базы(monkeypatch, временная_бд)

        df = загрузить_инструмент("TEST")
        assert df.index.is_monotonic_increasing

    def test_sec_code_и_class_code(self, monkeypatch, временная_бд):
        """sec_code и class_code должны быть заполнены."""
        _подменить_базы(monkeypatch, временная_бд)

        df = загрузить_инструмент("TEST")
        assert (df["sec_code"] == "TEST").all()
        assert (df["class_code"] == "SPBFUT").all()

    def test_несуществующий_инструмент(self, monkeypatch, временная_бд):
        """Должен вернуть None для несуществующего инструмента."""
        _подменить_базы(monkeypatch, временная_бд)

        df = загрузить_инструмент("NONEXISTENT")
        assert df is None

    def test_лимит_работает(self, monkeypatch, временная_бд):
        """Лимит должен ограничивать количество загруженных свечей."""
        _подменить_базы(monkeypatch, временная_бд)

        df = загрузить_инструмент("TEST", лимит=50)
        assert len(df) == 50

    def test_пустая_таблица(self, monkeypatch, бд_с_пустой_таблицей):
        """Должен вернуть None для инструмента с пустой таблицей."""
        _подменить_базы(monkeypatch, бд_с_пустой_таблицей)

        df = загрузить_инструмент("EMPTY")
        assert df is None


# ==================================
# Тесты для ресемплинга
# ==================================

class TestРесемплинг:
    """Тесты агрегации в разные таймфреймы."""

    @pytest.mark.parametrize("таймфрейм,ожидаемый_интервал", [
        ("5min", "5min"),
        ("15min", "15min"),
        ("30min", "30min"),
        ("1h", "1h"),
        ("4h", "4h"),
    ])
    def test_ресемплинг_в_таймфрейм(
        self, monkeypatch, временная_бд, таймфрейм, ожидаемый_интервал
    ):
        """Проверка ресемплинга в различные таймфреймы."""
        _подменить_базы(monkeypatch, временная_бд)

        df = загрузить_инструмент("TEST", таймфрейм=таймфрейм)
        assert df is not None

        # Проверяем, что интервал между свечами соответствует ожидаемому
        разница = df.index[1] - df.index[0]
        ожидаемая_разница = pd.Timedelta(ожидаемый_интервал)
        assert разница == ожидаемая_разница, (
            f"Ожидался интервал {ожидаемый_интервал}, получен {разница}"
        )

    def test_ресемплинг_5min_корректное_количество(self, monkeypatch, временная_бд):
        """
        180 минут / 5 = 36 свечей (+ возможно незаконченная последняя,
        но dropna убирает строки с NaN open).
        """
        _подменить_базы(monkeypatch, временная_бд)

        df = загрузить_инструмент("TEST", таймфрейм="5min")
        assert df is not None
        assert len(df) == 36, f"Ожидалось ~36 свечей, получено {len(df)}"

    def test_ресемплинг_1h_корректное_количество(self, monkeypatch, временная_бд):
        """
        180 минут / 60 = 3 часа = 3 свечи.
        """
        _подменить_базы(monkeypatch, временная_бд)

        df = загрузить_инструмент("TEST", таймфрейм="1h")
        assert df is not None
        assert len(df) == 3, f"Ожидалось 3 свечи, получено {len(df)}"

    def test_ресемплинг_сохраняет_ohlc_корректно(self, monkeypatch, временная_бд):
        """Проверка корректности OHLC после ресемплинга в 5min."""
        _подменить_базы(monkeypatch, временная_бд)

        # Загружаем минутные данные (первые 5 минут)
        минутные = загрузить_инструмент("TEST", таймфрейм="1min", лимит=5)
        # Загружаем 5-минутные без лимита, берём первую свечу
        пятиминутные = загрузить_инструмент("TEST", таймфрейм="5min")

        assert минутные is not None
        assert пятиминутные is not None
        первая_пятиминутка = пятиминутные.iloc[0]
        assert первая_пятиминутка["open"] == минутные.iloc[0]["open"]
        assert первая_пятиминутка["high"] == минутные["high"].max()
        assert первая_пятиминутка["low"] == минутные["low"].min()
        assert первая_пятиминутка["close"] == минутные.iloc[-1]["close"]
        assert первая_пятиминутка["volume"] == минутные["volume"].sum()

    def test_неподдерживаемый_таймфрейм(self, monkeypatch, временная_бд):
        """Должен выбросить ValueError для неподдерживаемого таймфрейма."""
        _подменить_базы(monkeypatch, временная_бд)

        with pytest.raises(ValueError, match="Неподдерживаемый таймфрейм"):
            загрузить_инструмент("TEST", таймфрейм="7min")


# ====================================
# Тесты для загрузить_диапазон()
# ====================================

class TestЗагрузитьДиапазон:
    """Тесты функции загрузить_диапазон."""

    def test_фильтр_по_дате_начала(self, monkeypatch, временная_бд):
        """Должен отфильтровать данные по дате начала."""
        _подменить_базы(monkeypatch, временная_бд)

        df = загрузить_диапазон("TEST", дата_начала="2025-10-28 11:00:00")
        assert df is not None
        assert len(df) > 0
        assert df.index[0] >= pd.Timestamp("2025-10-28 11:00:00")

    def test_фильтр_по_дате_конца(self, monkeypatch, временная_бд):
        """Должен отфильтровать данные по дате конца."""
        _подменить_базы(monkeypatch, временная_бд)

        df = загрузить_диапазон("TEST", дата_конца="2025-10-28 10:30:00")
        assert df is not None
        assert df.index[-1] <= pd.Timestamp("2025-10-28 10:30:00")

    def test_фильтр_по_обеим_датам(self, monkeypatch, временная_бд):
        """Должен отфильтровать по диапазону дат."""
        _подменить_базы(monkeypatch, временная_бд)

        df = загрузить_диапазон(
            "TEST",
            дата_начала="2025-10-28 11:00:00",
            дата_конца="2025-10-28 11:30:00",
        )
        assert df is not None
        assert df.index[0] >= pd.Timestamp("2025-10-28 11:00:00")
        assert df.index[-1] <= pd.Timestamp("2025-10-28 11:30:00")

    def test_несуществующий_инструмент_в_диапазоне(self, monkeypatch, временная_бд):
        """Должен вернуть None для несуществующего инструмента."""
        _подменить_базы(monkeypatch, временная_бд)

        df = загрузить_диапазон("NONEXISTENT")
        assert df is None

    def test_диапазон_с_ресемплингом(self, monkeypatch, временная_бд):
        """Должен работать с указанием таймфрейма."""
        _подменить_базы(monkeypatch, временная_бд)

        df = загрузить_диапазон(
            "TEST",
            таймфрейм="5min",
            дата_начала="2025-10-28 10:00:00",
            дата_конца="2025-10-28 10:30:00",
        )
        assert df is not None
        assert len(df) == 7  # 31 минута (10:00-10:30 включ.) / 5 = 7 свечей
