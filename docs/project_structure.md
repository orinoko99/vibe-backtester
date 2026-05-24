# Структура проекта backtester

```
backtester/
├── main.py                          # Точка входа в приложение
├── run_backtester.bat               # BAT-файл для запуска
├── .gitignore
├── README.md                        # Описание проекта
│
├── src/
│   ├── __init__.py
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py           # Главное окно PySide6
│   │   ├── chart_widget.py          # График (lightweight-charts-python)
│   │   ├── instrument_panel.py      # Панель выбора инструментов/таймфреймов
│   │   └── indicators_panel.py      # Панель добавления индикаторов
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── database.py              # Подключение к SQLite (sqlite3/SQLAlchemy)
│   │   ├── loader.py                # Загрузка свечных данных (с пагинацией)
│   │   ├── cache.py                 # Кэширование в Parquet (опционально)
│   │   └── models.py                # Pydantic-модели данных
│   │
│   ├── backtesting/
│   │   ├── __init__.py
│   │   ├── engine.py                # Ядро бэктестера (VectorBT)
│   │   ├── strategy.py              # Базовый класс стратегии
│   │   └── portfolio.py             # Портфельное тестирование
│   │
│   └── utils/
│       ├── __init__.py
│       └── config.py                # Конфигурация путей и параметров
│
├── tests/
│   ├── __init__.py
│   ├── test_database.py
│   ├── test_loader.py
│   ├── test_strategy.py
│   └── test_chart_widget.py
│
├── docs/
│   ├── ai_prompt                     # Инструкции для AI
│   ├── project.md                   # Описание проекта
│   ├── project_structure.md         # Структура (этот файл)
│   ├── roadmap.md                   # План разработки
│   ├── completed_tasks.md           # Трекер прогресса
│   ├── error_log.md                 # Журнал ошибок
│   └── tests_description.md         # Описание тестов
│
└── .ai/
    ├── state.json                   # Состояние агента
    └── tests.json                   # Результаты тестов
```
