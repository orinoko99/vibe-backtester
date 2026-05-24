#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Виджет интерактивного графика на базе lightweight-charts (TradingView).

Использует QWebEngineView для встраивания HTML/JS графика
непосредственно в окно PySide6.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QUrl, Slot
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


class ChartWidget(QWidget):
    """
    Виджет для отображения интерактивного графика свечей.

    Основан на TradingView Lightweight Charts,
    встроенных через QWebEngineView.
    """

    # Имя глобальной переменной JS, содержащей экземпляр графика
    _CHART_VAR: str = "chart_0"

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ) -> None:
        """
        Инициализация виджета графика.
        """
        super().__init__(parent)

        self._loaded: bool = False
        self._pending_scripts: List[str] = []

        # Создаём QWebEngineView
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._webview = QWebEngineView(self)
        self._webview.setUrl(QUrl.fromLocalFile(_LC_INDEX_PATH))
        self._webview.loadFinished.connect(self._on_load_finished)
        layout.addWidget(self._webview)

    # ------------------------------------------------------------------
    #  Загрузка и инициализация
    # ------------------------------------------------------------------

    @Slot(bool)
    def _on_load_finished(self, ok: bool) -> None:
        """
        Вызывается после загрузки HTML-страницы графика.
        Выполняет накопившиеся скрипты.
        """
        if not ok:
            return
        self._loaded = True

        # Выполняем все отложенные скрипты
        for script in self._pending_scripts:
            self._webview.page().runJavaScript(script)
        self._pending_scripts.clear()

    def _run_script(self, script: str) -> None:
        """
        Выполняет JavaScript в контексте графика.
        Если страница ещё не загружена — сохраняет скрипт в очередь.
        """
        if self._loaded:
            self._webview.page().runJavaScript(script)
        else:
            self._pending_scripts.append(script)

    # ------------------------------------------------------------------
    #  Установка данных
    # ------------------------------------------------------------------

    def _candle_to_js(
        self, candle: Candle
    ) -> Dict[str, Any]:
        """
        Преобразует объект Candle в словарь для JavaScript.
        """
        return {
            "time": int(candle.timestamp.timestamp()),
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
        }

    def _candle_to_volume_js(
        self, candle: Candle
    ) -> Dict[str, Any]:
        """
        Преобразует объект Candle в словарь для серии объёмов.
        Цвет объёма: зелёный если бычья, красный если медвежья.
        """
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

    def set_candles(
        self, candles: List[Candle]
    ) -> None:
        """
        Загружает список свечей на график.

        Параметры:
            candles — список объектов Candle для отображения
        """
        # Данные для свечного графика
        ohlcv_data = json.dumps(
            [self._candle_to_js(c) for c in candles]
        )
        # Данные для гистограммы объёмов
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
        """
        Добавляет или обновляет одну свечу на графике (streaming).

        Параметры:
            candle — объект Candle
        """
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
        self,
        start: datetime,
        end: datetime,
    ) -> None:
        """
        Устанавливает видимый диапазон графика.

        Параметры:
            start — начало видимого диапазона
            end — конец видимого диапазона
        """
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
        """
        Автомасштабирует график так, чтобы были видны все данные.
        """
        script = (
            f"if (typeof {self._CHART_VAR} !== 'undefined') {{\n"
            f"  {self._CHART_VAR}.chart.timeScale().fitContent();\n"
            f"}}"
        )
        self._run_script(script)

    def clear(self) -> None:
        """
        Очищает все данные с графика.
        """
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
        """
        Устанавливает цветовую тему графика.

        Параметры:
            background — цвет фона
            text_color — цвет текста
            grid_color — цвет сетки
        """
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
