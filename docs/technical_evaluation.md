# Teknik değerlendirme

## Tasarım kararları

Dört tabloluk sabit şema doğrudan Gemini promptuna aktarılır. Streamlit, SQLite ve doğrudan REST istemcisi PoC için yeterli bir akış sağlar. Canlı denemelerdeki gecikme ve zaman aşımları sonrasında ana model olarak `gemini-3.5-flash-lite` seçildi. Yerel model, yeterli donanım varsa değerlendirilebilecek bir alternatiftir.

Arayüzde ikinci model turu, aday SQL'in soru ve iş kurallarıyla uyumunu kontrol eder. Yürütme iznini SQLGlot denetimi ve SQLite authorizer belirler. Geçici model hatasında tur başına bir tekrar yapılır. SQL kontrolü yine başarısız olursa sorgu çalıştırılmaz.

## Doğrulama

- **60 otomatik test** geçti. Bunlar güvenlik, servis ve arayüz kontrollerini kapsıyor.
- **16 zorunlu ve 16 ek canlı senaryo** sentetik veride geçti. Veri sorularında model sonuçları bağımsız SQL ile karşılaştırıldı. Davranış ve güvenlik senaryolarında beklenen yanıt ve yürütme durumu kontrol edildi.
- Tam canlı koşular tek turlu akışa ait. İki turlu akış, Mayıs 2026 sorusunda ayrıca doğrulandı. Kontrollü bağlantı hatasından sonraki canlı tekrar, sekiz şehir için referans sonuçla eşleşti. İki hata olduğunda SQL yürütülmedi.

## Sınırlılıklar

- Modelin ikinci kontrolü sonuç doğruluğunu garanti etmez. Boş ayı sıfır ciroyla gösterme ve eşit cirolarda kararlı sıralama için ayrı sınır durum testleri gerekir.
- Windows ortamında pandas DLL yükleme sorunu nedeniyle uygulama mevcut Python ortamlarıyla çalıştırıldı. README adımlarıyla temiz kurulum henüz doğrulanmadı.
- Tam 16 senaryonun güncel iki turlu akışta yeniden çalıştırılması bekleniyor.

Geliştirme ve test tasarımında OpenAI Codex ve Gemini kullanıldı. Canlı sonuçlar [zorunlu test raporunda](../reports/test_results.json) ve [ek test raporunda](../reports/additional_test_results.json) yer alıyor.
