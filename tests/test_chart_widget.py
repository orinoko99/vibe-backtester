"""
Тесты для виджета графика (src/gui/chart_widget.py).

Проверяет создание ChartWidget, загрузку данных, базовые операции,
а также инструменты рисования и маркеры.
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


# ──────────────────────────────────────────────
# Тесты для инструментов рисования
# ──────────────────────────────────────────────


def test_drawing_default_state(chart_widget: ChartWidget) -> None:
    """
    Проверяет начальное состояние инструментов рисования.
    """
    assert chart_widget.active_tool == "none"
    assert chart_widget.drawing_color == "#1E80F0"
    assert chart_widget._drawings == []
    assert chart_widget._pending_point is None


def test_set_drawing_tool(chart_widget: ChartWidget) -> None:
    """
    Проверяет переключение инструментов рисования.
    """
    chart_widget.set_drawing_tool("horizontal_line")
    assert chart_widget.active_tool == "horizontal_line"
    assert chart_widget._pending_point is None

    chart_widget.set_drawing_tool("trend_line")
    assert chart_widget.active_tool == "trend_line"

    chart_widget.set_drawing_tool("none")
    assert chart_widget.active_tool == "none"


def test_set_drawing_color(chart_widget: ChartWidget) -> None:
    """
    Проверяет смену цвета рисования.
    """
    chart_widget.set_drawing_color("#FF0000")
    assert chart_widget.drawing_color == "#FF0000"

    chart_widget.set_drawing_color("#00FF00")
    assert chart_widget.drawing_color == "#00FF00"


def test_add_horizontal_line(chart_widget: ChartWidget) -> None:
    """
    Проверяет добавление горизонтальной линии.
    """
    line = chart_widget.add_horizontal_line(price=100.0, color="#FF0000", text="Тест")
    assert line is not None
    assert len(chart_widget._drawings) == 1
    assert chart_widget._drawings[0]["type"] == "horizontal_line"
    assert chart_widget._drawings[0]["price"] == 100.0
    assert chart_widget._drawings[0]["color"] == "#FF0000"


def test_add_horizontal_line_uses_default_color(chart_widget: ChartWidget) -> None:
    """
    Проверяет, что горизонтальная линия использует цвет по умолчанию.
    """
    chart_widget.set_drawing_color("#00FF00")
    line = chart_widget.add_horizontal_line(price=150.0)
    assert line is not None
    assert chart_widget._drawings[0]["color"] == "#00FF00"


def test_add_vertical_line(chart_widget: ChartWidget) -> None:
    """
    Проверяет добавление вертикальной линии.
    """
    line = chart_widget.add_vertical_line(
        time=datetime(2025, 10, 28, 9, 0), color="#00FF00", text="Старт"
    )
    assert line is not None
    assert len(chart_widget._drawings) == 1
    assert chart_widget._drawings[0]["type"] == "vertical_line"
    assert chart_widget._drawings[0]["time"] is not None


def test_add_vertical_line_with_string_time(chart_widget: ChartWidget) -> None:
    """
    Проверяет добавление вертикальной линии со строковым временем.
    """
    line = chart_widget.add_vertical_line(time="2025-10-28T09:00:00")
    assert line is not None
    assert chart_widget._drawings[0]["type"] == "vertical_line"


def test_add_trend_line(chart_widget: ChartWidget) -> None:
    """
    Проверяет добавление трендовой линии между двумя точками.
    """
    line = chart_widget.add_trend_line(
        start_time=datetime(2025, 10, 28, 9, 0),
        start_value=100.0,
        end_time=datetime(2025, 10, 28, 9, 4),
        end_value=106.0,
        color="#FF0000",
    )
    assert line is not None
    assert len(chart_widget._drawings) == 1
    assert chart_widget._drawings[0]["type"] == "trend_line"
    assert chart_widget._drawings[0]["start_value"] == 100.0
    assert chart_widget._drawings[0]["end_value"] == 106.0


def test_add_ray_line(chart_widget: ChartWidget) -> None:
    """
    Проверяет добавление луча.
    """
    ray = chart_widget.add_ray_line(
        start_time=datetime(2025, 10, 28, 9, 0),
        value=100.0,
        color="#FF0000",
    )
    assert ray is not None
    assert len(chart_widget._drawings) == 1
    assert chart_widget._drawings[0]["type"] == "ray_line"
    assert chart_widget._drawings[0]["value"] == 100.0


def test_add_vertical_span(chart_widget: ChartWidget) -> None:
    """
    Проверяет добавление вертикальной заливки.
    """
    span = chart_widget.add_vertical_span(
        start_time=datetime(2025, 10, 28, 9, 0),
        end_time=datetime(2025, 10, 28, 9, 4),
    )
    assert span is not None
    assert len(chart_widget._drawings) == 1
    assert chart_widget._drawings[0]["type"] == "vertical_span"


def test_add_marker(chart_widget: ChartWidget) -> None:
    """
    Проверяет добавление маркера на свечу.
    """
    marker_id = chart_widget.add_marker(
        time=datetime(2025, 10, 28, 9, 0),
        text="Вход",
        position="above",
        shape="arrow_up",
        color="#FF0000",
    )
    assert marker_id is not None
    assert isinstance(marker_id, str)
    assert len(chart_widget._drawings) == 1
    assert chart_widget._drawings[0]["type"] == "marker"
    assert chart_widget._drawings[0]["text"] == "Вход"


def test_remove_marker(chart_widget: ChartWidget) -> None:
    """
    Проверяет удаление маркера по ID.
    """
    marker_id = chart_widget.add_marker(
        time=datetime(2025, 10, 28, 9, 0),
        text="Тест",
    )
    assert len(chart_widget._drawings) == 1

    chart_widget.remove_marker(marker_id)
    assert len(chart_widget._drawings) == 0


def test_clear_drawings(chart_widget: ChartWidget) -> None:
    """
    Проверяет очистку всех рисунков и маркеров.
    """
    chart_widget.add_horizontal_line(price=100.0)
    chart_widget.add_marker(time=datetime(2025, 10, 28, 9, 0), text="Маркер")
    assert len(chart_widget._drawings) == 2

    chart_widget.clear_drawings()
    assert chart_widget._drawings == []
    assert chart_widget._pending_point is None


def test_get_drawings_returns_copy(chart_widget: ChartWidget) -> None:
    """
    Проверяет, что get_drawings возвращает копию списка рисунков.
    """
    chart_widget.add_horizontal_line(price=100.0)
    drawings = chart_widget.get_drawings()
    assert len(drawings) == 1
    # Изменение возвращённого списка не должно влиять на внутренний
    drawings.clear()
    assert len(chart_widget._drawings) == 1


def test_get_drawings_empty_by_default(chart_widget: ChartWidget) -> None:
    """
    Проверяет, что get_drawings возвращает пустой список.
    """
    assert chart_widget.get_drawings() == []


def test_multiple_drawings_tracked(chart_widget: ChartWidget) -> None:
    """
    Проверяет отслеживание нескольких рисунков одновременно.
    """
    chart_widget.add_horizontal_line(price=100.0)
    chart_widget.add_horizontal_line(price=200.0)
    chart_widget.add_vertical_line(time=datetime(2025, 10, 28, 9, 0))
    assert len(chart_widget.get_drawings()) == 3


def test_drawing_color_only_applies_to_new(chart_widget: ChartWidget) -> None:
    """
    Проверяет, что смена цвета не влияет на уже созданные рисунки.
    """
    line1 = chart_widget.add_horizontal_line(price=100.0, color="#FF0000")
    chart_widget.set_drawing_color("#00FF00")
    line2 = chart_widget.add_horizontal_line(price=200.0)
    assert chart_widget._drawings[0]["color"] == "#FF0000"
    assert chart_widget._drawings[1]["color"] == "#00FF00"


def test_clear_drawings_after_data_clear(chart_widget: ChartWidget, sample_candles: pl.DataFrame) -> None:
    """
    Проверяет, что clear_drawings работает после загрузки данных.
    """
    chart_widget.load_candles(sample_candles)
    chart_widget.add_horizontal_line(price=100.0)
    chart_widget.clear_drawings()
    assert chart_widget._drawings == []


def test_handle_chart_click_horizontal_line(chart_widget: ChartWidget) -> None:
    """
    Проверяет обработку клика для горизонтальной линии.
    """
    chart_widget.set_drawing_tool("horizontal_line")
    chart_widget._handle_chart_click(
        time=datetime(2025, 10, 28, 9, 0), price=100.0
    )
    assert len(chart_widget._drawings) == 1
    assert chart_widget._drawings[0]["type"] == "horizontal_line"
    assert chart_widget._drawings[0]["price"] == 100.0


def test_handle_chart_click_vertical_line(chart_widget: ChartWidget) -> None:
    """
    Проверяет обработку клика для вертикальной линии.
    """
    chart_widget.set_drawing_tool("vertical_line")
    dt = datetime(2025, 10, 28, 9, 0)
    chart_widget._handle_chart_click(time=dt, price=100.0)
    assert len(chart_widget._drawings) == 1
    assert chart_widget._drawings[0]["type"] == "vertical_line"


def test_handle_chart_click_marker(chart_widget: ChartWidget) -> None:
    """
    Проверяет обработку клика для маркера.
    """
    chart_widget.set_drawing_tool("marker")
    chart_widget._handle_chart_click(
        time=datetime(2025, 10, 28, 9, 0), price=100.0
    )
    assert len(chart_widget._drawings) == 1
    assert chart_widget._drawings[0]["type"] == "marker"


def test_handle_chart_click_ray_line(chart_widget: ChartWidget) -> None:
    """
    Проверяет обработку клика для луча.
    """
    chart_widget.set_drawing_tool("ray_line")
    chart_widget._handle_chart_click(
        time=datetime(2025, 10, 28, 9, 0), price=100.0
    )
    assert len(chart_widget._drawings) == 1
    assert chart_widget._drawings[0]["type"] == "ray_line"
    assert chart_widget._drawings[0]["value"] == 100.0


def test_handle_chart_click_trend_line_two_clicks(chart_widget: ChartWidget) -> None:
    """
    Проверяет обработку двух кликов для трендовой линии.
    Первый клик запоминает точку, второй создаёт линию.
    """
    chart_widget.set_drawing_tool("trend_line")

    # Первый клик — запоминает точку, ничего не рисует
    chart_widget._handle_chart_click(
        time=datetime(2025, 10, 28, 9, 0), price=100.0
    )
    assert chart_widget._pending_point is not None
    assert len(chart_widget._drawings) == 0

    # Второй клик — создаёт трендовую линию
    chart_widget._handle_chart_click(
        time=datetime(2025, 10, 28, 9, 4), price=106.0
    )
    assert chart_widget._pending_point is None
    assert len(chart_widget._drawings) == 1
    assert chart_widget._drawings[0]["type"] == "trend_line"
    assert chart_widget._drawings[0]["start_value"] == 100.0
    assert chart_widget._drawings[0]["end_value"] == 106.0


def test_handle_chart_click_vertical_span_two_clicks(chart_widget: ChartWidget) -> None:
    """
    Проверяет обработку двух кликов для вертикальной заливки.
    """
    chart_widget.set_drawing_tool("vertical_span")

    # Первый клик
    chart_widget._handle_chart_click(
        time=datetime(2025, 10, 28, 9, 0), price=100.0
    )
    assert chart_widget._pending_point is not None
    assert len(chart_widget._drawings) == 0

    # Второй клик — создаёт заливку
    chart_widget._handle_chart_click(
        time=datetime(2025, 10, 28, 9, 4), price=106.0
    )
    assert chart_widget._pending_point is None
    assert len(chart_widget._drawings) == 1
    assert chart_widget._drawings[0]["type"] == "vertical_span"


def test_handle_chart_click_with_none_time(chart_widget: ChartWidget) -> None:
    """
    Проверяет, что клик с None time/price игнорируется.
    """
    chart_widget.set_drawing_tool("horizontal_line")
    chart_widget._handle_chart_click(time=None, price=None)
    assert len(chart_widget._drawings) == 0


def test_handle_chart_click_with_none_tool(chart_widget: ChartWidget) -> None:
    """
    Проверяет, что клик с выключенным инструментом игнорируется.
    """
    chart_widget.set_drawing_tool("none")
    chart_widget._handle_chart_click(
        time=datetime(2025, 10, 28, 9, 0), price=100.0
    )
    assert len(chart_widget._drawings) == 0


def test_set_drawing_tool_resets_pending(chart_widget: ChartWidget) -> None:
    """
    Проверяет, что смена инструмента сбрасывает ожидающую точку.
    """
    chart_widget.set_drawing_tool("trend_line")
    chart_widget._handle_chart_click(
        time=datetime(2025, 10, 28, 9, 0), price=100.0
    )
    assert chart_widget._pending_point is not None

    # Смена инструмента сбрасывает ожидание
    chart_widget.set_drawing_tool("horizontal_line")
    assert chart_widget._pending_point is None
