"""Hava Durumu Yazılımı — uygulama giriş noktası."""
import logging
import sys
from pathlib import Path

import config
from database.db_manager import Database
from services.background_scheduler import BackgroundScheduler
from services.location_service import LocationService
from services.notification_service import NotificationService
from services.risk_analyzer import RiskAnalyzer
from services.weather_api import WeatherAPI
from ui.kvkk_form import KVKKForm
from ui.main_form import MainForm


def loglama_kur() -> None:
    """logs/app.log + konsola ortak log yazımı."""
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


def main() -> None:
    loglama_kur()
    logger = logging.getLogger(__name__)
    logger.info("Uygulama başlatılıyor: %s", config.APP_NAME)

    # Veritabanı bağlantısı
    db = Database(config.DB_HOST, config.DB_PORT, config.DB_USER,
                  config.DB_PASSWORD, config.DB_NAME)
    try:
        db.connect()
    except Exception as e:
        logger.error("Veritabanına bağlanılamadı: %s", e)
        sys.exit(1)

    # KVKK kontrolü — onaysız uygulama açılmaz
    user = db.kullanici_getir(1)
    if user is None or not user.kvkk_onay:
        import tkinter as tk
        gecici_kok = tk.Tk()
        gecici_kok.withdraw()
        kvkk = KVKKForm(gecici_kok, db)
        gecici_kok.wait_window(kvkk)
        gecici_kok.destroy()
        if not kvkk.onaylandi:
            logger.info("KVKK onaylanmadı; uygulama kapatılıyor.")
            db.disconnect()
            return

    # Servisler
    weather_api = WeatherAPI()
    location_service = LocationService(db)
    risk_analyzer = RiskAnalyzer()
    notification_service = NotificationService()
    scheduler = BackgroundScheduler(config.BACKGROUND_INTERVAL_MINUTES)

    # Ana pencere — tüm servisler constructor'a inject ediliyor
    app = MainForm(db, weather_api, location_service,
                   risk_analyzer=risk_analyzer,
                   notification_service=notification_service,
                   scheduler=scheduler)
    try:
        app.mainloop()
    finally:
        # WM_DELETE_WINDOW kancası scheduler'ı zaten durdurdu; yine de güvence:
        scheduler.durdur()
        db.disconnect()
        logger.info("Uygulama kapatıldı.")


if __name__ == "__main__":
    main()
