# Бэктестер стратегий

Desktop-приложение для тестирования торговых стратегий на исторических данных с интерактивными графиками.

## Возможности

- **Интерактивные графики** — свечные графики на базе lightweight-charts (TradingView-подобные) с зумом, скроллом и динамической подгрузкой данных
- **Бэктестинг** — прогон стратегий по историческим данным с расчётом метрик (total return, Sharpe ratio, max drawdown, win rate)
- **Портфельное тестирование** — запуск стратегий на нескольких инструментах одновременно с распределением капитала
- **Индикаторы** — SMA, EMA, Bollinger Bands, RSI, MACD, Volume Profile
- **Рисование на графике** — горизонтальные/вертикальные линии, трендовые линии, лучи, маркеры, заливки
- **Загрузка данных** — из SQLite-баз QUIK (фьючерсы и акции)

## Стек технологий

| Компонент | Технология |
|-----------|-----------|
| Язык | Python 3.14 |
| GUI | PySide6 (Qt6) |
| Графики | lightweight-charts-python |
| Обработка данных | Polars + NumPy |
| База данных | SQLite |
| Тестирование | pytest |

## Установка

```bash
# Клонировать репозиторий
git clone https://github.com/orinoko99/vibe-backtester.git
cd backtester

# Создать виртуальное окружение
python -m venv venv
venv\Scripts\activate

# Установить зависимости
pip install -r requirements.txt
```

## Запуск

```bash
run.bat
```

Или напрямую:

```bash
python src/main.py
```

## Структура проекта

```
backtester/
├── src/
│   ├── main.py              # Точка входа
│   ├── gui/                 # Графический интерфейс
│   ├── data/                # Загрузка и кэширование данных
│   ├── backtest/            # Движок бэктестинга
│   └── indicators/          # Индикаторы
├── tests/                   # Тесты (330+)
├── docs/                    # Документация
└── requirements.txt
```

## Тестирование

```bash
pytest tests/ -v
```

## Данные

Приложение загружает минутные свечи из SQLite-баз QUIK. Базы данных должны быть расположены по путям:

- Фьючерсы: `D:\_MARKET_TICKDATA\QUIK_DATA\allCandlesFutures.db`
- Акции: `D:\_MARKET_TICKDATA\QUIK_DATA\allCandlesShares.db`

## Лицензия

MIT
