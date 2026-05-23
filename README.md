# Vibe Backtester

Бэктестер торговых стратегий с интерактивными графиками и поддержкой портфелей инструментов.

## Возможности

- **Загрузка данных** — чтение минутных свечей из SQLite баз QUIK (фьючерсы и акции)
- **Бэктестинг** — прогон стратегий на исторических данных с расчётом метрик (доходность, Шарп, просадка, win rate)
- **Портфели** — тестирование нескольких инструментов одновременно с распределением капитала
- **Интерактивный график** — свечной график с зумом/паном, поддержка нескольких инструментов, Volume Profile
- **Рисование** — горизонтальные/вертикальные/трендовые линии, прямоугольники, текстовые метки
- **Индикаторы** — SMA, EMA, RSI, Bollinger Bands (отображение на графике)
- **Стратегии** — SMA crossover, возможность создания собственных стратегий через наследование

## Установка

```bash
# Клонировать репозиторий
git clone https://github.com/orinoko99/vibe-backtester.git
cd vibe-backtester

# Создать виртуальное окружение
python -m venv venv
venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt
```

## Запуск

```bash
python src/main.py
```

## Структура проекта

```
src/
├── main.py              # точка входа
├── data/
│   ├── db_connector.py  # подключение к SQLite БД
│   └── data_loader.py   # загрузка и ресемплинг свечных данных
├── backtester/
│   ├── strategy.py      # базовый класс стратегии
│   ├── engine.py        # ядро бэктестера
│   └── portfolio.py     # тестирование портфелей
├── indicators/
│   └── base.py          # SMA, EMA, RSI, MACD, BB, Stochastic
├── ui/
│   ├── app.py           # главное окно
│   ├── chart.py         # свечной график
│   ├── drawings.py      # инструменты рисования
│   └── instruments.py   # выбор инструментов/таймфрейма
└── utils/
    └── helpers.py       # вспомогательные функции
```

## Тестирование

```bash
pytest tests/ -v
```

Всего 122 теста покрывают модули данных, бэктестера, индикаторов и UI.

## Источники данных

Проект использует минутные свечные данные из SQLite баз данных QUIK:
- `allCandlesFutures.db`, `allCandlesFutures_2020.db`, `allCandlesFutures_2023.db`
- `allCandlesShares.db`, `allCandlesShares_2023.db`

Структура таблиц: `{SecCode}_M1` с колонками Date, O, H, L, C, V, OpenInterest.

## Технологии

- Python 3.14
- PyQt6, pyqtgraph — GUI и интерактивные графики
- pandas, numpy — обработка данных
- pytest — тестирование

## Лицензия

MIT
