"""Aşama 2 smoke test — Open-Meteo entegrasyonu gerçek istek atıyor mu?"""
import sys
from pathlib import Path

# Proje kökü path'e
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.location import Location
from services.weather_api import WeatherAPI


def test_anlik_veri():
    """İzmit koordinatlarıyla anlık veri çek — sıcaklık ve açıklama alanları gelmeli."""
    api = WeatherAPI()
    loc = Location(sehir="İzmit", ilce="Kocaeli", latitude=40.766, longitude=29.916)
    w = api.anlik_veri_cek(loc)
    assert w is not None
    # Sıcaklık makul aralıkta olmalı (Türkiye iklimi: -30..50)
    assert w.sicaklik is not None and -30.0 <= w.sicaklik <= 50.0
    assert w.kaynak_api == "Open-Meteo"
    # Durum açıklaması Türkçe ve None değil
    assert w.durum_aciklamasi is not None


def test_saatlik_tahmin_24():
    """24 saatlik tahmin tam 24 elemanlı dönmeli."""
    api = WeatherAPI()
    loc = Location(sehir="İzmit", latitude=40.766, longitude=29.916)
    saatlik = api.saatlik_tahmin_cek(loc, saat_sayisi=24)
    assert len(saatlik) == 24
    # İlk eleman geçerli sıcaklık taşımalı
    assert saatlik[0].sicaklik is not None


def test_gunluk_tahmin_7():
    """7 günlük tahmin 7 elemanlı dönmeli."""
    api = WeatherAPI()
    loc = Location(sehir="İzmit", latitude=40.766, longitude=29.916)
    gunluk = api.gunluk_tahmin_cek(loc, gun_sayisi=7)
    assert len(gunluk) == 7
    assert gunluk[0].sicaklik is not None  # max sıcaklık


def test_kod_aciklamasi():
    """WMO kod sözlüğü doğru çeviriyor mu?"""
    assert WeatherAPI.kod_aciklamasi(0) == "Açık"
    assert WeatherAPI.kod_aciklamasi(95) == "Gök gürültülü fırtına"
    assert WeatherAPI.kod_aciklamasi(9999) == "Bilinmiyor"
    assert WeatherAPI.kod_aciklamasi(None) == "Bilinmiyor"


def test_ag_hatasi_runtime_error():
    """Geçersiz host → RuntimeError yutulmadan fırlamalı."""
    api = WeatherAPI(base_url="http://geçersiz-host-deneme.invalid/forecast")
    loc = Location(sehir="X", latitude=0.0, longitude=0.0)
    try:
        api.anlik_veri_cek(loc)
    except RuntimeError as e:
        assert "Open-Meteo" in str(e)
        return
    raise AssertionError("Beklenen RuntimeError fırlatılmadı.")


def main():
    test_anlik_veri()
    test_saatlik_tahmin_24()
    test_gunluk_tahmin_7()
    test_kod_aciklamasi()
    test_ag_hatasi_runtime_error()
    print("✓ Aşama 2 testleri başarılı")


if __name__ == "__main__":
    main()
