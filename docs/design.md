# Teknik tasarım

Python + SQLite + Streamlit; doğrudan model istemcisi. SQLGlot ile AST doğrulaması, SQLite salt-okunur bağlantı ve authorizer planlanmıştır.

- `llm.py`: model istemcisi ve promptlar.
- `sql_security.py`: SQL doğrulama.
- `database.py`: bağlantı ve sınırlı yürütme.
- `service.py`: akış, hata yönetimi ve JSON log.

Yapılandırma, salt-okunur bağlantı temeli, sentetik veri üretimi ve gerçek DB şema çıkarımı uygulanmıştır. Sorgu üretimi/yürütme akışı kapalıdır. Model ve parametreler henüz belirlenmedi.

<a id="model-secenekleri"></a>

## Model seçenekleri - 02.11.2026

Donanım sorgusu: AMD Ryzen 7 4800H, 16.558.170.112 bayt RAM (yaklaşık 15,4 GiB), NVIDIA RTX 3050 Laptop 4 GB VRAM; entegre Radeon da var. VRAM bilgisi Windows raporudur, model çalışırken kullanılabilir bellek ölçülmedi. `ollama` komutu PATH üzerinde bulunmadı; kurulum/yerel API erişimi henüz doğrulanmadı.

| Seçenek | Avantaj | Kısıt / yapılacak kontrol |
|---|---|---|
| Ollama + `qwen3:4b` | Yerel başlangıç adayı; model dosyası 2,5 GB, Q4_K_M | Çalışma belleği dosya boyutundan fazladır; 4 GB GPU'ya tam sığma garantisi yok. Kısa bağlamla gerçek hız/Türkçe SQL testi yapılmalı |
| Ollama + `qwen3:8b` | Daha büyük yerel modeli karşılaştırma olanağı | Dosya yaklaşık 5,2 GB; mevcut GPU kapasitesini aşar. CPU/RAM aktarımıyla çalışması ve gecikme ölçülmeli; ilk tercih değil |
| Gemini Developer API ücretsiz katmanda erişilebilir bir metin modeli | Yerel GPU ihtiyacı yok, kurulumu hafif | API anahtarı, internet ve hesapta model/kota erişimi gerekir. Kesin model kimliği ve ücretsiz kullanım şartları seçim sırasında doğrulanmalı |

Öneri: Önce yerel `qwen3:4b` ile kısa bir ölçüm yap; hız veya doğruluk yetersizse API seçeneğine geç. Bu öneri donanım ve kurulum kolaylığına dayanır; Türkçe SQL başarısı henüz ölçülmedi. Ücretli servis zorunlu değil. Model indirme veya hesap açma bu adımda yapılmadı.

### İlk canlı çıktı için yapılacaklar

1. Yerelse Ollama'yı kur, `ollama pull qwen3:4b` ile modeli indir; `ollama list` ile kesin etiket/digest bilgisini kaydet. API ise anahtarı `.env` içine koy, loglara veya Git'e ekleme.
2. `src/llm.py` içinde seçilen sağlayıcı istemcisini ve promptu uygula. `schema_context` çıktısı, metrikler ve 2026-06-30 referans tarihi bağlama eklensin.
3. Başlangıçta temperature 0, sınırlı yanıt uzunluğu ve kısa bağlam kullan; desteklenen parametreleri kaydet. Ollama'da destek doğrulanırsa `think=false` denenebilir. Soğuk açılış ve sonraki çağrı sürelerini ayrı ölç.
4. Gerçek modelden şu beş Türkçe girdiye yanıt al: ilk 5 ürün cirosu, son 6 ay trendi, kategori ortalaması, “En iyi müşteri kimdir?”, olmayan doğum tarihi alanı.
5. Soru, tam model kimliği, parametreler, prompt sürümü, ham çıktı, süre ve hata durumunu `reports/test_report.md` içinde kaydet. Mock sonucu canlı çıktı sayma.
6. Gün 1'de ilk çıktıyı kaydetmek yeterli; güvenlik katmanı tamamlanana kadar model SQL'ini otomatik yürütme. Sonuç doğruluğunu sonraki aşamada bağımsız referans sorgularıyla karşılaştır.
7. Küçük örneklemde SQL/doğru davranış oranı, soğuk/sıcak gecikme ve erişim kararlılığına bakarak ana modeli seç. İlk canlı çıktı kaydı ve model gerekçesi tamamlanınca Gün 1 görevini kapat.

### Kaynaklar

- [Ollama Qwen3 4B model kartı](https://ollama.com/library/qwen3:4b)
- [Ollama Qwen3 8B model kartı](https://ollama.com/library/qwen3:8b)
- [Ollama üretim API'si](https://docs.ollama.com/api/generate)
- [Gemini API fiyatlandırma ve ücretsiz katman](https://ai.google.dev/gemini-api/docs/pricing)
- [Gemini API kota bilgileri](https://ai.google.dev/gemini-api/docs/rate-limits)

## Gemini entegrasyon kararı - 02.11.2026

Kullanıcı ücretsiz Gemini API kullanımını seçti; `.env` içindeki model kimliği `gemini-3.8-flash`. Yerel Ollama adayları önceki karşılaştırma kaydıdır. Donanım üzerinde model çalıştırılmaz.

`src/llm.py` doğrudan Gemini REST generateContent istemcisini ve `nl2sql-v1` promptunu içerir. Mevcut requests bağımlılığı kullanıldığı için yeni paket eklenmedi. Yapılandırmada anahtar repr dışında tutulur; `.env.example` yalnızca boş anahtar alanı içerir. Modelin erişilebilirliği ve ücretsiz kotası gerçek çağrıyla doğrulanmalıdır; kod hesap faturalandırma ayarını değiştirmez.

İstek temperature=0, maxOutputTokens=2048, responseMimeType=application/json içerir. Prompt şema, PK/FK, metrikler ve sabit tarihleri içerir. Model cevabı status/sql/message yapısına göre kontrol edilir. Bu biçim kontrolü SQL güvenlik kontrolü yerine geçmez; service ve SQL yürütme hâlâ kapalıdır. HTTP 429, erişim/kimlik/model hataları, bağlantı/zaman aşımı ve eksik/bozuk model cevabı ayrı ele alınır. İstemci retry yapmaz.

Kaynak: [Gemini models API](https://ai.google.dev/api/models), [generateContent API](https://ai.google.dev/api/generate-content).

Gemini 3 ailesinde kısa SQL üretimi için `thinkingConfig.thinkingLevel=LOW` kullanılır; [düşünme parametreleri](https://ai.google.dev/api/generate-content#ThinkingConfig). İlk metadata kontrolü model erişimini doğruladı; bu kontrol başarılı üretim veya ücretsiz faturalandırma doğrulaması değildir.

## Kullanılan model ve ilk canlı çıktı

Güncel model **gemini-3.5-flash-lite** (kullanıcı seçimi). 02.11.2026 tarihinde ilk iş sorusuna gerçek SQL yanıtı alındı; süre 32,6 saniye. Önceki 3.8 Flash denemeleri timeout, 2.5 Flash üretimi 404 verdi. Bu ortamda başarılı erişim nedeniyle Flash-Lite ile devam ediliyor; henüz Türkçe doğruluk ölçütlerini karşıladığı iddia edilmiyor. Tam değerlendirme Gün 4'te. Gün 1 SQL'i çalıştırılmadı; kaynak kayıt `reports/test_results.json` içinde. Kullanıcı ücretsiz katmanı tercih etti; istemci hesabın faturalandırma ayarını değiştirmez veya katmanı doğrulamaz.

## Gün 2: uygulanmış güvenlik ve yürütme

Akış `service.answer_question` → `llm.generate_sql` → `database.execute_query` şeklindedir. Yürütme fonksiyonu kendi içinde `sql_security.validate_sql` çağırır; model veya başka bir çağıran doğrulamayı atlayamaz. Parser tüm ifadeyi ayrıştırır; yalnızca tek SELECT/set sorgusu kabul eder, tüm CTE/alt sorgu kaynaklarını ve gerçek sütunları kontrol eder. SQL yorumları ayrıştırılır; literal içindeki yorum işaretleri korunur. Özgün SQL raporda kalır, yorumdan arındırılan sürüm yürütülür.

Bağlantı mode=ro, query_only ve authorizer ile kısıtlıdır. Yalnızca izinli dört tablo ve analitik fonksiyonlar okunur; sistem tabloları, uzantılar ve yazma komutları kapalıdır. Güvenilir metadata PRAGMA sorguları ayrı bağlantı yolundadır; kullanıcı SQL'i PRAGMA yetkisi almaz. Authorizer SQLite'ın COUNT(*)/alt sorgularda verdiği boş sütun, veritabanı adı None olan okuma olayını yalnızca izinli tablo adı için kabul eder.

SQL VM progress handler 100 adımda bir süreyi denetler; varsayılan yürütme sınırı 5 saniyedir. Model isteğinin süre sınırı ayrıdır. 500 görünür satır ve kesilme işareti için dış LIMIT 501 kullanılır. Model LIMIT/OFFSET'i iç sorguda korunur. Satır boyutu/ifade derinliği ayrıca sınırlandırılır. İzinli fonksiyon listesi PoC kapsamıyla sınırlıdır; recursive CTE, şema nitelemeleri ve tablo fonksiyonları reddedilir. Bu sınırlamalar genişletilirse güvenlik regresyonları tekrar çalıştırılmalıdır.

İlk dört canlı değerlendirme bağımsız referans SQL ile karşılaştırıldı: 4/4 PASS. 31 geliştirme testi ve 6 doğrudan SQL güvenlik kontrolü geçti. 05-16 canlı doğal dil kabul testleri henüz tamamlanmadı. Arayüz entegrasyonu ve JSON uygulama olay logu Gün 3 işidir.

## Seçilebilir değerlendirme

`scripts/run_evaluation.py` içindeki `evaluate_cases(settings, case_ids=None)` test seçimini veri dosyasından yapar; ilk dört sabit dilim yoktur. Kimlik listesi/aralıklar CLI --cases ile, tüm tanımlılar --all ile seçilir. Seçim API erişiminden önce doğrulanır. Satır/değer karşılaştırması results_match içinde değişmedi. Rapor evaluation altında seçili kimlikleri ve tamamlanmayı tutar; eski evaluation_first_four/evaluation verileri sonraki çalıştırmada geçmişe taşınır. Şimdiki kapsam reference_sql/ordered kullanan iş testleridir; davranış/güvenlik kabul testleri ayrıca genişletilecek.

## Gün 3 arayüz akışı

app.py Streamlit formundan service.answer_question çağırır; doğrudan LLM veya DB bağlantısı açmaz. Başarı/boş sonuç/açıklama/ret/hata durumları ayrı gösterilir. SQL reddedilmiş olsa bile üretilen metin görünür; başarılı tablo yalnızca execution sonucu varsa oluşturulur. Toplam süre arayüzde, yürütme süresi servis sonucunda ölçülür. Yinelenen sütun başlıkları yalnızca gösterimde ayırt edilir; gerçek sonuç/SQL değiştirilmez. Form yeniden çiziminde yeniden API çağrısı yapılmaz; eski yanıt oturumda, sorusuyla birlikte tutulur. DB erişim hataları iz dökümü göstermeden kontrollü sunulur. JSON olay logları ve test 05-10 bu değişikliğin dışında açık görevlerdir.

## Gün 3 son akış ve log sözleşmesi

Model çağrı sayısını service.py yönetir: en fazla iki; yalnızca timeout veya bağlantı/sunucu erişilemezliği için ikinci çağrı yapılır. Rate limit, şema, güvenlik, yetki ve SQL hataları otomatik tekrarlanmaz. Zaman aşımı servis akışını bozmadan kontrollü hata olarak döner; UI toplam süre ve retry sayısını gösterir. SQL'in tüm güvenlik kontrolleri her yürütmede zorunludur.

İstek sonunda tek JSONL event yazılır; event.attempts tüm model denemelerini ve hatalarını içerir. Soru, üretilen/yürütülen SQL, status/error_type ve toplam/model/yürütme süreleri birlikte ilişkilendirilir. raw model cevabı, API anahtarı ve sonuç satırları olay loguna alınmaz. Olay dosyası yazılamaması kullanıcıya ayrı uyarıdır; başarılı sorgu yeniden koşturulmaz. LOG_PATH varsayılan reports/events.jsonl; bu dosya yerel ve Git dışındadır.

Örnek olay biçimi (temsili, canlı başarı kanıtı değildir):

```json
{"request_id":"örnek-id","timestamp":"2026-11-02T16:00:00+03:00","question":"Müşteri sayısı?","generated_sql":"SELECT COUNT(*) FROM Customers","executed_sql":"SELECT * FROM (SELECT COUNT(*) FROM Customers) LIMIT 501","status":"success","error_type":null,"duration_ms":1500,"model_duration_ms":1490,"execution_duration_ms":10,"attempt_count":1,"retry_count":0,"attempts":[{"attempt":1,"status":"success","error_type":null,"duration_ms":1490}],"row_count":1,"truncated":false,"model_id":"gemini-3.5-flash-lite","reference_date":"2026-06-30"}
```

Yeni tasarım: sidebar ve üst başlık analitik çalışma alanını tanımlar; soru formu temel odak, sonuç/süre/tekrar sayısı ayrı kartlar, SQL açılır bölümde. Çıktılar kullanıcıya sonuç olarak yalnızca yürütme başarılıysa gösterilir. Modelin serbest açıklaması sayısal sonuç gibi sunulmaz. Prompt nl2sql-v2 şirket kavramını sessizce tüm müşterilere eşitlemek yerine netleştirme ister. Yeni promptun canlı kabul testleri henüz yapılmadı.

## Güncel görsel düzen

Önceki koyu başlık/yan panel düzeni kullanıcı isteğiyle değiştirildi. Arctic Reflection yönünde açık palet ve büyük tipografi var; sidebar kaldırıldı. Proje adı üstte, altı hazır soru üç sütunlu düğmelerde, ardından büyük soru formu ve sonuç kartları bulunur. Düğme callback yalnızca giriş değerini değiştirir; API çağrısı yalnızca form submit ile yapılır. Mobil boyutlarda başlık ve yatay boşluklar küçülür.

### Light / dark düzeltmesi

Sabit light color-scheme, sayfa/textarea/etiket metin renkleri kaldırıldı. Renkler Streamlit temasından miras alınıyor; yüzeyler saydam mavi katman ve currentColor tabanlı color-mix ile aydınlık/karanlık zemine uyuyor. Tema seçimi native Streamlit Settings üzerinden; yeni uygulama toggle eklenmedi. Böylece özel CSS seçilen native temayı zorlamıyor.

## İş ve davranış değerlendirmesi (01-10)

İş testlerinde reference_sql/ordered kullanılır; davranış testlerinde kind=behavior, expected_status kullanılır. check_case_result açıklama, SQL yokluğu ve execution yokluğunu birlikte arar; model erişim hatası doğru ret sayılmaz. 09 için netleştirme dalı tercih edildi. Prompt v3 müşteri listesi ve ciro sıralaması çıktı alanlarını açıklar. 05-10 canlı 6/6 PASS; offline ve takvim sınırları ayrı kontrollü pytest testleridir.
