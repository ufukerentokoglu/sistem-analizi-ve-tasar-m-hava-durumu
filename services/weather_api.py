"""Open-Meteo API istemcisi — anlık, saatlik ve günlük hava durumu verisi çeker."""
import logging
from datetime import datetime
from typing import Optional

import requests

import config
from models.location import Location
from models.weather import Weather

logger = logging.getLogger(__name__)


class WeatherAPI:
    """Open-Meteo API istemcisi."""

    BASE_URL: str = config.OPEN_METEO_BASE_URL
    TIMEOUT: int = 10  # saniye

    # Anlık endpoint'inden istenecek değişkenler (Open-Meteo isimlendirmesi).
    CURRENT_VARS: str = (
        "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,"
        "precipitation,weather_code,wind_speed_10m,wind_direction_10m,"
        "surface_pressure"
    )
    HOURLY_VARS: str = (
        "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,"
        "wind_direction_10m,weather_code,surface_pressure,apparent_temperature"
    )
    DAILY_VARS: str = (
        "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code,"
        "wind_speed_10m_max"
    )

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

    # ----- Yüksek seviye -----
    def anlik_veri_cek(self, location: Location) -> Weather:
        """Verilen konum için anlık hava durumunu döndürür."""
        params = {
            "latitude": float(location.latitude),
            "longitude": float(location.longitude),
            "current": self.CURRENT_VARS,
            "timezone": self.timezone,
            "wind_speed_unit": "kmh",
        }
        # Open-Meteo "current" alt-nesnesinde anlık değerleri verir.
        veri = self._istek_at(params)
        current = veri.get("current") or {}
        if not current:
            raise RuntimeError("Open-Meteo cevabında 'current' alanı yok.")

        olcum_tarihi = self._zaman_parse(current.get("time")) or datetime.now()
        kod = current.get("weather_code")
        return Weather(
            konum_id=location.id or 0,  # caller henüz DB id atamamış olabilir
            olcum_tarihi=olcum_tarihi,
            sicaklik=self._float_yoksa(current.get("temperature_2m")),
            hissedilen_sicaklik=self._float_yoksa(current.get("apparent_temperature")),
            nem=self._int_yoksa(current.get("relative_humidity_2m")),
            ruzgar_hizi=self._float_yoksa(current.get("wind_speed_10m")),
            ruzgar_yonu=self._int_yoksa(current.get("wind_direction_10m")),
            basinc=self._float_yoksa(current.get("surface_pressure")),
            yagis_mm=self._float_yoksa(current.get("precipitation")),
            durum_kodu=self._int_yoksa(kod),
            durum_aciklamasi=self.kod_aciklamasi(kod) if kod is not None else None,
            kaynak_api="Open-Meteo",
        )

    def saatlik_tahmin_cek(self, location: Location, saat_sayisi: int = 24) -> list[Weather]:
        """Önümüzdeki N saat için tahminleri döndürür."""
        if saat_sayisi <= 0:
            return []

        # Saatlik veri günün başından başlar; "şimdi"den N saat istemek için
        # bugünün geri kalanı + ekstra günler gerekebilir → +1 gün tampon ekle.
        forecast_days = max(1, (saat_sayisi + 23) // 24 + 1)
        params = {
            "latitude": float(location.latitude),
            "longitude": float(location.longitude),
            "hourly": self.HOURLY_VARS,
            "timezone": self.timezone,
            "forecast_days": min(forecast_days, 16),  # API üst sınırı
            "wind_speed_unit": "kmh",
        }
        veri = self._istek_at(params)
        hourly = veri.get("hourly") or {}
        zamanlar = hourly.get("time") or []
        if not zamanlar:
            raise RuntimeError("Open-Meteo cevabında 'hourly.time' yok.")

        # Şu anki saatten itibaren ilk N kaydı al.
        simdi = datetime.now()
        baslangic_idx = 0
        for i, zaman_str in enumerate(zamanlar):
            zaman = self._zaman_parse(zaman_str)
            if zaman is not None and zaman >= simdi.replace(minute=0, second=0, microsecond=0):
                baslangic_idx = i
                break

        bitis_idx = min(baslangic_idx + saat_sayisi, len(zamanlar))
        sonuc: list[Weather] = []
        for i in range(baslangic_idx, bitis_idx):
            kod = self._liste_eleman(hourly, "weather_code", i)
            sonuc.append(Weather(
                konum_id=location.id or 0,
                olcum_tarihi=self._zaman_parse(zamanlar[i]) or simdi,
                sicaklik=self._float_yoksa(self._liste_eleman(hourly, "temperature_2m", i)),
                hissedilen_sicaklik=self._float_yoksa(
                    self._liste_eleman(hourly, "apparent_temperature", i)),
                nem=self._int_yoksa(self._liste_eleman(hourly, "relative_humidity_2m", i)),
                ruzgar_hizi=self._float_yoksa(self._liste_eleman(hourly, "wind_speed_10m", i)),
                ruzgar_yonu=self._int_yoksa(self._liste_eleman(hourly, "wind_direction_10m", i)),
                basinc=self._float_yoksa(self._liste_eleman(hourly, "surface_pressure", i)),
                yagis_mm=self._float_yoksa(self._liste_eleman(hourly, "precipitation", i)),
                durum_kodu=self._int_yoksa(kod),
                durum_aciklamasi=self.kod_aciklamasi(kod) if kod is not None else None,
                kaynak_api="Open-Meteo",
            ))
        return sonuc

    def gunluk_tahmin_cek(self, location: Location, gun_sayisi: int = 7) -> list[Weather]:
        """Önümüzdeki N gün için günlük tahminleri döndürür."""
        if gun_sayisi <= 0:
            return []

        params = {
            "latitude": float(location.latitude),
            "longitude": float(location.longitude),
            "daily": self.DAILY_VARS,
            "timezone": self.timezone,
            "forecast_days": min(gun_sayisi, 16),
            "wind_speed_unit": "kmh",
        }
        veri = self._istek_at(params)
        daily = veri.get("daily") or {}
        zamanlar = daily.get("time") or []
        if not zamanlar:
            raise RuntimeError("Open-Meteo cevabında 'daily.time' yok.")

        sonuc: list[Weather] = []
        for i in range(min(gun_sayisi, len(zamanlar))):
            tarih = self._zaman_parse(zamanlar[i]) or datetime.now()
            kod = self._liste_eleman(daily, "weather_code", i)
            # Günlük min/max'ten "sicaklik" olarak max'ı yazıyoruz; gerçek "hissedilen" yok.
            max_s = self._float_yoksa(self._liste_eleman(daily, "temperature_2m_max", i))
            min_s = self._float_yoksa(self._liste_eleman(daily, "temperature_2m_min", i))
            sonuc.append(Weather(
                konum_id=location.id or 0,
                olcum_tarihi=tarih,
                sicaklik=max_s,
                hissedilen_sicaklik=min_s,  # günlük: hissedilen alanını min sıcaklık taşır
                ruzgar_hizi=self._float_yoksa(self._liste_eleman(daily, "wind_speed_10m_max", i)),
                yagis_mm=self._float_yoksa(self._liste_eleman(daily, "precipitation_sum", i)),
                durum_kodu=self._int_yoksa(kod),
                durum_aciklamasi=self.kod_aciklamasi(kod) if kod is not None else None,
                kaynak_api="Open-Meteo",
            ))
        return sonuc

    @classmethod
    def kod_aciklamasi(cls, weather_code: Optional[int]) -> str:
        """WMO weather code → Türkçe açıklama."""
        if weather_code is None:
            return "Bilinmiyor"
        try:
            return cls.WEATHER_CODES.get(int(weather_code), "Bilinmiyor")
        except (TypeError, ValueError):
            return "Bilinmiyor"

    # ----- Düşük seviye -----
    def _istek_at(self, params: dict) -> dict:
        """Düşük seviye GET isteği. Ağ/HTTP hatalarını RuntimeError'a çevirir."""
        try:
            r = requests.get(self.base_url, params=params, timeout=self.TIMEOUT)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            logger.error("Open-Meteo isteği başarısız: %s", e)
            raise RuntimeError(f"Open-Meteo isteği başarısız: {e}") from e
        except ValueError as e:
            # JSON parse hatası
            logger.error("Open-Meteo cevabı JSON olarak ayrıştırılamadı: %s", e)
            raise RuntimeError(f"Open-Meteo cevabı çözümlenemedi: {e}") from e

    # ----- Yardımcılar -----
    @staticmethod
    def _zaman_parse(zaman_str: Optional[str]) -> Optional[datetime]:
        """Open-Meteo ISO-8601 zaman dizisini datetime'a çevirir ('2025-05-22T14:00')."""
        if not zaman_str:
            return None
        try:
            return datetime.fromisoformat(zaman_str)
        except ValueError:
            return None

    @staticmethod
    def _float_yoksa(deger) -> Optional[float]:
        """None değilse float'a çevirir."""
        if deger is None:
            return None
        try:
            return float(deger)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _int_yoksa(deger) -> Optional[int]:
        """None değilse yuvarlayarak int'e çevirir."""
        if deger is None:
            return None
        try:
            return int(round(float(deger)))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _liste_eleman(blok: dict, anahtar: str, indeks: int):
        """hourly/daily listesinden güvenli okuma — eksik veride None döner."""
        liste = blok.get(anahtar) or []
        if 0 <= indeks < len(liste):
            return liste[indeks]
        return None
