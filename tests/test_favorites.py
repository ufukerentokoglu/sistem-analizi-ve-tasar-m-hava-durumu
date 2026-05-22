"""Aşama 5 doğrulama testi — favoriler ekle/sil/listele + duplicate engeli + UI akışı."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from database.db_manager import Database
from models.location import Location
from services.location_service import LocationService
from services.weather_api import WeatherAPI


def test_db_seviyesi_favori_crud():
    """DB seviyesinde: ekle → favori_mi → tekrar ekle (duplicate=aynı id) → sil."""
    db = Database(config.DB_HOST, config.DB_PORT, config.DB_USER,
                  config.DB_PASSWORD, config.DB_NAME)
    db.connect()
    try:
        svc = LocationService(db)
        # Test verisi olarak Antalya'yı kullan (testler arası izolasyon için sil/yeniden ekle)
        db.execute("DELETE FROM Konumlar WHERE sehir=%s", ("Antalya",))
        loc = svc.manuel_konum_ara("Antalya")
        assert loc is not None and loc.id is not None

        # Başlangıçta favori değil
        assert db.favori_mi(1, loc.id) is False

        # Ekle
        fav_id1 = db.favori_ekle(1, loc.id)
        assert fav_id1 > 0
        assert db.favori_mi(1, loc.id) is True

        # Aynı favoriyi tekrar eklemek hata vermemeli; aynı id dönmeli
        fav_id2 = db.favori_ekle(1, loc.id)
        assert fav_id2 == fav_id1, "Duplicate favori — aynı id dönmeli"

        # Liste içeriği
        favoriler = db.favorileri_getir(1)
        assert any(f.konum_id == loc.id for f in favoriler)

        # Sil
        assert db.favori_sil(1, loc.id) is True
        assert db.favori_mi(1, loc.id) is False
    finally:
        db.disconnect()


def test_ui_akisi():
    """MainForm üzerinden: aktif konumu favoriye ekle, listede gör, tıkla → Anlık'a yüklensin."""
    import tkinter as tk
    try:
        kontrol = tk.Tk()
        kontrol.withdraw()
        kontrol.destroy()
    except tk.TclError as e:
        print(f"⚠ Display yok, UI testi atlandı: {e}")
        return

    from ui.main_form import MainForm

    db = Database(config.DB_HOST, config.DB_PORT, config.DB_USER,
                  config.DB_PASSWORD, config.DB_NAME)
    db.connect()
    try:
        # Test öncesi temizlik — Bursa
        db.execute(
            "DELETE FROM Favoriler WHERE kullanici_id=1 AND konum_id IN "
            "(SELECT id FROM Konumlar WHERE sehir='Bursa')"
        )

        app = MainForm(db, WeatherAPI(), LocationService(db))

        durum = {"adim": "ara"}

        def adim_ara():
            app.aramayi_calistir("Bursa")

        def adim_favori_ekle():
            assert app.aktif_konum is not None, "Aktif konum oluşmamış"
            assert app.aktif_konum.id is not None
            # ttk.Button state lookup: instate kullan
            assert not app.btn_favori_ekle.instate(["disabled"]), (
                "Favori butonu hâlâ disabled durumda"
            )
            app.aktif_konumu_favoriye_ekle()
            durum["bursa_id"] = app.aktif_konum.id

        def adim_listede_var_mi():
            kid = durum["bursa_id"]
            # FavoritesForm listesini kontrol et
            items = app.favorites_form.tree.get_children()
            bulundu = False
            bursa_iid = None
            for iid in items:
                loc = app.favorites_form._konum_haritasi.get(iid)
                if loc and loc.id == kid:
                    bulundu = True
                    bursa_iid = iid
                    break
            assert bulundu, "Bursa favori listesinde görünmüyor"
            durum["bursa_iid"] = bursa_iid

            # Duplicate çağrı — hata vermemeli, id değişmemeli
            app.aktif_konumu_favoriye_ekle()
            # Hâlâ listede 1 kez olmalı
            ayni_kez = sum(
                1 for iid in app.favorites_form.tree.get_children()
                if app.favorites_form._konum_haritasi.get(iid) and
                app.favorites_form._konum_haritasi[iid].id == kid
            )
            assert ayni_kez == 1, f"Duplicate favori oluştu (kayıt sayısı={ayni_kez})"

        def adim_favoriden_yukle():
            # listeyi_yenile sonrası iid değişmiş olabilir → yeniden bul
            kid = durum["bursa_id"]
            iid_guncel = None
            for iid in app.favorites_form.tree.get_children():
                loc = app.favorites_form._konum_haritasi.get(iid)
                if loc and loc.id == kid:
                    iid_guncel = iid
                    break
            assert iid_guncel is not None, "Bursa iid yeniden bulunamadı"
            app.favorites_form.tree.selection_set(iid_guncel)
            # _favoriden_yukle → _hava_durumunu_yukle (yine API+thread, sonra Anlık'a basar)
            app.favorites_form._secileni_goster()

        def adim_kapan():
            app.destroy()

        # Senaryoyu zamanla:
        app.after(500, adim_ara)
        app.after(5500, adim_favori_ekle)
        app.after(6500, adim_listede_var_mi)
        app.after(7500, adim_favoriden_yukle)
        app.after(13000, adim_kapan)

        app.mainloop()

        # Pencere kapandı; son durum doğrulamaları
        assert "bursa_id" in durum
        # DB'de hâlâ favori olmalı (silmedik)
        assert db.favori_mi(1, durum["bursa_id"])
        # Bursa için en az bir HavaDurumu satırı oluşmuş olmalı
        sayim = db.fetch_one(
            "SELECT COUNT(*) AS c FROM HavaDurumu WHERE konum_id=%s",
            (durum["bursa_id"],),
        )
        assert int(sayim["c"]) >= 1, "Bursa için DB'ye ölçüm yazılmadı"
    finally:
        # Temizlik: bu test sürekli aynı favoriyi bırakmasın
        try:
            db.execute(
                "DELETE FROM Favoriler WHERE kullanici_id=1 AND konum_id IN "
                "(SELECT id FROM Konumlar WHERE sehir='Bursa')"
            )
        except Exception:
            pass
        db.disconnect()


def main():
    test_db_seviyesi_favori_crud()
    test_ui_akisi()
    print("✓ Aşama 5 testleri başarılı")


if __name__ == "__main__":
    main()
