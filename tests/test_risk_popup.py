"""Aşama 7 — UI risk akışı: yüksek sıcaklık inject et, pop-up açıldı mı, SMS log düştü mü?"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from database.db_manager import Database
from models.location import Location
from models.weather import Weather
from services.background_scheduler import BackgroundScheduler
from services.location_service import LocationService
from services.notification_service import NotificationService
from services.risk_analyzer import RiskAnalyzer
from services.weather_api import WeatherAPI


def test_risk_akisi_pop_up_ve_sms_log():
    import tkinter as tk
    try:
        kontrol = tk.Tk()
        kontrol.withdraw()
        kontrol.destroy()
    except tk.TclError as e:
        print(f"⚠ Display yok, atlanıyor: {e}")
        return

    from ui.main_form import MainForm
    from ui.risk_alert_form import RiskAlertForm

    db = Database(config.DB_HOST, config.DB_PORT, config.DB_USER,
                  config.DB_PASSWORD, config.DB_NAME)
    db.connect()

    # İzole SMS log dosyası — testin etkilenmemesi için
    test_log = Path(__file__).resolve().parent.parent / "logs" / "sms_test_popup.txt"
    if test_log.exists():
        test_log.unlink()

    # Kullanıcıya bir telefon ata (SMS log için gerekli) — sonra geri al
    onceki_telefon = None
    user_oncesi = db.kullanici_getir(1)
    if user_oncesi:
        onceki_telefon = user_oncesi.telefon
        user_oncesi.telefon = "+905551234567"
        db.kullanici_guncelle(user_oncesi)
    # Bildirim ayarını da varsayılana çek — başka bir test sms_aktif=False bırakmış olabilir
    from models.notification_setting import NotificationSetting
    db.bildirim_ayari_guncelle(NotificationSetting(
        kullanici_id=1, sms_aktif=True, email_aktif=True,
        risk_esigi="orta", bildirim_tipi="tum",
    ))

    try:
        notif = NotificationService(sms_log_path=test_log)
        sched = BackgroundScheduler(interval_minutes=1)
        app = MainForm(db, WeatherAPI(), LocationService(db),
                       risk_analyzer=RiskAnalyzer(),
                       notification_service=notif,
                       scheduler=sched)

        durum = {"popup_acildi": False}

        # Önce bir konum ayarla (favori/risk DB id gerektiriyor)
        def adim_konum():
            svc = LocationService(db)
            loc = svc.manuel_konum_ara("Adana")
            assert loc is not None and loc.id is not None
            app.aktif_konumu_guncelle(loc)
            # Yüksek sıcaklık ölçümü inject et
            risk_weather = Weather(
                konum_id=loc.id, olcum_tarihi=datetime.now(),
                sicaklik=42.5, nem=20, ruzgar_hizi=10.0, durum_kodu=0,
                durum_aciklamasi="Açık", kaynak_api="Open-Meteo",
            )
            # _risk_kontrol_et'i doğrudan çağır — pop-up açılmalı, SMS log düşmeli
            app._risk_kontrol_et(loc, risk_weather, kullanici_etkilesimi=True)

        def adim_pop_up_kontrol():
            # MainForm'un child'ları arasında RiskAlertForm var mı?
            for w in app.winfo_children():
                if isinstance(w, RiskAlertForm):
                    durum["popup_acildi"] = True
                    # Pop-up'ı kapat ki mainloop devam etsin
                    w.destroy()
                    break
            # Toplevel pencereler tk.Toplevel olarak ayrı bir hiyerarşi olabilir;
            # winfo_children genellikle yakalar ama yedek için döngüyü genişletelim:
            if not durum["popup_acildi"]:
                # tk.toplevel'lar app.tk.call('wm', 'stackorder', '.') ile listelenebilir
                # Daha basit: tüm widget'ları gez
                def gez(parent_w):
                    if isinstance(parent_w, RiskAlertForm):
                        durum["popup_acildi"] = True
                        parent_w.destroy()
                        return True
                    for ch in parent_w.winfo_children():
                        if gez(ch):
                            return True
                    return False
                gez(app)

        def adim_kapan():
            app._kapat()

        app.after(500, adim_konum)
        app.after(2500, adim_pop_up_kontrol)
        app.after(4000, adim_kapan)
        app.mainloop()

        # Doğrulamalar
        assert durum["popup_acildi"], "RiskAlertForm pop-up'ı açılmadı"
        assert test_log.exists(), "SMS log dosyası oluşmadı"
        icerik = test_log.read_text(encoding="utf-8")
        assert "+905551234567" in icerik
        assert "Adana" in icerik or "asiri_sicak" in icerik or "sıcak" in icerik.lower(), \
            f"SMS log içeriği beklenenden farklı:\n{icerik}"

        # DB'de risk kaydı var mı?
        riskler = db.fetch_all(
            "SELECT * FROM RiskliBolgeler WHERE risk_tipi='asiri_sicak' "
            "ORDER BY id DESC LIMIT 1"
        )
        assert len(riskler) >= 1, "RiskliBolgeler tablosuna risk kaydı düşmedi"

        # Scheduler temiz kapandı mı?
        assert sched.thread is None or not sched.thread.is_alive(), \
            "Scheduler thread'i kapanmadı"
        print("✓ Aşama 7 UI risk akışı testi başarılı")
    finally:
        # Telefonu eski haline döndür
        if user_oncesi is not None:
            user_oncesi.telefon = onceki_telefon
            db.kullanici_guncelle(user_oncesi)
        if test_log.exists():
            test_log.unlink()
        db.disconnect()


def main():
    test_risk_akisi_pop_up_ve_sms_log()


if __name__ == "__main__":
    main()
