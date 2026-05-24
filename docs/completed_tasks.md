# Выполненные задачи

- [x] **Этап 1.1** — Инициализация проекта — 2026-05-24 — commit d40b289
  - Установлены зависимости: PySide6, polars, lightweight-charts
  - Создана структура директорий `src/` и `tests/`
  - Создан `main.py` — точка входа с главным окном PySide6
  - Создан `run_backtester.bat` — bat-файл запуска
  - Создан `README.md`
  - Написаны и пройдены тесты (`tests/test_main.py` — 3 теста)

- [x] **Этап 1.2** — Модуль config.py — 2026-05-24 — commit adfcea2
  - Создан `src/utils/config.py` с путями к БД, настройками окна и графика
  - Написаны и пройдены тесты (`tests/test_config.py` — 23 теста)

- [x] **Этап 2.1** — Модуль data/models.py — 2026-05-24 — commit cd0ba30
  - Создан `src/data/models.py`: Pydantic-модели Candle и InstrumentInfo
  - Написаны и пройдены тесты (`tests/test_models.py` — 29 тестов)

- [x] **Этап 2.2** — Модуль data/database.py — 2026-05-24 — commit c6b8e70
  - Создан `src/data/database.py`: DatabaseManager, поиск инструментов, загрузка свечей
  - Написаны и пройдены тесты (`tests/test_database.py` — 23 теста)

- [x] **Этап 2.3** — Модуль data/loader.py — 2026-05-24 — commit aa74340
  - Создан `src/data/loader.py`: DataLoader с паддингом, shift/zoom, кэшированием
  - Написаны и пройдены тесты (`tests/test_loader.py` — 22 теста)

- [x] **Этап 3.1** — GUI: главное окно PySide6 — 2026-05-24 — commit 64791a1
  - Создан `src/gui/main_window.py` с меню, тулбаром, док-панелями, статус-баром
  - Обновлён `main.py` — импорт из `src.gui.main_window`
  - Написаны тесты (`tests/test_main.py` — 12 тестов)

- [x] **Этап 3.2** — GUI: виджет графика lightweight-charts — 2026-05-24 — commit 7d93be7
  - Создан `src/gui/chart_widget.py` на QWebEngineView
  - ChartWidget интегрирован в MainWindow
  - Методы: set_candles, set_visible_range, set_theme, fit_content
  - Написаны и пройдены тесты (`tests/test_main.py` — 15 тестов)

- [x] **Этап 3.3** — GUI: интерактивность графика — 2026-05-24 — commit c6aa781
  - QWebChannel мост для JS→Python (ChartBridge)
  - Подписка на subscribeVisibleTimeRangeChange
  - Интеграция DataLoader с ChartWidget
  - load_instrument с автоматической подгрузкой
  - 112 тестов проходят

- [x] **Этап 3.4** — GUI: панель выбора инструментов — 2026-05-24
  - Создан `src/gui/instrument_panel.py`: список инструментов, поиск по коду, кнопка загрузки
  - Сигнал `instrument_selected` подключён к `MainWindow.load_instrument`
  - Обновлён `test_main.py` (QDockWidget вместо устаревших классов-заглушек)
  - Написаны и пройдены тесты (`tests/test_instrument_panel.py` — 20 тестов)
  - Всего тестов: 117 (без test_main.py из-за QWebEngineView)
