"""Aşama 7 — RiskAnalyzer eşik testleri + NotificationService SMS log + Scheduler tetiklenme."""
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.location import Location
from models.user import User
from models.weather import Weather
from services.background_scheduler import BackgroundScheduler
from services.notification_service import NotificationService
from services.risk_analyzer import RiskAnalyzer


# ========= RiskAnalyzer eşikleri =========

def _loc() -> Location:
    return Location(id=1, sehir="Test", latitude=0.0, longitude=0.0)


def test_sicaklik_esik_uzeri_risk_var():
    """38.1 → risk var (orta), 43.0 → risk var (yüksek)."""
    a = RiskAnalyzer()
    risk1 = a.degerlendir(Weather(konum_id=1, olcum_tarihi=datetime.now(), sicaklik=38.1), _loc())
    assert risk1 is not None
    assert risk1.risk_tipi == "asiri_sicak"
    assert risk1.siddet in ("orta", "yuksek")

    risk2 = a.degerlendir(Weather(konum_id=1, olcum_tarihi=datetime.now(), sicaklik=43.5), _loc())
    assert risk2 is not None and risk2.siddet == "yuksek"


def test_sicaklik_esik_alti_risk_yok():
    """37.9 → risk yok."""
    a = RiskAnalyzer()
    risk = a.degerlendir(Weather(konum_id=1, olcum_tarihi=datetime.now(), sicaklik=37.9), _loc())
    assert risk is None


def test_firtina_kodu_her_zaman_yuksek():
    """WMO 95/96/99 → her zaman yüksek şiddet."""
    a = RiskAnalyzer()
    for kod in (95, 96, 99):
        risk = a.degerlendir(
            Weather(konum_id=1, olcum_tarihi=datetime.now(), sicaklik=20.0, durum_kodu=kod),
            _loc(),
        )
        assert risk is not None and risk.siddet == "yuksek", f"kod {kod} için yüksek bekleniyordu"
        assert risk.risk_tipi == "firtina"


def test_ruzgar_ve_yagis_esikleri():
    """Rüzgâr ≥60 km/h ve yağış ≥20 mm risk üretmeli."""
    a = RiskAnalyzer()
    r1 = a.degerlendir(
        Weather(konum_id=1, olcum_tarihi=datetime.now(), sicaklik=20.0, ruzgar_hizi=65.0),
        _loc(),
    )
    assert r1 is not None and r1.risk_tipi == "siddetli_ruzgar"
    r2 = a.degerlendir(
        Weather(konum_id=1, olcum_tarihi=datetime.now(), sicaklik=20.0, yagis_mm=25.0),
        _loc(),
    )
    assert r2 is not None and r2.risk_tipi == "yogun_yagis"


def test_dusuk_sicaklik_riski():
    """-12°C → asiri_soguk."""
    a = RiskAnalyzer()
    r = a.degerlendir(
        Weather(konum_id=1, olcum_tarihi=datetime.now(), sicaklik=-12.0), _loc()
    )
    assert r is not None and r.risk_tipi == "asiri_soguk"


# ========= NotificationService — SMS log dosyası =========

def test_sms_log_dosyasina_yaziyor(tmp_path: Path = None):
    """sms_gonder log dosyasına satır ekliyor mu?"""
    log_dosyasi = Path(__file__).resolve().parent.parent / "logs" / "sms_log_test.txt"
    if log_dosyasi.exists():
        log_dosyasi.unlink()
    svc = NotificationService(sms_log_path=log_dosyasi)
    ok = svc.sms_gonder("+905551234567", "Test mesajı — fırtına uyarısı")
    assert ok is True
    assert log_dosyasi.exists()
    icerik = log_dosyasi.read_text(encoding="utf-8")
    assert "+905551234567" in icerik
    assert "Test mesajı" in icerik
    log_dosyasi.unlink()  # temizlik


def test_risk_bildirimi_sms_ve_email_dict():
    """risk_bildirimi_gonder dict döner; SMTP yapılandırılmamışsa email False."""
    log_dosyasi = Path(__file__).resolve().parent.parent / "logs" / "sms_log_test2.txt"
    if log_dosyasi.exists():
        log_dosyasi.unlink()
    svc = NotificationService(sms_log_path=log_dosyasi)

    from models.risk_zone import RiskZone
    user = User(id=1, ad="Test", email="kullanici@example.com", telefon="+905551112233")
    loc = Location(id=1, sehir="İzmit", latitude=40.766, longitude=29.916)
    risk = RiskZone(konum_id=1, risk_tipi="asiri_sicak", baslangic=datetime.now(),
                    siddet="yuksek", aciklama="Sıcaklık 41.0°C")

    sonuc = svc.risk_bildirimi_gonder(user, risk, loc, sms_aktif=True, email_aktif=True)
    assert isinstance(sonuc, dict)
    assert "sms" in sonuc and "email" in sonuc
    assert sonuc["sms"] is True  # log dosyasına yazıldı

    # E-posta yapılandırılmamışsa False olmalı (config.EMAIL_GONDERIMI_AKTIF)
    import config
    if config.EMAIL_GONDERIMI_AKTIF:
        # Gerçek SMTP testte denenmeyebilir; sadece True/False olduğunu doğrula
        assert isinstance(sonuc["email"], bool)
    else:
        assert sonuc["email"] is False

    if log_dosyasi.exists():
        log_dosyasi.unlink()


# ========= BackgroundScheduler — tetiklenme ve temiz kapanış =========

def test_scheduler_tetikleniyor_ve_temiz_kapaniyor():
    """Scheduler interval'a göre tetikleniyor ve stop_event ile durabiliyor."""
    # 1 dakika minimum; gerçek 60sn beklemek yerine schedule kuyruğunu yapay tetikleyelim
    sch = BackgroundScheduler(interval_minutes=1)
    sayac = {"n": 0}

    def gorev():
        sayac["n"] += 1

    sch.gorev_ekle(gorev)
    sch.basla()
    assert sch.thread is not None and sch.thread.is_alive()

    # schedule kuyruğunu manuel olarak tetikle — interval'ın geçmesini beklemeden
    # her job'ın next_run'ını geçmişe çek, run_pending çağrılınca tetiklenir.
    from datetime import timedelta as _td
    for job in sch._scheduler.jobs:
        job.next_run = datetime.now() - _td(seconds=1)
    # En fazla 3 saniye içinde sayaç artmalı
    son = time.time() + 3
    while time.time() < son and sayac["n"] == 0:
        time.sleep(0.2)
    assert sayac["n"] >= 1, "Görev hiç tetiklenmedi"

    # Temiz kapanış
    sch.durdur()
    # Thread join'lendi mi?
    assert sch.thread is None
    # stop_event set'li
    assert sch.stop_event.is_set()


def main():
    test_sicaklik_esik_uzeri_risk_var()
    test_sicaklik_esik_alti_risk_yok()
    test_firtina_kodu_her_zaman_yuksek()
    test_ruzgar_ve_yagis_esikleri()
    test_dusuk_sicaklik_riski()
    test_sms_log_dosyasina_yaziyor()
    test_risk_bildirimi_sms_ve_email_dict()
    test_scheduler_tetikleniyor_ve_temiz_kapaniyor()
    print("✓ Aşama 7 testleri başarılı")


if __name__ == "__main__":
    main()
