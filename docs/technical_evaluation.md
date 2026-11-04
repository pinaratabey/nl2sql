# Teknik değerlendirme - taslak

Henüz uygulama değerlendirmesi yapılmadı. Son belge en fazla iki sayfa olacak.

Tamamlanacak: sınırlılıklar, karşılaşılan sorunlar, alternatifler, iyileştirmeler ve kullanılan AI araçları. Proje iskeleti ve planlama için OpenAI Codex kullanıldı.

# Teknik Değerlendirme Raporu — NL2SQL Agent (ENS-AI-001)

## 1. Mimari Kararlar ve Seçim Gerekçeleri
* **Doğrudan LLM İstemcisi:** LangChain veya LlamaIndex gibi ek orkestrasyon katmanları yerine doğrudan REST API istemcisi (`llm.py`) kullanılmıştır. Bu karar sistem karmaşıklığını önlemiş, milisaniye seviyesinde kontrol ve müdahale imkanı sağlamıştır.
* **Çift Katmanlı SQL Güvenliği:**
  1. *Yazılım Seviyesi (AST Parsing):* `sqlglot` kütüphanesi ile sorgu ağacı taranır, yorum satırları ayrıştırılır ve izinli olmayan tablolar/komutlar engellenir.
  2. *Motor Seviyesi (SQLite Authorizer & URI):* Veritabanı bağlantısı `mode=ro` (salt-okunur) açılır ve SQLite C-level Authorizer ile sistem tablolarına erişim engellenir.
* **Model Seçimi:** İlk denemelerdeki yüksek gecikme süreleri ve zaman aşımları nedeniyle `gemini-3.5-flash-lite` modeli tercih edilmiştir. Düşük düşünme düzeyi (`thinkingLevel=LOW`) ayarıyla kararlı ve hızlı yanıt üretmektedir.

## 2. Karşılaşılan Sorunlar ve Çözümler
* **Tarih Sınırları ve Göreli İfadeler:** "Geçen çeyrek", "son 30 gün" gibi ifadelerde sistem saatinden bağımsızlık ilkesi uygulanmış, yapılandırma dosyasındaki sabit referans tarihi (`2026-06-30`) prompt bağlamına entegre edilmiştir.
* **Prompt Injection Engelleme:** LLM çıktısının güvenilir olmama ihtimaline karşı güvenlik adımları prompta bırakılmamış, kod seviyesindeki AST denetleyicisi ile garanti altına alınmıştır.

## 3. Sınırlılıklar ve İyileştirme Önerileri
* **Gecikme Süreleri:** Ücretsiz katman API erişimindeki gecikmeler nedeniyle ortalama yanıt süreleri değişkenlik göstermektedir. Üretim ortamında yerel bir GPU üzerinde quantization uygulanmış `qwen3:4b` veya `qwen3:8b` modelleri tercih edilebilir.
* **Gelişmiş Semantik Katman:** Kompleks metrikler için veritabanı önünde bir Semantic Layer / Metric Dictionary katmanı kurulabilir.

## 4. Kullanılan Yapay Zekâ Araçları
* Proje mimarisi, güvenlik katmanları, test senaryoları ve kod yapılandırması aşamalarında OpenAI Codex ve Gemini asistan olarak kullanılmıştır.