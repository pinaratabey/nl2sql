# Test raporu

Ödevin 16 kabul testi henüz çalıştırılmadı. Ortam kontrolleri kabul testi veya canlı model başarısı sayılmaz. Sonuçlar ana planın günlük kaydına işlenecek.

02.11.2026: Geliştirme kontrolleri **4 passed** (pytest). Yeni test sentetik verinin bütünlüğü ve tekrar üretilebilirliğini kapsar. 16 kabul testi henüz çalıştırılmadı; canlı model başarısı raporlanmadı.

## Gemini canlı bağlantı denemesi - 02.11.2026

- Model: `gemini-3.8-flash`; soru: “En yüksek ciroya sahip 5 ürün hangisi?”
- Metadata HTTP 200; generateContent desteği doğrulandı.
- Üretim: 60 saniye, 120 saniye ve LOW düşünme düzeyiyle 60 saniyelik ayrı manuel tanı denemeleri zaman aşımına uğradı. Sandbox içindeki ilk bağlantı ayrıca ağ hatası verdi.
- **Canlı SQL çıktısı alınamadı.** SQL yürütülmedi; 16 kabul testi çalıştırılmadı. Başarılı model sonucu raporlanmıyor.
- İstemci ve hata akışları dahil geliştirme testleri: **6 passed**; model birim testleri mock kullanır.
- Sonraki kontrol: aynı model/anahtarla AI Studio'da kısa bir istemi deneyerek servis/hesap durumunu karşılaştırmak; ardından `--live-smoke` komutunu tekrar çalıştırmak. Hesap kotası veya faturalandırma bu çalışmada değiştirilmedi.

## API teşhisi - ikinci inceleme

| Kontrol | Sonuç | Süre |
|---|---|---|
| 3.8 Flash, tek kelimelik generateContent isteği | ReadTimeout | 20,54 sn |
| 3.8 Flash, güncel Interactions uç noktası | ReadTimeout | 25,41 sn |
| Aynı anahtar, 3.8 Flash metadata | HTTP 200 | 0,49 sn |
| Geçersiz model adına üretim | HTTP 404 | 0,26 sn |
| Model listesi | HTTP 200 | - |
| 2.5 Flash kısa üretim | HTTP 404 NOT_FOUND | 0,71 sn |

Sonuç: Sorun uzun SQL promptuna indirgenemiyor; kısa istem de timeout veriyor. POST yolu tümüyle kapalı değil, geçersiz modele hemen hata yanıtı alınabiliyor. 2.5 Flash model listesinde görünmesi üretim erişimini kanıtlamıyor. Kesin servis/hesap nedeni henüz saptanamadı. Ek Flash-Lite karşılaştırmasının izin isteği kullanıcı tarafından reddedildi; çağrılar yapılmadı. İlk canlı SQL çıktısı alınmadı; Gün 1 açık kalıyor. Anahtar ve hesap faturalandırması değiştirilmedi.

## İlk başarılı canlı çıktı - 02.11.2026

- Model / dönen sürüm: `gemini-3.5-flash-lite`.
- Soru: “En yüksek ciroya sahip 5 ürün hangisi?”
- Sonuç: Gerçek API yanıtı alındı; `status=ok`, süre **32.591 ms**.
- Prompt: `nl2sql-v1`; SQLite şeması, PK/FK, iş metrikleri ve sabit referans tarihi gönderildi.
- İstek parametreleri: temperature=0, maxOutputTokens=2048, responseMimeType=application/json, thinkingLevel=LOW. Modelin sunucu tarafında örnekleme parametrelerini uyguladığı garanti edilmez; gönderilen değerler kaydedilmiştir.
- Kullanım: 479 giriş + 87 çıktı = 566 token. Bu kullanım kaydı hesap faturalandırmasını doğrulamaz; hesap ayarları değiştirilmedi.
- Ham çıktı, sürüm, parametreler ve zaman damgası `test_results.json` içindeki başarılı `live_smoke_runs` kaydında korunuyor.

```sql
SELECT p.ProductName, SUM(oi.Quantity * oi.UnitPrice) AS TotalRevenue FROM OrderItems oi JOIN Products p ON oi.ProductID = p.ProductID GROUP BY p.ProductID, p.ProductName ORDER BY TotalRevenue DESC LIMIT 5;
```

Ciro ifadesi Quantity * UnitPrice kullanıyor; ürün JOIN'i, azalan ciro sıralaması ve LIMIT 5 mevcut. Bu yalnızca üretilen SQL'in incelemesidir. **SQL yürütülmedi ve sayısal doğruluk kabul testi yapılmadı.** Modelin “listelenmiştir” açıklaması gerçek sonuç tablosu olarak sunulmamalı.

Gün 1 teknik bitiş ölçütleri sağlandı: ortam, yeniden üretilebilir veri, doğrulanmış şema ve ilk canlı model çıktısı hazır. Önceki timeout kayıtları geçmiş teşhis kanıtıdır. Model değişiminden sonra başarılı üretim alındı; önceki modeldeki timeout'un sağlayıcı tarafındaki kesin nedeni bilinmiyor.

## Gün 2 - İlk dört canlı iş testi

Model: `gemini-3.5-flash-lite`. Sentetik veri; mutlak sayısal tolerans 0,01. 01-03 satır sırası karşılaştırılır; 04 kategoriye göre eşleştirilir.

| Test | Sonuç | Süre (ms) | Hata |
|---|---|---|---|
| 01 | FAIL | 13 | model_unavailable |
| 02 | FAIL | 7 | model_unavailable |
| 03 | FAIL | 6 | model_unavailable |
| 04 | FAIL | 6 | model_unavailable |

Veritabanı SHA-256 değişmedi: True. Üretilen/yürütülen SQL, beklenen ve gerçek satırlar ile ham model yanıtları `test_results.json` içindeki `evaluation_first_four` bölümünde. 05-16 canlı kabul testleri henüz çalıştırılmadı.

## Gün 2 - İlk dört canlı iş testi

Model: `gemini-3.5-flash-lite`. Sentetik veri; mutlak sayısal tolerans 0,01. 01-03 satır sırası karşılaştırılır; 04 kategoriye göre eşleştirilir.

| Test | Sonuç | Süre (ms) | Hata |
|---|---|---|---|
| 01 | PASS | 1061 | - |
| 02 | FAIL | 2872 | invalid_model_response |
| 03 | FAIL | 1100 | invalid_model_response |
| 04 | FAIL | 1568 | invalid_model_response |

Veritabanı SHA-256 değişmedi: True. Üretilen/yürütülen SQL, beklenen ve gerçek satırlar ile ham model yanıtları `test_results.json` içindeki `evaluation_first_four` bölümünde. 05-16 canlı kabul testleri henüz çalıştırılmadı.

## Gün 2 - İlk dört canlı iş testi

Model: `gemini-3.5-flash-lite`. Sentetik veri; mutlak sayısal tolerans 0,01. 01-03 satır sırası karşılaştırılır; 04 kategoriye göre eşleştirilir.

| Test | Sonuç | Süre (ms) | Hata |
|---|---|---|---|
| 01 | FAIL | 1250 | invalid_model_response |
| 02 | FAIL | 1220 | invalid_model_response |
| 03 | FAIL | 1545 | invalid_model_response |
| 04 | FAIL | 1432 | invalid_model_response |

Veritabanı SHA-256 değişmedi: True. Üretilen/yürütülen SQL, beklenen ve gerçek satırlar ile ham model yanıtları `test_results.json` içindeki `evaluation_first_four` bölümünde. 05-16 canlı kabul testleri henüz çalıştırılmadı.

## Gün 2 - İlk dört canlı iş testi

Model: `gemini-3.5-flash-lite`. Sentetik veri; mutlak sayısal tolerans 0,01. 01-03 satır sırası karşılaştırılır; 04 kategoriye göre eşleştirilir.

| Test | Sonuç | Süre (ms) | Hata |
|---|---|---|---|
| 01 | PASS | 2720 | - |
| 02 | PASS | 2754 | - |
| 03 | PASS | 1751 | - |
| 04 | PASS | 2362 | - |

Veritabanı SHA-256 değişmedi: True. Üretilen/yürütülen SQL, beklenen ve gerçek satırlar ile ham model yanıtları `test_results.json` içindeki `evaluation_first_four` bölümünde. 05-16 canlı kabul testleri henüz çalıştırılmadı.

### Gün 2 geliştirme ve erken güvenlik kontrolleri

31 pytest testi PASS: SQL/şema/CTE/yorum kontrolleri, yasak işlemler, SQLite savunma katmanı, satır/süre sınırı ve sonuç karşılaştırması. 11-16 senaryolarının doğrudan SQL katmanı kontrolleri 6/6 PASS; DB özeti değişmedi. 11/15 doğal dil model davranışı testleri değildir. Ayrıntılar JSON içindeki `early_security_checks` bölümünde. Geçmişteki başarısız değerlendirmeler tanı kanıtıdır; son canlı değerlendirme ilk dört testte 4/4 PASS.

## Gün 3 arayüz kontrolleri

38 pytest testi PASS (izinli ortamda 2,88 sn). Beş ekran testi AppTest ve servis stub'ı ile başarı, boş sonuç, netleştirme, ret, hata, satır kesilmesi, yeniden çizim ve boş gönderimi sınar. Bunlar yeni canlı model kabul testleri değildir; önceki 01-04 canlı sonuçları korunur. Sandbox altında socket kısıtı görüldüğü için ekran testleri izinli ortamda doğrulandı. JSON log ve kalan kabul testleri açık.

## Gün 3 hata/retry/log ve yeni tasarım doğrulaması

49 geliştirme testi PASS (2,93 sn). Yeni servis senaryoları: başarı, boş sonuç, açıklama, ret, olmayan alan, geçersiz SQL, timeout sonrası başarı, iki timeout ile durma, kota hatasında retry olmaması, eksik DB, log redaksiyonu ve log yazılamaması. Beş UI durum testi de geçti. Bunlar mock/stub model kontrolleridir; yeni canlı başarı raporlanmıyor. Güncel prompt nl2sql-v2, 05-10 canlı testleri açık.

## Arctic Reflection arayüz revizyonu

50 geliştirme testi PASS (3,53 sn). Altı hazır soru, soru alanına aktarım, sol panelin kaldırılması ve API çağrısı yapılmadan seçim doğrulandı. Yeni canlı model/kabul testi çalıştırılmadı.

## Seçili canlı kabul testleri: 05, 06, 07, 08, 09, 10

Model: `gemini-3.5-flash-lite`. Sentetik veri; mutlak sayısal tolerans 0,01. Sıra kontrolü her testin ordered alanına göre yapılır.

| Test | Sonuç | Süre (ms) | Hata |
|---|---|---|---|
| 05 | FAIL | 49 | model_unavailable |
| 06 | FAIL | 27 | model_unavailable |
| 07 | FAIL | 34 | model_unavailable |
| 08 | FAIL | 30 | model_unavailable |
| 09 | FAIL | 54 | model_unavailable |
| 10 | FAIL | 39 | model_unavailable |

Veritabanı SHA-256 değişmedi: True. Üretilen/yürütülen SQL, beklenen ve gerçek satırlar ile ham model yanıtları `test_results.json` içindeki `evaluation` bölümünde. Bu çalıştırma yalnızca seçilen testleri kapsar; tüm kabul testlerinin çalıştığı anlamına gelmez.

## Seçili canlı kabul testleri: 05, 06, 07, 08, 09, 10

Model: `gemini-3.5-flash-lite`. Sentetik veri; mutlak sayısal tolerans 0,01. Sıra kontrolü her testin ordered alanına göre yapılır.

| Test | Sonuç | Süre (ms) | Hata |
|---|---|---|---|
| 05 | PASS | 1617 | - |
| 06 | PASS | 2051 | - |
| 07 | PASS | 1981 | - |
| 08 | PASS | 1667 | - |
| 09 | PASS | 1380 | - |
| 10 | PASS | 1678 | - |

Veritabanı SHA-256 değişmedi: True. Üretilen/yürütülen SQL, beklenen ve gerçek satırlar ile ham model yanıtları `test_results.json` içindeki `evaluation` bölümünde. Bu çalıştırma yalnızca seçilen testleri kapsar; tüm kabul testlerinin çalıştığı anlamına gelmez.

### Gün 3 tamamlanma kanıtı

Canlı 05-10: 6/6 PASS, prompt nl2sql-v3. 05 siparişsiz 30 müşteri; 06 üç segment; 07 ilk çeyrek lider şehir; 08 Haziran ilk üç ürün. 09 model ciro/sipariş/metrik seçimini sordu; 10 doğum tarihi alanının bulunmadığını açıkladı. 09-10 SQL üretmedi/yürütmedi. DB değişmedi.

57 geliştirme testi PASS (3,75 sn). Tarih sınırları ayrı küçük veriyle test edildi. Kapalı model HTTP ConnectionError enjeksiyonuyla iki denemede durdu, SQL yürütmedi ve hata loglandı. Bunlar canlı model başarısından ayrı hata/birim testleridir. Önceki 01-04 başarısı eski prompt içindir; v3 altında birleşik regresyon ve 11-16 canlı testleri açık.

## Seçili canlı kabul testleri: 01, 02, 03, 04, 05, 06, 07, 08, 09, 10

Model: `gemini-3.5-flash-lite`. Sentetik veri; mutlak sayısal tolerans 0,01. Sıra kontrolü her testin ordered alanına göre yapılır.

| Test | Sonuç | Süre (ms) | Hata |
|---|---|---|---|
| 01 | PASS | 24882 | - |
| 02 | PASS | 18208 | - |
| 03 | PASS | 26313 | - |
| 04 | PASS | 14223 | - |
| 05 | PASS | 26631 | - |
| 06 | PASS | 27422 | - |
| 07 | PASS | 34588 | - |
| 08 | PASS | 24300 | - |
| 09 | PASS | 26900 | - |
| 10 | PASS | 37276 | - |

Veritabanı SHA-256 değişmedi: True. Üretilen/yürütülen SQL, beklenen ve gerçek satırlar ile ham model yanıtları `test_results.json` içindeki `evaluation` bölümünde. Bu çalıştırma yalnızca seçilen testleri kapsar; tüm kabul testlerinin çalıştığı anlamına gelmez.

## Seçili canlı kabul testleri: 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13, 14, 15, 16

Model: `gemini-3.5-flash-lite`. Sentetik veri; mutlak sayısal tolerans 0,01. Sıra kontrolü her testin ordered alanına göre yapılır.

| Test | Sonuç | Süre (ms) | Hata |
|---|---|---|---|
| 01 | PASS | 78288 | - |
| 02 | PASS | 22214 | - |
| 03 | PASS | 16777 | - |
| 04 | PASS | 23747 | - |
| 05 | PASS | 80378 | - |
| 06 | PASS | 28874 | - |
| 07 | PASS | 31323 | - |
| 08 | FAIL | 61729 | model_unavailable |
| 09 | PASS | 16580 | - |
| 10 | PASS | 22421 | - |
| 11 | PASS | 17510 | - |
| 12 | PASS | 10574 | - |
| 13 | PASS | 19199 | - |
| 14 | FAIL | 20268 | - |
| 15 | PASS | 35933 | - |
| 16 | PASS | 21395 | - |

Veritabanı SHA-256 değişmedi: True. Üretilen/yürütülen SQL, beklenen ve gerçek satırlar ile ham model yanıtları `test_results.json` içindeki `evaluation` bölümünde. Bu çalıştırma yalnızca seçilen testleri kapsar; tüm kabul testlerinin çalıştığı anlamına gelmez.

## Seçili canlı kabul testleri: 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13, 14, 15, 16

Model: `gemini-3.5-flash-lite`. Sentetik veri; mutlak sayısal tolerans 0,01. Sıra kontrolü her testin ordered alanına göre yapılır.

| Test | Sonuç | Süre (ms) | Hata |
|---|---|---|---|
| 01 | PASS | 36295 | - |
| 02 | PASS | 22152 | - |
| 03 | PASS | 17362 | - |
| 04 | PASS | 18515 | - |
| 05 | PASS | 23234 | - |
| 06 | PASS | 19146 | - |
| 07 | PASS | 40737 | - |
| 08 | PASS | 19649 | - |
| 09 | PASS | 23334 | - |
| 10 | PASS | 39742 | - |
| 11 | PASS | 18504 | - |
| 12 | PASS | 17913 | - |
| 13 | PASS | 30399 | - |
| 14 | FAIL | 56514 | - |
| 15 | PASS | 20925 | - |
| 16 | PASS | 15929 | - |

Veritabanı SHA-256 değişmedi: True. Üretilen/yürütülen SQL, beklenen ve gerçek satırlar ile ham model yanıtları `test_results.json` içindeki `evaluation` bölümünde. Bu çalıştırma yalnızca seçilen testleri kapsar; tüm kabul testlerinin çalıştığı anlamına gelmez.

## Seçili canlı kabul testleri: 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13, 14, 15, 16

Model: `gemini-3.5-flash-lite`. Sentetik veri; mutlak sayısal tolerans 0,01. Sıra kontrolü her testin ordered alanına göre yapılır.

| Test | Sonuç | Süre (ms) | Hata |
|---|---|---|---|
| 01 | PASS | 31822 | - |
| 02 | PASS | 18719 | - |
| 03 | PASS | 24689 | - |
| 04 | PASS | 17602 | - |
| 05 | PASS | 25535 | - |
| 06 | PASS | 17964 | - |
| 07 | PASS | 14697 | - |
| 08 | PASS | 14595 | - |
| 09 | PASS | 13944 | - |
| 10 | PASS | 16852 | - |
| 11 | PASS | 18676 | - |
| 12 | PASS | 18350 | - |
| 13 | PASS | 15407 | - |
| 14 | FAIL | 14077 | - |
| 15 | PASS | 14435 | - |
| 16 | PASS | 15167 | - |

Veritabanı SHA-256 değişmedi: True. Üretilen/yürütülen SQL, beklenen ve gerçek satırlar ile ham model yanıtları `test_results.json` içindeki `evaluation` bölümünde. Bu çalıştırma yalnızca seçilen testleri kapsar; tüm kabul testlerinin çalıştığı anlamına gelmez.

## Seçili canlı kabul testleri: 14

Model: `gemini-3.5-flash-lite`. Sentetik veri; mutlak sayısal tolerans 0,01. Sıra kontrolü her testin ordered alanına göre yapılır.

| Test | Sonuç | Süre (ms) | Hata |
|---|---|---|---|
| 14 | FAIL | 1369 | - |

Veritabanı SHA-256 değişmedi: True. Üretilen/yürütülen SQL, beklenen ve gerçek satırlar ile ham model yanıtları `test_results.json` içindeki `evaluation` bölümünde. Bu çalıştırma yalnızca seçilen testleri kapsar; tüm kabul testlerinin çalıştığı anlamına gelmez.

## Seçili canlı kabul testleri: 14

Model: `gemini-3.5-flash-lite`. Sentetik veri; mutlak sayısal tolerans 0,01. Sıra kontrolü her testin ordered alanına göre yapılır.

| Test | Sonuç | Süre (ms) | Hata |
|---|---|---|---|
| 14 | FAIL | 12915 | - |

Veritabanı SHA-256 değişmedi: True. Üretilen/yürütülen SQL, beklenen ve gerçek satırlar ile ham model yanıtları `test_results.json` içindeki `evaluation` bölümünde. Bu çalıştırma yalnızca seçilen testleri kapsar; tüm kabul testlerinin çalıştığı anlamına gelmez.

## Seçili canlı kabul testleri: 14

Model: `gemini-3.5-flash-lite`. Sentetik veri; mutlak sayısal tolerans 0,01. Sıra kontrolü her testin ordered alanına göre yapılır.

| Test | Sonuç | Süre (ms) | Hata |
|---|---|---|---|
| 14 | FAIL | 30872 | - |

Veritabanı SHA-256 değişmedi: True. Üretilen/yürütülen SQL, beklenen ve gerçek satırlar ile ham model yanıtları `test_results.json` içindeki `evaluation` bölümünde. Bu çalıştırma yalnızca seçilen testleri kapsar; tüm kabul testlerinin çalıştığı anlamına gelmez.

## Seçili canlı kabul testleri: 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13, 14, 15, 16

Model: `gemini-3.5-flash-lite`. Sentetik veri; mutlak sayısal tolerans 0,01. Sıra kontrolü her testin ordered alanına göre yapılır.

| Test | Sonuç | Süre (ms) | Hata |
|---|---|---|---|
| 01 | PASS | 18299 | - |
| 02 | PASS | 27070 | - |
| 03 | FAIL | 68514 | model_unavailable |
| 04 | PASS | 21498 | - |
| 05 | PASS | 26425 | - |
| 06 | PASS | 12451 | - |
| 07 | PASS | 17183 | - |
| 08 | PASS | 10532 | - |
| 09 | PASS | 16561 | - |
| 10 | PASS | 38995 | - |
| 11 | PASS | 14829 | - |
| 12 | PASS | 16472 | - |
| 13 | PASS | 24039 | - |
| 14 | PASS | 10740 | - |
| 15 | PASS | 25574 | - |
| 16 | PASS | 12985 | - |

Veritabanı SHA-256 değişmedi: True. Üretilen/yürütülen SQL, beklenen ve gerçek satırlar ile ham model yanıtları `test_results.json` içindeki `evaluation` bölümünde. Bu çalıştırma yalnızca seçilen testleri kapsar; tüm kabul testlerinin çalıştığı anlamına gelmez.

## Seçili canlı kabul testleri: 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13, 14, 15, 16

Model: `gemini-3.5-flash-lite`. Sentetik veri; mutlak sayısal tolerans 0,01. Sıra kontrolü her testin ordered alanına göre yapılır.

| Test | Sonuç | Süre (ms) | Hata |
|---|---|---|---|
| 01 | PASS | 16374 | - |
| 02 | PASS | 13984 | - |
| 03 | PASS | 15959 | - |
| 04 | PASS | 10220 | - |
| 05 | PASS | 21795 | - |
| 06 | PASS | 15961 | - |
| 07 | PASS | 22297 | - |
| 08 | PASS | 1311 | - |
| 09 | PASS | 12262 | - |
| 10 | PASS | 13393 | - |
| 11 | PASS | 14108 | - |
| 12 | PASS | 21483 | - |
| 13 | PASS | 13086 | - |
| 14 | PASS | 13700 | - |
| 15 | PASS | 14825 | - |
| 16 | PASS | 39504 | - |

Veritabanı SHA-256 değişmedi: True. Üretilen/yürütülen SQL, beklenen ve gerçek satırlar ile ham model yanıtları `test_results.json` içindeki `evaluation` bölümünde. Bu çalıştırma yalnızca seçilen testleri kapsar; tüm kabul testlerinin çalıştığı anlamına gelmez.
