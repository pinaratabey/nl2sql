"""Tablo sonuçlarını yeniden sorgulamadan Altair grafikleri oluşturur."""

import re

import altair as alt
import pandas as pd


BAR_COLOR = "#36cfc2"
LINE_COLOR = "#f8bd63"
CATEGORY_LIMIT = 20


def _bar_chart(data, dimension, metric, tooltips=None):
    return (
        alt.Chart(data)
        .mark_bar(color=BAR_COLOR, cornerRadiusEnd=4)
        .encode(
            x=alt.X("value:Q", title=metric),
            y=alt.Y("label:N", title=dimension, sort=data["label"].tolist(),
                    axis=alt.Axis(labelLimit=275, labelOverlap=False)),
            tooltip=tooltips or [
                alt.Tooltip("label:N", title=dimension),
                alt.Tooltip("value:Q", title=metric, format=",.2f"),
            ],
        )
        .properties(height=max(130, len(data) * 22))
    )


def _line_chart(data, x, dimension, metric):
    return alt.Chart(data).mark_line(color=BAR_COLOR, strokeWidth=3, point=True).encode(
        x=x,
        y=alt.Y("value:Q", title=metric),
        tooltip=[
            alt.Tooltip("label:N", title=dimension),
            alt.Tooltip("value:Q", title=metric, format=",.2f"),
        ],
    ).properties(height=270)


def monthly_revenue_chart(monthly_revenue):
    data = pd.DataFrame(monthly_revenue, columns=["month", "value"])
    data["label"] = pd.to_datetime(data["month"], format="%Y-%m").dt.strftime("%m.%Y")
    x = alt.X("label:O", title="Ay", sort=data["label"].tolist(), axis=alt.Axis(labelAngle=0))
    return _line_chart(data, x, "Ay", "Ciro (TL)")


def _pareto_chart(frame):
    data = pd.DataFrame({
        "rank": range(1, len(frame) + 1),
        "product": frame["Ürün"],
        "revenue": frame["Ciro (TL)"],
        "share": frame["Birikimli ciro payı (%)"],
    })
    rank_ticks = data["rank"].tolist() if len(data) <= 20 else [1, *range(10, len(data) + 1, 10)]
    base = alt.Chart(data).encode(
        x=alt.X("rank:O", title="Ciroya göre ürün sırası",
                axis=alt.Axis(values=rank_ticks, labelAngle=0)),
        tooltip=[
            alt.Tooltip("rank:O", title="Sıra"),
            alt.Tooltip("product:N", title="Ürün"),
            alt.Tooltip("revenue:Q", title="Ciro (TL)", format=",.2f"),
            alt.Tooltip("share:Q", title="Birikimli ciro payı (%)", format=".2f"),
        ],
    )
    revenue = base.mark_bar(color=BAR_COLOR, cornerRadiusEnd=2).encode(
        y=alt.Y("revenue:Q", title="Ciro (TL)", axis=alt.Axis(titleColor=BAR_COLOR)),
    )
    percentage = alt.Scale(domain=[0, 100])
    share_axis = alt.Axis(orient="right", titleColor=LINE_COLOR, grid=False, labelExpr="datum.label + '%'")
    cumulative = base.mark_line(color=LINE_COLOR, strokeWidth=3, point=len(data) <= 20).encode(
        y=alt.Y("share:Q", title="Birikimli ciro payı (%)", scale=percentage,
                axis=share_axis),
    )
    threshold = alt.Chart(pd.DataFrame({"target": [80]})).mark_rule(
        color=LINE_COLOR, opacity=0.65, strokeDash=[5, 5],
    ).encode(
        y=alt.Y("target:Q", title="Birikimli ciro payı (%)", scale=percentage, axis=share_axis),
        tooltip=alt.Tooltip("target:Q", title="Pareto eşiği (%)"),
    )
    return alt.layer(revenue, alt.layer(threshold, cumulative)).resolve_scale(y="independent").properties(height=300)


def _basket_chart(frame):
    data = pd.DataFrame({
        "label": frame["Ürün 1"] + " + " + frame["Ürün 2"],
        "value": frame["Birlikte sipariş"],
        "support": frame["Destek (%)"],
        "lift": frame["Lift"],
    })
    return _bar_chart(data, "Ürün çifti", "Birlikte sipariş", [
        alt.Tooltip("label:N", title="Ürün çifti"),
        alt.Tooltip("value:Q", title="Birlikte sipariş", format=",d"),
        alt.Tooltip("support:Q", title="Destek (%)", format=".2f"),
        alt.Tooltip("lift:Q", title="Lift", format=".2f"),
    ])


def result_chart(frame, analysis_key=None):
    if analysis_key == "pareto":
        return _pareto_chart(frame), "Kesik çizgi toplam cironun %80 eşiğini gösterir."
    if analysis_key == "basket":
        return _basket_chart(frame), "Destek, çiftin tüm siparişlerde görülme oranıdır. Lift 1’in üzerindeyse çift, bağımsız satın alma varsayımına göre beklenenden daha sık görülür."
    if len(frame) < 2:
        return None, None

    metrics = [
        column for column in frame.select_dtypes(include="number")
        if not re.search(r"id\b|kimlik", column, flags=re.IGNORECASE)
        and frame[column].notna().sum() >= 2
    ]
    if not metrics:
        return None, None
    metric = metrics[0]
    dimensions = [
        column for column in frame.select_dtypes(exclude="number")
        if frame[column].notna().all() and frame[column].is_unique
    ]
    for dimension in dimensions:
        labels = frame[dimension].astype(str)
        if labels.str.fullmatch(r"\d{4}-\d{2}(-\d{2})?").all():
            dates = pd.to_datetime(labels, format="ISO8601", errors="coerce")
            if dates.notna().all() and dates.is_unique:
                data = pd.DataFrame({"date": dates, "label": labels, "value": frame[metric]}).dropna()
                return _line_chart(data, alt.X("date:T", title=dimension), dimension, metric), None
    if not dimensions:
        return None, None

    dimension = dimensions[0]
    data = pd.DataFrame({"label": frame[dimension].astype(str), "value": frame[metric]}).dropna()
    note = f"Grafikte ilk {CATEGORY_LIMIT} kategori gösteriliyor." if len(data) > CATEGORY_LIMIT else None
    return _bar_chart(data.head(CATEGORY_LIMIT), dimension, metric), note
