"""Uygulama yapılandırması — .env dosyasından ayarları yükler ve modül seviyesinde sunar."""
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Proje kök dizini (.env arama noktası).
# PyInstaller bundle'ında __file__ geçici çıkarım dizinindedir; gerçek "kullanıcının yanı"
# sys.executable'ın klasörüdür. Frozen kontrolüyle doğru yere bakıyoruz.
if getattr(sys, "frozen", False):
    _PROJE_KOK = Path(sys.executable).resolve().parent
else:
    _PROJE_KOK = Path(__file__).resolve().parent
_ENV_DOSYASI = _PROJE_KOK / ".env"
_ENV_ORNEK = _PROJE_KOK / ".env.example"

# .env yoksa açıklayıcı uyarı ver, .env.example'dan geriye düşmeye çalış
if _ENV_DOSYASI.exists():
    load_dotenv(_ENV_DOSYASI)
elif _ENV_ORNEK.exists():
    # .env.example bulundu ama .env yok — geliştirici uyarısı (test ortamı için izin veriyoruz)
    logging.warning(
        ".env dosyası bulunamadı. Lütfen '.env.example' dosyasını '.env' olarak "
        "kopyalayıp kendi değerlerinizi doldurun. Şimdilik .env.example yükleniyor."
    )
    load_dotenv(_ENV_ORNEK)
else:
    logging.warning(".env veya .env.example bulunamadı; sadece sistem ortam değişkenleri kullanılacak.")


def _env_str(anahtar: str, varsayilan: str = "") -> str:
    """String tipinde ortam değişkeni okur."""
    return os.getenv(anahtar, varsayilan)


def _env_int(anahtar: str, varsayilan: int) -> int:
    """Integer tipinde ortam değişkeni okur, dönüşüm hatasında varsayılana düşer."""
    ham = os.getenv(anahtar)
    if ham is None or ham.strip() == "":
        return varsayilan
    try:
        return int(ham)
    except ValueError:
        logging.warning("'%s' değeri int'e çevrilemedi: %r — varsayılan %s kullanılacak.",
                        anahtar, ham, varsayilan)
        return varsayilan


# ---- MySQL Veritabanı ----
DB_HOST: str = _env_str("DB_HOST", "localhost")
DB_PORT: int = _env_int("DB_PORT", 3306)
DB_USER: str = _env_str("DB_USER", "root")
DB_PASSWORD: str = _env_str("DB_PASSWORD", "")
DB_NAME: str = _env_str("DB_NAME", "havadurumu")

# Zorunlu DB alanları eksikse çalışma zamanı hatası
_eksik_db_alanlari: list[str] = []
if not DB_HOST:
    _eksik_db_alanlari.append("DB_HOST")
if not DB_USER:
    _eksik_db_alanlari.append("DB_USER")
if not DB_NAME:
    _eksik_db_alanlari.append("DB_NAME")
if _eksik_db_alanlari:
    raise RuntimeError(
        f"Veritabanı yapılandırması eksik: {', '.join(_eksik_db_alanlari)}. "
        f"Lütfen .env dosyasını kontrol edin."
    )

# ---- SMTP ----
SMTP_HOST: str = _env_str("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT: int = _env_int("SMTP_PORT", 587)
SMTP_USER: str = _env_str("SMTP_USER", "")
SMTP_PASSWORD: str = _env_str("SMTP_PASSWORD", "")
SMTP_FROM_NAME: str = _env_str("SMTP_FROM_NAME", "Hava Durumu Uygulaması")

# SMTP kullanıcı/şifre boşsa e-posta gönderimi devre dışı sayılır
EMAIL_GONDERIMI_AKTIF: bool = bool(SMTP_USER and SMTP_PASSWORD)
if not EMAIL_GONDERIMI_AKTIF:
    logging.warning(
        "SMTP kullanıcı/şifre tanımlı değil; e-posta gönderimi devre dışı. "
        "Gerçek e-posta için .env içinde SMTP_USER ve SMTP_PASSWORD doldurun."
    )

# ---- Open-Meteo ----
OPEN_METEO_BASE_URL: str = _env_str("OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1/forecast")
OPEN_METEO_TIMEZONE: str = _env_str("OPEN_METEO_TIMEZONE", "Europe/Istanbul")

# ---- Arka plan ----
BACKGROUND_INTERVAL_MINUTES: int = _env_int("BACKGROUND_INTERVAL_MINUTES", 5)

# ---- Genel ----
APP_NAME: str = _env_str("APP_NAME", "Hava Durumu Yazılımı")
LOG_DIR: str = _env_str("LOG_DIR", "logs")
LOG_LEVEL: str = _env_str("LOG_LEVEL", "INFO").upper()

# LOG_DIR yoksa oluştur (logs/ altına sms_log.txt vb. yazılacak)
_log_yolu = _PROJE_KOK / LOG_DIR
try:
    _log_yolu.mkdir(parents=True, exist_ok=True)
except OSError as e:
    logging.error("Log dizini oluşturulamadı (%s): %s", _log_yolu, e)
