# Структура проекта vibe-backtester

```
vibe-backtester/
├── .ai/
│   ├── state.json          # состояние агента
│   └── tests.json          # информация о тестах
├── docs/
│   ├── ai_prompt           # инструкции для ИИ (только чтение)
│   ├── project.md          # описание проекта
│   ├── project_structure.md # структура проекта
│   ├── roadmap.md          # план разработки
│   ├── completed_tasks.md  # трекер прогресса
│   ├── error_log.md        # лог ошибок
│   └── tests_description.md # описание тестов
├── src/
│   ├── __init__.py
│   ├── main.py             # точка входа
│   ├── data/
│   │   ├── __init__.py
│   │   ├── db_connector.py # подключение к SQLite БД
│   │   └── data_loader.py  # загрузка свечных данных
│   ├── backtester/
│   │   ├── __init__.py
│   │   ├── engine.py       # ядро бэктестера
│   │   ├── portfolio.py    # тестирование портфелей
│   │   └── strategy.py     # базовый класс стратегии
│   ├── indicators/
│   │   ├── __init__.py
│   │   └── base.py         # базовые индикаторы
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── app.py          # GUI приложение
│   │   ├── chart.py        # интерактивный график
│   │   ├── instruments.py  # выбор инструментов
│   │   └── drawings.py     # рисование на графике
│   └── utils/
│       ├── __init__.py
│       └── helpers.py      # вспомогательные функции
├── tests/
│   ├── __init__.py
│   └── test_data.py
├── README.md
├── .gitignore
└── requirements.txt
```
