import json
import sqlite3
from contextlib import closing
from dataclasses import replace
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from scripts.setup_db import DDL
from src.charts import result_chart
from src.config import load_settings
from src.sales import load_sales_filters, summarize_sales
from src.service import run_analysis


@pytest.fixture
def analysis_settings(tmp_path):
    database = tmp_path / "analyses.db"
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.executescript(DDL)
        connection.executescript("""
            INSERT INTO Customers VALUES (1, 'Ada', 'İzmir', 'Bireysel'), (2, 'Can', 'Ankara', 'KOBİ');
            INSERT INTO Products VALUES (1, 'Çay', 'İçecek', 99), (2, 'Süt', 'İçecek', 99);
            INSERT INTO Orders VALUES
                (1, 1, '2026-01-01'), (2, 1, '2026-02-01'),
                (3, 2, '2026-03-01'), (4, 2, '2026-04-01');
            INSERT INTO OrderItems VALUES
                (1, 1, 1, 1, 20), (2, 1, 1, 2, 20), (3, 1, 2, 1, 10),
                (4, 2, 1, 1, 20), (5, 3, 2, 1, 10), (6, 4, 1, 1, 20);
        """)
    return replace(load_settings(), database_path=database, gemini_api_key="", log_path=tmp_path / "events.jsonl")


@pytest.mark.parametrize(("key", "expected"), [
    ("pareto", [["Çay", 100.0, 83.33], ["Süt", 20.0, 100.0]]),
    ("basket", [["Çay", "Süt", 1, 25.0, 0.67]]),
    ("segment", [["Bireysel", 90.0, 2], ["KOBİ", 30.0, 2]]),
])
def test_presets_calculate_expected_metrics(analysis_settings, key, expected):
    response = run_analysis(key, analysis_settings)
    assert response["status"] == "success"
    assert response["execution"]["rows"] == expected
    event = json.loads(analysis_settings.log_path.read_text(encoding="utf-8"))
    assert event["analysis"] == key
    assert event["model_id"] is None


def test_pareto_uses_all_products_in_cumulative_share_when_truncated(analysis_settings):
    response = run_analysis("pareto", replace(analysis_settings, max_result_rows=1))
    assert response["execution"]["truncated"]
    assert response["execution"]["rows"] == [["Çay", 100.0, 83.33]]


def test_result_chart_requires_a_metric_and_distinguishes_trends():
    chart, _ = result_chart(pd.DataFrame({"Ay": ["2026-02", "2026-01"], "Ciro (TL)": [10, 5]}))
    assert chart.to_dict()["mark"]["type"] == "line"
    chart, _ = result_chart(pd.DataFrame({"Ürün": ["Çay", "Süt"], "Ciro (TL)": [10, 5]}))
    assert chart.to_dict()["mark"]["type"] == "bar"
    assert result_chart(pd.DataFrame({"CustomerID": [1, 2], "Name": ["Ada", "Can"]})) == (None, None)


def test_preset_buttons_render_charts_without_model_access(monkeypatch, analysis_settings):
    monkeypatch.setattr("src.config.load_settings", lambda: analysis_settings)
    app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"), default_timeout=15).run()
    assert app.selectbox(key="question_model").disabled
    assert any("Coming soon!" in caption.value for caption in app.caption)
    initial_chart_count = len(app.get("vega_lite_chart"))
    for key in ("pareto", "basket", "segment"):
        app.button(key=f"analysis_{key}").click().run()
        assert not app.exception
        assert len(app.get("vega_lite_chart")) == initial_chart_count + 1
        assert len(app.dataframe) == 1
    assert len(analysis_settings.log_path.read_text(encoding="utf-8").splitlines()) == 3


def test_sales_summary_combines_filters_and_keeps_zero_months(analysis_settings):
    filters = load_sales_filters(analysis_settings)
    assert (filters.start, filters.end) == (date(2026, 1, 1), date(2026, 4, 1))
    assert set(filters.cities) == {"İzmir", "Ankara"}
    assert set(filters.segments) == {"Bireysel", "KOBİ"}

    summary = summarize_sales(analysis_settings, filters.start, date(2026, 3, 1), "İzmir", "Bireysel")
    assert (summary.revenue, summary.order_count, summary.average_order_value) == (90.0, 2, 45.0)
    assert summary.monthly_revenue == (("2026-01", 70.0), ("2026-02", 20.0), ("2026-03", 0.0))

    empty = summarize_sales(analysis_settings, filters.start, filters.end, "İzmir", "KOBİ")
    assert (empty.revenue, empty.order_count, empty.average_order_value) == (0.0, 0, None)


def test_sales_overview_updates_metrics_and_chart(monkeypatch, analysis_settings):
    monkeypatch.setattr("src.config.load_settings", lambda: analysis_settings)
    app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"), default_timeout=15).run()
    assert not app.exception
    assert [metric.value for metric in app.metric] == ["120,00 TL", "4", "30,00 TL"]
    app.date_input(key="sales_period").set_value((date(2026, 1, 1), date(2026, 1, 1))).run()
    app.selectbox(key="sales_city").set_value("İzmir").run()
    assert not app.exception
    assert [metric.value for metric in app.metric] == ["70,00 TL", "1", "70,00 TL"]
    assert len(app.get("vega_lite_chart")) == 1

    app.selectbox(key="sales_segment").set_value("KOBİ").run()
    assert not app.exception
    assert [metric.value for metric in app.metric] == ["0,00 TL", "0", "—"]
    assert any("filtrelere uyan sipariş bulunamadı" in item.value for item in app.info)
    assert not app.get("vega_lite_chart")
