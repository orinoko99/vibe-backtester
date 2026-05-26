"""
Виджет графика на основе lightweight-charts, встроенный в PySide6.

Использует QtChart из библиотеки lightweight-charts для отображения
интерактивных свечных графиков (TradingView-подобных) внутри QMainWindow.
Поддерживает инструменты рисования: линии, трендовые линии, маркеры и т.д.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable, Literal

logger = logging.getLogger(__name__)

import polars as pl
import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import QVBoxLayout, QWidget

from lightweight_charts.widgets import QtChart
from lightweight_charts.abstract import Line

from src.indicators.base import IndicatorResult, IndicatorType


# Типы для подсказок
DrawingToolType = Literal[
    "horizontal_line", "vertical_line", "trend_line",
    "ray_line", "vertical_span", "marker", "none",
]
MarkerPosition = Literal["above", "below", "inside"]
MarkerShape = Literal["arrow_up", "arrow_down", "circle", "square"]
LineStyle = Literal["solid", "dotted", "dashed", "large_dashed", "sparse_dotted"]


class ChartWidget(QWidget):
    """
    Виджет-обёртка над lightweight-charts QtChart.

    Предоставляет удобный интерфейс для загрузки свечных данных,
    управления отображением, инструментов рисования и интеграции с MainWindow.

    Атрибуты:
        chart (QtChart): Экземпляр lightweight-charts графика.
        webview (QWebEngineView): WebView для отображения графика.
        chart_layout (QVBoxLayout): Макет для размещения графика.
        active_tool (DrawingToolType): Текущий активный инструмент рисования.
        drawing_color (str): Цвет для новых рисунков.
        _drawings (list[dict]): Список созданных рисунков для отслеживания.
    """

    # Сигнал на замену стандартному обработчику клика
    # (None = использовать встроенный interactive drawing)

    def __init__(self, parent: QWidget = None) -> None:
        """
        Инициализирует виджет графика.

        Параметры:
            parent: Родительский QWidget (обычно chart_container из MainWindow).
        """
        super().__init__(parent)

        # Создаём макет для размещения графика
        self.chart_layout = QVBoxLayout()
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        self.chart_layout.setSpacing(0)
        self.setLayout(self.chart_layout)

        # Создаём экземпляр lightweight-charts графика
        # QtChart создаёт внутри QWebEngineView и настраивает QWebChannel
        # toolbox=True — перетаскивание нарисованных примитивов на графике
        self.chart = QtChart(
            widget=self,
            inner_width=1.0,
            inner_height=1.0,
            toolbox=True,
        )

        # Получаем ссылку на webview и добавляем его в макет
        self.webview = self.chart.get_webview()
        self.webview.setObjectName("chartWebView")
        self.chart_layout.addWidget(self.webview)

        # Состояние инструментов рисования
        self.active_tool: DrawingToolType = "none"
        self.drawing_color: str = "#1E80F0"
        # Подпись для новых рисунков (поле «Текст» на панели над графиком)
        self.drawing_text: str = ""
        self._drawings: list[dict[str, Any]] = []

        # Ожидающая точка для двухшаговых инструментов (время в формате шкалы графика)
        self._pending_point: tuple[float, float | None] | None = None

        # Колбэк при изменении списка рисунков (для обновления UI)
        self.on_drawings_changed: Callable[[], None] | None = None

        # Активные индикаторы и их подчарты
        self._indicator_lines: dict[str, Line] = {}
        self._indicator_hists: dict[str, Any] = {}
        self._indicator_subcharts: dict[str, QtChart] = {}

        # Кэш всех загруженных свечей для мержа при динамической подгрузке
        self._cached_candles: pl.DataFrame | None = None

        # Хеш последних загруженных данных для защиты от повторного chart.set()
        self._last_data_hash: int = 0

        # Подписываемся на клик по графику для интерактивного рисования
        self._on_click(lambda time, price: self._handle_chart_click(time, price))

        # Spacebar — переход к последним котировкам
        self._scroll_shortcut = QShortcut(QKeySequence(Qt.Key_Space), self)
        self._scroll_shortcut.activated.connect(self.scroll_to_last)

    def load_candles(self, dataframe: pl.DataFrame, replace: bool = True) -> None:
        """
        Загружает свечные данные в график из Polars DataFrame.

        Если replace=True — заменяет все данные новыми.
        Если replace=False — мержит с кэшированными данными (для динамической подгрузки).

        Ожидаемые колонки в Polars DataFrame:
        - date (Datetime или str): дата/время свечи
        - open (float): цена открытия
        - high (float): максимальная цена
        - low (float): минимальная цена
        - close (float): цена закрытия
        - volume (int, опционально): объём торгов

        Параметры:
            dataframe: Polars DataFrame со свечными данными.
            replace: True — полная замена, False — мерж с кэшем.
        """
        if dataframe.is_empty():
            return

        # Мержим с кэшем, если это догрузка
        if not replace and self._cached_candles is not None and not self._cached_candles.is_empty():
            dataframe = pl.concat([self._cached_candles, dataframe]).unique(
                subset=["date"], keep="first"
            ).sort("date")

        # Сохраняем в кэш
        self._cached_candles = dataframe

        # Конвертируем Polars в Pandas для передачи в lightweight-charts
        pandas_df = dataframe.to_pandas()

        # Переименовываем колонки в формат lightweight-charts
        column_map: dict[str, str] = {
            "date": "time",
            "Date": "time",
            "open": "open",
            "O": "open",
            "high": "high",
            "H": "high",
            "low": "low",
            "L": "low",
            "close": "close",
            "C": "close",
            "volume": "volume",
            "V": "volume",
        }

        # Выбираем только нужные колонки и переименовываем
        result_df = pandas_df.rename(columns=column_map)

        # Оставляем только те колонки, которые нужны графику
        required_cols = ["time", "open", "high", "low", "close"]
        available_cols = [col for col in required_cols if col in result_df.columns]
        if len(available_cols) < 5:
            raise ValueError(
                "DataFrame должен содержать колонки: date/time, open, high, low, close"
            )

        result_df = result_df[required_cols + (["volume"] if "volume" in result_df.columns else [])]

        # Форматируем время: lightweight-charts сам конвертирует datetime в Unix
        # timestamp внутри _df_datetime_format. Передаём datetime64[ns] как есть.
        if result_df["time"].dtype == "datetime64[ns]":
            result_df["time"] = result_df["time"].dt.strftime("%Y-%m-%dT%H:%M:%S")

        # Проверяем, изменились ли данные (защита от повторного chart.set())
        data_hash = hash(str(result_df.values.tobytes()))
        if replace and data_hash == self._last_data_hash:
            return

        # Загружаем данные в график (ожидает Pandas DataFrame)
        self.chart.set(result_df)

        if replace:
            self._last_data_hash = data_hash

    def fit(self) -> None:
        """Автоматически подгоняет масштаб графика под все загруженные данные."""
        self.chart.fit()

    def scroll_to_last(self) -> None:
        """Перемещает график к последней свече (последним котировкам)."""
        self.chart.fit()
        # Вызываем JS для скролла к реальному времени
        self.webview.page().runJavaScript(
            "try { chart.timeScale().scrollToRealTime(); } catch(e) {}"
        )

    def set_title(self, title: str) -> None:
        """
        Устанавливает заголовок графика.

        Параметры:
            title: Текст заголовка.
        """
        self.chart.watermark(title)

    def clear(self) -> None:
        """Очищает все данные с графика."""
        self.chart.hide_data()
        self._cached_candles = None

    def on_range_change(self, callback) -> None:
        """
        Подписывается на событие изменения видимого диапазона графика.

        callback будет вызван с аргументами (bars_before, bars_after)
        при каждом изменении видимого диапазона.

        Параметры:
            callback: Функция обратного вызова вида
                      callback(bars_before: float, bars_after: float).
        """
        def handler(chart, bars_before: float, bars_after: float) -> None:
            callback(bars_before, bars_after)

        self.chart.events.range_change += handler

    # ──────────────────────────────────────────────
    # Инструменты рисования
    # ──────────────────────────────────────────────

    def set_drawing_tool(self, tool: DrawingToolType) -> None:
        """
        Устанавливает активный инструмент рисования.

        Параметры:
            tool: Тип инструмента ('horizontal_line', 'vertical_line',
                  'trend_line', 'ray_line', 'vertical_span', 'marker', 'none').
        """
        self.active_tool = tool
        self._pending_point = None

    def _coerce_chart_time(self, value: Any) -> float:
        """
        Преобразует сохранённое время в формат шкалы графика (float).

        В _drawings время хранится как float; старые записи могли быть str '1740.0'.
        """
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return self.chart._single_datetime_format(value)
        return self.chart._single_datetime_format(value)

    def _fill_color(self, color: str | None) -> str:
        """Полупрозрачная заливка для box/vertical_span."""
        c = color or self.drawing_color
        if c.startswith("#") and len(c) == 7:
            r, g, b = int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
            return f"rgba({r}, {g}, {b}, 0.2)"
        if c.startswith("rgb("):
            return c.replace("rgb(", "rgba(").replace(")", ", 0.2)")
        return c

    def _price_range_from_cache(self) -> tuple[float, float]:
        """Минимум/максимум цен по загруженным свечам (для заливки на весь экран)."""
        if self._cached_candles is None or self._cached_candles.is_empty():
            return 0.0, 1.0
        return (
            float(self._cached_candles["low"].min()),
            float(self._cached_candles["high"].max()),
        )

    def set_drawing_color(self, color: str) -> None:
        """
        Устанавливает цвет для новых рисунков.

        Параметры:
            color: Цвет в формате HEX (#RRGGBB) или rgba(...).
        """
        self.drawing_color = color

    def set_drawing_text(self, text: str) -> None:
        """Устанавливает текст подписи для новых рисунков."""
        self.drawing_text = text or ""

    def add_horizontal_line(
        self,
        price: float | int,
        color: str | None = None,
        width: int = 2,
        style: LineStyle = "solid",
        text: str = "",
        axis_label_visible: bool = True,
    ) -> Any:
        """
        Добавляет горизонтальную линию на график.

        Параметры:
            price: Цена, на которой рисуется линия.
            color: Цвет линии. Если None — используется drawing_color.
            width: Толщина линии.
            style: Стиль линии.
            text: Текст подписи на оси.
            axis_label_visible: Показывать ли подпись на оси.

        Возвращает:
            Объект HorizontalLine.
        """
        line_color = color or self.drawing_color
        entry_index = len(self._drawings)

        def on_drag(chart: Any, line: Any) -> None:
            """Обновляет цену в списке рисунков при перетаскивании линии."""
            if entry_index < len(self._drawings):
                self._drawings[entry_index]["price"] = float(line.price)
                self._notify_drawings_changed()

        result = self.chart.horizontal_line(
            price=price,
            color=line_color,
            width=width,
            style=style,
            text=text,
            axis_label_visible=axis_label_visible,
            func=on_drag,
        )
        self._drawings.append({
            "type": "horizontal_line",
            "object": result,
            "price": price,
            "color": line_color,
            "text": text,
        })
        return result

    def add_vertical_line(
        self,
        time: datetime | str | float,
        color: str | None = None,
        width: int = 2,
        style: LineStyle = "solid",
        text: str = "",
    ) -> Any:
        """
        Добавляет вертикальную линию на график.

        Параметры:
            time: Время, на котором рисуется линия.
            color: Цвет линии. Если None — используется drawing_color.
            width: Толщина линии.
            style: Стиль линии.
            text: Текст подписи.

        Возвращает:
            Объект VerticalLine.
        """
        chart_time = self._coerce_chart_time(time)
        result = self.chart.vertical_line(
            time=chart_time,
            color=color or self.drawing_color,
            width=width,
            style=style,
            text=text,
        )
        self._drawings.append({
            "type": "vertical_line",
            "object": result,
            "time": chart_time,
            "color": color or self.drawing_color,
            "text": text,
        })
        return result

    def add_trend_line(
        self,
        start_time: datetime | str | float,
        start_value: float | int,
        end_time: datetime | str | float,
        end_value: float | int,
        color: str | None = None,
        width: int = 2,
        style: LineStyle = "solid",
    ) -> Any:
        """
        Добавляет трендовую линию (от точки A до точки B).

        Параметры:
            start_time: Время начальной точки.
            start_value: Цена начальной точки.
            end_time: Время конечной точки.
            end_value: Цена конечной точки.
            color: Цвет линии. Если None — используется drawing_color.
            width: Толщина линии.
            style: Стиль линии.

        Возвращает:
            Объект TwoPointDrawing.
        """
        result = self.chart.trend_line(
            start_time=start_time,
            start_value=start_value,
            end_time=end_time,
            end_value=end_value,
            line_color=color or self.drawing_color,
            width=width,
            style=style,
        )
        self._drawings.append({
            "type": "trend_line",
            "object": result,
            "start_time": self._coerce_chart_time(start_time),
            "start_value": start_value,
            "end_time": self._coerce_chart_time(end_time),
            "end_value": end_value,
            "color": color or self.drawing_color,
        })
        return result

    def add_ray_line(
        self,
        start_time: datetime | str | float,
        value: float | int,
        color: str | None = None,
        width: int = 2,
        style: LineStyle = "solid",
        text: str = "",
    ) -> Any:
        """
        Добавляет луч (линию от точки в бесконечность).

        Параметры:
            start_time: Время начальной точки.
            value: Цена начальной точки.
            color: Цвет линии. Если None — используется drawing_color.
            width: Толщина линии.
            style: Стиль линии.
            text: Текст подписи.

        Возвращает:
            Объект RayLine.
        """
        result = self.chart.ray_line(
            start_time=start_time,
            value=value,
            color=color or self.drawing_color,
            width=width,
            style=style,
            text=text,
        )
        self._drawings.append({
            "type": "ray_line",
            "object": result,
            "start_time": self._coerce_chart_time(start_time),
            "value": value,
            "color": color or self.drawing_color,
            "text": text,
        })
        return result

    def add_vertical_span(
        self,
        start_time: datetime | str | float | tuple | list,
        end_time: datetime | str | float | None = None,
        start_value: float | None = None,
        end_value: float | None = None,
        color: str | None = None,
    ) -> Any:
        """
        Добавляет вертикальную заливку между двумя моментами времени.

        Использует chart.box вместо vertical_span библиотеки (там нет calculateTrendLine в JS).
        """
        t0 = self._coerce_chart_time(start_time)
        t1 = self._coerce_chart_time(end_time) if end_time is not None else t0
        if t0 > t1:
            t0, t1 = t1, t0

        lo, hi = self._price_range_from_cache()
        v0 = float(start_value) if start_value is not None else lo
        v1 = float(end_value) if end_value is not None else hi
        price_lo, price_hi = min(v0, v1), max(v0, v1)

        line_color = color or self.drawing_color
        fill_color = self._fill_color(color)

        result = self.chart.box(
            start_time=t0,
            start_value=price_lo,
            end_time=t1,
            end_value=price_hi,
            color=line_color,
            fill_color=fill_color,
            width=1,
            style="solid",
        )
        self._drawings.append({
            "type": "vertical_span",
            "object": result,
            "start_time": t0,
            "end_time": t1,
            "start_value": price_lo,
            "end_value": price_hi,
            "color": line_color,
        })
        return result

    def add_marker(
        self,
        time: datetime | str | float,
        text: str = "",
        position: MarkerPosition = "below",
        shape: MarkerShape = "arrow_up",
        color: str | None = None,
    ) -> str:
        """
        Добавляет текстовый маркер на свечу.

        Параметры:
            time: Время свечи, к которой привязывается маркер.
            text: Текст маркера.
            position: Позиция ('above', 'below', 'inside').
            shape: Форма ('arrow_up', 'arrow_down', 'circle', 'square').
            color: Цвет маркера. Если None — используется drawing_color.

        Возвращает:
            ID созданного маркера (str).
        """
        chart_time = self._coerce_chart_time(time)
        marker_id = self.chart.marker(
            time=chart_time,
            position=position,
            shape=shape,
            color=color or self.drawing_color,
            text=text,
        )
        self._drawings.append({
            "type": "marker",
            "id": marker_id,
            "time": chart_time,
            "text": text,
            "position": position,
            "shape": shape,
            "color": color or self.drawing_color,
        })
        return marker_id

    def remove_marker(self, marker_id: str) -> None:
        """
        Удаляет маркер по его ID.

        Параметры:
            marker_id: ID маркера (возвращается add_marker).
        """
        self.chart.remove_marker(marker_id)
        self._drawings[:] = [d for d in self._drawings if d.get("id") != marker_id]
        self._notify_drawings_changed()

    def clear_drawings(self) -> None:
        """Удаляет все рисунки и маркеры с графика."""
        for drawing in self._drawings:
            drawing_type = drawing.get("type")
            obj = drawing.get("object")
            marker_id = drawing.get("id")

            if drawing_type == "marker" and marker_id:
                try:
                    self.chart.remove_marker(marker_id)
                except Exception as exc:
                    logger.warning("Не удалось удалить маркер %s: %s", marker_id, exc)
            elif obj is not None and hasattr(obj, "delete"):
                try:
                    obj.delete()
                except Exception as exc:
                    logger.warning("Не удалось удалить рисунок %s: %s", drawing_type, exc)

        # Очищаем маркеры на стороне библиотеки (на случай рассинхрона)
        try:
            self.chart.clear_markers()
        except Exception as exc:
            logger.warning("clear_markers: %s", exc)

        self._drawings.clear()
        self._pending_point = None
        self._notify_drawings_changed()

        # Дополнительно сбрасываем маркеры в WebEngine
        try:
            self.webview.page().runJavaScript(
                f"try {{ {self.chart.id}.series.setMarkers([]) }} catch(e) {{}}"
            )
        except Exception:
            pass

    def delete_drawing(self, index: int) -> bool:
        """
        Удаляет один рисунок по индексу.

        Параметры:
            index: Индекс рисунка в списке _drawings.

        Возвращает:
            True, если рисунок удалён.
        """
        if index < 0 or index >= len(self._drawings):
            return False

        drawing = self._drawings.pop(index)
        drawing_type = drawing.get("type")
        obj = drawing.get("object")
        marker_id = drawing.get("id")

        if drawing_type == "marker" and marker_id:
            self.chart.remove_marker(marker_id)
        elif obj is not None and hasattr(obj, "delete"):
            try:
                obj.delete()
            except Exception:
                pass

        self._notify_drawings_changed()
        return True

    def update_drawing(self, index: int, **kwargs) -> bool:
        """
        Обновляет свойства существующего рисунка (цвет, ширина, стиль).

        Параметры:
            index: Индекс рисунка в списке _drawings.
            **kwargs: Свойства для обновления (color, width, style, text и т.д.).

        Возвращает:
            True, если рисунок обновлён.
        """
        if index < 0 or index >= len(self._drawings):
            return False

        drawing = self._drawings[index]
        obj = drawing.get("object")
        drawing_type = drawing.get("type")

        if "color" in kwargs:
            drawing["color"] = kwargs["color"]
        if "text" in kwargs:
            drawing["text"] = kwargs["text"]

        # Маркер: текст меняется только пересозданием
        if drawing_type == "marker" and "text" in kwargs:
            marker_id = drawing.get("id")
            if marker_id:
                try:
                    self.chart.remove_marker(marker_id)
                except Exception:
                    pass
                new_id = self.chart.marker(
                    time=drawing["time"],
                    position=drawing.get("position", "below"),
                    shape=drawing.get("shape", "arrow_up"),
                    color=drawing.get("color", self.drawing_color),
                    text=kwargs["text"],
                )
                drawing["id"] = new_id

        if obj is not None and hasattr(obj, "options"):
            try:
                color = kwargs.get("color", drawing.get("color"))
                style = kwargs.get("style", "solid")
                width = kwargs.get("width", 2)
                text = kwargs.get("text", drawing.get("text", ""))
                obj.options(color=color, style=style, width=width)
                if text and drawing_type in ("horizontal_line", "vertical_line", "ray_line"):
                    obj.options(text=text)
            except Exception:
                pass

        self._notify_drawings_changed()
        return True

    def get_drawings(self) -> list[dict[str, Any]]:
        """
        Возвращает список всех созданных рисунков.

        Возвращает:
            Список словарей с информацией о каждом рисунке.
        """
        return self._drawings.copy()

    def serialize_drawings(self) -> list[dict[str, Any]]:
        """
        Сериализует рисунки для сохранения (без lwc-объектов).

        Возвращает:
            Список словарей с данными рисунков (без поля 'object').
        """
        serialized = []
        for d in self._drawings:
            entry = {k: v for k, v in d.items() if k != "object"}
            serialized.append(entry)
        return serialized

    def restore_drawings(self, drawings_data: list[dict[str, Any]]) -> None:
        """
        Восстанавливает рисунки из сериализованных данных.

        Параметры:
            drawings_data: Список словарей с данными рисунков.
        """
        # Сначала очищаем текущие рисунки
        self.clear_drawings()

        for d in drawings_data:
            drawing_type = d.get("type")
            color = d.get("color", self.drawing_color)

            try:
                if drawing_type == "horizontal_line":
                    self.add_horizontal_line(
                        price=float(d["price"]),
                        color=color,
                        text=d.get("text", ""),
                    )
                elif drawing_type == "vertical_line":
                    self.add_vertical_line(
                        time=self._coerce_chart_time(d["time"]),
                        color=color,
                        text=d.get("text", ""),
                    )
                elif drawing_type == "trend_line":
                    self.add_trend_line(
                        start_time=self._coerce_chart_time(d["start_time"]),
                        start_value=float(d["start_value"]),
                        end_time=self._coerce_chart_time(d["end_time"]),
                        end_value=float(d["end_value"]),
                        color=color,
                    )
                elif drawing_type == "ray_line":
                    self.add_ray_line(
                        start_time=self._coerce_chart_time(d["start_time"]),
                        value=float(d["value"]),
                        color=color,
                        text=d.get("text", ""),
                    )
                elif drawing_type == "vertical_span":
                    self.add_vertical_span(
                        start_time=self._coerce_chart_time(d["start_time"]),
                        end_time=self._coerce_chart_time(d["end_time"]),
                        start_value=d.get("start_value"),
                        end_value=d.get("end_value"),
                        color=color,
                    )
                elif drawing_type == "marker":
                    self.add_marker(
                        time=self._coerce_chart_time(d["time"]),
                        text=d.get("text", ""),
                        position=d.get("position", "below"),
                        shape=d.get("shape", "arrow_up"),
                        color=color,
                    )
            except (KeyError, ValueError, TypeError, OSError) as exc:
                logger.warning("Не удалось восстановить рисунок %s: %s", drawing_type, exc)

        self._notify_drawings_changed()

    def _notify_drawings_changed(self) -> None:
        """Уведомляет подписчиков об изменении списка рисунков."""
        if self.on_drawings_changed is not None:
            self.on_drawings_changed()

    # ──────────────────────────────────────────────
    # Обработка кликов для интерактивного рисования
    # ──────────────────────────────────────────────

    def _snap_chart_time(self, raw_time: float | datetime | str) -> float:
        """
        Приводит время к формату шкалы графика (как у свечей lightweight-charts).

        coordinateToTime возвращает unix-время; библиотека выравнивает его
        по интервалу свечей через _single_datetime_format.
        """
        return self.chart._single_datetime_format(raw_time)

    def _on_click(self, callback: Callable[[float | None, float | None], None]) -> None:
        """
        Подписывается на событие клика по графику.

        Параметры:
            callback: Функция вида callback(chart_time, price).
                      chart_time — число в формате шкалы графика (не datetime).
        """
        def handler(chart, time: float | None, price: float | None) -> None:
            # Передаём время как есть: fromtimestamp ломает привязку к свечам
            callback(time, price)

        self.chart.events.click += handler

    def _handle_chart_click(
        self,
        time: float | datetime | None,
        price: float | None,
    ) -> None:
        """
        Обрабатывает клик по графику для активного инструмента рисования.

        Параметры:
            time: Время клика (float с графика или datetime в тестах).
            price: Цена клика (float или None).
        """
        # Режим курсора: выбор и перемещение объектов через toolbox графика
        if self.active_tool == "none":
            return

        label = self.drawing_text
        chart_time: float | None = None
        if time is not None:
            try:
                if isinstance(time, (int, float)) and time > 0:
                    chart_time = self._snap_chart_time(float(time))
                elif isinstance(time, datetime):
                    chart_time = self._snap_chart_time(time)
            except (TypeError, ValueError, OSError) as exc:
                logger.warning("Не удалось разобрать время клика: %s", exc)

        if chart_time is None:
            return

        # Для инструментов только по времени цена может отсутствовать
        if price is None and self.active_tool not in (
            "vertical_line", "marker", "vertical_span",
        ):
            return

        tool = self.active_tool

        try:
            if tool == "horizontal_line":
                self.add_horizontal_line(price=price, text=label)

            elif tool == "vertical_line":
                self.add_vertical_line(time=chart_time, text=label)

            elif tool == "marker":
                self.add_marker(
                    time=chart_time,
                    text=label or "●",
                    position="below",
                    shape="arrow_up",
                )

            elif tool == "ray_line":
                self.add_ray_line(start_time=chart_time, value=price, text=label)

            elif tool == "vertical_span":
                if self._pending_point is None:
                    self._pending_point = (chart_time, price)
                else:
                    start_time, start_price = self._pending_point
                    self.add_vertical_span(
                        start_time=start_time,
                        end_time=chart_time,
                        start_value=start_price,
                        end_value=price,
                    )
                    self._pending_point = None

            elif tool == "trend_line":
                if self._pending_point is None:
                    self._pending_point = (chart_time, price)
                else:
                    start_time, start_price = self._pending_point
                    self.add_trend_line(
                        start_time=start_time,
                        start_value=start_price,
                        end_time=chart_time,
                        end_value=price,
                    )
                    self._pending_point = None

            self._notify_drawings_changed()
        except Exception as exc:
            logger.warning(
                "Ошибка рисования инструментом %s: %s", tool, exc,
            )

    # ══════════════════════════════════════════════
    # Управление индикаторами
    # ══════════════════════════════════════════════

    def add_indicator(self, indicator_result: IndicatorResult) -> None:
        """
        Добавляет рассчитанный индикатор на график.

        Автоматически определяет способ отображения:
        - OVERLAY → линия на основном графике
        - OSCILLATOR → линия на отдельной панели под графиком
        - VOLUME_PROFILE → гистограмма на основном графике

        Параметры:
            indicator_result: Результат расчёта индикатора.
        """
        # Определяем имя индикатора по первой серии в series_names
        if not indicator_result.series_names:
            return

        # Преобразуем IndicatorResult в Pandas DataFrame
        pandas_df = self._indicator_result_to_pandas(indicator_result)
        indicator_name = indicator_result.panel or "indicator"

        if indicator_result.overlay:
            # OVERLAY — линия поверх свечей
            for series_name, color in indicator_result.series_names.items():
                if series_name not in pandas_df.columns:
                    continue

                line_name = f"{indicator_name}_{series_name}"
                # lightweight-charts требует, чтобы колонка в DataFrame
                # совпадала с именем линии (если имя задано)
                line_df = pandas_df[["time", series_name]].copy()
                line_df.columns = ["time", line_name]
                line_df = line_df.dropna()

                if line_df.empty:
                    continue

                # Создаём или обновляем линию
                if line_name in self._indicator_lines:
                    line = self._indicator_lines[line_name]
                    line.set(line_df)
                else:
                    line = self.chart.create_line(
                        name=line_name,
                        color=color,
                        width=2,
                    )
                    line.set(line_df)
                    self._indicator_lines[line_name] = line

        else:
            # OSCILLATOR или VOLUME_PROFILE — создаём подчарт
            series_cols = [c for c in pandas_df.columns if c != "time"]
            if not series_cols:
                return

            if indicator_name not in self._indicator_subcharts:
                # Создаём подчарт высотой 30% от основного
                subchart = self.chart.create_subchart(
                    position="bottom",
                    height=0.3,
                    sync=True,
                )
                self._indicator_subcharts[indicator_name] = subchart

            subchart = self._indicator_subcharts[indicator_name]

            for series_name, color in indicator_result.series_names.items():
                if series_name not in pandas_df.columns:
                    continue

                line_name = f"{indicator_name}_{series_name}"
                line_df = pandas_df[["time", series_name]].copy()
                line_df.columns = ["time", line_name]
                line_df = line_df.dropna()

                if line_df.empty:
                    continue

                key = f"sub_{line_name}"
                if key in self._indicator_lines:
                    line = self._indicator_lines[key]
                    line.set(line_df)
                else:
                    line = subchart.create_line(
                        name=line_name,
                        color=color,
                        width=2,
                        price_line=False,
                        price_label=False,
                    )
                    line.set(line_df)
                    self._indicator_lines[key] = line

    def remove_indicator(self, name: str) -> None:
        """
        Удаляет индикатор и его линии/подчарт с графика.

        Параметры:
            name: Имя индикатора (panel или display_name).
        """
        # Удаляем линии, связанные с индикатором
        keys_to_remove: list[str] = []
        for key in self._indicator_lines:
            if key.startswith(name) or f"_{name}" in key:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._indicator_lines[key]

        # Удаляем подчарт
        if name in self._indicator_subcharts:
            subchart = self._indicator_subcharts.pop(name)
            # subchart.remove() — если такой метод есть, иначе скрываем
            subchart.hide_data()

    def clear_indicators(self) -> None:
        """Удаляет все индикаторы с графика."""
        for subchart in self._indicator_subcharts.values():
            subchart.hide_data()

        self._indicator_lines.clear()
        self._indicator_hists.clear()
        self._indicator_subcharts.clear()

    def _indicator_result_to_pandas(
        self, indicator_result: IndicatorResult,
    ) -> pd.DataFrame:
        """
        Преобразует IndicatorResult в Pandas DataFrame для lightweight-charts.

        Параметры:
            indicator_result: Результат расчёта индикатора.

        Возвращает:
            Pandas DataFrame с колонкой 'time' и рядами значений.
        """
        df = indicator_result.data.to_pandas()

        # Переименовываем колонку date/time
        if "time" not in df.columns:
            for col in ("date", "Date", "datetime", "DateTime"):
                if col in df.columns:
                    df = df.rename(columns={col: "time"})
                    break

        # Форматируем время: lightweight-charts сам конвертирует datetime
        if "time" in df.columns and hasattr(df["time"], "dtype"):
            if str(df["time"].dtype) == "datetime64[ns]":
                df["time"] = df["time"].dt.strftime("%Y-%m-%dT%H:%M:%S")

        return df
