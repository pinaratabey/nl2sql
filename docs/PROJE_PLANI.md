# NL2SQL - Günlük Geliştirme Takibi

> Güncel aşama: **Gün 3 tamamlandı; sıradaki aşama Gün 4** | Son güncelleme: 03.11.2026
> Tüm gereksinimler ve ayrıntılı işler: [PROJE_DETAYLARI.md](PROJE_DETAYLARI.md)

Bu dosyadan günlük ilerlemeyi takip edin. Her görevdeki **detay** bağlantısı yapılacak alt işleri ve bitiş ölçütlerini açar. `[x]` tamamlandı, `[ ]` tamamlanmadı anlamındadır. Kısmen yapılan görev açık kalır. Görevi ancak bağlantıdaki bitiş ölçütleri sağlandığında kapatın; kanıtı kısa ilerleme kaydına yazın.

## Gün 1 - Ortam, veri ve model

- [x] **Geliştirme ortamı ve proje yapısı** — Python 3.12 sanal ortamı, bağımlılıklar, sade klasör yapısı ve README hazır. [Detay](PROJE_DETAYLARI.md#dosya-yapisi) · [Teknolojiler](PROJE_DETAYLARI.md#teknoloji)
- [x] **Veri seti ve şema** — Kullanıcı onayıyla sentetik veri üretildi; gerçek DB üzerinden sütun, tip ve PK/FK doğrulandı. [Detay](PROJE_DETAYLARI.md#veri) · [Gün 1 işleri](PROJE_DETAYLARI.md#gun-1)
- [x] **Model seçimi ve ilk canlı çıktı** — `gemini-3.5-flash-lite` gerçek iş sorusuna 32,6 saniyede SQL üretti; [canlı çıktı kaydı](reports/test_report.md). [Detay](PROJE_DETAYLARI.md#teknoloji) · [Gün 1 işleri](PROJE_DETAYLARI.md#gun-1)

**Gün sonu hedefi:** Yeniden yüklenebilen veri, doğrulanmış şema ve kayıtlı ilk canlı model çıktısı.

## Gün 2 - SQL üretimi ve güvenlik

- [x] **SQL üretimi** — Canlı Gemini üretimi güvenlik denetimli yürütmeye bağlandı. [Detay](PROJE_DETAYLARI.md#gun-2) · [İş kuralları](PROJE_DETAYLARI.md#veri)
- [x] **Güvenli sorgu çalıştırma** — AST/şema kontrolü, authorizer, salt-okunur bağlantı, 5 saniye ve 500 satır sınırı kuruldu. [Detay](PROJE_DETAYLARI.md#guvenlik)
- [x] **İlk iş testleri ve güvenlik kontrolü** — Canlı test 01-04: 4/4 PASS; doğrudan güvenlik katmanı: 6/6 PASS; 33 geliştirme testi geçti. [Detay](PROJE_DETAYLARI.md#gun-2) · [Test tanımları](PROJE_DETAYLARI.md#testler)

**Gün sonu hedefi:** İlk dört iş testi doğru; yasak sorgular engelleniyor ve yürütme sınırları çalışıyor.

## Gün 3 - Arayüz, hatalar ve loglar

- [x] **Minimum arayüz** — Soru formu güvenli servise bağlı; SQL, sonuç, durum, süre, boş sonuç ve hata gösteriliyor. Beş ekran durumu AppTest ile doğrulandı. [Detay](PROJE_DETAYLARI.md#gun-3) · [Kapsam](PROJE_DETAYLARI.md#kapsam)
- [x] **Hata yönetimi ve JSON loglar** — Kontrollü açıklama/ret/boş sonuç ve hata akışları; geçici model hatasında en fazla bir retry; istek başına JSONL log. 57 geliştirme testi PASS. [Detay](PROJE_DETAYLARI.md#guvenlik) · [Gün 3 işleri](PROJE_DETAYLARI.md#gun-3)
- [x] **Kalan iş ve davranış testleri** — Canlı 05-10: 6/6 PASS; sabit tarih sınırları ve kapalı modelde en fazla bir retry/yürütmesiz hata doğrulandı. [Detay](PROJE_DETAYLARI.md#testler) · [Gün 3 işleri](PROJE_DETAYLARI.md#gun-3)

**Gün sonu hedefi:** Kullanılabilir uçtan uca arayüz, kontrollü hata akışları ve örnek loglar.

## Gün 4 - Testler ve dokümantasyon

- [ ] **16 test ve düzeltmeler** — Bağımsız beklenen sonuçlar, canlı model raporu, güvenlik kontrolleri ve farklı soru ifadeleri. [Detay](PROJE_DETAYLARI.md#testler) · [Gün 4 işleri](PROJE_DETAYLARI.md#gun-4)
- [ ] **Teknik belgeler** — Kurulum, şema, mimari, model/prompt gerekçeleri ve teknik değerlendirme taslağı. [Detay](PROJE_DETAYLARI.md#teslim) · [Gün 4 işleri](PROJE_DETAYLARI.md#gun-4)

**Gün sonu hedefi:** En az 6/8 iş, 2/2 davranış ve 6/6 güvenlik testi PASS; Markdown ve JSON raporları hazır.

## Gün 5 - Son kontrol ve teslim

- [ ] **Temiz kurulum ve son testler** — README ile sıfırdan kur, son kodda testleri çalıştır ve kodu dondur. [Detay](PROJE_DETAYLARI.md#gun-5)
- [ ] **Demo ve bireysel savunma** — 5-7 dakikalık demo, kişi başı 10 dakikalık savunma provası. [Detay](PROJE_DETAYLARI.md#gun-5)
- [ ] **Teslim paketi** — Tüm belgeler, en fazla iki sayfalık değerlendirme, raporlar ve teslim kanalı/tarihi. [Kontrol listesi](PROJE_DETAYLARI.md#teslim)

**Gün sonu hedefi:** Tekrar kurulabilen, kabul ölçütlerini sağlayan ve ekipçe açıklanabilen teslim.

## Şu ana kadar yapılanlar

- Python ortamı ve proje yapısı kuruldu; Gemini modeli bağlandı.
- Türkçe soruları SQL'e çeviren, sorguları güvenli biçimde çalıştıran akış tamamlandı.
- Soru girişi, hazır sorular ve sonuç tablosu içeren Streamlit arayüzü hazırlandı.
- Hata yönetimi, geçici bağlantı hatasında yeniden deneme ve işlem kayıtları eklendi.
- Veri seti hızlı tüketim sektörüne uyarlandı: 300 müşteri, 60 ürün, 2.400 sipariş ve 8.395 sipariş kalemi. Türkçe ad-soyadlar ve ambalajlı ürün adları kullanıldı; eski veri seti silindi.
- Son değişikliklerden sonra 57 geliştirme testi geçti. Önceki sürümlerde canlı testler 01–10 geçti; güncel veri ve model istemiyle toplu canlı doğrulama henüz yapılmadı.

**Sıradaki iş:** Güvenlik testleri 11–16'yı tamamlamak, tüm kabul testlerini güncel sürümde birlikte çalıştırmak ve teslim belgelerini hazırlamak.

## Dosya ve klasörler

| Konum | İçeriği ve amacı |
|---|---|
| `app.py` | Streamlit arayüzü; soruyu alır, SQL'i ve sonuçları gösterir. |
| `src/` | Model bağlantısı, SQL güvenliği ve sorgu çalıştırma gibi temel uygulama kodları. Dosyalar aşağıda açıklanmıştır. |
| `data/analytics.db` | Güncel hızlı tüketim satış veritabanı. |
| `scripts/` | Veri setini oluşturan (`setup_db.py`) ve canlı kabul testlerini çalıştıran (`run_evaluation.py`) betikler. |
| `tests/` | Otomatik geliştirme testleri (`test_agent.py`) ve kabul testi soruları/beklenen davranışları (`cases.json`). |
| `reports/` | Test raporu (`test_report.md`), sayısal sonuçlar (`test_results.json`) ve işlem kayıtları (`events.jsonl`). |
| `docs/` | Veri şeması, uygulama tasarımı ve teknik değerlendirme belgeleri. |
| `README.md` | Kurulum ve çalıştırma açıklamaları. |
| `PROJE_PLANI.md` | İş planı, kısa ilerleme özeti ve dosya rehberi. |
| `PROJE_DETAYLARI.md` | Ayrıntılı gereksinimler, iş kuralları ve teslim ölçütleri. |
| `requirements.txt` | Gerekli Python paketleri. |
| `.env` / `.env.example` | Yerel bağlantı ve model ayarları / örnek yapılandırma. |
| `.venv/` | Projenin Python ortamı ve yüklü paketleri. |
| `.pytest/` | Testlerin geçici dosyaları burada oluşturulur; her test çalıştırmasında önceki içerik temizlenir. Gerektiğinde silinebilir. |
| `pytest.ini` | Test ayarları; önbelleği kapatır ve geçici dosyaları tek `.pytest/` klasöründe tutar. |
| `.gitignore` | Sürüm takibine alınmayacak dosyaların kuralları. |

Canlı testleri seçerek çalıştırma: `.\.venv\Scripts\python.exe scripts/run_evaluation.py --cases 01-04`. Tüm tanımlı testler için `--all` kullanılır.

### `src/` klasörünün içindekiler

| Dosya | Ne işe yarar? |
|---|---|
| `config.py` | `.env` dosyasından model, API anahtarı, veritabanı yolu ve süre/satır sınırlarını okur; ayarların uygunluğunu kontrol eder. |
| `schema.py` | Veritabanındaki tabloları, sütunları ve tablolar arasındaki ilişkileri okur. Modelin hangi alanları kullanabileceğini bilmesini sağlar. |
| `llm.py` | Kullanıcının sorusunu, tablo bilgilerini ve iş kurallarını Gemini'ye gönderir; üretilen SQL'i alır. Soru belirsizse açıklama istenmesini, olmayan bir alan sorulursa reddedilmesini sağlar. |
| `sql_security.py` | SQL'in yalnızca izin verilen tablo ve sütunları kullandığını, veri değiştiren veya yasak bir işlem içermediğini kontrol eder. |
| `database.py` | Güvenlik kontrolünden geçen SQL'i veritabanını değiştirmeden çalıştırır. Süre ve sonuç satırı sınırlarını uygular; sonuçları döndürür. |
| `service.py` | Bütün adımları birbirine bağlar. Soruyu modele iletir, SQL'i çalıştırma adımına gönderir, hataları yönetir ve işlem kaydını yazar. Geçici model hatasında bir kez yeniden dener. |
| `__pycache__/` | Python'un otomatik oluşturduğu önbellek dosyalarıdır; kaynak kod burada düzenlenmez. |

## Bir sorgunun izlediği yol

Örneğin kullanıcı **“En yüksek ciroya sahip 5 ürün hangisi?”** sorusunu yazar:

1. **`app.py`** soruyu alır ve **`service.py`** dosyasına iletir. **`config.py`** bağlantı ayarlarını ve sınırları sağlar.
2. **`llm.py`**, **`schema.py`** üzerinden tablo bilgilerini alır; soruyu ve ciro hesaplama kuralını Gemini'ye gönderir.
3. **Gemini** soruya uygun SQL'i üretir. Soru belirsizse veya istenen bilgi veritabanında yoksa kullanıcıya açıklama döner; SQL çalıştırılmaz.
4. **`database.py`**, SQL'i önce **`sql_security.py`** ile kontrol ettirir. Uygun sorguyu **`data/analytics.db`** üzerinde yalnızca okuma yaparak çalıştırır.
5. **`service.py`** sonucu alır ve işlem özetini **`reports/events.jsonl`** dosyasına kaydeder.
6. **`app.py`** üretilen SQL'i, sonuç tablosunu ve süre bilgisini ekranda gösterir. Hata veya boş sonuç varsa bunu da açıklar.

Kısaca: **Soru → Modelin SQL üretmesi → Güvenlik kontrolü → Veritabanı → Sonucun ekranda gösterilmesi.**
