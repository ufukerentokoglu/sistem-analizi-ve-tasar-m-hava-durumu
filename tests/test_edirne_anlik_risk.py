"""Edirne — anlık risk uyarısı entegrasyon testi.

Üç adım:
  1) Open-Meteo'dan Edirne için ANLIK veri çek.
  2) RiskAnalyzer ile değerlendir, sonucu yazdır.
  3) Eşik aşan SENTETİK senaryo ile NotificationService.sms_gonder akışını uçtan uca dene.
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.location import Location
from models.risk_zone import RiskZone
from models.user import User
from models.weather import Weather
from services.location_service import LocationService
from services.notification_service import NotificationService
from services.risk_analyzer import RiskAnalyzer
from services.weather_api import WeatherAPI


EDIRNE = Location(
    sehir="Edirne",
    latitude=41.6760,
    longitude=26.5556,
    ulke="Türkiye",
    id=999,  # DB'siz çalışıyoruz; sahte id yeterli
)


def _bolum(baslik: str) -> None:
    print("\n" + "=" * 60)
    print(baslik)
    print("=" * 60)


def adim1_anlik_veri_ve_risk() -> tuple[Weather, RiskZone | None]:
    _bolum("ADIM 1 — Edirne için Open-Meteo anlık verisi")
    api = WeatherAPI()
    weather = api.anlik_veri_cek(EDIRNE)
    print(f"Ölçüm zamanı : {weather.olcum_tarihi}")
    print(f"Sıcaklık     : {weather.sicaklik} °C  (hissedilen {weather.hissedilen_sicaklik} °C)")
    print(f"Nem          : {weather.nem} %")
    print(f"Rüzgâr       : {weather.ruzgar_hizi} km/h, yön {weather.ruzgar_yonu}°")
    print(f"Yağış        : {weather.yagis_mm} mm")
    print(f"Basınç       : {weather.basinc} hPa")
    print(f"WMO kodu     : {weather.durum_kodu} → {weather.durum_aciklamasi}")

    analyzer = RiskAnalyzer()
    risk = analyzer.degerlendir(weather, EDIRNE)
    if risk is None:
        print("\n→ Anlık veride risk eşiği aşılmadı. UYARI ÜRETİLMEDİ.")
    else:
        print(f"\n⚠ ANLIK RİSK TESPİT EDİLDİ")
        print(f"   Risk tipi  : {risk.risk_tipi}")
        print(f"   Şiddet     : {risk.siddet}")
        print(f"   Başlangıç  : {risk.baslangic}")
        print(f"   Açıklama   : {risk.aciklama}")
    return weather, risk


def adim2_senaryo_bildirim() -> None:
    _bolum("ADIM 2 — Eşik üstü senaryo + SMS bildirim simülasyonu")

    # Eşikleri aşan sentetik bir hava durumu (fırtına kodu + yoğun yağış + güçlü rüzgâr)
    senaryo = Weather(
        konum_id=EDIRNE.id,
        olcum_tarihi=datetime.now(),
        sicaklik=22.0,
        ruzgar_hizi=95.0,    # 60 km/h eşiğinin üstü (yüksek)
        yagis_mm=42.0,       # 20 mm eşiğinin üstü (yüksek)
        durum_kodu=95,       # WMO gök gürültülü fırtına
        durum_aciklamasi="Gök gürültülü fırtına",
        kaynak_api="SENARYO",
    )
    print(f"Senaryo: kod={senaryo.durum_kodu}, rüzgâr={senaryo.ruzgar_hizi} km/h, "
          f"yağış={senaryo.yagis_mm} mm")

    analyzer = RiskAnalyzer()
    risk = analyzer.degerlendir(senaryo, EDIRNE)
    assert risk is not None, "Senaryo risk üretmeliydi"
    print(f"→ Risk: {risk.risk_tipi} ({risk.siddet}) — {risk.aciklama}")

    # SMS log dosyasına bildirimi yaz
    log_dosyasi = Path(__file__).resolve().parent.parent / "logs" / "edirne_test_sms.txt"
    if log_dosyasi.exists():
        log_dosyasi.unlink()

    svc = NotificationService(sms_log_path=log_dosyasi)
    user = User(
        id=1,
        ad="Test Kullanıcı",
        email="kullanici@example.com",
        telefon="+905551112233",
    )
    sonuc = svc.risk_bildirimi_gonder(
        user, risk, EDIRNE,
        sms_aktif=True,
        email_aktif=True,
    )
    print(f"Bildirim sonucu: SMS={sonuc['sms']}, E-posta={sonuc['email']}")
    assert sonuc["sms"] is True, "SMS log dosyasına yazılamadı"

    print("\n--- SMS log içeriği ---")
    print(log_dosyasi.read_text(encoding="utf-8").rstrip())
    print("-----------------------")


def main() -> int:
    print(f"Hedef bölge: {EDIRNE.sehir} (lat={EDIRNE.latitude}, lon={EDIRNE.longitude})")
    try:
        adim1_anlik_veri_ve_risk()
    except Exception as e:
        print(f"\n[HATA] Anlık veri çekilemedi: {e}")
        print("       (İnternet bağlantısı veya Open-Meteo erişimini kontrol edin.)")
        # Senaryo testi yine de çalıştırılabilir
    adim2_senaryo_bildirim()
    print("\n✓ Edirne anlık risk uyarısı testi tamamlandı.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
