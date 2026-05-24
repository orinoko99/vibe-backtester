#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Виджет интерактивного графика на базе lightweight-charts (TradingView).

Использует QWebEngineView для встраивания HTML/JS графика
непосредственно в окно PySide6.

Поддерживает двустороннюю связь JS <-> Python через QWebChannel:
- Python задаёт данные свечей, видимый диапазон, тему
- JS уведомляет Python об изменении видимого диапазона
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QVBoxLayout, QWidget

import lightweight_charts

from src.data.models import Candle

# Путь к index.html из пакета lightweight-charts
_LC_INDEX_PATH: str = os.path.join(
    os.path.dirname(os.path.dirname(lightweight_charts.__file__)),
    "lightweight_charts",
    "js",
    "index.html",
)


class ChartBridge(QObject):
    """
    Мост между JavaScript и Python для обмена событиями графика.

    Регистрируется в QWebChannel, чтобы JS мог вызывать
    его слоты при изменении видимого диапазона.
    """

    # Сигнал испускается при изменении видимого диапазона в JS
    visible_range_changed = Signal(float, float)  # from_timestamp, to_timestamp

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

    @Slot(float, float)
    def on_visible_range_changed(
        self, from_ts: float, to_ts: float
    ) -> None:
        """
        Вызывается из JavaScript при изменении видимого диапазона.
        """
        self.visible_range_changed.emit(from_ts, to_ts)

    @Slot(str)
    def on_log(self, message: str) -> None:
        """
        Вызывается из JavaScript для логирования (отладка).
        """
        pass


class ChartWidget(QWidget):
    """
    Виджет для отображения интерактивного графика свечей.

    Основан на TradingView Lightweight Charts,
    встроенных через QWebEngineView с QWebChannel.
    """

    _CHART_VAR: str = "chart_0"

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self._loaded: bool = False
        self._pending_scripts: List[str] = []
        self._on_range_change: Optional[Callable[[datetime, datetime], None]] = None

        # Создаём QWebChannel и мост
        self._bridge = ChartBridge(self)
        self._channel = QWebChannel(self)
        self._channel.registerObject("bridge", self._bridge)

        # Подключаем сигнал моста
        self._bridge.visible_range_changed.connect(
            self._on_visible_range_changed
        )

        # Создаём QWebEngineView
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._webview = QWebEngineView(self)
        self._webview.page().setWebChannel(self._channel)
        self._webview.loadFinished.connect(self._on_load_finished)
        self._webview.setUrl(QUrl.fromLocalFile(_LC_INDEX_PATH))
        layout.addWidget(self._webview)

    # ------------------------------------------------------------------
    #  Свойства
    # ------------------------------------------------------------------

    @property
    def bridge(self) -> ChartBridge:
        """Возвращает мост JS-Python."""
        return self._bridge

    # ------------------------------------------------------------------
    #  Callback: изменение видимого диапазона
    # ------------------------------------------------------------------

    def set_on_visible_range_changed(
        self,
        callback: Callable[[datetime, datetime], None],
    ) -> None:
        """
        Устанавливает callback на изменение видимого диапазона.

        Callback принимает (start: datetime, end: datetime).
        """
        self._on_range_change = callback

    def _on_visible_range_changed(
        self, from_ts: float, to_ts: float
    ) -> None:
        """
        Обрабатывает сигнал от моста: конвертирует timestamp в datetime
        и вызывает пользовательский callback.
        """
        start = datetime.fromtimestamp(from_ts, tz=timezone.utc)
        end = datetime.fromtimestamp(to_ts, tz=timezone.utc)
        if self._on_range_change is not None:
            self._on_range_change(start, end)

    # ------------------------------------------------------------------
    #  Загрузка и инициализация
    # ------------------------------------------------------------------

    @Slot(bool)
    def _on_load_finished(self, ok: bool) -> None:
        """
        Вызывается после загрузки HTML-страницы графика.
        Выполняет накопившиеся скрипты и регистрирует
        подписку на изменение видимого диапазона.
        """
        if not ok:
            return
        self._loaded = True

        # Регистрируем подписку на изменение видимого диапазона
        init_script = (
            f"if (typeof {self._CHART_VAR} !== 'undefined') {{\n"
            f"  {self._CHART_VAR}.chart.timeScale()"
            f".subscribeVisibleTimeRangeChange(function() {{\n"
            f"    var range = {self._CHART_VAR}.chart.timeScale()"
            f".getVisibleRange();\n"
            f"    if (range) {{\n"
            f"      new QWebChannel(qt.webChannelTransport, "
            f"function(channel) {{\n"
            f"        channel.objects.bridge"
            f".on_visible_range_changed("
            f"range.from, range.to);\n"
            f"      }});\n"
            f"    }}\n"
            f"  }});\n"
            f"}}"
        )
        self._webview.page().runJavaScript(init_script)

        # Выполняем отложенные скрипты
        for script in self._pending_scripts:
            self._webview.page().runJavaScript(script)
        self._pending_scripts.clear()

    def _run_script(self, script: str) -> None:
        """Выполняет JavaScript в контексте графика."""
        if self._loaded:
            self._webview.page().runJavaScript(script)
        else:
            self._pending_scripts.append(script)

    # ------------------------------------------------------------------
    #  Установка данных
    # ------------------------------------------------------------------

    def _candle_to_js(self, candle: Candle) -> Dict[str, Any]:
        return {
            "time": int(candle.timestamp.timestamp()),
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
        }

    def _candle_to_volume_js(self, candle: Candle) -> Dict[str, Any]:
        color = (
            "rgba(38, 166, 154, 0.8)"
            if candle.is_bullish or not candle.is_bearish
            else "rgba(239, 83, 80, 0.8)"
        )
        return {
            "time": int(candle.timestamp.timestamp()),
            "value": candle.volume,
            "color": color,
        }

    def set_candles(self, candles: List[Candle]) -> None:
        """Загружает список свечей на график."""
        ohlcv_data = json.dumps(
            [self._candle_to_js(c) for c in candles]
        )
        volume_data = json.dumps(
            [self._candle_to_volume_js(c) for c in candles]
        )
        script = (
            f"if (typeof {self._CHART_VAR} !== 'undefined') {{\n"
            f"  {self._CHART_VAR}.series.setData({ohlcv_data});\n"
            f"  {self._CHART_VAR}.volumeSeries.setData({volume_data});\n"
            f"}}"
        )
        self._run_script(script)

    def update_candle(self, candle: Candle) -> None:
        """Добавляет или обновляет одну свечу на графике."""
        candle_js = json.dumps(self._candle_to_js(candle))
        volume_js = json.dumps(self._candle_to_volume_js(candle))
        script = (
            f"if (typeof {self._CHART_VAR} !== 'undefined') {{\n"
            f"  {self._CHART_VAR}.series.update({candle_js});\n"
            f"  {self._CHART_VAR}.volumeSeries.update({volume_js});\n"
            f"}}"
        )
        self._run_script(script)

    def set_visible_range(
        self, start: datetime, end: datetime
    ) -> None:
        """Устанавливает видимый диапазон графика."""
        from_ts = int(start.timestamp())
        to_ts = int(end.timestamp())
        script = (
            f"if (typeof {self._CHART_VAR} !== 'undefined') {{\n"
            f"  {self._CHART_VAR}.chart.timeScale()"
            f".setVisibleRange({{from: {from_ts}, to: {to_ts}}});\n"
            f"}}"
        )
        self._run_script(script)

    def fit_content(self) -> None:
        """Автомасштабирует график."""
        script = (
            f"if (typeof {self._CHART_VAR} !== 'undefined') {{\n"
            f"  {self._CHART_VAR}.chart.timeScale().fitContent();\n"
            f"}}"
        )
        self._run_script(script)

    def clear(self) -> None:
        """Очищает все данные с графика."""
        script = (
            f"if (typeof {self._CHART_VAR} !== 'undefined') {{\n"
            f"  {self._CHART_VAR}.series.setData([]);\n"
            f"  {self._CHART_VAR}.volumeSeries.setData([]);\n"
            f"}}"
        )
        self._run_script(script)

    # ------------------------------------------------------------------
    #  Настройки внешнего вида
    # ------------------------------------------------------------------

    def set_theme(
        self,
        background: str = "#1a1a2e",
        text_color: str = "#ffffff",
        grid_color: str = "#2a2a3e",
    ) -> None:
        """Устанавливает цветовую тему графика."""
        script = (
            f"if (typeof {self._CHART_VAR} !== 'undefined') {{\n"
            f"  document.getElementById('container')"
            f".style.backgroundColor = '{background}';\n"
            f"  {self._CHART_VAR}.chart.applyOptions({{\n"
            f"    layout: {{\n"
            f"      background: {{color: '{background}'}},\n"
            f"      textColor: '{text_color}'\n"
            f"    }},\n"
            f"    grid: {{\n"
            f"      vertLines: {{color: '{grid_color}'}},\n"
            f"      horzLines: {{color: '{grid_color}'}}\n"
            f"    }}\n"
            f"  }});\n"
            f"}}"
        )
        self._run_script(script)
