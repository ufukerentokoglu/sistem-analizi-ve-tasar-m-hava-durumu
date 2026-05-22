# Hava Durumu Yazılımı

Python + Tkinter ile geliştirilen, konum tabanlı meteorolojik veri görüntüleme uygulaması. Open-Meteo API'sinden anlık ve saatlik veri çeker, MySQL'de saklar, Matplotlib ile zaman serisi grafikleri çizer; yüksek sıcaklık, fırtına, yoğun yağış gibi risk durumlarında SMS simülasyonu ve e-posta üzerinden uyarı gönderir.

---

## 1. Gereksinimler

- **Python 3.11+** (3.13 ile test edildi)
- **MySQL 8.x** (yerel veya uzak)
- İnternet bağlantısı (Open-Meteo API + IP geolocation için)
- macOS / Linux / Windows (geliştirme macOS'ta yapıldı; Windows için PyInstaller komutundaki ayırıcıyı `:` yerine `;` yapın)

---

## 2. Kurulum

### 2.1. Depoyu klonla

```bash
git clone <repo-url>
cd "sistem analizi ve tasarımı hava durumu"
```

### 2.2. Sanal ortam oluştur ve bağımlılıkları kur

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2.3. `.env` dosyasını oluştur

```bash
cp .env.example .env
```

Aşağıdaki alanları kendi MySQL bilgilerinize göre doldurun:

```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=YourPassword
DB_NAME=havadurumu
```

E-posta bildirimi istiyorsanız Gmail uygulama şifrenizi ekleyin:

```env
SMTP_USER=siz@gmail.com
SMTP_PASSWORD=uygulama-sifresi-16-karakter
```

### 2.4. Veritabanı şemasını yükle

```bash
mysql -u root -p < database/schema.sql
```

Bu komut `havadurumu` veritabanını + 6 tabloyu oluşturur, tek kullanıcılı modelin seed kaydını atar. İdempotent — tekrar çalıştırılabilir.

### 2.5. Uygulamayı başlat

```bash
python main.py
```

İlk açılışta KVKK aydınlatma metni görünecektir; onaylayınca ana pencere açılır.

---

## 3. Kullanım

| Sekme | İşlev |
|---|---|
| **Anlık** | Sıcaklık (büyük), hissedilen, durum, nem/rüzgâr/basınç/yağış kartları |
| **Tahmin** | 24 saatlik sıcaklık / nem / rüzgâr grafikleri (Matplotlib) |
| **Favoriler** | Kayıtlı bölgeler + son sıcaklık + çift tıkla yükle |
| **Ayarlar** | SMS/e-posta aç-kapa, risk eşiği, telefon, e-posta |

Üst şerit:
- **📍 Konumumu Tespit Et** — IP üzerinden tespit
- **★ Favorilere Ekle** — aktif konumu favorilere ekler
- **Şehir / İlçe** kutuları — manuel arama (Enter ile)

Arka planda her 5 dakikada bir (yapılandırılabilir: `BACKGROUND_INTERVAL_MINUTES`) aktif konum + tüm favoriler için veri yenilenir; risk eşiği aşıldığında pop-up + SMS log + e-posta tetiklenir.

---

## 4. Klasör Yapısı

```
hava_durumu/
├── main.py                      # Uygulama giriş noktası (logging + KVKK + ana pencere)
├── config.py                    # .env yükleyici + sabitler
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
│
├── database/
│   ├── schema.sql               # MySQL tablo oluşturma scripti (idempotent)
│   └── db_manager.py            # Database sınıfı — tüm CRUD
│
├── models/                      # @dataclass'lar
│   ├── user.py
│   ├── location.py
│   ├── weather.py
│   ├── favorite.py
│   ├── notification_setting.py
│   └── risk_zone.py
│
├── services/
│   ├── weather_api.py           # Open-Meteo istemcisi (anlık/saatlik/günlük)
│   ├── location_service.py      # IP geolocation + manuel + sabit şehir sözlüğü
│   ├── risk_analyzer.py         # Eşik tabanlı risk değerlendirmesi
│   ├── notification_service.py  # SMS log + SMTP e-posta
│   └── background_scheduler.py  # threading + schedule (5 dk periyot)
│
├── ui/
│   ├── main_form.py             # Ana pencere — sekmeli yapı, üst şerit
│   ├── search_form.py           # Şehir/ilçe arama
│   ├── weather_display_form.py  # Anlık veri kartları
│   ├── chart_form.py            # Matplotlib zaman serileri
│   ├── favorites_form.py        # Favori yönetimi
│   ├── settings_form.py         # Bildirim tercihleri
│   ├── risk_alert_form.py       # Risk pop-up (Toplevel modal)
│   └── kvkk_form.py             # İlk açılış KVKK dialog'u
│
├── logs/
│   ├── sms_log.txt              # Çalışınca oluşur (SMS simülasyonu)
│   └── app.log                  # Uygulama log'u
│
└── tests/
    ├── test_database.py         # Aşama 1: DB CRUD smoke
    ├── test_weather_api.py      # Aşama 2: Open-Meteo gerçek istek + hata
    ├── test_location_service.py # Aşama 3: IP + manuel + offline
    ├── test_ui_smoke.py         # Aşama 4: UI açılış + arama → DB
    ├── test_favorites.py        # Aşama 5: favori CRUD + UI akış
    ├── test_chart.py            # Aşama 6: 3 grafik + %H:%M + leak
    ├── test_risk_analyzer.py    # Aşama 7: eşik testleri + SMS + scheduler
    ├── test_risk_popup.py       # Aşama 7: pop-up + DB risk + bildirim
    └── test_kvkk_settings.py    # Aşama 8: KVKK + ayarlar persist
```

---

## 5. Mimari Özet

```
            ┌──────────────────────────────────────────────┐
            │                  main.py                     │
            │  loglama_kur → DB connect → KVKK → MainForm  │
            └──────────────────────┬───────────────────────┘
                                   │ dependency injection
        ┌──────────────────────────┼─────────────────────────────┐
        ▼                          ▼                             ▼
   Database              WeatherAPI / LocationService     BackgroundScheduler
   (MySQL CRUD)           RiskAnalyzer / NotificationSvc  (threading + schedule)
        │                          │                             │
        └──────────── MainForm (tk.Tk) ───────────────────────────┘
                            │
        ┌───────────┬───────┴────────┬─────────────┐
        ▼           ▼                ▼             ▼
   AnlıkSekme  TahminSekme    FavorilerSekme  AyarlarSekme
   (Display)   (ChartForm)    (FavoritesForm) (SettingsForm)
```

**Veri akışı (manuel arama):**
1. SearchForm → `MainForm.aramayi_calistir(sehir)`
2. Background thread → `LocationService.manuel_konum_ara()` (DB veya sabit dict)
3. `Database.konum_ekle()` → konum id
4. `WeatherAPI.anlik_veri_cek()` → Weather nesnesi
5. `Database.hava_durumu_ekle()` → ölçüm satırı
6. UI thread → `WeatherDisplayForm.veriyi_goster()` + favoriler listesi yenile
7. `RiskAnalyzer.degerlendir()` → risk varsa `NotificationService.risk_bildirimi_gonder()` + `RiskAlertForm` pop-up

**Periyodik döngü:**
- `BackgroundScheduler` her 5 dk'da `MainForm.periyodik_kontrol()` çağırır
- Aktif konum + favoriler için yukarıdaki akış tekrarlanır
- Aynı `(konum, risk_tipi)` için 1 saatlik tekrar bildirim engeli

---

## 6. Testleri Çalıştırma

```bash
# Tüm test dosyaları (her biri kendi içinde main() çağrısı yapar)
for t in test_database test_weather_api test_location_service test_chart \
         test_favorites test_risk_analyzer test_ui_smoke test_kvkk_settings \
         test_risk_popup; do
  python -m tests.$t
done
```

**Önemli:** UI testleri `tkinter.Tk()` açabildiği bir ortam gerektirir (CI'da bir sanal display kullanın).

---

## 7. Paketleme (PyInstaller)

### macOS / Linux

```bash
pyinstaller --onefile --windowed --name HavaDurumu \
  --add-data "database/schema.sql:database" \
  --add-data ".env.example:." \
  main.py
```

### Windows

```cmd
pyinstaller --onefile --windowed --name HavaDurumu ^
  --add-data "database/schema.sql;database" ^
  --add-data ".env.example;." ^
  main.py
```

Çıktı:
- `dist/HavaDurumu` (Linux / macOS — tek dosya)
- `dist/HavaDurumu.app` (macOS bundle)
- `dist/HavaDurumu.exe` (Windows)

Dağıtırken `.env` dosyasını binary'nin yanına koymak yeterli — `config.py` `frozen` modda binary'nin klasöründen okur.

---

## 8. Konfigürasyon (`.env`)

| Anahtar | Default | Açıklama |
|---|---|---|
| `DB_HOST` | `localhost` | MySQL host |
| `DB_PORT` | `3306` | MySQL port |
| `DB_USER` | `root` | MySQL kullanıcı |
| `DB_PASSWORD` | (boş) | MySQL şifre |
| `DB_NAME` | `havadurumu` | Veritabanı adı |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP sunucusu |
| `SMTP_PORT` | `587` | STARTTLS portu |
| `SMTP_USER` | (boş) | Gönderici e-posta |
| `SMTP_PASSWORD` | (boş) | Uygulama şifresi (Gmail için) |
| `SMTP_FROM_NAME` | `Hava Durumu Uygulaması` | Gönderici görünen ad |
| `OPEN_METEO_BASE_URL` | `https://api.open-meteo.com/v1/forecast` | API endpoint |
| `OPEN_METEO_TIMEZONE` | `Europe/Istanbul` | Saat dilimi |
| `BACKGROUND_INTERVAL_MINUTES` | `5` | Periyodik kontrol aralığı |
| `APP_NAME` | `Hava Durumu Yazılımı` | Uygulama adı |
| `LOG_DIR` | `logs` | Log dizini |
| `LOG_LEVEL` | `INFO` | Logging seviyesi |

---

## 9. Sınıf Sayımı (Sunum İçin)

**11 sınıf:** `Database`, `WeatherAPI`, `LocationService`, `RiskAnalyzer`, `NotificationService`, `BackgroundScheduler`, `User`, `Location`, `Weather`, `Favorite`, `NotificationSetting` (+ `RiskZone`)

**8 form:** `MainForm`, `SearchForm`, `WeatherDisplayForm`, `ChartForm`, `FavoritesForm`, `SettingsForm`, `RiskAlertForm`, `KVKKForm`

**White-box metriklerini çıkarmak için:**

```bash
find . -name "*.py" -not -path "./.venv/*" -not -path "./tests/*" | xargs wc -l
grep -rn "^\s*#" --include="*.py" . | wc -l       # yorum satırı
grep -rn "try:" --include="*.py" . | wc -l        # try-catch
grep -rnE "if |elif " --include="*.py" . | wc -l  # koşul
grep -rnE "for |while " --include="*.py" . | wc -l# döngü
grep -rn "def " --include="*.py" . | wc -l        # fonksiyon
```

---

## 10. Lisans / Katkıda Bulunan

Sistem Analizi ve Tasarımı dersi proje ödevi.
