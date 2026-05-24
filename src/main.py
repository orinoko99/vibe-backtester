"""
Точка входа в приложение бэктестер стратегий.

Создаёт QApplication, инициализирует главное окно (MainWindow),
встраивает график (ChartWidget) и опционально загружает
демонстрационные данные.
"""

import sys

from PySide6.QtWidgets import QApplication

from src.data.loader import DEFAULT_FUTURES_DB_PATHS, load_candles
from src.gui.main_window import MainWindow


def main() -> None:
    """
    Главная функция запуска приложения.

    Создаёт экземпляр QApplication, настраивает главное окно,
    пытается загрузить демо-данные из доступных БД, и запускает
    цикл обработки событий Qt.
    """
    # Создаём Qt-приложение
    app = QApplication(sys.argv)
    app.setApplicationName("Бэктестер стратегий")
    app.setApplicationVersion("0.1.0")

    # Создаём главное окно
    window = MainWindow()
    window.show()

    # Пытаемся загрузить демонстрационные данные
    _try_load_demo_data(window)

    # Запускаем цикл обработки событий
    sys.exit(app.exec())


def _try_load_demo_data(window: MainWindow) -> None:
    """
    Пытается загрузить данные первого доступного инструмента
    из доступных баз данных фьючерсов.

    Если ни одна база не найдена — график остаётся пустым,
    в статус-бар выводится сообщение.
    """
    for db_path in DEFAULT_FUTURES_DB_PATHS:
        try:
            # Получаем список инструментов из первой доступной БД
            from src.data.loader import get_table_list

            tables = get_table_list(db_path)
            if not tables:
                continue

            # Берём первый инструмент и загружаем его данные
            first_table = tables[0]
            sec_code = first_table.rsplit("_", 1)[0]

            df = load_candles(db_path, sec_code)
            if not df.is_empty():
                window.load_and_display(db_path, sec_code)
                return

        except (FileNotFoundError, ValueError):
            continue

    # Если ничего не загрузилось — показываем сообщение
    window.set_status_message(
        "Базы данных не найдены. Загрузите данные через меню Файл."
    )


if __name__ == "__main__":
    main()
