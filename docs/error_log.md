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

## 2026-05-25 — Исправление багов рисования, таймфрейма и сохранения
Проблема: 
  - Инструменты рисования (кроме горизонтальной линии) не работали при клике
  - Очистка всех рисунков не очищала JS-side маркеры
  - Рисунки сохранялись с ключом (db, sec, timeframe), при смене таймфрейма терялись 
  - Рисунки не очищались при переключении между инструментами без сохранённых рисунков
  - Не было UI для редактирования/удаления отдельных рисунков
Файлы: src/gui/chart_widget.py, src/gui/main_window.py, src/gui/drawing_toolbar.py
Решение:
  - Исправлен ключ сохранения: теперь (db_path, sec_code) вместо (db_path, sec_code, timeframe), таймфрейм сохраняется внутри значения
  - Добавлен принудительный вызов clear_drawings() перед загрузкой данных нового инструмента
  - Добавлена JS-side очистка маркеров в clear_drawings()
  - Добавлены методы update_drawing(), on_drawings_changed callback
  - Добавлен список рисунков в DrawingToolbar с кнопками "Изменить цвет" и "Удалить"
  - Добавлены сигналы delete_drawing_requested, edit_drawing_requested
  - Исправлен _handle_chart_click: разрешён price=None для vertical_line, marker, vertical_span
  - Добавлены 22 новых теста
Статус: Исправлено, 355 тестов проходят

## 2026-05-25 — Доработка (время клика, таймфрейм по инструменту)
Проблема:
  - Вертикальные/трендовые инструменты не рисовались: время клика преобразовывалось через datetime.fromtimestamp вместо формата шкалы графика
  - Смена таймфрейма не передавала timeframe в load_and_display явно
  - Таймфрейм не запоминался при переключении между инструментами
  - «Очистить всё» не обновляло кэш сохранённых рисунков
Файлы: src/gui/chart_widget.py, src/gui/main_window.py
Решение:
  - _snap_chart_time() + передача raw float времени в методы рисования
  - _instrument_timeframes + восстановление комбобокса при выборе инструмента
  - _save_drawings() после очистки; chart.clear_markers()
Статус: Исправлено, 138 тестов GUI (venv) pass

## 2026-05-25 — calculateTrendLine, время 1740.0, смена ТФ
Проблема:
  - vertical_span вызывал JS calculateTrendLine (функция отсутствует) — ломал весь график
  - Время рисунков сохранялось как str('1740.0'), restore вызывал pd.to_datetime → ошибка
  - Смена ТФ не перезагружала данные: оставался кэш дат M1 и camera restore
  - Горизонтальные линии нельзя было перетаскивать
Файлы: src/gui/chart_widget.py, src/gui/main_window.py
Решение:
  - vertical_span → chart.box(); время хранится float; _coerce_chart_time при restore
  - toolbox=True; horizontal_line с func для drag
  - load_and_display(..., use_saved_camera=False) при смене ТФ; сброс _loaded_start/_end
Статус: Исправлено, 119 тестов GUI pass (venv)

## 2026-05-26 — Исправление таймфреймов, шкалы времени, тормозов и мигания
Проблема:
  - chart.set() вызывался при каждом range_change → перерендер всех свечей, лаг, мигание
  - Неверный расчёт visible_bars (деление на 4) — данные не подгружались вовремя
  - Ресемпл всех M1 на каждый range_change — лишняя нагрузка CPU
  - Память не чистилась при скролле без подгрузки (trim только при need_load)
  - load_and_display не устанавливал _current_db_path/_current_sec_code — _restore_drawings падал
Файлы: src/gui/main_window.py, src/gui/chart_widget.py
Решение:
  - Убран chart.set() из _on_chart_range_change — теперь только подгрузка M1 из БД
  - Добавлен _resampled_cache (кэш ресемпла) — ресемпл только при изменении M1
  - Добавлен _last_data_hash (хеш данных) — защита от повторного chart.set()
  - Добавлен _refresh_chart_display() вместо _apply_display_from_m1 — грузит все свечи, без среза
  - Добавлен _merge_m1_candles() — инкрементальное добавление M1
  - Исправлен _trim_m1_cache — использует _resampled_cache, тримминг в отдельном методе
  - _load_data_before/after теперь в M1, с правильным расчётом минут через таймфрейм
  - Добавлены константы LOAD_CHUNK_BARS / LOAD_THRESHOLD_BARS
  - load_and_display устанавливает _current_db_path/_current_sec_code
  - Удалён мёртвый _slice_display_df
Статус: Исправлено, 359 тестов проходят

## 2026-05-26 — Исправление zoom (сброс видимого диапазона при подгрузке данных)
Проблема:
  - При приближении/отдалении графика zoom сбрасывался на первоначальное значение
  - chart.set() (вызов из _refresh_chart_display) через series.setData() в JS сбрасывал visible range
Файлы: src/gui/main_window.py:500-526, 528-563, 729-753
Воспроизведение:
  - Открыть инструмент → подождать загрузки данных → приблизить (zoom in) → проскроллить к краю данных
  - При подгрузке M1 и вызове _refresh_chart_display → chart.set() → zoom сбрасывался
Решение:
  - Добавлен _save_visible_range_from_cache() — сохраняет unix-timestamps границ видимой области из _resampled_cache
  - _on_chart_range_change() теперь вычисляет и сохраняет границы, а также проверяет флаг _restoring_range
  - _refresh_chart_display() — перед chart.set() сохраняет saved_visible_start/end, после chart.set() вызывает chart.set_visible_range() для восстановления zoom
  - Флаг _restoring_range предотвращает бесконечный цикл (range_change игнорируется во время восстановления)
  - Добавлены 8 новых тестов
Статус: Исправлено, 356 тестов проходят (все, кроме about_dialog)
