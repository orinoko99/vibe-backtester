"""
Виджет графика на основе lightweight-charts, встроенный в PySide6.

Использует QtChart из библиотеки lightweight-charts для отображения
интерактивных свечных графиков (TradingView-подобных) внутри QMainWindow.
Поддерживает инструменты рисования: линии, трендовые линии, маркеры и т.д.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Literal

import polars as pl
import pandas as pd
from PySide6.QtWidgets import QVBoxLayout, QWidget

from lightweight_charts.widgets import QtChart


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
        self.chart = QtChart(
            widget=self,
            inner_width=1.0,
            inner_height=1.0,
            toolbox=False,
        )

        # Получаем ссылку на webview и добавляем его в макет
        self.webview = self.chart.get_webview()
        self.webview.setObjectName("chartWebView")
        self.chart_layout.addWidget(self.webview)

        # Состояние инструментов рисования
        self.active_tool: DrawingToolType = "none"
        self.drawing_color: str = "#1E80F0"
        self._drawings: list[dict[str, Any]] = []

        # Состояние для двухточечных инструментов (trend_line)
        self._pending_point: tuple[datetime, float] | None = None

        # Подписываемся на клик по графику для интерактивного рисования
        self._on_click(lambda time, price: self._handle_chart_click(time, price))

    def load_candles(self, dataframe: pl.DataFrame) -> None:
        """
        Загружает свечные данные в график из Polars DataFrame.

        Ожидаемые колонки в Polars DataFrame:
        - date (Datetime или str): дата/время свечи
        - open (float): цена открытия
        - high (float): максимальная цена
        - low (float): минимальная цена
        - close (float): цена закрытия
        - volume (int, опционально): объём торгов

        Библиотека lightweight-charts ожидает Pandas DataFrame с колонками
        time, open, high, low, close (volume опционально).

        Параметры:
            dataframe: Polars DataFrame со свечными данными.
        """
        if dataframe.is_empty():
            return

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

        # Форматируем время: если это datetime, конвертируем в строку ISO
        if result_df["time"].dtype == "datetime64[ns]":
            result_df["time"] = result_df["time"].dt.strftime("%Y-%m-%dT%H:%M:%S")

        # Загружаем данные в график (ожидает Pandas DataFrame)
        self.chart.set(result_df)

    def fit(self) -> None:
        """Автоматически подгоняет масштаб графика под все загруженные данные."""
        self.chart.fit()

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

    def set_drawing_color(self, color: str) -> None:
        """
        Устанавливает цвет для новых рисунков.

        Параметры:
            color: Цвет в формате HEX (#RRGGBB) или rgba(...).
        """
        self.drawing_color = color

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
        result = self.chart.horizontal_line(
            price=price,
            color=color or self.drawing_color,
            width=width,
            style=style,
            text=text,
            axis_label_visible=axis_label_visible,
        )
        self._drawings.append({
            "type": "horizontal_line",
            "object": result,
            "price": price,
            "color": color or self.drawing_color,
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
        result = self.chart.vertical_line(
            time=time,
            color=color or self.drawing_color,
            width=width,
            style=style,
            text=text,
        )
        self._drawings.append({
            "type": "vertical_line",
            "object": result,
            "time": str(time),
            "color": color or self.drawing_color,
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
            "start_time": str(start_time),
            "start_value": start_value,
            "end_time": str(end_time),
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
            "start_time": str(start_time),
            "value": value,
            "color": color or self.drawing_color,
        })
        return result

    def add_vertical_span(
        self,
        start_time: datetime | str | float | tuple | list,
        end_time: datetime | str | float | None = None,
        color: str | None = None,
    ) -> Any:
        """
        Добавляет вертикальную заливку (прямоугольник) между двумя датами.

        Параметры:
            start_time: Начальное время (или кортеж/список [start, end]).
            end_time: Конечное время (если не задано в start_time).
            color: Цвет заливки. Если None — используется drawing_color.

        Возвращает:
            Объект VerticalSpan.
        """
        result = self.chart.vertical_span(
            start_time=start_time,
            end_time=end_time,
            color=color or self.drawing_color.replace(
                "rgb", "rgba"
            ).replace(")", ", 0.2)") if color is None and self.drawing_color.startswith("rgb") else (color or self.drawing_color),
        )
        self._drawings.append({
            "type": "vertical_span",
            "object": result,
            "start_time": str(start_time),
            "end_time": str(end_time),
            "color": color or self.drawing_color,
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
        marker_id = self.chart.marker(
            time=time,
            position=position,
            shape=shape,
            color=color or self.drawing_color,
            text=text,
        )
        self._drawings.append({
            "type": "marker",
            "id": marker_id,
            "time": str(time),
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

    def clear_drawings(self) -> None:
        """Удаляет все рисунки и маркеры с графика."""
        self.chart.clear_markers()
        self._drawings.clear()
        self._pending_point = None

    def get_drawings(self) -> list[dict[str, Any]]:
        """
        Возвращает список всех созданных рисунков.

        Возвращает:
            Список словарей с информацией о каждом рисунке.
        """
        return self._drawings.copy()

    # ──────────────────────────────────────────────
    # Обработка кликов для интерактивного рисования
    # ──────────────────────────────────────────────

    def _on_click(self, callback: Callable[[datetime | None, float | None], None]) -> None:
        """
        Подписывается на событие клика по графику.

        Параметры:
            callback: Функция вида callback(time, price).
        """
        def handler(chart, time: float | None, price: float | None) -> None:
            parsed_time: datetime | None = None
            if time is not None and time > 0:
                try:
                    parsed_time = datetime.fromtimestamp(time)
                except (OSError, ValueError):
                    parsed_time = None
            callback(parsed_time, price)

        self.chart.events.click += handler

    def _handle_chart_click(
        self, time: datetime | None, price: float | None
    ) -> None:
        """
        Обрабатывает клик по графику для активного инструмента рисования.

        Параметры:
            time: Время клика (datetime или None).
            price: Цена клика (float или None).
        """
        if self.active_tool == "none":
            return
        if time is None or price is None:
            return

        tool = self.active_tool

        if tool == "horizontal_line":
            self.add_horizontal_line(price=price)

        elif tool == "vertical_line":
            self.add_vertical_line(time=time)

        elif tool == "marker":
            self.add_marker(time=time, text="", position="below", shape="arrow_up")

        elif tool == "ray_line":
            self.add_ray_line(start_time=time, value=price)

        elif tool == "vertical_span":
            if self._pending_point is None:
                self._pending_point = (time, price)
            else:
                start_time, _ = self._pending_point
                self.add_vertical_span(start_time=start_time, end_time=time)
                self._pending_point = None

        elif tool == "trend_line":
            if self._pending_point is None:
                # Первый клик — запоминаем начальную точку
                self._pending_point = (time, price)
            else:
                # Второй клик — рисуем линию от первой точки до второй
                start_time, start_price = self._pending_point
                self.add_trend_line(
                    start_time=start_time, start_value=start_price,
                    end_time=time, end_value=price,
                )
                self._pending_point = None
