"""Risk analizi — hava durumu verisini eşiklere göre değerlendirir."""
import logging
from datetime import datetime
from typing import Optional

from models.location import Location
from models.risk_zone import RiskZone
from models.weather import Weather

logger = logging.getLogger(__name__)


class RiskAnalyzer:
    """Hava verisini risk eşiklerine göre değerlendirir."""

    # Eşikler (Türkiye iklimi referans)
    ESIK_SICAKLIK_YUKSEK: float = 38.0      # °C — sıcak hava dalgası
    ESIK_SICAKLIK_DUSUK: float = -10.0      # °C — şiddetli soğuk
    ESIK_RUZGAR_YUKSEK: float = 60.0        # km/h (~17 m/s) — fırtına
    ESIK_YAGIS_YUKSEK: float = 20.0         # mm/saat — sel/yoğun yağış
    FIRTINA_KODLARI: set[int] = {95, 96, 99}  # WMO: gök gürültüsü + dolu

    # "Yüksek" şiddet sınırları (eşikten ne kadar uzaklaşırsa "yuksek" sayılır)
    YUKSEK_SICAK_FARK: float = 5.0    # > 43°C → yüksek
    YUKSEK_RUZGAR_FARK: float = 30.0  # > 90 km/h → yüksek
    YUKSEK_YAGIS_FARK: float = 20.0   # > 40 mm → yüksek

    def degerlendir(self, weather: Weather, location: Location) -> Optional[RiskZone]:
        """Risk varsa RiskZone döndür, yoksa None."""
        if weather is None:
            return None

        risk_tipi: Optional[str] = None
        aciklama_parcalari: list[str] = []

        # 1) Fırtına (WMO kodu) — en kritik
        kod = weather.durum_kodu
        if kod is not None and int(kod) in self.FIRTINA_KODLARI:
            risk_tipi = "firtina"
            aciklama_parcalari.append(
                f"Şiddetli hava olayı kodu: {kod} ({weather.durum_aciklamasi or '-'})"
            )

        # 2) Yüksek sıcaklık
        if weather.sicaklik is not None and weather.sicaklik >= self.ESIK_SICAKLIK_YUKSEK:
            risk_tipi = risk_tipi or "asiri_sicak"
            aciklama_parcalari.append(f"Sıcaklık {weather.sicaklik:.1f}°C")

        # 3) Aşırı düşük sıcaklık
        if weather.sicaklik is not None and weather.sicaklik <= self.ESIK_SICAKLIK_DUSUK:
            risk_tipi = risk_tipi or "asiri_soguk"
            aciklama_parcalari.append(f"Sıcaklık {weather.sicaklik:.1f}°C")

        # 4) Şiddetli rüzgar
        if weather.ruzgar_hizi is not None and weather.ruzgar_hizi >= self.ESIK_RUZGAR_YUKSEK:
            risk_tipi = risk_tipi or "siddetli_ruzgar"
            aciklama_parcalari.append(f"Rüzgâr {weather.ruzgar_hizi:.0f} km/h")

        # 5) Yoğun yağış
        if weather.yagis_mm is not None and weather.yagis_mm >= self.ESIK_YAGIS_YUKSEK:
            risk_tipi = risk_tipi or "yogun_yagis"
            aciklama_parcalari.append(f"Yağış {weather.yagis_mm:.1f} mm")

        if risk_tipi is None:
            return None

        siddet = self._siddet_belirle(weather)
        aciklama = "; ".join(aciklama_parcalari) if aciklama_parcalari else None
        if location.id is None:
            logger.warning("RiskZone üretildi ama konum.id None — DB'ye yazılmayacak.")

        return RiskZone(
            konum_id=location.id or 0,
            risk_tipi=risk_tipi,
            baslangic=weather.olcum_tarihi or datetime.now(),
            siddet=siddet,
            aciklama=aciklama,
        )

    def _siddet_belirle(self, weather: Weather) -> str:
        """'dusuk' | 'orta' | 'yuksek' döner — eşikten uzaklığa göre."""
        # Fırtına kodları → her zaman yüksek
        if weather.durum_kodu is not None and int(weather.durum_kodu) in self.FIRTINA_KODLARI:
            return "yuksek"

        # Sıcak
        if weather.sicaklik is not None:
            if weather.sicaklik >= self.ESIK_SICAKLIK_YUKSEK + self.YUKSEK_SICAK_FARK:
                return "yuksek"
            if weather.sicaklik <= self.ESIK_SICAKLIK_DUSUK - self.YUKSEK_SICAK_FARK:
                return "yuksek"

        # Rüzgar
        if weather.ruzgar_hizi is not None and \
                weather.ruzgar_hizi >= self.ESIK_RUZGAR_YUKSEK + self.YUKSEK_RUZGAR_FARK:
            return "yuksek"

        # Yağış
        if weather.yagis_mm is not None and \
                weather.yagis_mm >= self.ESIK_YAGIS_YUKSEK + self.YUKSEK_YAGIS_FARK:
            return "yuksek"

        # Eşiğe en az birinde takıldı → orta varsayılan
        # Düşük: eşiğin çok az altı / üstü — burada zaten tetiklenmiş demek ki "orta"
        return "orta"
