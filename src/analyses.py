"""Kullanıcının doğrudan çalıştırabileceği sabit satış analizleri."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Analysis:
    title: str
    description: str
    icon: str
    sql: str


ANALYSES = {
    "pareto": Analysis(
        "Pareto analizi",
        "Hangi ürünler toplam cironun büyük bölümünü oluşturuyor?",
        ":material/stacked_bar_chart:",
        """
        WITH product_revenue AS (
            SELECT p.ProductID, p.ProductName, SUM(i.Quantity * i.UnitPrice) AS Revenue
            FROM OrderItems AS i JOIN Products AS p ON i.ProductID = p.ProductID
            GROUP BY p.ProductID, p.ProductName
        )
        SELECT ProductName AS "Ürün", ROUND(Revenue, 2) AS "Ciro (TL)",
               ROUND(100.0 * SUM(Revenue) OVER (
                   ORDER BY Revenue DESC, ProductID ROWS UNBOUNDED PRECEDING
               ) / NULLIF(SUM(Revenue) OVER (), 0), 2) AS "Birikimli ciro payı (%)"
        FROM product_revenue
        ORDER BY Revenue DESC, ProductID
        """,
    ),
    "basket": Analysis(
        "Sepet analizi",
        "Aynı siparişte en sık birlikte alınan 15 ürün çifti.",
        ":material/shopping_basket:",
        """
        WITH basket_items AS (
            SELECT DISTINCT OrderID, ProductID FROM OrderItems
        ), product_counts AS (
            SELECT ProductID, COUNT(*) AS OrderCount FROM basket_items GROUP BY ProductID
        ), pair_counts AS (
            SELECT a.ProductID AS FirstProduct, b.ProductID AS SecondProduct, COUNT(*) AS PairCount
            FROM basket_items AS a
            JOIN basket_items AS b ON a.OrderID = b.OrderID AND a.ProductID < b.ProductID
            GROUP BY a.ProductID, b.ProductID
        ), order_total AS (
            SELECT COUNT(*) AS TotalOrders FROM Orders
        )
        SELECT p1.ProductName AS "Ürün 1", p2.ProductName AS "Ürün 2",
               pairs.PairCount AS "Birlikte sipariş",
               ROUND(100.0 * pairs.PairCount / totals.TotalOrders, 2) AS "Destek (%)",
               ROUND(1.0 * pairs.PairCount * totals.TotalOrders / f.OrderCount / s.OrderCount, 2) AS "Lift"
        FROM pair_counts AS pairs
        JOIN Products AS p1 ON p1.ProductID = pairs.FirstProduct
        JOIN Products AS p2 ON p2.ProductID = pairs.SecondProduct
        JOIN product_counts AS f ON f.ProductID = pairs.FirstProduct
        JOIN product_counts AS s ON s.ProductID = pairs.SecondProduct
        CROSS JOIN order_total AS totals
        ORDER BY pairs.PairCount DESC, pairs.FirstProduct, pairs.SecondProduct
        LIMIT 15
        """,
    ),
    "segment": Analysis(
        "Segment karşılaştırması",
        "Bireysel, KOBİ ve Kurumsal müşteri segmentlerinin cirosu.",
        ":material/groups:",
        """
        SELECT c.Segment AS "Segment", ROUND(SUM(i.Quantity * i.UnitPrice), 2) AS "Ciro (TL)",
               COUNT(DISTINCT o.OrderID) AS "Sipariş adedi"
        FROM Customers AS c
        JOIN Orders AS o ON o.CustomerID = c.CustomerID
        JOIN OrderItems AS i ON i.OrderID = o.OrderID
        GROUP BY c.Segment
        ORDER BY SUM(i.Quantity * i.UnitPrice) DESC, c.Segment
        """,
    ),
}
