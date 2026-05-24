# Backtester

Desktop-приложение для бэктестинга торговых стратегий с интерактивными графиками.

## Стек технологий

- **Python 3.14+**
- **GUI:** PySide6 (Qt6)
- **Графики:** lightweight-charts (TradingView-style)
- **Обработка данных:** Polars + Pandas
- **Бэктестинг:** VectorBT (open-source)
- **Хранилище:** SQLite

## Установка и запуск

### Предварительные требования

- Python 3.14 или выше
- Виртуальное окружение (venv)

### Установка зависимостей

```bash
python -m venv venv
venv\Scripts\pip install -r requirements.txt
```

### Запуск

Через bat-файл:
```
run_backtester.bat
```

Или напрямую:
```
venv\Scripts\python main.py
```

## Структура проекта

```
src/               # Исходный код
  gui/             # Компоненты графического интерфейса
  data/            # Загрузка и кэширование рыночных данных
  backtesting/     # Движок бэктестинга
  utils/           # Вспомогательные утилиты
tests/             # Тесты pytest
docs/              # Документация и roadmap
```

## Данные

Используются SQLite-базы с минутными свечами:
- Фьючерсы: `allCandlesFutures.db`, `allCandlesFutures_2020.db`, `allCandlesFutures_2023.db`
- Акции: `allCandlesShares.db`, `allCandlesShares_2023.db`
