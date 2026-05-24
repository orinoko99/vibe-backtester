"""
Интеграционные тесты: загрузка данных из SQLite и отображение на графике.

Проверяет полный pipeline: создание тестовой БД → загрузка через loader
→ передача данных в ChartWidget → корректность отображения.
"""

import sqlite3
from pathlib import Path

import polars as pl
import pytest
from PySide6.QtWidgets import QApplication

from src.data.loader import load_candles
from src.gui.chart_widget import ChartWidget
from src.gui.main_window import MainWindow


@pytest.fixture
def real_app(qtbot) -> QApplication:
    """
    Фикстура: возвращает экземпляр QApplication (создаётся qtbot).
    """
    return QApplication.instance()


@pytest.fixture
def temp_db_with_data(tmp_path: Path) -> str:
    """
    Фикстура: создаёт временную SQLite БД с тестовыми свечными данными.
    """
    db_file = tmp_path / "test_integration.db"
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()

    # Создаём таблицу, идентичную реальной структуре QUIK
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

    # Вставляем тестовые данные (20 свечей)
    test_data = [
        (i, f"2025-10-28 {9 + (i - 1) // 60:02d}:{(i - 1) % 60:02d}:00",
         "TEST", "SPBFUT",
         str(100.0 + i * 0.5), str(105.0 + i * 0.5),
         str(99.0 + i * 0.5), str(102.0 + i * 0.5),
         1000 + i * 100, 500 + i * 10)
        for i in range(1, 21)
    ]

    cursor.executemany(
        """INSERT INTO 'TEST_M1' ("ID", "Date", "SecCode", "ClassCode",
           "O", "H", "L", "C", "V", "OpenInterest")
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        test_data,
    )

    conn.commit()
    conn.close()
    return str(db_file)


@pytest.fixture
def main_window(qtbot) -> MainWindow:
    """
    Фикстура: создаёт MainWindow с интегрированным ChartWidget.
    """
    window = MainWindow()
    window.show()
    qtbot.addWidget(window)
    return window


def test_main_window_has_chart_widget(main_window: MainWindow) -> None:
    """
    Проверяет, что MainWindow содержит ChartWidget после инициализации.
    """
    assert hasattr(main_window, "chart_widget")
    assert isinstance(main_window.chart_widget, ChartWidget)


def test_chart_widget_is_inside_chart_container(main_window: MainWindow) -> None:
    """
    Проверяет, что ChartWidget находится внутри chart_container.
    """
    assert main_window.chart_widget.parent() is main_window.chart_container


def test_load_and_display_updates_status(main_window: MainWindow, temp_db_with_data: str) -> None:
    """
    Проверяет, что load_and_display обновляет статус-бар.
    """
    main_window.load_and_display(temp_db_with_data, "TEST")
    status_text = main_window.statusBar().currentMessage()
    assert "Загружено" in status_text
    assert "TEST" in status_text
    assert "20" in status_text  # 20 свечей


def test_load_and_display_with_date_filter(main_window: MainWindow, temp_db_with_data: str) -> None:
    """
    Проверяет загрузку с фильтром по дате.
    """
    main_window.load_and_display(
        temp_db_with_data, "TEST",
        start_date="2025-10-28 09:05:00",
        end_date="2025-10-28 09:10:00",
    )
    status_text = main_window.statusBar().currentMessage()
    # Должно загрузиться 6 свечей (с 5 по 10)
    assert "6" in status_text


def test_load_and_display_file_not_found(main_window: MainWindow) -> None:
    """
    Проверяет обработку ошибки при отсутствии файла БД.
    """
    main_window.load_and_display("C:\\nonexistent\\test.db", "TEST")
    status_text = main_window.statusBar().currentMessage()
    assert "Ошибка" in status_text
    assert "Файл базы данных не найден" in status_text


def test_load_and_display_table_not_found(main_window: MainWindow, temp_db_with_data: str) -> None:
    """
    Проверяет обработку ошибки при отсутствии таблицы.
    """
    main_window.load_and_display(temp_db_with_data, "NONEXISTENT")
    status_text = main_window.statusBar().currentMessage()
    assert "Ошибка" in status_text
    assert "не найдена" in status_text


def test_load_and_display_empty_data(main_window: MainWindow, tmp_path: Path) -> None:
    """
    Проверяет обработку пустого набора данных.
    """
    # Создаём БД с таблицей, но без данных
    db_file = tmp_path / "empty_data.db"
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE 'EMPTY_M1' (
            'ID' INTEGER PRIMARY KEY,
            'Date' TEXT,
            'SecCode' TEXT,
            'ClassCode' TEXT,
            'O' TEXT, 'H' TEXT, 'L' TEXT, 'C' TEXT,
            'V' INTEGER, 'OpenInterest' INTEGER
        )
    """)
    conn.commit()
    conn.close()

    main_window.load_and_display(str(db_file), "EMPTY")
    status_text = main_window.statusBar().currentMessage()
    assert "Нет данных" in status_text


def test_loader_and_chart_data_consistency(main_window: MainWindow, temp_db_with_data: str) -> None:
    """
    Проверяет, что данные, переданные в график, соответствуют загруженным.
    """
    # Загружаем данные через loader напрямую
    df_direct = load_candles(temp_db_with_data, "TEST")

    # Загружаем через MainWindow
    main_window.load_and_display(temp_db_with_data, "TEST")

    # Проверяем, что количество свечей совпадает
    status_text = main_window.statusBar().currentMessage()
    assert str(len(df_direct)) in status_text


def test_multiple_loads_clear_previous_data(main_window: MainWindow, temp_db_with_data: str) -> None:
    """
    Проверяет, что повторная загрузка обновляет данные.
    """
    # Первая загрузка
    main_window.load_and_display(temp_db_with_data, "TEST")
    first_status = main_window.statusBar().currentMessage()

    # Вторая загрузка с фильтром (меньше данных)
    main_window.load_and_display(
        temp_db_with_data, "TEST",
        start_date="2025-10-28 09:00:00",
        end_date="2025-10-28 09:04:00",
    )
    second_status = main_window.statusBar().currentMessage()

    assert first_status != second_status
    assert "5" in second_status  # 5 свечей


def test_demo_data_loading_with_missing_db(main_window: MainWindow) -> None:
    """
    Проверяет, что при передаче несуществующей БД в load_and_display
    отображается сообщение об ошибке.
    """
    main_window.load_and_display(
        "C:\\nonexistent_demo_path\\test.db", "TEST"
    )
    status_text = main_window.statusBar().currentMessage()
    assert "Ошибка" in status_text
