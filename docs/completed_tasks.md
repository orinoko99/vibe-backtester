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

- [x] **Этап 3.1** — GUI: главное окно PySide6 — 2026-05-24
  - Создан `src/gui/main_window.py` с меню, тулбаром, док-панелями, статус-баром
  - Обновлён `main.py` — импорт из `src.gui.main_window`
  - Написаны тесты (`tests/test_main.py` — 12 тестов)
  - Создан `src/data/loader.py`: DataLoader с паддингом, shift/zoom, кэшированием
  - Написаны и пройдены тесты (`tests/test_loader.py` — 22 теста)
