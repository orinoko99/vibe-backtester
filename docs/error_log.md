# Лог ошибок и исправлений

<!-- Формат записи:
## ГГГГ-ММ-ДД ЧЧ:ММ
Проблема: ...
Файлы: ...
Воспроизведение: ...
Предлагаемое решение: ...
-->

## 2026-05-25
Проблема: Мёртвый код в PortfolioBacktestEngine.run() — aligned_data создаётся, но не используется
Файлы: src/backtest/portfolio.py:236
Воспроизведение: В run() aligned_data заполняется, но в прогоне engine.run() используется напрямую filtered data
Решение: Удалить aligned_data, останется только цикл с прямым запуском engine.run()

## 2026-05-25
Проблема: Мёртвый код в _calculate_portfolio_metrics() — цикл подсчёта total_pnl перезаписывается следующей строкой
Файлы: src/backtest/portfolio.py:580-582
Воспроизведение: result.total_pnl = final_equity - initial_equity перезаписывает результат цикла
Решение: Удалить бесполезный цикл, оставить только result.total_pnl = final_equity - initial_equity

## 2026-05-25
Проблема: Дублирование расчёта метрик между _calculate_metrics (PortfolioResult.__post_init__) и _calculate_portfolio_metrics (в Engine)
Файлы: src/backtest/portfolio.py:455-501, 571-607
Воспроизведение: Оба метода считают total_return, sharpe_ratio, max_drawdown одинаково
Решение: Упростить — Engine._calculate_portfolio_metrics создаёт PortfolioResult и полагается на его __post_init__

## 2026-05-25 — Исправление
Проблема: Удалён мёртвый код (engines, allocations loop) и дублирующийся расчёт метрик
Файлы: src/backtest/portfolio.py
Решение: Удалены строки с engines, allocations loop; _calculate_portfolio_metrics теперь полагается на __post_init__ PortfolioResult
Статус: Исправлено, тесты проходят (67/67)
