"""
Главное окно приложения бэктестера.

Объединяет:
- Панель выбора инструментов
- Панель индикаторов
- Интерактивный свечной график
- Инструменты рисования
- Панель запуска бэктеста и результатов
"""

from typing import Optional

import numpy as np
import pandas as pd
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

from src.backtester.engine import Бэктестер, РезультатБэктеста
from src.data.data_loader import загрузить_инструмент, получить_доступные_инструменты
from src.indicators.base import SMA, EMA, RSI, MACD, BollingerBands, Stochastic
from src.ui.chart import График
from src.ui.drawings import ИнструментыРисования
from src.ui.instruments import ПанельИнструментов


class СтратегияПростаяСкользящая:
    """
    Простая тестовая стратегия на пересечении скользящих средних.

    Покупает когда короткая SMA пересекает длинную снизу вверх,
    продаёт когда сверху вниз.
    """
    def __init__(self, период_быстрый: int = 5, период_медленный: int = 20) -> None:
        from src.backtester.strategy import Стратегия

        class _СтратегияSMA(Стратегия):
            def __init__(
                self, быстрый: int, медленный: int
            ) -> None:
                super().__init__()
                self.быстрый = быстрый
                self.медленный = медленный
                self._sma_быстрый: Optional[pd.Series] = None
                self._sma_медленный: Optional[pd.Series] = None

            def init(self) -> None:
                if self.данные is not None:
                    self._sma_быстрый = self.данные["close"].rolling(
                        self.быстрый
                    ).mean()
                    self._sma_медленный = self.данные["close"].rolling(
                        self.медленный
                    ).mean()

            def next(self) -> None:
                if (
                    self.данные is None
                    or self._sma_быстрый is None
                    or self._sma_медленный is None
                ):
                    return
                i = self._индекс
                if i < 1:
                    return
                if pd.isna(self._sma_быстрый.iloc[i]) or pd.isna(
                    self._sma_медленный.iloc[i]
                ):
                    return

                быстрый_тек = float(self._sma_быстрый.iloc[i])
                быстрый_пред = float(self._sma_быстрый.iloc[i - 1])
                медленный_тек = float(self._sma_медленный.iloc[i])
                медленный_пред = float(self._sma_медленный.iloc[i - 1])

                # Пересечение вверх
                if быстрый_пред <= медленный_пред and быстрый_тек > медленный_тек:
                    self.купить(размер=1, комментарий="SMA cross up")

                # Пересечение вниз
                elif быстрый_пред >= медленный_пред and быстрый_тек < медленный_тек:
                    self.продать(размер=1, комментарий="SMA cross down")

        self._класс = _СтратегияSMA
        self.период_быстрый = период_быстрый
        self.период_медленный = период_медленный

    def создать(self):
        return self._класс(self.период_быстрый, self.период_медленный)

    def __str__(self) -> str:
        return f"SMA({self.период_быстрый},{self.период_медленный})"


# Доступные стратегии
ДОСТУПНЫЕ_СТРАТЕГИИ: dict[str, СтратегияПростаяСкользящая] = {
    "SMA(5,20)": СтратегияПростаяСкользящая(5, 20),
    "SMA(10,30)": СтратегияПростаяСкользящая(10, 30),
    "SMA(20,50)": СтратегияПростаяСкользящая(20, 50),
}


class ПанельБэктеста(QtWidgets.QWidget):
    """
    Панель управления бэктестом.

    Позволяет выбрать стратегию, запустить бэктест
    и просмотреть результаты.
    """

    сигнал_запустить_бэктест = QtCore.pyqtSignal(str, str)
    """Сигнал: (код_инструмента, название_стратегии)"""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(layout)

        # Заголовок
        заголовок = QtWidgets.QLabel("Бэктест")
        заголовок.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(заголовок)

        # Выбор стратегии
        layout.addWidget(QtWidgets.QLabel("Стратегия:"))
        self.выбор_стратегии = QtWidgets.QComboBox()
        for имя in ДОСТУПНЫЕ_СТРАТЕГИИ:
            self.выбор_стратегии.addItem(имя)
        layout.addWidget(self.выбор_стратегии)

        # Кнопка запуска
        self.кнопка_запустить = QtWidgets.QPushButton("Запустить бэктест")
        self.кнопка_запустить.setStyleSheet(
            "background-color: #2d7d2d; color: white; "
            "padding: 6px; font-weight: bold;"
        )
        layout.addWidget(self.кнопка_запустить)

        # Разделитель
        разделитель = QtWidgets.QFrame()
        разделитель.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        layout.addWidget(разделитель)

        # Метка результатов
        self.метка_результатов = QtWidgets.QLabel("Результаты:")
        self.метка_результатов.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.метка_результатов)

        # Таблица метрик
        self.таблица_метрик = QtWidgets.QTableWidget(0, 2)
        self.таблица_метрик.setHorizontalHeaderLabels(["Метрика", "Значение"])
        self.таблица_метрик.horizontalHeader().setStretchLastSection(True)
        self.таблица_метрик.setMaximumHeight(250)
        layout.addWidget(self.таблица_метрик)

        layout.addStretch()

    def показать_результаты(self, результат: РезультатБэктеста) -> None:
        """Заполняет таблицу метрик результатами бэктеста."""
        метрики = результат.метрики
        данные = [
            ("Общая доходность", f"{метрики['total_return']:.2f}%"),
            ("Абсолютная прибыль", f"{метрики['total_pnl']:.2f}"),
            ("Коэф. Шарпа", f"{метрики['sharpe_ratio']:.2f}"),
            ("Макс. просадка", f"{метрики['max_drawdown']:.2f}%"),
            ("Всего сделок", str(метрики['num_trades'])),
            ("Win Rate", f"{метрики['win_rate']:.1f}%"),
            ("Сред. прибыль", f"{метрики['avg_win']:.2f}"),
            ("Сред. убыток", f"{метрики['avg_loss']:.2f}"),
            ("Лучшая сделка", f"{метрики['best_trade']:.2f}%"),
            ("Худшая сделка", f"{метрики['worst_trade']:.2f}%"),
        ]
        self.таблица_метрик.setRowCount(len(данные))
        for i, (название, значение) in enumerate(данные):
            self.таблица_метрик.setItem(i, 0, QtWidgets.QTableWidgetItem(название))
            self.таблица_метрик.setItem(i, 1, QtWidgets.QTableWidgetItem(значение))
        self.таблица_метрик.resizeColumnsToContents()


class ПанельИндикаторов(QtWidgets.QWidget):
    """
    Панель управления индикаторами на графике.

    Позволяет выбрать тип индикатора, настроить параметры
    и добавить/удалить его с графика.
    """

    сигнал_добавить_индикатор = QtCore.pyqtSignal(str, int)
    """Сигнал: (тип_индикатора, период)"""

    сигнал_удалить_индикатор = QtCore.pyqtSignal(str)
    """Сигнал: (название_индикатора)"""

    ТИПЫ_ИНДИКАТОРОВ = [
        "SMA",
        "EMA",
        "RSI",
        "Bollinger Bands",
    ]

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(5, 2, 5, 2)
        self.setLayout(layout)

        # Надпись "Индикаторы"
        метка = QtWidgets.QLabel("Индикаторы:")
        метка.setStyleSheet("font-weight: bold;")
        layout.addWidget(метка)

        # Выбор типа индикатора
        self.выбор_типа = QtWidgets.QComboBox()
        for тип in self.ТИПЫ_ИНДИКАТОРОВ:
            self.выбор_типа.addItem(тип)
        layout.addWidget(self.выбор_типа)

        # Период
        layout.addWidget(QtWidgets.QLabel("Период:"))
        self.поле_периода = QtWidgets.QSpinBox()
        self.поле_периода.setMinimum(2)
        self.поле_периода.setMaximum(200)
        self.поле_периода.setValue(14)
        layout.addWidget(self.поле_периода)

        # Кнопка "Добавить"
        self.кнопка_добавить = QtWidgets.QPushButton("+")
        self.кнопка_добавить.setMaximumWidth(30)
        self.кнопка_добавить.setStyleSheet(
            "background-color: #2d7d2d; color: white; font-weight: bold;"
        )
        layout.addWidget(self.кнопка_добавить)

        # Список активных индикаторов
        self.список_активных = QtWidgets.QListWidget()
        self.список_активных.setMaximumWidth(200)
        self.список_активных.setMaximumHeight(50)
        layout.addWidget(self.список_активных)

        # Кнопка "Удалить"
        self.кнопка_удалить = QtWidgets.QPushButton("✕")
        self.кнопка_удалить.setMaximumWidth(30)
        self.кнопка_удалить.setStyleSheet(
            "background-color: #8b0000; color: white; font-weight: bold;"
        )
        layout.addWidget(self.кнопка_удалить)

        layout.addStretch()

        self.кнопка_добавить.clicked.connect(self._on_добавить)
        self.кнопка_удалить.clicked.connect(self._on_удалить)

    def _on_добавить(self) -> None:
        """Обработчик добавления индикатора."""
        тип = self.выбор_типа.currentText()
        период = self.поле_периода.value()
        self.сигнал_добавить_индикатор.emit(тип, период)

    def _on_удалить(self) -> None:
        """Обработчик удаления индикатора."""
        выбранные = self.список_активных.selectedItems()
        for элемент in выбранные:
            self.сигнал_удалить_индикатор.emit(элемент.text())

    def добавить_в_активные(self, название: str) -> None:
        """Добавляет индикатор в список активных."""
        for i in range(self.список_активных.count()):
            if self.список_активных.item(i).text() == название:
                return
        self.список_активных.addItem(название)

    def удалить_из_активных(self, название: str) -> None:
        """Удаляет индикатор из списка активных."""
        for i in range(self.список_активных.count()):
            if self.список_активных.item(i).text() == название:
                self.список_активных.takeItem(i)
                break


class ГлавноеОкно(QtWidgets.QMainWindow):
    """
    Главное окно приложения.

    Содержит панель инструментов, свечной график,
    панель бэктеста и панель для результатов.
    """

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Vibe Backtester")
        self.setMinimumSize(1400, 700)

        # Центральный виджет
        центральный = QtWidgets.QWidget()
        self.setCentralWidget(центральный)
        layout = QtWidgets.QHBoxLayout()
        центральный.setLayout(layout)

        # Левая часть: график
        левая_часть = QtWidgets.QWidget()
        левая_layout = QtWidgets.QVBoxLayout()
        левая_часть.setLayout(левая_layout)

        # Панель инструментов (сверху)
        self.панель_инструментов = ПанельИнструментов()
        левая_layout.addWidget(self.панель_инструментов)

        # Панель индикаторов
        self.панель_индикаторов = ПанельИндикаторов()
        левая_layout.addWidget(self.панель_индикаторов)

        # График (центр)
        self.график = График()
        левая_layout.addWidget(self.график, stretch=1)
        layout.addWidget(левая_часть, stretch=1)

        # Инструменты рисования
        self.рисование = ИнструментыРисования(self.график)

        # Словарь индикаторов на графике: {название: PlotDataItem}
        self._индикаторы_на_графике: dict[str, pg.PlotDataItem] = {}
        # Словарь загруженных данных: {код: DataFrame}
        self._данные_инструментов: dict[str, pd.DataFrame] = {}

        # Правая часть: панель бэктеста
        self.панель_бэктеста = ПанельБэктеста()
        self.панель_бэктеста.setMaximumWidth(350)
        layout.addWidget(self.панель_бэктеста)

        # Статус-бар
        self.statusBar().showMessage("Готов к работе")

        # Загружаем список инструментов при старте
        self._загрузить_список_инструментов()

        # Подключаем сигналы
        self._подключить_сигналы()

    def _загрузить_список_инструментов(self) -> None:
        """Загружает список доступных инструментов из БД."""
        self.statusBar().showMessage("Загрузка списка инструментов...")
        try:
            инструменты = получить_доступные_инструменты()
            коды = [инстр["код"] for инстр in инструменты]
            self.панель_инструментов.выбор_инструмента.загрузить_инструменты(коды)
            self.панель_инструментов.выбор_инструмента.setPlaceholderText(
                f"Найдено {len(коды)} инструментов"
            )
            self.statusBar().showMessage(
                f"Загружено {len(коды)} инструментов"
            )
        except Exception as e:
            self.панель_инструментов.выбор_инструмента.setPlaceholderText(
                "Базы данных не найдены"
            )
            self.statusBar().showMessage(f"Ошибка загрузки: {e}")

    def _подключить_сигналы(self) -> None:
        """Подключает сигналы от панели инструментов к обработчикам."""
        self.панель_инструментов.сигнал_добавить_инструмент.connect(
            self._на_добавление_инструмента
        )
        self.панель_инструментов.сигнал_удалить_инструмент.connect(
            self._на_удаление_инструмента
        )
        self.панель_инструментов.сигнал_изменить_таймфрейм.connect(
            self._на_изменение_таймфрейма
        )
        self.панель_инструментов.сигнал_показать_объём.connect(
            self.график.показать_объём
        )
        self.панель_инструментов.кнопка_автомасштаб.clicked.connect(
            self.график.автомасштаб
        )
        self.панель_бэктеста.кнопка_запустить.clicked.connect(
            self._на_запуск_бэктеста
        )
        self.панель_индикаторов.сигнал_добавить_индикатор.connect(
            self._на_добавление_индикатора
        )
        self.панель_индикаторов.сигнал_удалить_индикатор.connect(
            self._на_удаление_индикатора
        )

    def _на_добавление_инструмента(
        self, код: str, таймфрейм: str
    ) -> None:
        """Обработчик добавления инструмента на график."""
        if код in self.график.список_инструментов:
            self.statusBar().showMessage(
                f"Инструмент {код} уже добавлен на график"
            )
            return

        self.statusBar().showMessage(f"Загрузка {код} ({таймфрейм})...")
        try:
            данные = загрузить_инструмент(код, таймфрейм=таймфрейм)
            if данные is None or len(данные) == 0:
                self.statusBar().showMessage(
                    f"Нет данных для {код} ({таймфрейм})"
                )
                return

            успех = self.график.добавить_инструмент(код, данные, таймфрейм)
            if успех:
                self.панель_инструментов.добавить_в_активные(код)
                self._данные_инструментов[код] = данные
                self.statusBar().showMessage(
                    f"Добавлен {код} ({таймфрейм}), "
                    f"свечей: {len(данные)}"
                )
            else:
                self.statusBar().showMessage(
                    f"Не удалось добавить {код}"
                )
        except Exception as e:
            self.statusBar().showMessage(f"Ошибка загрузки {код}: {e}")

    def _на_удаление_инструмента(self, код: str) -> None:
        """Обработчик удаления инструмента с графика."""
        успех = self.график.удалить_инструмент(код)
        if успех:
            self.панель_инструментов.удалить_из_активных(код)
            self._данные_инструментов.pop(код, None)
            # Очищаем индикаторы при смене инструмента
            for название in list(self._индикаторы_на_графике.keys()):
                self.график.removeItem(self._индикаторы_на_графике.pop(название))
            self.панель_индикаторов.список_активных.clear()
            self.statusBar().showMessage(f"Удалён {код} с графика")

    def _на_изменение_таймфрейма(self, таймфрейм: str) -> None:
        """Обработчик изменения таймфрейма."""
        активные = self.график.список_инструментов.copy()
        if not активные:
            return

        self.statusBar().showMessage(
            f"Переключение на {таймфрейм} для {len(активные)} инструментов..."
        )

        for код in активные:
            self.график.удалить_инструмент(код)
            self._данные_инструментов.pop(код, None)

        # Очищаем индикаторы
        for название in list(self._индикаторы_на_графике.keys()):
            self.график.removeItem(self._индикаторы_на_графике.pop(название))
        self.панель_индикаторов.список_активных.clear()

        for код in активные:
            self._на_добавление_инструмента(код, таймфрейм)

    def _на_запуск_бэктеста(self) -> None:
        """Обработчик запуска бэктеста."""
        # Берём первый активный инструмент на графике
        активные = self.график.список_инструментов
        if not активные:
            self.statusBar().showMessage(
                "Сначала добавьте инструмент на график"
            )
            return

        код = активные[0]
        имя_стратегии = self.панель_бэктеста.выбор_стратегии.currentText()
        описание_стратегии = ДОСТУПНЫЕ_СТРАТЕГИИ.get(имя_стратегии)

        if описание_стратегии is None:
            self.statusBar().showMessage(f"Стратегия {имя_стратегии} не найдена")
            return

        self.statusBar().showMessage(
            f"Запуск бэктеста: {код} / {имя_стратегии}..."
        )

        try:
            # Загружаем данные для бэктеста
            данные = загрузить_инструмент(код)
            if данные is None or len(данные) == 0:
                self.statusBar().showMessage(f"Нет данных для {код}")
                return

            # Создаём стратегию и бэктестер
            стратегия = описание_стратегии.создать()
            бэктестер = Бэктестер()
            результат = бэктестер.прогнать(стратегия, данные)

            # Показываем результаты
            self.панель_бэктеста.показать_результаты(результат)

            # Добавляем кривую капитала на график
            self._отобразить_эквити(результат, код)

            self.statusBar().showMessage(
                f"Бэктест завершён: "
                f"доходность {результат.метрики['total_return']:.2f}%, "
                f"сделок: {результат.метрики['num_trades']}"
            )
        except Exception as e:
            self.statusBar().showMessage(f"Ошибка бэктеста: {e}")

    def _на_добавление_индикатора(self, тип: str, период: int) -> None:
        """Обработчик добавления индикатора на график."""
        активные = self.график.список_инструментов
        if not активные:
            self.statusBar().showMessage(
                "Сначала добавьте инструмент на график"
            )
            return

        код = активные[0]
        данные = self._данные_инструментов.get(код)
        if данные is None:
            self.statusBar().showMessage(
                f"Нет данных для расчёта индикатора"
            )
            return

        название = f"{тип}({период})"
        if название in self._индикаторы_на_графике:
            self.statusBar().showMessage(
                f"Индикатор {название} уже добавлен"
            )
            return

        try:
            if тип == "SMA":
                индикатор = SMA(период)
                значения = индикатор.рассчитать(данные["close"])
            elif тип == "EMA":
                индикатор = EMA(период)
                значения = индикатор.рассчитать(данные["close"])
            elif тип == "RSI":
                индикатор = RSI(период)
                значения = индикатор.рассчитать(данные["close"])
            elif тип == "Bollinger Bands":
                индикатор = BollingerBands(период)
                bb = индикатор.рассчитать(данные["close"])
                # Рисуем среднюю, верхнюю и нижнюю полосы
                for имя_полосы, цвет in [
                    ("средняя", (255, 255, 0)),
                    ("верхняя", (255, 150, 50)),
                    ("нижняя", (255, 150, 50)),
                ]:
                    полоса_название = f"BB({период})_{имя_полосы}"
                    if имя_полосы in ("верхняя", "нижняя"):
                        стиль = QtCore.Qt.PenStyle.DashLine
                    else:
                        стиль = QtCore.Qt.PenStyle.SolidLine
                    self._нарисовать_индикатор(
                        полоса_название, bb[имя_полосы], данные, цвет, стиль
                    )
                self.панель_индикаторов.добавить_в_активные(название)
                self.statusBar().showMessage(
                    f"Добавлен {название}"
                )
                self.график.автомасштаб()
                return
            else:
                self.statusBar().showMessage(
                    f"Неизвестный тип индикатора: {тип}"
                )
                return

            self._нарисовать_индикатор(
                название, значения, данные
            )
            self.панель_индикаторов.добавить_в_активные(название)
            self.statusBar().showMessage(f"Добавлен {название}")
            self.график.автомасштаб()

        except Exception as e:
            self.statusBar().showMessage(f"Ошибка индикатора: {e}")

    def _нарисовать_индикатор(
        self,
        название: str,
        значения: pd.Series,
        данные: pd.DataFrame,
        цвет: tuple = (255, 255, 100),
        стиль: QtCore.Qt.PenStyle = QtCore.Qt.PenStyle.SolidLine,
    ) -> None:
        """
        Рисует линию индикатора на графике.

        Параметры
        ----------
        название : str
            Уникальное имя линии.
        значения : pd.Series
            Значения индикатора.
        данные : pd.DataFrame
            Исходные данные (для временных меток).
        цвет : tuple
            RGB-цвет линии.
        стиль : QtCore.Qt.PenStyle
            Стиль линии.
        """
        if название in self._индикаторы_на_графике:
            self.график.removeItem(self._индикаторы_на_графике[название])

        времена = np.array([
            t.timestamp() for t in значения.index
        ], dtype=float)
        значения_массив = значения.values.astype(float)

        # Убираем NaN
        маска = ~np.isnan(значения_массив)
        времена = времена[маска]
        значения_массив = значения_массив[маска]

        линия = pg.PlotDataItem(
            времена,
            значения_массив,
            pen=pg.mkPen(цвет, width=1.5, style=стиль),
            name=название,
        )
        self.график.addItem(линия)
        self._индикаторы_на_графике[название] = линия

    def _на_удаление_индикатора(self, название: str) -> None:
        """Обработчик удаления индикатора с графика."""
        # Удаляем BB полосы если это BB индикатор
        for ключ in list(self._индикаторы_на_графике.keys()):
            if ключ.startswith(название.replace(")", "_")):
                self.график.removeItem(self._индикаторы_на_графике.pop(ключ))

        if название in self._индикаторы_на_графике:
            self.график.removeItem(self._индикаторы_на_графике.pop(название))
            self.панель_индикаторов.удалить_из_активных(название)
            self.statusBar().showMessage(f"Удалён {название} с графика")

    def _отобразить_эквити(
        self, результат: РезультатБэктеста, код: str
    ) -> None:
        """Отображает кривую капитала на графике."""
        имя_кривой = f"{код}_equity"
        # Удаляем старую кривую если есть
        for item in self.график.listDataItems():
            if item.name() == имя_кривой:
                self.график.removeItem(item)

        эквити = результат.эквити
        времена = [t.timestamp() for t in эквити.index]
        нормализованное = эквити / эквити.iloc[0] * 100

        кривая = pg.PlotDataItem(
            времена,
            нормализованное.values,
            pen=pg.mkPen((255, 255, 100), width=1.5),
            name=имя_кривой,
        )
        кривая.setParentItem(self.график.getPlotItem())
        self.график.addItem(кривая)
        self.график.автомасштаб()
