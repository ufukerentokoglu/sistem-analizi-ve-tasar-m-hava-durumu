"""Aşama 1 smoke test — DB temel CRUD'ı sağlıyor mu?"""
import os
import sys
from datetime import datetime
from pathlib import Path

# Test dosyası modül kökünden çalıştırılırken proje kökünü path'e ekle
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.db_manager import Database
from models.location import Location
from models.weather import Weather
import config


def test_full_flow():
    db = Database(config.DB_HOST, config.DB_PORT, config.DB_USER,
                  config.DB_PASSWORD, config.DB_NAME)
    db.connect()
    try:
        # Konum ekle
        loc = Location(sehir="İzmit", ilce="Kocaeli", latitude=40.766, longitude=29.916)
        konum_id = db.konum_ekle(loc)
        assert konum_id > 0

        # Tekrar ekle — aynı id dönmeli
        konum_id2 = db.konum_ekle(loc)
        assert konum_id == konum_id2

        # Hava durumu ekle
        w = Weather(konum_id=konum_id, olcum_tarihi=datetime.now(),
                    sicaklik=22.5, nem=65, ruzgar_hizi=12.3)
        weather_id = db.hava_durumu_ekle(w)
        assert weather_id > 0

        # Sorgula
        son = db.son_hava_durumu_getir(konum_id)
        assert son is not None and son.sicaklik == 22.5

        # Favori ekle/sil
        db.favori_ekle(1, konum_id)
        assert db.favori_mi(1, konum_id)
        db.favori_sil(1, konum_id)
        assert not db.favori_mi(1, konum_id)
    finally:
        db.disconnect()
    print("✓ Aşama 1 testleri başarılı")


if __name__ == "__main__":
    test_full_flow()
