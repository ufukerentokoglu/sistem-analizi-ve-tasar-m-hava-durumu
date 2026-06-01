"""Sunum demosu — Edirne için risk uyarısı popup'ını ekrana getirir.

Akış:
  1) Normal uygulamayı başlatır (main.py akışının kısa sürümü).
  2) WeatherAPI.anlik_veri_cek'i yamayla (sadece Edirne için) sentetik fırtına
     verisi döndürecek şekilde değiştirir — gerçek API yerine.
  3) Uygulama açıldıktan ~1 sn sonra Edirne'yi otomatik arar; risk akışı
     RiskAlertForm popup'ını ekrana getirir.

Çalıştırma:
    python3 demo_edirne_uyari.py
"""
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from database.db_manager import Database
from models.location import Location
from models.weather import Weather
from services.background_scheduler import BackgroundScheduler
from services.location_service import LocationService
from services.notification_service import NotificationService
from services.risk_analyzer import RiskAnalyzer
from services.weather_api import WeatherAPI
from ui.kvkk_form import KVKKForm
from ui.main_form import MainForm


def _loglama_kur() -> None:
    log_dosyasi = Path(config.LOG_DIR) / "app.log"
    log_dosyasi.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_dosyasi, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def _edirne_firtina_uret(konum_id: int) -> Weather:
    """Sunum için sahte ama gerçekçi 'şiddetli fırtına' verisi."""
    return Weather(
        konum_id=konum_id,
        olcum_tarihi=datetime.now(),
        sicaklik=19.5,
        hissedilen_sicaklik=17.0,
        nem=88,
        ruzgar_hizi=98.0,        # eşik 60 km/h — yüksek şiddet
        ruzgar_yonu=270,
        basinc=994.0,
        yagis_mm=46.0,           # eşik 20 mm — yoğun yağış
        durum_kodu=95,           # WMO: gök gürültülü fırtına
        durum_aciklamasi="Gök gürültülü fırtına",
        kaynak_api="DEMO",
    )


def _weather_api_yamala(api: WeatherAPI) -> None:
    """Sadece Edirne için sentetik veri döndür, diğer konumlar normal akışta kalsın."""
    gercek_anlik = api.anlik_veri_cek

    def yamali_anlik(location: Location) -> Weather:
        if location.sehir.lower().startswith("edirne"):
            logging.getLogger(__name__).info(
                "[DEMO] Edirne için sentetik fırtına verisi döndürülüyor.")
            return _edirne_firtina_uret(location.id or 0)
        return gercek_anlik(location)

    api.anlik_veri_cek = yamali_anlik  # type: ignore[assignment]


def main() -> int:
    _loglama_kur()
    logger = logging.getLogger(__name__)
    logger.info("[DEMO] Edirne risk uyarısı demosu başlatılıyor…")

    # DB
    db = Database(config.DB_HOST, config.DB_PORT, config.DB_USER,
                  config.DB_PASSWORD, config.DB_NAME)
    try:
        db.connect()
    except Exception as e:
        logger.error("Veritabanına bağlanılamadı: %s", e)
        print(f"\n[HATA] Veritabanına bağlanılamadı: {e}\n"
              "       Demo için MySQL'in çalışıyor ve .env doğru olmalı.")
        return 1

    # KVKK — onaysız geçilemez (main.py ile aynı davranış)
    user = db.kullanici_getir(1)
    if user is None or not user.kvkk_onay:
        import tkinter as tk
        gecici_kok = tk.Tk()
        gecici_kok.withdraw()
        kvkk = KVKKForm(gecici_kok, db)
        gecici_kok.wait_window(kvkk)
        gecici_kok.destroy()
        if not kvkk.onaylandi:
            logger.info("KVKK onaylanmadı; demo kapatılıyor.")
            db.disconnect()
            return 0

    # Servisler
    weather_api = WeatherAPI()
    _weather_api_yamala(weather_api)  # ← demo yaması

    location_service = LocationService(db)
    risk_analyzer = RiskAnalyzer()
    notification_service = NotificationService()
    scheduler = BackgroundScheduler(config.BACKGROUND_INTERVAL_MINUTES)

    app = MainForm(db, weather_api, location_service,
                   risk_analyzer=risk_analyzer,
                   notification_service=notification_service,
                   scheduler=scheduler)

    # Pencere açıldıktan ~1.2 sn sonra Edirne'yi otomatik ara → popup tetiklenir
    def _edirne_ara():
        logger.info("[DEMO] Edirne otomatik aranıyor…")
        try:
            app.aramayi_calistir("Edirne")
        except Exception as e:
            logger.error("[DEMO] Edirne araması başlatılamadı: %s", e)

    app.after(1200, _edirne_ara)

    try:
        app.mainloop()
    finally:
        scheduler.durdur()
        db.disconnect()
        logger.info("[DEMO] Kapatıldı.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
