# Hava Durumu Yazılımı — Tam Proje Agent Görev Dökümanı

> **Agent talimatı:**
> - Bu döküman, **tam projenin** tek seferde uygulanacak teknik şartnamesidir.
> - Aşamaları sırayla tamamla. Bir aşama bitmeden bir sonrakine geçme.
> - Her aşamanın sonunda "Bitti Kriterleri"ni doğrula.
> - Türkçe değişken, sınıf adları, tablo/sütun adlarını **birebir** koru.
> - Belirsizlik varsa varsayım yapma; soru sor.
> - Kod açıklayıcı Türkçe yorum satırları içersin (white-box metrik için lazım).
> - `try/except` blokları: DB, API çağrısı, dosya işlemleri ve SMTP için zorunlu.

---

## 1. Proje Tanımı

**Hava Durumu Yazılımı**, Python + Tkinter ile geliştirilen, konum tabanlı meteorolojik veri görüntüleme uygulamasıdır.

**Çekirdek özellikler:**
- Şehir/ilçe ile manuel arama **veya** IP geolocation ile otomatik konum tespiti
- Open-Meteo API'den anlık + saatlik hava durumu verisi
- MySQL'de veri saklama (tüm sorgular, ölçümler, geçmiş)
- Favori bölgeler yönetimi
- Matplotlib ile sıcaklık/nem/rüzgar zaman serisi grafikleri
- Risk analizi (uç sıcaklık, fırtına, yoğun yağış)
- Risk durumunda: **SMS simülasyonu** (log dosyasına yazma) + **gerçek e-posta** (SMTP)
- Arka planda her 5 dakikada bir otomatik veri güncelleme

---

## 2. Kilitlenmiş Teknoloji Matrisi

| Konu | Karar |
|---|---|
| Python sürümü | 3.11+ |
| GUI | Tkinter (standart kütüphane) |
| Grafik | Matplotlib |
| Veritabanı | MySQL (`mysql-connector-python`) |
| Karakter seti | `utf8mb4` / `utf8mb4_unicode_ci` |
| Hava API'si | Open-Meteo (anahtarsız, ücretsiz) |
| Konum tespiti | IP tabanlı (`geocoder` paketi) |
| SMS bildirimi | Simülasyon → `logs/sms_log.txt` |
| E-posta bildirimi | SMTP (Gmail önerilir) |
| Kullanıcı modeli | Tek kullanıcı (id=1 sabit kayıt) |
| Arka plan kontrolü | `threading` + `schedule` (5 dk periyot) |
| Paketleme | PyInstaller (`.exe`) |
| Hedef OS | Windows öncelikli, platform bağımsız |

---

## 3. Final Klasör Yapısı

```
hava_durumu/
├── main.py                      # Uygulama giriş noktası
├── config.py                    # .env'den ayarları yükler
├── .env.example                 # Örnek env şablonu
├── .gitignore
├── requirements.txt
├── README.md                    # Kurulum, kullanım, mimari özet
│
├── database/
│   ├── __init__.py
│   ├── schema.sql               # MySQL tablo oluşturma scripti
│   └── db_manager.py            # Database sınıfı (tüm CRUD)
│
├── models/
│   ├── __init__.py
│   ├── user.py                  # User dataclass
│   ├── location.py              # Location dataclass
│   ├── weather.py               # Weather dataclass
│   ├── favorite.py              # Favorite dataclass
│   ├── notification_setting.py  # NotificationSetting dataclass
│   └── risk_zone.py             # RiskZone dataclass
│
├── services/
│   ├── __init__.py
│   ├── weather_api.py           # Open-Meteo istemcisi
│   ├── location_service.py      # IP geolocation + manuel arama
│   ├── risk_analyzer.py         # Risk eşik analizi
│   ├── notification_service.py  # SMS log + e-posta gönderimi
│   └── background_scheduler.py  # Periyodik güncelleme
│
├── ui/
│   ├── __init__.py
│   ├── main_form.py             # Ana pencere
│   ├── search_form.py           # Şehir/ilçe arama
│   ├── weather_display_form.py  # Anlık veri paneli
│   ├── chart_form.py            # Matplotlib grafik ekranı
│   ├── favorites_form.py        # Favoriler yönetimi
│   ├── settings_form.py         # Bildirim ayarları
│   ├── risk_alert_form.py       # Risk uyarı pop-up
│   └── kvkk_form.py             # İlk açılış KVKK izin dialog'u
│
├── logs/
│   ├── .gitkeep
│   ├── sms_log.txt              # Çalışınca oluşur
│   └── app.log                  # Genel uygulama logu
│
└── tests/
    ├── __init__.py
    ├── test_database.py
    ├── test_weather_api.py
    ├── test_location_service.py
    └── test_risk_analyzer.py
```

---

## 4. `requirements.txt`

```
mysql-connector-python==8.4.0
python-dotenv==1.0.1
geocoder==1.38.1
requests==2.32.3
schedule==1.2.2
matplotlib==3.9.2
pyinstaller==6.10.0
```

> `tkinter` standart kütüphanede, kurulmasına gerek yok.

---

## 5. `.gitignore`

```
.env
__pycache__/
*.pyc
*.pyo
.venv/
venv/
.idea/
.vscode/
logs/*.txt
logs/*.log
build/
dist/
*.spec
*.egg-info/
```

---

## 6. `.env.example` ve `config.py`

### `.env.example`

```env
# ---- MySQL Veritabanı ----
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=havadurumu

# ---- SMTP (E-posta bildirimi) ----
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_NAME=Hava Durumu Uygulaması

# ---- Open-Meteo ----
OPEN_METEO_BASE_URL=https://api.open-meteo.com/v1/forecast
OPEN_METEO_TIMEZONE=Europe/Istanbul

# ---- Arka plan ----
BACKGROUND_INTERVAL_MINUTES=5

# ---- Genel ----
APP_NAME=Hava Durumu Yazılımı
LOG_DIR=logs
LOG_LEVEL=INFO
```

### `config.py` davranışı

- `python-dotenv` ile `.env` yükle (yoksa `.env.example`'dan açıklayıcı hata ver)
- Sabitleri modül seviyesinde expose et: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `SMTP_*`, `OPEN_METEO_BASE_URL`, vb.
- `DB_*` eksikse `RuntimeError("Veritabanı yapılandırması eksik: ...")` fırlat
- SMTP eksikse uyarı log'la ama çökme (e-posta gönderimi kapatılır)
- `LOG_DIR` yoksa oluştur
- `BACKGROUND_INTERVAL_MINUTES` `int`'e cast et, default 5

---

## 7. Veritabanı: `database/schema.sql`

**Idempotent** (tekrar tekrar çalıştırılabilir) olacak şekilde:

```sql
CREATE DATABASE IF NOT EXISTS havadurumu
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE havadurumu;

-- 1) Kullanicilar (tek kullanıcı modeli — id=1 sabit kayıt)
CREATE TABLE IF NOT EXISTS Kullanicilar (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ad VARCHAR(100) NOT NULL DEFAULT 'Kullanıcı',
    email VARCHAR(150),
    telefon VARCHAR(20),
    kvkk_onay BOOLEAN NOT NULL DEFAULT FALSE,
    kayit_tarihi TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2) Konumlar
CREATE TABLE IF NOT EXISTS Konumlar (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sehir VARCHAR(100) NOT NULL,
    ilce VARCHAR(100),
    ulke VARCHAR(100) NOT NULL DEFAULT 'Türkiye',
    latitude DECIMAL(10, 7) NOT NULL,
    longitude DECIMAL(10, 7) NOT NULL,
    olusturma_tarihi TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uniq_konum (sehir, ilce, ulke)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3) Hava Durumu Ölçümleri
CREATE TABLE IF NOT EXISTS HavaDurumu (
    id INT AUTO_INCREMENT PRIMARY KEY,
    konum_id INT NOT NULL,
    olcum_tarihi DATETIME NOT NULL,
    sicaklik DECIMAL(5,2),
    hissedilen_sicaklik DECIMAL(5,2),
    nem INT,
    ruzgar_hizi DECIMAL(5,2),
    ruzgar_yonu INT,
    basinc DECIMAL(7,2),
    yagis_mm DECIMAL(5,2),
    durum_kodu INT,
    durum_aciklamasi VARCHAR(100),
    kaynak_api VARCHAR(50) NOT NULL DEFAULT 'Open-Meteo',
    olusturma_tarihi TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (konum_id) REFERENCES Konumlar(id) ON DELETE CASCADE,
    INDEX idx_konum_tarih (konum_id, olcum_tarihi DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4) Favoriler
CREATE TABLE IF NOT EXISTS Favoriler (
    id INT AUTO_INCREMENT PRIMARY KEY,
    kullanici_id INT NOT NULL,
    konum_id INT NOT NULL,
    sira INT NOT NULL DEFAULT 0,
    eklenme_tarihi TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (kullanici_id) REFERENCES Kullanicilar(id) ON DELETE CASCADE,
    FOREIGN KEY (konum_id) REFERENCES Konumlar(id) ON DELETE CASCADE,
    UNIQUE KEY uniq_favori (kullanici_id, konum_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5) Bildirim Ayarları
CREATE TABLE IF NOT EXISTS BildirimAyarlari (
    id INT AUTO_INCREMENT PRIMARY KEY,
    kullanici_id INT NOT NULL UNIQUE,
    sms_aktif BOOLEAN NOT NULL DEFAULT TRUE,
    email_aktif BOOLEAN NOT NULL DEFAULT TRUE,
    risk_esigi ENUM('dusuk', 'orta', 'yuksek') NOT NULL DEFAULT 'orta',
    bildirim_tipi VARCHAR(50) NOT NULL DEFAULT 'tum',
    guncelleme_tarihi TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (kullanici_id) REFERENCES Kullanicilar(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6) Riskli Bölgeler
CREATE TABLE IF NOT EXISTS RiskliBolgeler (
    id INT AUTO_INCREMENT PRIMARY KEY,
    konum_id INT NOT NULL,
    risk_tipi VARCHAR(50) NOT NULL,
    siddet ENUM('dusuk', 'orta', 'yuksek') NOT NULL DEFAULT 'orta',
    baslangic DATETIME NOT NULL,
    bitis DATETIME,
    aciklama TEXT,
    olusturma_tarihi TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (konum_id) REFERENCES Konumlar(id) ON DELETE CASCADE,
    INDEX idx_aktif_riskler (konum_id, baslangic, bitis)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Seed: tek kullanıcı kaydı + default bildirim ayarı
INSERT IGNORE INTO Kullanicilar (id, ad) VALUES (1, 'Kullanıcı');
INSERT IGNORE INTO BildirimAyarlari (kullanici_id) VALUES (1);
```

---

## 8. Model Sınıfları (`models/`)

Hepsi `@dataclass`. `id` ve tarih alanları `Optional` ve `None` default'lu.

### `models/user.py`
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class User:
    ad: str = "Kullanıcı"
    email: Optional[str] = None
    telefon: Optional[str] = None
    kvkk_onay: bool = False
    id: Optional[int] = None
    kayit_tarihi: Optional[datetime] = None
```

### `models/location.py`
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Location:
    sehir: str
    latitude: float
    longitude: float
    ilce: Optional[str] = None
    ulke: str = "Türkiye"
    id: Optional[int] = None
    olusturma_tarihi: Optional[datetime] = None
```

### `models/weather.py`
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Weather:
    konum_id: int
    olcum_tarihi: datetime
    sicaklik: Optional[float] = None
    hissedilen_sicaklik: Optional[float] = None
    nem: Optional[int] = None
    ruzgar_hizi: Optional[float] = None
    ruzgar_yonu: Optional[int] = None
    basinc: Optional[float] = None
    yagis_mm: Optional[float] = None
    durum_kodu: Optional[int] = None
    durum_aciklamasi: Optional[str] = None
    kaynak_api: str = "Open-Meteo"
    id: Optional[int] = None
    olusturma_tarihi: Optional[datetime] = None
```

### `models/favorite.py`
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Favorite:
    kullanici_id: int
    konum_id: int
    sira: int = 0
    id: Optional[int] = None
    eklenme_tarihi: Optional[datetime] = None
```

### `models/notification_setting.py`
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class NotificationSetting:
    kullanici_id: int
    sms_aktif: bool = True
    email_aktif: bool = True
    risk_esigi: str = "orta"   # 'dusuk' | 'orta' | 'yuksek'
    bildirim_tipi: str = "tum"
    id: Optional[int] = None
    guncelleme_tarihi: Optional[datetime] = None
```

### `models/risk_zone.py`
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class RiskZone:
    konum_id: int
    risk_tipi: str
    baslangic: datetime
    siddet: str = "orta"        # 'dusuk' | 'orta' | 'yuksek'
    bitis: Optional[datetime] = None
    aciklama: Optional[str] = None
    id: Optional[int] = None
    olusturma_tarihi: Optional[datetime] = None
```

---

## AŞAMA 1 — Veritabanı Katmanı

### Görevler
1. Klasör yapısını oluştur (Bölüm 3'teki gibi).
2. `requirements.txt`, `.gitignore`, `.env.example`, `config.py` oluştur.
3. `database/schema.sql` yaz (Bölüm 7).
4. Tüm modelleri yaz (Bölüm 8).
5. `database/db_manager.py` içinde `Database` sınıfını uygula.
6. `tests/test_database.py` ile smoke test yaz ve çalıştır.

### `Database` Sınıfı İmzaları

```python
from typing import Optional
import mysql.connector
from mysql.connector import Error

from models.user import User
from models.location import Location
from models.weather import Weather
from models.favorite import Favorite
from models.notification_setting import NotificationSetting
from models.risk_zone import RiskZone


class Database:
    """MySQL bağlantısı ve CRUD operasyonlarını yöneten sınıf."""

    def __init__(self, host: str, port: int, user: str, password: str, database: str): ...

    # ----- Bağlantı yönetimi -----
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def is_connected(self) -> bool: ...
    def __enter__(self): ...
    def __exit__(self, exc_type, exc_val, exc_tb): ...

    # ----- Düşük seviye -----
    def execute(self, query: str, params: tuple | None = None) -> int:
        """INSERT'te lastrowid, diğerinde rowcount döner."""
    def fetch_one(self, query: str, params: tuple | None = None) -> Optional[dict]: ...
    def fetch_all(self, query: str, params: tuple | None = None) -> list[dict]: ...

    # ----- Kullanıcı -----
    def kullanici_getir(self, kullanici_id: int = 1) -> Optional[User]: ...
    def kullanici_guncelle(self, user: User) -> bool: ...

    # ----- Konum -----
    def konum_ekle(self, location: Location) -> int:
        """Var olan (sehir, ilce, ulke) ise mevcut id döner, yoksa ekleyip yeni id verir."""
    def konum_getir(self, konum_id: int) -> Optional[Location]: ...
    def konum_ara(self, sehir: str, ilce: Optional[str] = None) -> Optional[Location]: ...
    def tum_konumlari_getir(self) -> list[Location]: ...

    # ----- Hava Durumu -----
    def hava_durumu_ekle(self, weather: Weather) -> int: ...
    def son_hava_durumu_getir(self, konum_id: int) -> Optional[Weather]: ...
    def hava_durumu_gecmisi(self, konum_id: int, gun_sayisi: int = 7) -> list[Weather]: ...
    def eski_kayitlari_temizle(self, gun_sayisi: int = 30) -> int: ...

    # ----- Favoriler -----
    def favori_ekle(self, kullanici_id: int, konum_id: int) -> int: ...
    def favori_sil(self, kullanici_id: int, konum_id: int) -> bool: ...
    def favorileri_getir(self, kullanici_id: int) -> list[Favorite]: ...
    def favori_mi(self, kullanici_id: int, konum_id: int) -> bool: ...

    # ----- Bildirim Ayarları -----
    def bildirim_ayari_getir(self, kullanici_id: int) -> Optional[NotificationSetting]: ...
    def bildirim_ayari_guncelle(self, setting: NotificationSetting) -> bool: ...

    # ----- Riskli Bölgeler -----
    def riskli_bolge_ekle(self, risk: RiskZone) -> int: ...
    def aktif_riskleri_getir(self, konum_id: Optional[int] = None) -> list[RiskZone]: ...
    def riskli_bolge_kapat(self, risk_id: int) -> bool: ...

    # ----- Yardımcılar -----
    @staticmethod
    def _row_to_user(row: dict) -> User: ...
    @staticmethod
    def _row_to_location(row: dict) -> Location: ...
    @staticmethod
    def _row_to_weather(row: dict) -> Weather: ...
    @staticmethod
    def _row_to_favorite(row: dict) -> Favorite: ...
    @staticmethod
    def _row_to_notification_setting(row: dict) -> NotificationSetting: ...
    @staticmethod
    def _row_to_risk_zone(row: dict) -> RiskZone: ...
```

### Smoke Test (`tests/test_database.py`)

```python
"""Aşama 1 smoke test — DB temel CRUD'ı sağlıyor mu?"""
from datetime import datetime
from database.db_manager import Database
from models.location import Location
from models.weather import Weather
import config

def test_full_flow():
    db = Database(config.DB_HOST, config.DB_PORT, config.DB_USER,
                  config.DB_PASSWORD, config.DB_NAME)
    db.connect()
    try:
        # Konum ekle
        loc = Location(sehir="İzmit", ilce="Kocaeli", latitude=40.766, longitude=29.916)
        konum_id = db.konum_ekle(loc)
        assert konum_id > 0

        # Tekrar ekle — aynı id dönmeli
        konum_id2 = db.konum_ekle(loc)
        assert konum_id == konum_id2

        # Hava durumu ekle
        w = Weather(konum_id=konum_id, olcum_tarihi=datetime.now(),
                    sicaklik=22.5, nem=65, ruzgar_hizi=12.3)
        weather_id = db.hava_durumu_ekle(w)
        assert weather_id > 0

        # Sorgula
        son = db.son_hava_durumu_getir(konum_id)
        assert son is not None and son.sicaklik == 22.5

        # Favori ekle/sil
        db.favori_ekle(1, konum_id)
        assert db.favori_mi(1, konum_id)
        db.favori_sil(1, konum_id)
        assert not db.favori_mi(1, konum_id)
    finally:
        db.disconnect()
    print("✓ Aşama 1 testleri başarılı")

if __name__ == "__main__":
    test_full_flow()
```

### Bitti Kriterleri — Aşama 1
- [ ] `pip install -r requirements.txt` hatasız
- [ ] `schema.sql` MySQL'de hatasız çalışıyor, tekrar çalıştırınca da patlamıyor
- [ ] `python -m tests.test_database` çıktı: `✓ Aşama 1 testleri başarılı`
- [ ] `Database` sınıfı tüm imzaları uyguluyor

---

## AŞAMA 2 — Open-Meteo API Entegrasyonu

### Open-Meteo Referansı

- Endpoint: `https://api.open-meteo.com/v1/forecast`
- Query parametreleri (zorunlular): `latitude`, `longitude`
- Önemli parametreler:
  - `current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,wind_speed_10m,wind_direction_10m,surface_pressure`
  - `hourly=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code`
  - `daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code`
  - `timezone=Europe/Istanbul` (config'ten)
  - `forecast_days=7`
- API key gerekmez.

### `services/weather_api.py`

```python
import requests
from datetime import datetime
from typing import Optional

from models.location import Location
from models.weather import Weather
import config


class WeatherAPI:
    """Open-Meteo API istemcisi."""

    BASE_URL = config.OPEN_METEO_BASE_URL
    TIMEOUT = 10  # saniye

    # WMO weather code → Türkçe açıklama
    WEATHER_CODES: dict[int, str] = {
        0: "Açık",
        1: "Genelde açık",
        2: "Parçalı bulutlu",
        3: "Bulutlu",
        45: "Sis",
        48: "Yoğun sis",
        51: "Hafif çisenti",
        53: "Çisenti",
        55: "Yoğun çisenti",
        61: "Hafif yağmur",
        63: "Yağmur",
        65: "Şiddetli yağmur",
        71: "Hafif kar",
        73: "Kar",
        75: "Yoğun kar",
        77: "Kar taneleri",
        80: "Hafif sağanak",
        81: "Sağanak",
        82: "Şiddetli sağanak",
        85: "Hafif kar sağanağı",
        86: "Yoğun kar sağanağı",
        95: "Gök gürültülü fırtına",
        96: "Dolu ile fırtına",
        99: "Şiddetli dolu fırtınası",
    }

    def __init__(self, base_url: Optional[str] = None, timezone: Optional[str] = None):
        self.base_url = base_url or self.BASE_URL
        self.timezone = timezone or config.OPEN_METEO_TIMEZONE

    def anlik_veri_cek(self, location: Location) -> Weather:
        """Verilen konum için anlık hava durumunu döndürür."""
        ...

    def saatlik_tahmin_cek(self, location: Location, saat_sayisi: int = 24) -> list[Weather]:
        """Önümüzdeki N saat için tahminleri döndürür."""
        ...

    def gunluk_tahmin_cek(self, location: Location, gun_sayisi: int = 7) -> list[Weather]:
        """Önümüzdeki N gün için günlük tahminleri döndürür."""
        ...

    @classmethod
    def kod_aciklamasi(cls, weather_code: int) -> str:
        """WMO weather code → Türkçe açıklama."""
        return cls.WEATHER_CODES.get(weather_code, "Bilinmiyor")

    def _istek_at(self, params: dict) -> dict:
        """Düşük seviye GET isteği. Hata yönetimi burada."""
        try:
            r = requests.get(self.base_url, params=params, timeout=self.TIMEOUT)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Open-Meteo isteği başarısız: {e}") from e
```

### Bitti Kriterleri — Aşama 2
- [ ] `anlik_veri_cek()` çağrısı: İzmit koordinatlarıyla doğru `Weather` nesnesi dönüyor
- [ ] `saatlik_tahmin_cek()` 24 elemanlı liste dönüyor
- [ ] Ağ hatasında `RuntimeError` fırlatıyor, sessizce yutmuyor
- [ ] `tests/test_weather_api.py` smoke test'i geçiyor

---

## AŞAMA 3 — Konum Servisi

### `services/location_service.py`

```python
import geocoder
from typing import Optional

from models.location import Location
from database.db_manager import Database


class LocationService:
    """IP geolocation + manuel konum arama servisi."""

    # Türkiye'nin büyük şehir koordinatları (manuel arama hatasında fallback)
    SEHIR_KOORDINATLARI: dict[str, tuple[float, float]] = {
        "istanbul": (41.0082, 28.9784),
        "ankara": (39.9334, 32.8597),
        "izmir": (38.4192, 27.1287),
        "kocaeli": (40.8533, 29.8815),
        "izmit": (40.7654, 29.9408),
        "bursa": (40.1828, 29.0665),
        "antalya": (36.8969, 30.7133),
        "adana": (37.0000, 35.3213),
        "gaziantep": (37.0662, 37.3833),
        "konya": (37.8746, 32.4932),
        # ... ihtiyaç hâlinde genişlet
    }

    def __init__(self, db: Database):
        self.db = db

    def otomatik_konum_tespit(self) -> Optional[Location]:
        """IP üzerinden kullanıcının konumunu tespit eder."""
        try:
            g = geocoder.ip("me")
            if not g.ok:
                return None
            loc = Location(
                sehir=g.city or "Bilinmeyen",
                ilce=None,
                ulke=g.country or "Türkiye",
                latitude=float(g.latlng[0]),
                longitude=float(g.latlng[1]),
            )
            return loc
        except Exception:
            return None

    def manuel_konum_ara(self, sehir: str, ilce: Optional[str] = None) -> Optional[Location]:
        """Şehir/ilçe adıyla DB'de arar, yoksa SEHIR_KOORDINATLARI'ndan oluşturup ekler."""
        # Önce DB
        loc = self.db.konum_ara(sehir, ilce)
        if loc:
            return loc

        # Sonra sabit dict
        key = sehir.lower().strip()
        if key in self.SEHIR_KOORDINATLARI:
            lat, lon = self.SEHIR_KOORDINATLARI[key]
            loc = Location(sehir=sehir, ilce=ilce, latitude=lat, longitude=lon)
            konum_id = self.db.konum_ekle(loc)
            loc.id = konum_id
            return loc

        return None

    def konum_kaydet(self, location: Location) -> Location:
        """Konumu DB'ye ekler/günceller, id atanmış nesneyi döner."""
        konum_id = self.db.konum_ekle(location)
        location.id = konum_id
        return location
```

### Bitti Kriterleri — Aşama 3
- [ ] `otomatik_konum_tespit()` internet bağlıyken `Location` döndürüyor
- [ ] `manuel_konum_ara("İzmit")` çalışıyor (DB'de yokken sabit dict'ten oluşturuyor, sonraki çağrıda DB'den dönüyor)
- [ ] İnternet yokken `otomatik_konum_tespit()` `None` dönüyor, exception fırlatmıyor

---

## AŞAMA 4 — Tkinter Ana Pencere İskeleti

### Genel UI Tasarım Notları
- Pencere boyutu: 1100x700, ortalanmış
- Tema: Tkinter `ttk` (Clam veya Vista — platforma göre)
- Ana pencerede sekme yapısı (`ttk.Notebook`): **Anlık**, **Tahmin**, **Favoriler**, **Ayarlar**
- Üstte: konum bilgisi + "Konumumu Tespit Et" butonu + arama kutusu
- Renk paleti: mavi tonları (`#1E88E5` ana, `#0D47A1` koyu, `#E3F2FD` arkaplan)

### `ui/main_form.py`

```python
import tkinter as tk
from tkinter import ttk

from database.db_manager import Database
from services.weather_api import WeatherAPI
from services.location_service import LocationService
from models.location import Location


class MainForm(tk.Tk):
    """Ana uygulama penceresi."""

    def __init__(self, db: Database, weather_api: WeatherAPI, location_service: LocationService):
        super().__init__()
        self.db = db
        self.weather_api = weather_api
        self.location_service = location_service
        self.aktif_konum: Location | None = None

        self.title("Hava Durumu Yazılımı")
        self.geometry("1100x700")
        self._merkezle()
        self._arayuzu_olustur()

    def _merkezle(self) -> None: ...
    def _arayuzu_olustur(self) -> None: ...
    def _ust_seridi_olustur(self, parent: tk.Widget) -> None: ...
    def _sekmeleri_olustur(self, parent: tk.Widget) -> None: ...

    # Etkileşim
    def konumu_tespit_et(self) -> None: ...
    def aramayi_calistir(self, sehir: str, ilce: str | None = None) -> None: ...
    def aktif_konumu_guncelle(self, location: Location) -> None: ...
```

### `ui/search_form.py`

```python
import tkinter as tk
from tkinter import ttk
from typing import Callable

class SearchForm(ttk.Frame):
    """Şehir/ilçe arama formu (üst şeritte gömülü)."""

    def __init__(self, parent, on_search: Callable[[str, str | None], None]):
        super().__init__(parent)
        self.on_search = on_search
        self._arayuzu_olustur()

    def _arayuzu_olustur(self) -> None: ...
    def _arama_tetikle(self) -> None: ...
```

### `ui/weather_display_form.py`

```python
import tkinter as tk
from tkinter import ttk

from models.weather import Weather
from models.location import Location

class WeatherDisplayForm(ttk.Frame):
    """Anlık hava durumu paneli."""

    def __init__(self, parent):
        super().__init__(parent)
        self._arayuzu_olustur()

    def _arayuzu_olustur(self) -> None:
        """Sıcaklık (büyük), durum açıklaması, nem/rüzgar/basınç kartları."""
        ...

    def veriyi_goster(self, location: Location, weather: Weather) -> None: ...
    def temizle(self) -> None: ...
```

### Bitti Kriterleri — Aşama 4
- [ ] `python main.py` ile pencere açılıyor
- [ ] Üstte konum + arama kutusu görünüyor
- [ ] "Konumumu Tespit Et" butonu çalışıyor (LocationService'i tetikliyor)
- [ ] Arama → API çağrısı → ekrana sıcaklık/nem/rüzgar yansıyor
- [ ] DB'ye ölçüm kaydediliyor

---

## AŞAMA 5 — Favoriler

### `ui/favorites_form.py`

```python
import tkinter as tk
from tkinter import ttk, messagebox

from database.db_manager import Database
from services.weather_api import WeatherAPI


class FavoritesForm(ttk.Frame):
    """Favori bölgeler listesi + ekleme/silme."""

    def __init__(self, parent, db: Database, weather_api: WeatherAPI,
                 kullanici_id: int = 1, on_select=None):
        super().__init__(parent)
        self.db = db
        self.weather_api = weather_api
        self.kullanici_id = kullanici_id
        self.on_select = on_select
        self._arayuzu_olustur()
        self.listeyi_yenile()

    def _arayuzu_olustur(self) -> None: ...
    def listeyi_yenile(self) -> None: ...
    def favori_ekle(self, konum_id: int) -> None: ...
    def favori_sil(self, konum_id: int) -> None: ...
    def _secileni_goster(self, event=None) -> None: ...
```

### MainForm Güncellemesi
- Aktif konum ekranında **"Favorilere Ekle"** butonu — basınca o konumu DB'ye favori olarak kaydeder
- Favoriler sekmesinde liste, her satırda: şehir adı + son sıcaklık + Sil butonu
- Favoriye tıklanınca o konumun anlık verisi Anlık sekmesinde yüklenir

### Bitti Kriterleri — Aşama 5
- [ ] Konum aktifken "Favorilere Ekle" çalışıyor
- [ ] Favoriler sekmesinde liste güncel
- [ ] Favoriye tıklayınca o konum aktif oluyor
- [ ] Aynı konum iki kez eklenemiyor (DB unique constraint)

---

## AŞAMA 6 — Matplotlib Grafikleri

### `ui/chart_form.py`

```python
import tkinter as tk
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from database.db_manager import Database
from services.weather_api import WeatherAPI
from models.location import Location


class ChartForm(ttk.Frame):
    """Sıcaklık/nem/rüzgar zaman serisi grafikleri."""

    def __init__(self, parent, db: Database, weather_api: WeatherAPI):
        super().__init__(parent)
        self.db = db
        self.weather_api = weather_api
        self._arayuzu_olustur()

    def _arayuzu_olustur(self) -> None:
        """Üstte 3 buton: Sıcaklık | Nem | Rüzgar. Altında matplotlib canvas."""
        ...

    def sicaklik_grafigi(self, location: Location, saat_sayisi: int = 24) -> None: ...
    def nem_grafigi(self, location: Location, saat_sayisi: int = 24) -> None: ...
    def ruzgar_grafigi(self, location: Location, saat_sayisi: int = 24) -> None: ...
    def _canvas_temizle(self) -> None: ...
    def _figure_ciz(self, x_data, y_data, baslik: str, y_etiket: str) -> None: ...
```

### Bitti Kriterleri — Aşama 6
- [ ] Tahmin sekmesinde grafik gösteriliyor
- [ ] 3 buton (Sıcaklık/Nem/Rüzgar) ayrı ayrı çalışıyor
- [ ] Grafik temizleme + yeniden çizim memory leak yapmıyor (eski figure kapatılıyor)
- [ ] X ekseni Türkçe saat formatında (`%H:%M`)

---

## AŞAMA 7 — Risk Analizi + Bildirim Sistemi

### `services/risk_analyzer.py`

```python
from typing import Optional

from models.weather import Weather
from models.location import Location
from models.risk_zone import RiskZone
from datetime import datetime


class RiskAnalyzer:
    """Hava verisini risk eşiklerine göre değerlendirir."""

    # Eşikler (Türkiye iklimi referans)
    ESIK_SICAKLIK_YUKSEK = 38.0     # °C
    ESIK_SICAKLIK_DUSUK = -10.0     # °C
    ESIK_RUZGAR_YUKSEK = 60.0       # km/h (~17 m/s)
    ESIK_YAGIS_YUKSEK = 20.0        # mm/saat
    FIRTINA_KODLARI = {95, 96, 99}  # WMO

    def degerlendir(self, weather: Weather, location: Location) -> Optional[RiskZone]:
        """Risk varsa RiskZone döndür, yoksa None."""
        ...

    def _siddet_belirle(self, weather: Weather) -> str:
        """'dusuk' | 'orta' | 'yuksek' döner."""
        ...
```

### `services/notification_service.py`

```python
import logging
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Optional

from models.user import User
from models.risk_zone import RiskZone
from models.location import Location
import config


class NotificationService:
    """SMS simülasyonu + gerçek e-posta gönderimi."""

    def __init__(self, sms_log_path: Optional[Path] = None):
        self.sms_log_path = sms_log_path or Path(config.LOG_DIR) / "sms_log.txt"
        self.sms_log_path.parent.mkdir(parents=True, exist_ok=True)

    def sms_gonder(self, telefon: str, mesaj: str) -> bool:
        """SMS gönderir (simülasyon: log dosyasına yazma)."""
        ...

    def email_gonder(self, alici_email: str, konu: str, govde: str) -> bool:
        """SMTP üzerinden e-posta gönderir."""
        ...

    def risk_bildirimi_gonder(self, user: User, risk: RiskZone, location: Location,
                              sms_aktif: bool, email_aktif: bool) -> dict:
        """Hem SMS hem e-posta gönderir, sonuç dict'i döner: {sms: bool, email: bool}."""
        ...

    def _mesaj_olustur(self, risk: RiskZone, location: Location) -> str:
        """Risk için Türkçe mesaj metni oluşturur."""
        ...
```

### SMS Log Formatı (örnek satır)
```
[2025-11-15 14:32:01] TO: +905551234567 | MSG: ⚠ İzmit/Kocaeli için fırtına uyarısı! Şiddet: yüksek. Lütfen tedbirli olun.
```

### `services/background_scheduler.py`

```python
import threading
import schedule
import time
import logging
from typing import Callable, Optional


class BackgroundScheduler:
    """schedule + threading ile periyodik görev çalıştırıcı."""

    def __init__(self, interval_minutes: int = 5):
        self.interval_minutes = interval_minutes
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.gorevler: list[Callable] = []

    def gorev_ekle(self, fn: Callable) -> None: ...
    def basla(self) -> None: ...
    def durdur(self) -> None: ...
    def _calistir(self) -> None: ...
```

### `ui/risk_alert_form.py`

```python
import tkinter as tk
from tkinter import ttk

from models.risk_zone import RiskZone
from models.location import Location


class RiskAlertForm(tk.Toplevel):
    """Risk uyarı pop-up."""

    SIDDET_RENKLERI = {"dusuk": "#FFC107", "orta": "#FF9800", "yuksek": "#D32F2F"}

    def __init__(self, parent, risk: RiskZone, location: Location):
        super().__init__(parent)
        self.title("⚠ Hava Durumu Uyarısı")
        self.geometry("450x300")
        self.transient(parent)
        self.grab_set()
        self._arayuzu_olustur(risk, location)

    def _arayuzu_olustur(self, risk: RiskZone, location: Location) -> None: ...
```

### MainForm Entegrasyonu
- `MainForm.__init__` içinde:
  - `BackgroundScheduler` oluştur
  - Her 5 dk'da bir: aktif konum + favoriler için `weather_api.anlik_veri_cek()` → `db.hava_durumu_ekle()` → `risk_analyzer.degerlendir()` → risk varsa `notification_service.risk_bildirimi_gonder()` + `RiskAlertForm` aç
  - Pencere kapanırken (`WM_DELETE_WINDOW`) scheduler.durdur()

### Bitti Kriterleri — Aşama 7
- [ ] `risk_analyzer.degerlendir(weather, location)` test edilebilir: yüksek sıcaklıkta `RiskZone` dönüyor
- [ ] `logs/sms_log.txt` dosyasına simüle SMS düşüyor
- [ ] SMTP env vars set'liyken e-posta gerçekten gidiyor (test e-posta'ya)
- [ ] Arka plan thread'i 5 dk'da bir tetikleniyor (ya da `BACKGROUND_INTERVAL_MINUTES` değerine göre)
- [ ] Uygulama kapanırken thread temiz duruyor (`stop_event.set()`)
- [ ] Risk anında `RiskAlertForm` pop-up'ı modal olarak açılıyor

---

## AŞAMA 8 — KVKK, Ayarlar, Test, Paketleme

### `ui/kvkk_form.py`

```python
import tkinter as tk
from tkinter import ttk

from database.db_manager import Database


class KVKKForm(tk.Toplevel):
    """İlk açılışta konum izni ve KVKK onayı dialog'u."""

    KVKK_METNI = """
    6698 sayılı Kişisel Verilerin Korunması Kanunu kapsamında bilgilendirme:

    • Uygulamamız konum bilginizi (IP üzerinden) yalnızca hava durumu sorgulaması
      amacıyla kullanır.
    • Verileriniz yerel MySQL veritabanınızda saklanır, hiçbir üçüncü tarafla
      paylaşılmaz.
    • Bildirim için verdiğiniz telefon ve e-posta bilgileri sadece tarafınıza
      uyarı göndermek için kullanılır.
    • İstediğiniz zaman Ayarlar ekranından bildirimleri kapatabilirsiniz.

    "Onaylıyorum" diyerek bu şartları kabul etmiş sayılırsınız.
    """

    def __init__(self, parent, db: Database, kullanici_id: int = 1):
        super().__init__(parent)
        self.db = db
        self.kullanici_id = kullanici_id
        self.onaylandi = False
        self.title("Konum İzni ve KVKK")
        self.geometry("600x500")
        self.transient(parent)
        self.grab_set()
        self._arayuzu_olustur()

    def _arayuzu_olustur(self) -> None: ...
    def _onayla(self) -> None: ...
    def _reddet(self) -> None: ...
```

**main.py akışı:** uygulama açılışında `db.kullanici_getir(1)` → `kvkk_onay == False` ise `KVKKForm` modal aç, onaylanmazsa uygulama kapansın.

### `ui/settings_form.py`

```python
import tkinter as tk
from tkinter import ttk, messagebox

from database.db_manager import Database
from models.notification_setting import NotificationSetting


class SettingsForm(ttk.Frame):
    """Bildirim tercihleri ekranı."""

    def __init__(self, parent, db: Database, kullanici_id: int = 1):
        super().__init__(parent)
        self.db = db
        self.kullanici_id = kullanici_id
        self._arayuzu_olustur()
        self._ayarlari_yukle()

    def _arayuzu_olustur(self) -> None:
        """Form: SMS aktif (checkbox), E-posta aktif (checkbox),
        Risk eşiği (radio: dusuk/orta/yuksek), Telefon (entry),
        E-posta (entry), Kaydet butonu."""
        ...

    def _ayarlari_yukle(self) -> None: ...
    def _kaydet(self) -> None: ...
```

### Unit Testler

**`tests/test_weather_api.py`** — API mock'lanmadan smoke test (gerçek istek)
**`tests/test_location_service.py`** — DB mock'lu, sabit koordinatlardan oluşturma testleri
**`tests/test_risk_analyzer.py`** — Eşik sınırlarında doğru sonuç (sıcaklık 38.1 → risk var, 37.9 → yok)

### Paketleme

```bash
pyinstaller --onefile --windowed --name HavaDurumu \
  --icon=assets/icon.ico \
  --add-data "database/schema.sql;database" \
  main.py
```

### `README.md` (özet içerik)

- Kurulum: MySQL kurulumu + `pip install -r requirements.txt` + `.env` oluşturma
- İlk çalıştırma: `mysql -u root -p < database/schema.sql` sonra `python main.py`
- Klasör yapısı açıklaması
- Mimari diyagram (VTOC referansı)
- Lisans ve katkıda bulunan ekip

### Bitti Kriterleri — Aşama 8
- [ ] İlk açılışta KVKK ekranı geliyor, onaysız uygulama kapanıyor
- [ ] Ayarlar ekranından bildirim ayarları kaydedilebiliyor ve persist oluyor
- [ ] `pytest tests/` tüm testler geçiyor (en az 4 dosya, her birinde 2+ test)
- [ ] `pyinstaller` ile `.exe` üretilebiliyor
- [ ] `dist/HavaDurumu.exe` başka klasörde çalışıyor (MySQL bağlantısı varsa)
- [ ] `README.md` kurulum adımlarını eksiksiz içeriyor

---

## 9. `main.py` Beklenen Yapı

```python
"""Hava Durumu Yazılımı — Uygulama giriş noktası."""
import logging
from pathlib import Path

import config
from database.db_manager import Database
from services.weather_api import WeatherAPI
from services.location_service import LocationService
from services.risk_analyzer import RiskAnalyzer
from services.notification_service import NotificationService
from services.background_scheduler import BackgroundScheduler
from ui.main_form import MainForm
from ui.kvkk_form import KVKKForm


def loglama_kur() -> None: ...

def main() -> None:
    loglama_kur()

    # DB bağlantısı
    db = Database(config.DB_HOST, config.DB_PORT, config.DB_USER,
                  config.DB_PASSWORD, config.DB_NAME)
    db.connect()

    # Servisler
    weather_api = WeatherAPI()
    location_service = LocationService(db)
    risk_analyzer = RiskAnalyzer()
    notification_service = NotificationService()
    scheduler = BackgroundScheduler(config.BACKGROUND_INTERVAL_MINUTES)

    # KVKK kontrolü
    user = db.kullanici_getir(1)
    if user is None or not user.kvkk_onay:
        # KVKKForm Tk root gerektirir — geçici root aç
        import tkinter as tk
        gecici = tk.Tk()
        gecici.withdraw()
        kvkk = KVKKForm(gecici, db)
        gecici.wait_window(kvkk)
        if not kvkk.onaylandi:
            db.disconnect()
            return
        gecici.destroy()

    # Ana pencere
    app = MainForm(db, weather_api, location_service)
    app.risk_analyzer = risk_analyzer
    app.notification_service = notification_service
    app.scheduler = scheduler

    try:
        app.mainloop()
    finally:
        scheduler.durdur()
        db.disconnect()


if __name__ == "__main__":
    main()
```

---

## 10. Kod Standartları

- **Türkçe:** Tüm değişken/sınıf/fonksiyon adları kararlaştırıldığı şekilde kalsın.
- **Type hints:** Tüm fonksiyon parametreleri ve dönüş değerleri tip ipuçlu olsun.
- **Docstring:** Her sınıf ve public metot için kısa Türkçe docstring.
- **Yorum satırı:** Karmaşık iş mantığı bloklarında 1-2 satırlık Türkçe yorum (white-box metrik için).
- **try/except:** DB, API, dosya, SMTP işlemlerinin etrafına koy. Yutma — log'la.
- **Logging:** `logging` modülü kullan, `print()` kullanma. Log seviyeleri: `INFO` normal, `WARNING` beklenebilir hata, `ERROR` kritik.
- **Sabit değerler:** Sınıf üst değişkeni olarak tanımla (`ESIK_SICAKLIK_YUKSEK = 38.0` gibi).
- **Connection management:** Database sınıfı context manager (`__enter__`/`__exit__`) olarak da kullanılabilir olmalı.

### Log Formatı
```python
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(Path(config.LOG_DIR) / "app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
```

---

## 11. Sunum (3. Aşama) Hazırlığı

Tüm aşamalar bittiğinde sunumda kullanılacak çıktılar:

### Akış Diyagramları (5 modül için — ayrı slide'lar)
1. **Konum Modülü** — Otomatik (IP) / manuel arama dallanması + DB ekleme
2. **HavaDurumu Modülü** — API çağrısı → doğrulama → DB ekleme/güncelleme
3. **Favoriler Modülü** — Ekleme / Silme / Listeleme / Güncelleme (CRUD baklavası)
4. **Bildirim & Risk Modülü** — Periyodik kontrol → risk var mı → SMS log + e-posta + pop-up
5. **Görselleştirme Modülü** — Sıcaklık / Nem / Rüzgar seçimi → Matplotlib

### Sınıflar (11 adet — slide'da listelenecek)
`Database`, `WeatherAPI`, `LocationService`, `RiskAnalyzer`, `NotificationService`, `BackgroundScheduler`, `Weather`, `Location`, `Favorite`, `NotificationSetting`, `User`

### Formlar (8 adet — her biri için ekran görüntüsü)
`MainForm`, `SearchForm`, `WeatherDisplayForm`, `ChartForm`, `FavoritesForm`, `SettingsForm`, `RiskAlertForm`, `KVKKForm`

### White-box Metrikleri (en sonda hesaplanacak)
Sunum sonunda bu metrikleri toplamak için kullanılacak komut:
```bash
# Toplam satır, yorum satırı, fonksiyon, sınıf vb.
find . -name "*.py" -not -path "./venv/*" -not -path "./tests/*" | xargs wc -l
grep -rn "^\s*#" --include="*.py" . | wc -l                   # yorum satırı
grep -rn "try:" --include="*.py" . | wc -l                    # try-catch
grep -rnE "if |elif " --include="*.py" . | wc -l              # koşul
grep -rnE "for |while " --include="*.py" . | wc -l            # döngü
grep -rn "def " --include="*.py" . | wc -l                    # fonksiyon
```

Sunum slide'ında doldurulacak alanlar:
- Açıklama satırı sayısı: ___
- Try-catch sayısı: ___
- Koşul sayısı: ___
- Döngü sayısı: ___
- Değişken sayısı: ___ (manuel sayım veya `ast` modülüyle)
- Fonksiyon sayısı: ___
- Tekrarlı satır sayısı: ___ (manuel/pylint)
- Toplam satır sayısı: ___

---

## 12. Genel Bitti Checklist (Proje Sonu)

- [ ] `python main.py` ile uygulama açılıyor, ilk açılışta KVKK soruyor
- [ ] Konum otomatik tespit + manuel arama her ikisi de çalışıyor
- [ ] Anlık veri ekranı sıcaklık/nem/rüzgar/basınç gösteriyor
- [ ] Grafik sekmesinde 3 farklı grafik (sıcaklık, nem, rüzgar) çiziliyor
- [ ] Favoriler ekleme/silme çalışıyor, persist oluyor
- [ ] Ayarlar ekranı bildirim tercihlerini DB'ye yazıyor
- [ ] Arka plan thread'i periyodik veri çekiyor, risk anında pop-up + SMS log + e-posta tetikliyor
- [ ] Tüm `tests/` dosyaları geçiyor
- [ ] `pyinstaller` ile `.exe` üretildi, başka klasörde çalışıyor
- [ ] `README.md` eksiksiz, kurulumdan paketlemeye tüm adımları içeriyor
- [ ] Sunum için: her form'un ekran görüntüsü `assets/screenshots/` altında, white-box metrikleri çıkarıldı

---

**Bu döküman tam projenin teknik şartnamesidir. Aşamaları sırayla bitir, her aşama sonunda kriterleri doğrula.**
