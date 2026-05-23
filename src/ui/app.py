"""
Главное окно приложения бэктестера.

Объединяет:
- Панель выбора инструментов
- Интерактивный свечной график
- Инструменты рисования
- Панель запуска бэктеста и результатов
"""

from typing import Optional

import pandas as pd
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

from src.backtester.engine import Бэктестер, РезультатБэктеста
from src.data.data_loader import загрузить_инструмент, получить_доступные_инструменты
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

        # График (центр)
        self.график = График()
        левая_layout.addWidget(self.график, stretch=1)
        layout.addWidget(левая_часть, stretch=1)

        # Инструменты рисования
        self.рисование = ИнструментыРисования(self.график)

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
