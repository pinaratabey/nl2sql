"""Satış özeti için filtre seçenekleri ve aylık toplulaştırmalar."""

from dataclasses import dataclass
from datetime import date, timedelta
from math import fsum

from src.config import Settings
from src.database import QueryError, execute_query


FILTER_SQL = """
SELECT 'period' AS kind, MIN(OrderDate) AS first_value, MAX(OrderDate) AS last_value FROM Orders
UNION ALL
SELECT DISTINCT 'city', City, NULL FROM Customers
UNION ALL
SELECT DISTINCT 'segment', Segment, NULL FROM Customers
"""

MONTHLY_SQL = """
SELECT SUBSTR(o.OrderDate, 1, 7) AS sales_month,
       COUNT(DISTINCT o.OrderID) AS order_count,
       COALESCE(SUM(i.Quantity * i.UnitPrice), 0) AS revenue
FROM Orders AS o
JOIN Customers AS c ON c.CustomerID = o.CustomerID
LEFT JOIN OrderItems AS i ON i.OrderID = o.OrderID
WHERE o.OrderDate BETWEEN ? AND ?
    AND (? IS NULL OR c.City = ?)
    AND (? IS NULL OR c.Segment = ?)
GROUP BY SUBSTR(o.OrderDate, 1, 7)
ORDER BY sales_month
"""


@dataclass(frozen=True)
class SalesFilters:
    start: date
    end: date
    cities: tuple[str, ...]
    segments: tuple[str, ...]


@dataclass(frozen=True)
class SalesSummary:
    revenue: float
    order_count: int
    average_order_value: float | None
    monthly_revenue: tuple[tuple[str, float], ...]


def load_sales_filters(settings: Settings) -> SalesFilters | None:
    result = execute_query(FILTER_SQL, settings.database_path, settings.query_timeout_seconds)
    if result["truncated"]:
        raise QueryError("sales_filter_limit", "Satış özeti filtre seçenekleri okunamadı.")
    options = {"city": [], "segment": []}
    for kind, first, last in result["rows"]:
        if kind == "period":
            if first is None:
                return None
            start, end = date.fromisoformat(first), date.fromisoformat(last)
        else:
            options[kind].append(first)
    return SalesFilters(start, end, tuple(sorted(options["city"])), tuple(sorted(options["segment"])))


def summarize_sales(
    settings: Settings, start: date, end: date, city: str | None = None, segment: str | None = None,
) -> SalesSummary:
    if start > end:
        raise ValueError("Başlangıç tarihi bitiş tarihinden sonra olamaz.")
    result = execute_query(
        MONTHLY_SQL, settings.database_path, settings.query_timeout_seconds,
        parameters=(start.isoformat(), end.isoformat(), city, city, segment, segment),
    )
    if result["truncated"]:
        raise QueryError("sales_period_limit", "Satış özeti için daha kısa bir tarih aralığı seçin.")
    rows = result["rows"]
    revenue = fsum(amount for _, _, amount in rows)
    order_count = sum(count for _, count, _ in rows)
    revenue_by_month = {month: round(amount, 2) for month, _, amount in rows}
    monthly = []
    month, last_month = start.replace(day=1), end.replace(day=1)
    while True:
        label = month.isoformat()[:7]
        monthly.append((label, revenue_by_month.get(label, 0.0)))
        if month == last_month:
            break
        month = (month + timedelta(days=32)).replace(day=1)
    return SalesSummary(
        round(revenue, 2), order_count, round(revenue / order_count, 2) if order_count else None, tuple(monthly),
    )
