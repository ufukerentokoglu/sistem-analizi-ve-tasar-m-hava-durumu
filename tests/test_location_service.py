"""Aşama 3 smoke test — LocationService manuel arama ve IP tespit davranışı."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Proje kökü path'e
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from database.db_manager import Database
from models.location import Location
from services.location_service import LocationService


def test_manuel_arama_db_de_yokken_sabit_dict_ten_dolduruyor():
    """DB konum_ara None döndüğünde sabit dict'ten doldurup konum_ekle çağırılmalı."""
    sahte_db = MagicMock(spec=Database)
    sahte_db.konum_ara.return_value = None
    sahte_db.konum_ekle.return_value = 42  # id

    svc = LocationService(sahte_db)
    loc = svc.manuel_konum_ara("İzmit")
    assert loc is not None
    assert loc.sehir == "İzmit"
    assert loc.id == 42
    # Sabit dict'teki koordinatları kullanmalı
    beklenen_lat, beklenen_lon = LocationService.SEHIR_KOORDINATLARI["izmit"]
    assert loc.latitude == beklenen_lat
    assert loc.longitude == beklenen_lon
    sahte_db.konum_ekle.assert_called_once()


def test_manuel_arama_db_de_varsa_db_den_donuyor():
    """DB'de kayıtlı konum varsa sabit dict'e bakılmadan o dönmeli."""
    sahte_db = MagicMock(spec=Database)
    mevcut_loc = Location(
        id=7, sehir="İstanbul", latitude=41.0082, longitude=28.9784
    )
    sahte_db.konum_ara.return_value = mevcut_loc

    svc = LocationService(sahte_db)
    loc = svc.manuel_konum_ara("İstanbul")
    assert loc is mevcut_loc
    sahte_db.konum_ekle.assert_not_called()


def test_manuel_arama_bilinmeyen_sehir_none_doner():
    """Sabit dict'te de DB'de de yoksa None dönmeli."""
    sahte_db = MagicMock(spec=Database)
    sahte_db.konum_ara.return_value = None

    svc = LocationService(sahte_db)
    loc = svc.manuel_konum_ara("Atlantis")
    assert loc is None
    sahte_db.konum_ekle.assert_not_called()


def test_manuel_arama_turkce_karakter_normalize_ediyor():
    """'İzmir' / 'izmir' / 'İZMİR' aynı sabit anahtara çözülmeli."""
    sahte_db = MagicMock(spec=Database)
    sahte_db.konum_ara.return_value = None
    sahte_db.konum_ekle.return_value = 1

    svc = LocationService(sahte_db)
    for varyant in ["İzmir", "izmir", "İZMİR", " İzmir "]:
        loc = svc.manuel_konum_ara(varyant)
        assert loc is not None, f"varyant başarısız: {varyant!r}"
        assert loc.latitude == LocationService.SEHIR_KOORDINATLARI["izmir"][0]


def test_otomatik_konum_internet_yokken_none_doner():
    """geocoder.ip içinde exception fırlasa bile None dönmeli, exception sızdırmamalı."""
    sahte_db = MagicMock(spec=Database)
    svc = LocationService(sahte_db)
    with patch("services.location_service.geocoder.ip", side_effect=Exception("ağ yok")):
        sonuc = svc.otomatik_konum_tespit()
    assert sonuc is None


def test_otomatik_konum_ok_false_iken_none():
    """geocoder.ip ok=False döndürürse None."""
    sahte_db = MagicMock(spec=Database)
    svc = LocationService(sahte_db)
    sahte_g = MagicMock()
    sahte_g.ok = False
    sahte_g.latlng = None
    with patch("services.location_service.geocoder.ip", return_value=sahte_g):
        sonuc = svc.otomatik_konum_tespit()
    assert sonuc is None


def test_entegrasyon_manuel_arama_persist():
    """Gerçek DB ile: ilk çağrı sabit dict'ten oluşturup yazıyor; ikinci çağrı DB'den dönüyor."""
    db = Database(config.DB_HOST, config.DB_PORT, config.DB_USER,
                  config.DB_PASSWORD, config.DB_NAME)
    db.connect()
    try:
        svc = LocationService(db)
        # Test ortamı: önce temizleyelim (önceki testlerden kalmış olabilir)
        # NOT: schema'da ON DELETE CASCADE var, hava_durumu kayıtları da gider.
        db.execute(
            "DELETE FROM Konumlar WHERE sehir=%s AND (ilce IS NULL OR ilce=%s)",
            ("Mersin", "Mersin"),
        )

        loc1 = svc.manuel_konum_ara("Mersin")
        assert loc1 is not None and loc1.id is not None
        loc2 = svc.manuel_konum_ara("Mersin")
        assert loc2 is not None and loc2.id == loc1.id, "İkinci çağrı DB'den aynı id'yi vermeli"
    finally:
        db.disconnect()


def main():
    test_manuel_arama_db_de_yokken_sabit_dict_ten_dolduruyor()
    test_manuel_arama_db_de_varsa_db_den_donuyor()
    test_manuel_arama_bilinmeyen_sehir_none_doner()
    test_manuel_arama_turkce_karakter_normalize_ediyor()
    test_otomatik_konum_internet_yokken_none_doner()
    test_otomatik_konum_ok_false_iken_none()
    test_entegrasyon_manuel_arama_persist()
    print("✓ Aşama 3 testleri başarılı")


if __name__ == "__main__":
    main()
