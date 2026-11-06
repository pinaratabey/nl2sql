# NL2SQL Agent

NL2SQL Agent, Türkçe satış sorularını Gemini ile SQLite sorgularına dönüştüren bir Streamlit uygulamasıdır. Örnek veri seti müşterileri, ürünleri ve siparişleri içerir. Uygulama SQL'i denetler ve sorguları salt okunur çalıştırır.

## Gereksinimler

- Python 3.12
- Gemini API anahtarı ve anahtarınızla erişebildiğiniz bir Gemini modeli

## Kurulum ve çalıştırma

Aşağıdaki komutları proje klasöründe PowerShell ile çalıştırın.

**1. Sanal ortamı oluşturun ve bağımlılıkları yükleyin.**

Önce PowerShell'de `py -3.12 --version` komutunu çalıştırın. `Python 3.12.x` görüyorsanız aşağıdaki kurulum komutlarına geçin.

- Python 3.12 yüklü değilse [Windows için Python kurulum kılavuzunu](https://docs.python.org/3.12/using/windows.html) izleyin. Microsoft Store'dan kuruyorsanız yayıncısı **Python Software Foundation** olan **Python 3.12** paketini seçin. Kurulumdan sonra PowerShell'i kapatıp yeniden açın.
- `python` komutu Microsoft Store'u açıyorsa `py -3.12` ile devam edin. Gerekirse Windows Başlat menüsünde **Uygulama yürütme diğer adlarını yönet** ayarını açıp `python.exe` komutunun hangi kuruluma bağlı olduğunu kontrol edin.
- `py` komutu bulunamaz ama `python --version` çıktısı **Python 3.12.x** ise ilk komutu `python -m venv .venv` olarak çalıştırın.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Komutlar sanal ortamdaki Python'u doğrudan kullanır. PowerShell'de ortamı etkinleştirmeniz gerekmez. Projeyi başka bir bilgisayara taşıdığınızda `.venv` klasörünü o bilgisayarda yeniden oluşturun.

**2. Gemini bağlantısını ayarlayın.**

Proje kökünde örnek ayar dosyasını kopyalayın. `.env` zaten varsa kopyalama adımını atlayın.

```powershell
Copy-Item .env.example .env
```

`.env` dosyasında `GEMINI_API_KEY` alanına API anahtarınızı yazın. Veritabanı, referans tarihi, süre ve satır sınırları ile log yolu şablonda hazırdır. Gerekirse `GEMINI_MODEL` değerini erişebildiğiniz modelin adıyla değiştirin.

API anahtarınızı yalnızca yerel `.env` dosyanızda saklayın. Bu dosya Git tarafından yok sayılır.

**3. Örnek veritabanını oluşturun.**

```powershell
.\.venv\Scripts\python.exe scripts/setup_db.py
```

Betik `data/analytics.db` dosyasını oluşturur. Dosya zaten varsa bu adımı atlayın.

**4. Uygulamayı başlatın.**

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Tarayıcıda [http://localhost:8501](http://localhost:8501) adresini açın.

## Kullanım

1. Soru alanına “En yüksek ciroya sahip 5 ürün hangisi?” yazın veya **Örnek sorular** bölümünden bir soru seçin.
2. **Sorgula** düğmesine basın. Sonucu tabloda inceleyebilir, üretilen SQL'i açabilir veya sonuçları CSV olarak indirebilirsiniz.
3. Bir önceki sonuca dayanarak yeni bir soru sormak için **Önceki soruya bağlı sorgula** düğmesini kullanın. Sorgu geçmişine **Sorgu loglarını göster** seçeneğinden ulaşabilirsiniz.

Örnek veri setinin referans tarihi 30 Haziran 2026'dır. “Son 6 ay” gibi ifadeler bu tarihe göre yorumlanır.

## Testler

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Gemini bağlantısını gerçek bir API isteğiyle kontrol etmek için aşağıdaki komutu çalıştırın. Bu kontrol SQL üretir ancak sorguyu veritabanında yürütmez.

```powershell
.\.venv\Scripts\python.exe scripts/run_evaluation.py --live-smoke
```

Veri modeli ve sorgu akışı için [veritabanı şemasına](docs/schema.md) ve [mimari belgeye](docs/design.md) bakın.
