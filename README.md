# NL2SQL Agent

ENS-AI-001 için Türkçe doğal dilden güvenli SQLite sorgulamasına yönelik PoC.
Günlük süreç takibi: [PROJE_PLANI.md](PROJE_PLANI.md).
Ayrıntılı gereksinimler ve görevler: [PROJE_DETAYLARI.md](PROJE_DETAYLARI.md).

## Durum

Gün 3 arayüz entegrasyonu hazır; SQL güvenliği ve kontrollü yürütme servise bağlıdır. İlk dört canlı iş testi 4/4 PASS. Model üretimi, AST/şema denetimi ve salt-okunur yürütme servis katmanında çalışır; arayüz soru girişinden bu servisi çağırır. Sentetik veri seti ve şema hazır; gemini-3.5-flash-lite ile ilk canlı SQL yanıtı kaydedildi.

## Kurulum (PowerShell)

Python 3.12 gereklidir. Normal bir Python kurulumunda:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Mevcut bilgisayarda Python komutu Windows Store yönlendirmesi olduğu için ilk sanal ortam Codex'in beraberinde gelen Python 3.12.14 ile oluşturuldu. Proje komutları doğrudan `.venv\Scripts\python.exe` kullanır; aktivasyon gerekmez. Başka bilgisayarda sanal ortam kopyalanmamalı, yeniden oluşturulmalıdır.

## Veri ve model

Kullanıcı isteğiyle 300 müşteri, 60 ürün, 2.400 sipariş ve 8.395 kalemden oluşan, Türkçe müşteri adları ve ambalajlı ürünler içeren hızlı tüketim (FMCG) örnek verisi `data/analytics.db` içine yüklendi. Öğreticinin resmî veri seti değildir. Şema ve dağılımlar: [docs/schema.md](docs/schema.md).

```powershell
.\.venv\Scripts\python.exe scripts/setup_db.py
# Mevcut dosya varsa üzerine yazmaz; alternatif yol:
.\.venv\Scripts\python.exe scripts/setup_db.py --output data/analytics_rebuilt.db
```

Sabit seed 20260630; farklı yol üretildiğinde `.env` içindeki DATABASE_PATH güncellenmeli. Oluşturulmuş DB Git'e eklenmez; betikten tekrar kurulur. Gemini sağlayıcısı seçildi; model `.env` içindeki GEMINI_MODEL değerinden okunur. İlk başarılı canlı istek (32,6 saniye) günlük takipte ve test raporunda kayıtlıdır. Seçenekler ve donanım bilgisi [docs/design.md](docs/design.md) içinde. Referans tarih `2026-06-30` olarak sabittir.

## Kontroller

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
```

Temel ortam testleri sabit referans tarihini, eksik DB'nin yanlışlıkla oluşturulmamasını, salt-okunur bağlantıyı ve sentetik verinin bütünlük/tekrar üretilebilirliğini kontrol eder. İlk dört kabul testi hazır ve canlı çalıştırıldı; tam 16 test henüz bitmedi. Geliştirme testlerinin güncel sayısı 31.

## Dosyaların sorumlulukları

`src/config.py`: ayarlar; `schema.py`: şema; `llm.py`: model/prompt; `sql_security.py`: doğrulama; `database.py`: bağlantı/yürütme; `service.py`: uygulama akışı ve loglar. Tasarım `docs/design.md` dosyasında tutulur. Demo metni ve örnek log açıklamaları da ilgili mevcut belgelere eklenecek.

## Gemini bağlantısı

`.env` içine GEMINI_API_KEY ve GEMINI_MODEL ekleyin; anahtarı `.env.example` veya Git'e koymayın. İstemci REST generateContent uç noktasını kullanır; yalnızca şema, iş tanımları ve soru gönderilir, veri satırları gönderilmez. API anahtarı HTTP başlığında taşınır. Temperature 0, en fazla 2048 çıktı tokenı, JSON yanıt ve yapılandırılabilir süre sınırı kullanılır; otomatik yeniden deneme yapılmaz.

```powershell
.\.venv\Scripts\python.exe scripts/run_evaluation.py --live-smoke
```

Bu komut SQL **üretir, çalıştırmaz**. Başarılı canlı kayıt `reports/test_results.json` içindeki `live_smoke_runs` listesine eklenir; 16 kabul testinin durumu ayrı kalır. Model/kota/erişim hataları sınıflandırılmış mesajlarla gösterilir. HTTP hata gövdeleri ve anahtar loglanmaz.

## Canlı iş testlerini seçerek çalıştırma

```powershell
.\.venv\Scripts\python.exe scripts/run_evaluation.py --cases 01-04
```

Bu komut dört gerçek API isteği gönderir, SQL'i güvenlik katmanından geçirip salt-okunur çalıştırır ve bağımsız referans sonuçlarla karşılaştırır. Sonuçlar `reports/test_results.json` ve `reports/test_report.md` içinde tutulur; önceki değerlendirmeler JSON geçmişinde korunur. Anahtar raporlara yazılmaz. SQL guard kontrolleri: tek SELECT, izinli tablo/sütunlar, alt sorgu/CTE denetimi, yorum ayrıştırma ve fonksiyon kısıtlaması. Yürütmede authorizer, varsayılan 5 saniye, 500 satır ve kesilme bildirimi vardır. Güvenilir metadata erişimi kullanıcı SQL yolundan ayrıdır.

Test seçimi örnekleri:

```powershell
# Tek test
.\.venv\Scripts\python.exe scripts/run_evaluation.py --cases 02
# Belirli testler
.\.venv\Scripts\python.exe scripts/run_evaluation.py --cases 01,04
# Aralık veya karma seçim
.\.venv\Scripts\python.exe scripts/run_evaluation.py --cases 01-03,04
# Dosyada tanımlı tüm testler (şu an 01-10)
.\.venv\Scripts\python.exe scripts/run_evaluation.py --all
```

Python karşılığı: `evaluate_cases(settings, case_ids=["01", "04"])`; `case_ids=None` tüm tanımlı testleri seçer. Seçim sırası korunur, tekrarlar kaldırılır. Tanımsız test veya hatalı aralık API çağrısından önce reddedilir. `--first-four`, `--cases 01-04` ile aynı eski kısayoldur. Çalıştırma modları birlikte kullanılamaz.

Yeni raporlar JSON içindeki `evaluation` bölümüne yazılır; seçilen kimlikler ve tamamlanma bilgisi kaydedilir. Önceki `evaluation`/`evaluation_first_four` kaydı sonraki çalıştırmada `evaluation_history` içine taşınır. Mevcut geçmiş raporlar bu kod düzenlemesi sırasında değiştirilmedi. Değerlendirici 01-08 iş testlerinde referans SQL, 09-10 davranış testlerinde beklenen durum ve SQL yürütülmemesini kontrol eder. 11-16 canlı güvenlik testleri sonraki aşamada eklenecek. `--all` henüz tüm 16 test anlamına gelmez.

## Soru arayüzü

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Soru yazıp **Sorgula** düğmesine basın. Form gönderimi gerçek Gemini isteği yapar; salt-okunur, süre/satır limitli yürütme servis üzerinden yapılır. Ekran son soruyu, durumu, toplam süreyi, üretilen SQL'i ve sonuç tablosunu gösterir. Boş sonuç, açıklama ihtiyacı, ret ve hata ayrı mesajlarla sunulur. Satır limiti aşılırsa kesilme uyarısı görünür. Eksik DB/model/anahtar durumunda gönderim kapalıdır. Anahtar ekrana yazılmaz.

Son sonuç oturumda korunur; sadece ekranın yeniden çizilmesi model isteğini tekrarlamaz. Boş gönderim eski sonucu temizler ve API'ye gitmez. Bu ekran takip sorularını önceki sorgunun bağlamıyla birleştirmez. JSON olay logları ve hata yönetimi hazır; Gün 3 canlı testleri 05-10 tamamlandı (6/6 PASS).

## Hata yönetimi ve olay kayıtları

Arayüzü yeniden başlatıp/yenileyip tasarımı kullanabilirsiniz. Geçici Gemini bağlantı/zaman aşımı hatasında servis **en fazla bir kez** tekrar dener. Kota, kimlik, model, SQL veya güvenlik reddi tekrar denenmez. 60 saniyelik iki timeout yaklaşık 120 saniye beklemeye yol açabilir; tekrar deneme servis erişimini garanti etmez. Belirsizlik ve ret yanıtlarında SQL yürütülmez; boş sonuç normal bir sonuçtur. Şirket ifadesi gibi veri modeline belirsiz eşleşen kavramlar için prompt netleştirme ister.

Servise gelen her istek `reports/events.jsonl` içinde bir JSON satırına yazılır. Konum `.env` içindeki `LOG_PATH` ile değişir; dosya ilk sorguda oluşur. İstek kimliği, soru, SQL, durum, hata türü, süreler, denemeler, model ve satır bilgisi tutulur. Anahtar yazılmaz; olay dosyaları Git dışındadır. Log yazılamazsa ekranda uyarı gösterilir, sorgu yeniden çalıştırılmaz. Uygulama yanıtında `request_id`, `attempt_count`, `retry_count` ve `duration_ms` alanları da bulunur.

57 geliştirme testi geçti. 05-10 canlı kabul testleri 6/6 PASS; tarih sınırları ve kapalı model davranışı da doğrulandı. İstemci (`llm.py`) kendi başına retry yapmaz; sınırlandırılmış retry yalnızca servis katmanındadır.

### Güncel arayüz

Arctic Reflection yönünde açık buz beyazı/mavi/gri palet, geniş ve büyük soru alanı kullanılır. Sol panel yoktur; proje adı NL2SQL Agent üsttedir. Hazır soru düğmelerinden birine basınca soru girişe aktarılır; düzenleyip **Sorgula** ile çalıştırabilirsiniz. Hazır soru seçimi API isteği göndermez. Son arayüz kontrolleriyle 50 geliştirme testi geçti.

## Gün 3 doğrulaması

```powershell
.\.venv\Scripts\python.exe scripts/run_evaluation.py --cases 05-10
```

05-08 referans SQL ile karşılaştırılır. 09 metrik netleştirme sorusu ve yürütmesiz yanıt, 10 olmayan alan için kontrollü ret ve yürütmesiz yanıt gerektirir. Güncel prompt nl2sql-v3 ile altısı da canlı geçti. Kapalı model kontrolü HTTP bağlantı hatası enjekte edilerek ayrı pytest testinde yapılır; sunucuya erişim olmadan iki denemeden sonra durduğu ve SQL çalıştırmadığı doğrulanır. Son toplam 57 geliştirme testi PASS. Tüm testlerin son promptla birleşik regresyonu ve 11-16 canlı kontrolleri Gün 4 işidir.

### CSV, takip soruları ve SQL kontrolü

**CSV indir** düğmesi ekranda dönen satırları UTF-8 olarak indirir. **Önceki soruya bağlı sorgula** son üç ilgili soruyu bağlam olarak kullanır. **Sorgula** bağımsız bir soru başlatır.

Arayüzde Gemini'nin ürettiği SQL ikinci bir model çağrısıyla incelenir ve gerekirse düzeltilir. Kontrol başarısız olursa sorgu yürütülmez. İncelenen SQL, yürütmeden önce mevcut yerel güvenlik kontrollerinden de geçer. Mevcut komut satırı kabul testleri tek turlu ayarlarını korur.

**Sorgu loglarını göster** anahtarı, yerel olay dosyasından son 200 kaydı durum filtresiyle birlikte sayfa başına 10 kayıt olarak gösterir. **İndirilecek logları seç** alanından bir veya birden çok kayıt seçip **Seçili logları indir** ile JSON olarak dışa aktarabilirsiniz.
