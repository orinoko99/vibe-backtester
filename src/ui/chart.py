"""
Модуль интерактивного свечного графика на основе PyQtGraph.

Предоставляет:
- CandlestickItem — отрисовка свечей
- ChartWidget — основной виджет графика с поддержкой:
  - Масштабирования колесом мыши
  - Перемещения графика (pan)
  - Автомасштабирования по вертикали
  - Отображения объёма
  - Добавления нескольких инструментов
"""

from typing import Optional

import numpy as np
import pandas as pd
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

# Цвета для свечей (RGB)
ЦВЕТ_БЫЧЬЯ = (0, 200, 80)    # зелёный — рост
ЦВЕТ_МЕДВЕЖЬЯ = (220, 50, 50)  # красный — падение
ЦВЕТ_ОБЪЁМ = (100, 100, 180, 80)  # полупрозрачный синий для объёма


class СвечаГрафик(pg.GraphicsObject):
    """
    Графический объект для отрисовки свечного графика.

    Принимает numpy-массив свечей и отрисовывает их как
    свечные бары (high-low линия + open-close прямоугольник).

    Параметры
    ----------
    данные : np.ndarray
        Массив со столбцами: [time, open, high, low, close, volume].
    ширина_свечи : float
        Ширина свечи в долях от временнóго интервала (по умолчанию 0.6).
    """

    def __init__(
        self,
        данные: Optional[np.ndarray] = None,
        ширина_свечи: float = 0.6,
    ) -> None:
        super().__init__()
        self.ширина_свечи = ширина_свечи
        self.данные: Optional[np.ndarray] = данные
        self._путь: Optional[QtGui.QPainterPath] = None
        self._объём_прямоугольники: list[QtCore.QRectF] = []
        self._показывать_объём: bool = True
        if данные is not None:
            self.обновить(данные)

    def обновить(self, данные: np.ndarray) -> None:
        """
        Обновляет данные и перестраивает путь отрисовки.

        Параметры
        ----------
        данные : np.ndarray
            Массив со столбцами: [time, open, high, low, close, volume].
            Время должно быть в секундах или любом числовом формате.
        """
        self.данные = данные
        self._построить_путь()
        self.update()

    def установить_показ_объёма(self, показать: bool) -> None:
        """Включает/выключает отображение объёма под свечами."""
        self._показывать_объём = показать
        self._построить_путь()
        self.update()

    def _построить_путь(self) -> None:
        """Строит QPainterPath для всех свечей."""
        данные = self.данные
        if данные is None or len(данные) == 0:
            self._путь = QtGui.QPainterPath()
            self._объём_прямоугольники = []
            return

        путь = QtGui.QPainterPath()
        объём_прямоугольники = []

        for i in range(len(данные)):
            время = float(данные[i, 0])
            o = float(данные[i, 1])
            h = float(данные[i, 2])
            l = float(данные[i, 3])
            c = float(данные[i, 4])
            v = float(данные[i, 5])

            # Ширина половины свечи
            пол_ширины = self.ширина_свечи / 2.0

            # Вертикальная линия high-low
            путь.moveTo(время, h)
            путь.lineTo(время, l)

            if o < c:  # Бычья свеча (рост)
                верх = c
                низ = o
            else:
                верх = o
                низ = c

            # Тело свечи (прямоугольник open-close)
            путь.addRect(QtCore.QRectF(
                время - пол_ширины, низ,
                self.ширина_свечи, верх - низ,
            ))

            # Объём (только если включён)
            if self._показывать_объём:
                коэф_высоты = 0.2
                макс_объём = float(np.max(данные[:, 5])) if len(данные) > 0 else 1
                if макс_объём > 0:
                    высота_объёма = (v / макс_объём) * (
                        float(np.max(данные[:, 3])) - float(np.min(данные[:, 2]))
                    ) * коэф_высоты
                    # Объём рисуем ниже свечей
                    мин_цена = float(np.min(данные[:, 2]))
                    y_объём = мин_цена - высота_объёма * 1.5
                    объём_прямоугольники.append(QtCore.QRectF(
                        время - пол_ширины * 0.5, y_объём,
                        self.ширина_свечи * 0.5, высота_объёма,
                    ))

        self._путь = путь
        self._объём_прямоугольники = объём_прямоугольники

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionGraphicsItem,
        widget: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        """Отрисовывает свечи."""
        if self._путь is None or self.данные is None:
            return

        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)

        # Рисуем объём
        if self._показывать_объём and self._объём_прямоугольники:
            painter.setBrush(QtGui.QColor(*ЦВЕТ_ОБЪЁМ))
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            for rect in self._объём_прямоугольники:
                painter.drawRect(rect)

        # Рисуем свечи
        данные = self.данные
        for i in range(len(данные)):
            время = float(данные[i, 0])
            o = float(данные[i, 1])
            c = float(данные[i, 4])

            if o <= c:
                цвет = QtGui.QColor(*ЦВЕТ_БЫЧЬЯ)
            else:
                цвет = QtGui.QColor(*ЦВЕТ_МЕДВЕЖЬЯ)

            painter.setPen(QtGui.QPen(цвет, 1.0))
            painter.setBrush(цвет)

            h = float(данные[i, 2])
            l = float(данные[i, 3])
            пол_ширины = self.ширина_свечи / 2.0

            # Вертикальная линия high-low
            painter.drawLine(
                QtCore.QPointF(время, h),
                QtCore.QPointF(время, l),
            )

            # Тело свечи
            верх = max(o, c)
            низ = min(o, c)
            painter.drawRect(QtCore.QRectF(
                время - пол_ширины, низ,
                self.ширина_свечи, верх - низ,
            ))

    def boundingRect(self) -> QtCore.QRectF:
        """Возвращает ограничивающий прямоугольник."""
        if self._путь is None:
            return QtCore.QRectF()
        return self._путь.boundingRect()


class График(pg.PlotWidget):
    """
    Основной виджет интерактивного графика со свечами.

    Поддерживает:
    - Масштабирование колёсиком мыши
    - Перемещение графика (pan)
    - Автомасштабирование
    - Несколько свечных рядов (инструментов)
    - Отображение объёма

    Параметры
    ----------
    parent : Optional[QtWidgets.QWidget]
        Родительский виджет.
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        # Настройка отображения
        self.setBackground("black")
        self.showGrid(x=True, y=True, alpha=0.15)

        # Включаем интерактивность
        self.setMouseEnabled(x=True, y=True)
        self.setAutoVisible(x=True, y=True)

        # Отключаем авто-диапазон по умолчанию
        self.enableAutoRange(axis="xy", enable=False)

        # Словарь инструментов: {код: СвечаГрафик}
        self.инструменты: dict[str, СвечаГрафик] = {}

        # Цвета для разных инструментов
        self._палитра_цветов = [
            (0, 200, 80),    # зелёный
            (80, 150, 255),  # синий
            (255, 200, 0),   # жёлтый
            (255, 100, 200), # розовый
            (0, 200, 255),   # голубой
        ]
        self._след_цвет = 0

    def добавить_инструмент(
        self,
        код: str,
        данные: pd.DataFrame,
        таймфрейм: str = "1min",
    ) -> bool:
        """
        Добавляет инструмент на график.

        Параметры
        ----------
        код : str
            Код инструмента (уникальный идентификатор).
        данные : pd.DataFrame
            DataFrame с колонками open, high, low, close, volume
            и datetime-индексом.
        таймфрейм : str
            Таймфрейм данных (для отображения подписей оси X).

        Возвращает
        -------
        bool
            True, если инструмент добавлен успешно.
        """
        if код in self.инструменты:
            return False

        # Преобразуем DataFrame в numpy-массив
        # Время в секундах от начала эпохи
        времена = np.array([
            t.timestamp() for t in данные.index
        ], dtype=float)

        данные_массив = np.column_stack([
            времена,
            данные["open"].values.astype(float),
            данные["high"].values.astype(float),
            данные["low"].values.astype(float),
            данные["close"].values.astype(float),
            данные["volume"].values.astype(float),
        ])

        свечи = СвечаГрафик(данные_массив)

        # Устанавливаем цвет на основе палитры
        цвет = self._палитра_цветов[
            self._след_цвет % len(self._палитра_цветов)
        ]
        self._след_цвет += 1

        self.addItem(свечи)
        self.инструменты[код] = свечи
        self.автомасштаб()

        return True

    def удалить_инструмент(self, код: str) -> bool:
        """
        Удаляет инструмент с графика.

        Параметры
        ----------
        код : str
            Код инструмента.

        Возвращает
        -------
        bool
            True, если инструмент удалён.
        """
        if код not in self.инструменты:
            return False
        свечи = self.инструменты.pop(код)
        self.removeItem(свечи)
        return True

    def автомасштаб(self) -> None:
        """Автомасштабирует график по всем данным."""
        self.enableAutoRange(axis="xy", enable=True)
        self.enableAutoRange(axis="xy", enable=False)

    def автомасштаб_по_y(self) -> None:
        """Автомасштабирует график только по вертикали."""
        self.enableAutoRange(axis="y", enable=True)
        self.enableAutoRange(axis="y", enable=False)

    def показать_объём(self, показать: bool) -> None:
        """Включает/выключает объём для всех инструментов."""
        for свечи in self.инструменты.values():
            свечи.установить_показ_объёма(показать)

    def очистить(self) -> None:
        """Удаляет все инструменты с графика."""
        for код in list(self.инструменты.keys()):
            self.удалить_инструмент(код)

    @property
    def список_инструментов(self) -> list[str]:
        """Возвращает список кодов добавленных инструментов."""
        return list(self.инструменты.keys())
