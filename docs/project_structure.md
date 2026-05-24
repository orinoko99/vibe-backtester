# Структура проекта backtester

```
backtester/
├── .ai/                    # Служебные файлы агента
│   ├── state.json          # Текущее состояние агента (FSM)
│   └── tests.json          # Информация о тестах
├── docs/                   # Документация и инструкции
│   ├── ai_prompt           # Главный промпт агента (только чтение)
│   ├── project.md          # Описание проекта
│   ├── PROMPT.txt          # Быстрый запуск агента
│   ├── project_structure.md # Этот файл — структура проекта
│   ├── roadmap.md          # План разработки
│   ├── completed_tasks.md  # История выполненных задач
│   └── error_log.md        # Лог ошибок и исправлений
├── src/                    # Исходный код
│   ├── __init__.py
│   ├── main.py             # Точка входа в приложение
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py  # Главное окно приложения
│   │   └── chart_widget.py # Виджет графика (lightweight-charts + PySide6)
│   ├── data/
│   │   ├── __init__.py
│   │   ├── loader.py       # Загрузка данных из SQLite
│   │   └── cache.py        # Кэширование в Parquet
│   ├── backtest/
│   │   ├── __init__.py
│   │   ├── engine.py       # Движок бэктестинга
│   │   └── portfolio.py    # Портфельное тестирование
│   ├── indicators/
│   │   ├── __init__.py
│   │   └── base.py         # Базовые индикаторы
│   └── utils/
│       ├── __init__.py
│       └── db_utils.py     # Утилиты для работы с БД
├── tests/                  # Тесты
│   ├── __init__.py
│   ├── test_loader.py
│   ├── test_chart.py
│   └── test_backtest.py
├── venv/                   # Виртуальное окружение
├── .gitignore
├── opencode.json
├── requirements.txt        # Зависимости проекта
└── run.bat                 # BAT-файл для запуска приложения
```
