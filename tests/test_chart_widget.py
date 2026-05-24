"""
Тесты для виджета графика (src/gui/chart_widget.py).

Проверяет создание ChartWidget, загрузку данных и базовые операции.
"""

from datetime import datetime

import polars as pl
import pytest

from src.gui.chart_widget import ChartWidget


@pytest.fixture
def sample_candles() -> pl.DataFrame:
    """
    Фикстура: создаёт тестовый DataFrame со свечными данными.
    """
    return pl.DataFrame({
        "date": [
            datetime(2025, 10, 28, 9, 0),
            datetime(2025, 10, 28, 9, 1),
            datetime(2025, 10, 28, 9, 2),
            datetime(2025, 10, 28, 9, 3),
            datetime(2025, 10, 28, 9, 4),
        ],
        "open": [100.0, 102.0, 103.0, 101.0, 104.0],
        "high": [105.0, 104.0, 106.0, 104.0, 107.0],
        "low": [99.0, 101.0, 102.0, 100.0, 103.0],
        "close": [102.0, 103.0, 101.0, 104.0, 106.0],
        "volume": [1000, 800, 1200, 900, 1500],
    })


@pytest.fixture
def chart_widget(qtbot) -> ChartWidget:
    """
    Фикстура: создаёт ChartWidget для тестирования.
    """
    widget = ChartWidget()
    qtbot.addWidget(widget)
    return widget


def test_chart_widget_creation(chart_widget: ChartWidget) -> None:
    """
    Проверяет, что виджет графика создаётся корректно.
    """
    assert chart_widget is not None
    assert isinstance(chart_widget, ChartWidget)


def test_chart_widget_has_chart_attribute(chart_widget: ChartWidget) -> None:
    """
    Проверяет, что виджет содержит экземпляр QtChart.
    """
    assert hasattr(chart_widget, "chart")
    assert chart_widget.chart is not None


def test_chart_widget_has_webview(chart_widget: ChartWidget) -> None:
    """
    Проверяет, что виджет содержит QWebEngineView.
    """
    assert hasattr(chart_widget, "webview")
    assert chart_widget.webview is not None
    assert chart_widget.webview.objectName() == "chartWebView"


def test_chart_widget_has_layout(chart_widget: ChartWidget) -> None:
    """
    Проверяет, что виджет имеет макет для размещения графика.
    """
    assert chart_widget.layout() is not None
    assert chart_widget.layout().objectName() == ""


def test_load_candles_accepts_polars_df(chart_widget: ChartWidget, sample_candles: pl.DataFrame) -> None:
    """
    Проверяет, что метод load_candles принимает Polars DataFrame без ошибок.
    """
    try:
        chart_widget.load_candles(sample_candles)
    except Exception as exc:
        pytest.fail(f"load_candles вызвал исключение: {exc}")


def test_load_candles_with_optional_volume(chart_widget: ChartWidget) -> None:
    """
    Проверяет загрузку данных без колонки volume.
    """
    df_no_volume = pl.DataFrame({
        "date": [datetime(2025, 10, 28, 9, 0)],
        "open": [100.0],
        "high": [105.0],
        "low": [99.0],
        "close": [102.0],
    })
    try:
        chart_widget.load_candles(df_no_volume)
    except Exception as exc:
        pytest.fail(f"load_candles без volume вызвал исключение: {exc}")


def test_load_candles_empty_dataframe(chart_widget: ChartWidget) -> None:
    """
    Проверяет загрузку пустого DataFrame (должен работать без ошибок).
    """
    empty_df = pl.DataFrame({
        "date": [],
        "open": [],
        "high": [],
        "low": [],
        "close": [],
    })
    try:
        chart_widget.load_candles(empty_df)
    except Exception as exc:
        pytest.fail(f"load_candles с пустым DataFrame вызвал исключение: {exc}")


def test_load_candles_with_loader_column_names(chart_widget: ChartWidget) -> None:
    """
    Проверяет загрузку данных с именами колонок из loader.py.
    """
    df = pl.DataFrame({
        "date": [datetime(2025, 10, 28, 9, 0)],
        "open": [100.0],
        "high": [105.0],
        "low": [99.0],
        "close": [102.0],
        "volume": [1000],
    })
    try:
        chart_widget.load_candles(df)
    except Exception as exc:
        pytest.fail(f"load_candles с колонками loader вызвал исключение: {exc}")


def test_fit_method(chart_widget: ChartWidget, sample_candles: pl.DataFrame) -> None:
    """
    Проверяет, что метод fit() не вызывает ошибок.
    """
    chart_widget.load_candles(sample_candles)
    try:
        chart_widget.fit()
    except Exception as exc:
        pytest.fail(f"fit() вызвал исключение: {exc}")


def test_set_title(chart_widget: ChartWidget) -> None:
    """
    Проверяет установку заголовка графика.
    """
    try:
        chart_widget.set_title("Тестовый график")
    except Exception as exc:
        pytest.fail(f"set_title вызвал исключение: {exc}")


def test_clear_method(chart_widget: ChartWidget, sample_candles: pl.DataFrame) -> None:
    """
    Проверяет, что clear() не вызывает ошибок.
    """
    chart_widget.load_candles(sample_candles)
    try:
        chart_widget.clear()
    except Exception as exc:
        pytest.fail(f"clear() вызвал исключение: {exc}")


def test_chart_widget_visible(chart_widget: ChartWidget, qtbot) -> None:
    """
    Проверяет, что виджет становится видимым после show().
    """
    chart_widget.show()
    qtbot.wait(100)  # Даём время на инициализацию webview
    assert chart_widget.isVisible()


def test_chart_widget_accepts_parent(qtbot) -> None:
    """
    Проверяет, что ChartWidget можно создать с родительским виджетом.
    """
    parent = ChartWidget()
    qtbot.addWidget(parent)
    child = ChartWidget(parent=parent)
    qtbot.addWidget(child)
    assert child.parent() is parent


def test_chart_widget_webview_in_layout(chart_widget: ChartWidget) -> None:
    """
    Проверяет, что webview является дочерним элементом макета.
    """
    assert chart_widget.webview.parent() is chart_widget
    # Проверяем, что webview находится в менеджере макета
    layout_items = [
        chart_widget.chart_layout.itemAt(i).widget()
        for i in range(chart_widget.chart_layout.count())
    ]
    assert chart_widget.webview in layout_items
