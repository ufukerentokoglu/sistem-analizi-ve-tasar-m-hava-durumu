"""Konum servisi — IP geolocation ve manuel şehir/ilçe arama."""
import logging
from typing import Optional

import geocoder

from database.db_manager import Database
from models.location import Location

logger = logging.getLogger(__name__)


class LocationService:
    """IP geolocation + manuel konum arama servisi."""

    # Türkiye'nin başlıca şehirleri — manuel arama için fallback koordinatları.
    # Anahtarlar lower-case, Türkçe karakterler dahil; arama normalize ederek bakar.
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
        "mersin": (36.8121, 34.6415),
        "kayseri": (38.7322, 35.4853),
        "eskisehir": (39.7767, 30.5206),
        "diyarbakir": (37.9144, 40.2306),
        "samsun": (41.2867, 36.3300),
        "trabzon": (41.0015, 39.7178),
        "erzurum": (39.9000, 41.2700),
        "malatya": (38.3552, 38.3095),
        "sanliurfa": (37.1591, 38.7969),
        "van": (38.4942, 43.3800),
        "balikesir": (39.6484, 27.8826),
        "manisa": (38.6191, 27.4289),
        "sakarya": (40.7569, 30.3783),
        "tekirdag": (40.9833, 27.5167),
        "denizli": (37.7765, 29.0864),
        "mugla": (37.2153, 28.3636),
        "aydin": (37.8560, 27.8416),
        "tokat": (40.3167, 36.5500),
        "afyonkarahisar": (38.7507, 30.5567),
        "rize": (41.0201, 40.5234),
        "edirne": (41.6760, 26.5556),
    }

    def __init__(self, db: Database):
        self.db = db

    # ----- IP tabanlı tespit -----
    def otomatik_konum_tespit(self) -> Optional[Location]:
        """IP üzerinden kullanıcının konumunu tespit eder. İnternet yoksa None."""
        try:
            g = geocoder.ip("me")
            # geocoder ok flag'i bağlantı + cevabın geçerliliğini birlikte kapsar
            if not g.ok or not g.latlng:
                logger.warning("IP geolocation başarısız (ok=False veya koordinat yok).")
                return None
            return Location(
                sehir=g.city or "Bilinmeyen",
                ilce=None,
                ulke=g.country or "Türkiye",
                latitude=float(g.latlng[0]),
                longitude=float(g.latlng[1]),
            )
        except Exception as e:
            # geocoder ağ hatalarında requests exceptions fırlatabiliyor — yutup None dönüyoruz.
            logger.warning("IP geolocation hatası: %s", e)
            return None

    # ----- Manuel arama -----
    def manuel_konum_ara(self, sehir: str, ilce: Optional[str] = None) -> Optional[Location]:
        """Şehir/ilçe adıyla DB'de arar, yoksa SEHIR_KOORDINATLARI'ndan oluşturup ekler."""
        if not sehir or not sehir.strip():
            return None

        sehir_temiz = sehir.strip()
        ilce_temiz = ilce.strip() if ilce and ilce.strip() else None

        # 1) Önce DB
        try:
            loc = self.db.konum_ara(sehir_temiz, ilce_temiz)
        except Exception as e:
            logger.error("DB konum arama hatası: %s", e)
            loc = None
        if loc:
            return loc

        # 2) Sabit dict — Türkçe karakterleri normalize ederek bak
        anahtar = self._normalize(sehir_temiz)
        if anahtar in self.SEHIR_KOORDINATLARI:
            lat, lon = self.SEHIR_KOORDINATLARI[anahtar]
            yeni = Location(sehir=sehir_temiz, ilce=ilce_temiz, latitude=lat, longitude=lon)
            try:
                konum_id = self.db.konum_ekle(yeni)
                yeni.id = konum_id
            except Exception as e:
                # DB hatası olsa bile koordinatları olan Location'ı geri verelim;
                # sonraki çağrıda yeniden denenebilir.
                logger.error("Konum DB'ye yazılamadı: %s", e)
            return yeni

        return None

    def konum_kaydet(self, location: Location) -> Location:
        """Konumu DB'ye ekler/günceller, id atanmış nesneyi döner."""
        try:
            konum_id = self.db.konum_ekle(location)
            location.id = konum_id
        except Exception as e:
            logger.error("Konum kaydetme hatası: %s", e)
            raise
        return location

    # ----- Yardımcı -----
    @staticmethod
    def _normalize(metin: str) -> str:
        """Şehir adını sabit sözlükle eşleştirmek için normalize eder
        (lower-case + Türkçe karakter dönüşümü + boşluk temizliği)."""
        cevirici = str.maketrans({
            "ı": "i", "İ": "i",
            "ş": "s", "Ş": "s",
            "ç": "c", "Ç": "c",
            "ğ": "g", "Ğ": "g",
            "ü": "u", "Ü": "u",
            "ö": "o", "Ö": "o",
        })
        return metin.translate(cevirici).lower().strip()
