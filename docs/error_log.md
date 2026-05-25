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

## 2026-05-25 — Исправление
Проблема: Финальное ревью Этап 2.4 — все найденные проблемы исправлены
Файлы: множественные (см. список ниже)
Решение: 
  - Удалены неиспользуемые импорты (Any, Order, PositionSide, Trade, Callable, Optional, Histogram, Qt, ClassVar) — 9 файлов
  - Удалена мёртвая переменная vah_mask в volume_profile.py
  - Удалены мёртвые методы _calculate_allocations, _get_rebalance_indices в portfolio.py
  - Исправлен баг с inf в returns (models.py, portfolio.py) — np.isnan → np.isfinite
  - Добавлено логирование в пустые except в main_window.py
  - Устранено дублирование циклов по БД в loader.py (вынесен общий метод)
Статус: Исправлено, требуется прогон тестов
