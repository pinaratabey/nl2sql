"""Deterministik sentetik veri üretir. Var olan DB'nin üzerine yazmaz."""
import argparse
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = 20260630
FIRST_NAMES = ["Ayşe", "Mehmet", "Fatma", "Mustafa", "Zeynep", "Ahmet", "Elif", "Ali", "Emine", "Hüseyin", "Hatice", "Hasan", "Meryem", "İbrahim", "Özlem", "Murat", "Derya", "Emre", "Selin", "Can", "Esra", "Burak", "Ebru", "Oğuz", "İrem", "Onur", "Ceren", "Uğur", "Pınar", "Serkan"]
LAST_NAMES = ["Yılmaz", "Kaya", "Demir", "Çelik", "Şahin", "Yıldız", "Yıldırım", "Öztürk", "Aydın", "Arslan"]
# Örnek perakende fiyatları (TL); güncel piyasa fiyatı iddiası taşımaz.
CATALOG = {
    "Temel Gıda": [("Baldo Pirinç 1 kg", 89.90), ("Pilavlık Bulgur 1 kg", 39.90), ("Kırmızı Mercimek 1 kg", 59.90), ("Nohut 1 kg", 79.90), ("Kuru Fasulye 1 kg", 89.90), ("Burgu Makarna 500 g", 24.90), ("Buğday Unu 2 kg", 54.90), ("Toz Şeker 1 kg", 44.90), ("Ayçiçek Yağı 1 L", 84.90), ("Domates Salçası 830 g", 69.90)],
    "Süt ve Kahvaltılık": [("Tam Yağlı Süt 1 L", 39.90), ("Yarım Yağlı Süt 1 L", 36.90), ("Yoğurt 1 kg", 64.90), ("Beyaz Peynir 500 g", 119.90), ("Taze Kaşar Peyniri 400 g", 139.90), ("Tereyağı 250 g", 109.90), ("Yumurta 10'lu", 69.90), ("Siyah Zeytin 500 g", 99.90), ("Çiçek Balı 450 g", 149.90), ("Çilek Reçeli 380 g", 59.90)],
    "İçecek": [("Doğal Kaynak Suyu 1,5 L", 14.90), ("Maden Suyu 6 x 200 ml", 49.90), ("Portakal Suyu 1 L", 54.90), ("Vişne Nektarı 1 L", 49.90), ("Kola 1 L", 44.90), ("Limonata 1 L", 39.90), ("Şeftalili Soğuk Çay 1 L", 34.90), ("Siyah Çay 500 g", 109.90), ("Türk Kahvesi 100 g", 64.90), ("Ayran 1 L", 34.90)],
    "Atıştırmalık": [("Sütlü Çikolata 80 g", 39.90), ("Bitter Çikolata 80 g", 44.90), ("Fındıklı Gofret 40 g", 14.90), ("Yulaflı Bisküvi 125 g", 24.90), ("Tuzlu Kraker 100 g", 19.90), ("Patates Cipsi 150 g", 49.90), ("Kavrulmuş Fındık 150 g", 99.90), ("Antep Fıstığı 150 g", 149.90), ("Çekirdek 150 g", 34.90), ("Kakaolu Kek 200 g", 39.90)],
    "Ev Temizliği": [("Sıvı Çamaşır Deterjanı 1,5 L", 149.90), ("Toz Çamaşır Deterjanı 3 kg", 199.90), ("Bulaşık Deterjanı 750 ml", 54.90), ("Bulaşık Makinesi Tableti 30'lu", 179.90), ("Yüzey Temizleyici 1 L", 49.90), ("Çamaşır Suyu 1 L", 39.90), ("Cam Temizleyici 500 ml", 34.90), ("Çamaşır Yumuşatıcısı 1,5 L", 79.90), ("Kağıt Havlu 6'lı", 89.90), ("Tuvalet Kağıdı 12'li", 129.90)],
    "Kişisel Bakım": [("Şampuan 400 ml", 89.90), ("Saç Kremi 350 ml", 79.90), ("Duş Jeli 500 ml", 74.90), ("Sıvı El Sabunu 500 ml", 39.90), ("Katı Sabun 4 x 90 g", 49.90), ("Diş Macunu 75 ml", 59.90), ("Diş Fırçası 2'li", 49.90), ("Islak Mendil 90'lı", 34.90), ("Kağıt Mendil 10'lu", 29.90), ("Deodorant 150 ml", 99.90)],
}


def customer_name(customer_id: int) -> str:
    index = customer_id - 1
    return f"{FIRST_NAMES[index % len(FIRST_NAMES)]} {LAST_NAMES[index // len(FIRST_NAMES)]}"


DDL = """
CREATE TABLE Customers (
 CustomerID INTEGER PRIMARY KEY, Name TEXT NOT NULL, City TEXT NOT NULL,
 Segment TEXT NOT NULL CHECK(Segment IN ('Bireysel', 'KOBİ', 'Kurumsal')));
CREATE TABLE Products (
 ProductID INTEGER PRIMARY KEY, ProductName TEXT NOT NULL, Category TEXT NOT NULL,
 Price REAL NOT NULL CHECK(Price > 0));
CREATE TABLE Orders (
 OrderID INTEGER PRIMARY KEY, CustomerID INTEGER NOT NULL REFERENCES Customers(CustomerID),
 OrderDate TEXT NOT NULL CHECK(OrderDate BETWEEN '2025-07-01' AND '2026-06-30'));
CREATE TABLE OrderItems (
 OrderItemID INTEGER PRIMARY KEY, OrderID INTEGER NOT NULL REFERENCES Orders(OrderID),
 ProductID INTEGER NOT NULL REFERENCES Products(ProductID),
 Quantity INTEGER NOT NULL CHECK(Quantity > 0), UnitPrice REAL NOT NULL CHECK(UnitPrice > 0));
CREATE INDEX idx_orders_customer ON Orders(CustomerID);
CREATE INDEX idx_orders_date ON Orders(OrderDate);
CREATE INDEX idx_items_order ON OrderItems(OrderID);
CREATE INDEX idx_items_product ON OrderItems(ProductID);
"""


def create_dataset(path: Path, seed: int = SEED) -> dict:
    rng = random.Random(seed)
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidental replacement of existing data.
    with path.open("xb"):
        pass
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.executescript(DDL)
        cities = ["İzmir", "İstanbul", "Ankara", "Bursa", "Antalya", "Konya", "Adana", "Eskişehir"]
        segments = ["Bireysel", "KOBİ", "Kurumsal"]
        categories = list(CATALOG)
        customers = [(i, customer_name(i), cities[(i-1) % 8], segments[(i-1) % 3]) for i in range(1, 301)]
        products = []
        for i in range(1, 61):
            category = categories[(i-1) % len(categories)]
            name, price = CATALOG[category][(i-1) // len(categories)]
            rng.randint(2500, 250000)  # Siparişlerin sabit seed dağılımını koru.
            products.append((i, name, category, price))
        connection.executemany("INSERT INTO Customers VALUES (?, ?, ?, ?)", customers)
        connection.executemany("INSERT INTO Products VALUES (?, ?, ?, ?)", products)
        boundary_dates = ["2025-07-01", "2026-01-01", "2026-03-31", "2026-04-01", "2026-04-02", "2026-05-31", "2026-06-01", "2026-06-30"]
        orders, items = [], []
        for order_id in range(1, 2401):
            when = boundary_dates[order_id-1] if order_id <= len(boundary_dates) else (date(2025, 7, 1) + timedelta(days=rng.randrange(365))).isoformat()
            # IDs 271-300 intentionally have no orders; first 270 all have at least one.
            customer = order_id if order_id <= 270 else rng.randint(1, 270)
            orders.append((order_id, customer, when))
            for product_id in rng.sample(range(1, 61), rng.randint(2, 5)):
                price_cents = round(products[product_id-1][3] * 100)
                sold_cents = price_cents * rng.choice([85, 90, 95, 100, 105]) // 100
                items.append((len(items)+1, order_id, product_id, rng.randint(1, 8), sold_cents / 100))
        connection.executemany("INSERT INTO Orders VALUES (?, ?, ?)", orders)
        connection.executemany("INSERT INTO OrderItems VALUES (?, ?, ?, ?, ?)", items)
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Yabancı anahtar doğrulaması başarısız.")
        connection.commit()
        return {"seed": seed, "Customers": len(customers), "Products": len(products), "Orders": len(orders), "OrderItems": len(items)}
    finally:
        connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data/analytics.db")
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    try:
        print(create_dataset(args.output, args.seed))
    except FileExistsError:
        parser.exit(1, "Veritabanı zaten var; üzerine yazılmadı. Yeni bir --output yolu seçin.\n")
