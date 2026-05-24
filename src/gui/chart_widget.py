"""
Виджет графика на основе lightweight-charts, встроенный в PySide6.

Использует QtChart из библиотеки lightweight-charts для отображения
интерактивных свечных графиков (TradingView-подобных) внутри QMainWindow.
"""

import polars as pl
import pandas as pd
from PySide6.QtWidgets import QVBoxLayout, QWidget

from lightweight_charts.widgets import QtChart


class ChartWidget(QWidget):
    """
    Виджет-обёртка над lightweight-charts QtChart.

    Предоставляет удобный интерфейс для загрузки свечных данных,
    управления отображением и интеграции с MainWindow.

    Атрибуты:
        chart (QtChart): Экземпляр lightweight-charts графика.
        webview (QWebEngineView): WebView для отображения графика.
        chart_layout (QVBoxLayout): Макет для размещения графика.
    """

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
