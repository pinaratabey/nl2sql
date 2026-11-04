# Veri şeması ve hızlı tüketim (FMCG) veri seti

Bu veri kullanıcı isteğiyle yerel olarak üretilmiştir; öğreticinin resmî veri seti değildir. Gerçek kişi veya şirket kaydı içermez.

Müşteriler Ayşe Yılmaz, Mehmet Kaya ve Pınar Demir gibi doğal Türkçe ad ve soyadlarla temsil edilir. Bireysel segmentinde tüketiciyi, KOBİ ve Kurumsal segmentlerinde işletmenin irtibat kişisini gösterir. 300 farklı ad-soyad bileşimi kullanılır.

60 ambalajlı ürün, Temel Gıda, Süt ve Kahvaltılık, İçecek, Atıştırmalık, Ev Temizliği ve Kişisel Bakım kategorilerine ayrılır. Ürün adları ambalaj miktarını içerir; Quantity bu ambalajdan kaç adet satıldığını belirtir. Fiyatlar TL cinsinden örnek perakende fiyatlarıdır; güncel piyasa fiyatlarını temsil etmez.

## Üretim ve yeniden kurulum

- Betik: `scripts/setup_db.py`; yalnızca Python standart kütüphanesini kullanır.
- Sabit seed: `20260630`. Aynı seed aynı mantıksal veriyi üretir.
- İlk kurulum: `.\.venv\Scripts\python.exe scripts/setup_db.py`.
- Mevcut dosyanın üzerine yazılmaz. Yeniden üretim için `--output data/analytics_rebuilt.db` kullanın; ardından DATABASE_PATH ayarını bu dosyaya yönlendirin.
- Veri tabanı binary dosyası Git dışında; tekrar üretme betiği sürümlenir.

## Doğrulanmış şema

### Customers - 300 kayıt

| Sütun | SQLite tipi | PK | Zorunlu |
|---|---|---|---|
| CustomerID | INTEGER | Evet | Evet |
| Name | TEXT | - | Evet |
| City | TEXT | - | Evet |
| Segment | TEXT | - | Evet |


### OrderItems - 8395 kayıt

| Sütun | SQLite tipi | PK | Zorunlu |
|---|---|---|---|
| OrderItemID | INTEGER | Evet | Evet |
| OrderID | INTEGER | - | Evet |
| ProductID | INTEGER | - | Evet |
| Quantity | INTEGER | - | Evet |
| UnitPrice | REAL | - | Evet |

- FK: `OrderItems.ProductID → Products.ProductID`
- FK: `OrderItems.OrderID → Orders.OrderID`

### Orders - 2400 kayıt

| Sütun | SQLite tipi | PK | Zorunlu |
|---|---|---|---|
| OrderID | INTEGER | Evet | Evet |
| CustomerID | INTEGER | - | Evet |
| OrderDate | TEXT | - | Evet |

- FK: `Orders.CustomerID → Customers.CustomerID`

### Products - 60 kayıt

| Sütun | SQLite tipi | PK | Zorunlu |
|---|---|---|---|
| ProductID | INTEGER | Evet | Evet |
| ProductName | TEXT | - | Evet |
| Category | TEXT | - | Evet |
| Price | REAL | - | Evet |


## Test kapsamını destekleyen dağılımlar

- 8 şehir (İzmir dahil), 3 segment, 6 kategori.
- 270 müşterinin siparişi var; 30 müşterinin hiç siparişi yok.
- Tarihler 2025-07-01 ile 2026-06-30 arasında; 12 ayın tamamında sipariş var.
- 2026-01-01, 03-31, 04-01, 04-02, 05-31, 06-01 ve 06-30 sınırlarında kayıt var.
- Sipariş başına 2-5 farklı ürün, kalem başına 1-8 adet.
- Satış fiyatları liste fiyatının %85, %90, %95, %100 veya %105 düzeyinden kuruşa indirilerek hesaplanır; ciroda UnitPrice kullanılmasını sınar.
- Parasal alanlar REAL tutulur; sonuç karşılaştırmasında uygun yuvarlama/tolerans tanımlanmalıdır.

## Şema çıkarım yöntemi

`src/schema.py` salt-okunur bağlantıda güvenilir metadata erişimiyle tablo varlığını, `PRAGMA table_info` ile sütun/tip/PK, `PRAGMA foreign_key_list` ile FK bilgilerini çıkarır. Bunlar uygulama içi sabit metadata sorgularıdır; kullanıcı veya model SQL yoluna PRAGMA yetkisi vermez. `schema_context` çıktısı LLM promptuna aktarılmaya hazırdır.

```text
Customers(CustomerID INTEGER PK, Name TEXT, City TEXT, Segment TEXT)
OrderItems(OrderItemID INTEGER PK, OrderID INTEGER, ProductID INTEGER, Quantity INTEGER, UnitPrice REAL)
FK: OrderItems.ProductID -> Products.ProductID
FK: OrderItems.OrderID -> Orders.OrderID
Orders(OrderID INTEGER PK, CustomerID INTEGER, OrderDate TEXT)
FK: Orders.CustomerID -> Customers.CustomerID
Products(ProductID INTEGER PK, ProductName TEXT, Category TEXT, Price REAL)
```

## İş kuralları

Metrikler ve sabit tarih aralıkları [ayrıntılı gereksinimlerde](../PROJE_DETAYLARI.md#veri) tanımlıdır. Referans tarihi 2026-06-30 olarak kalır. Sentetik veriyle alınan sonuçlar resmî veri setindeki sayısal sonuçlarla aynı olmak zorunda değildir.
