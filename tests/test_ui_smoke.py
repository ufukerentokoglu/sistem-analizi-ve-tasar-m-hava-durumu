"""Aşama 4 UI smoke test — pencereyi headless modda kısaca açıp arama akışını doğrular.

NOT: Bu test gerçek bir display gerektirebilir. Display yoksa skip mesajıyla geçer.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from database.db_manager import Database
from services.location_service import LocationService
from services.weather_api import WeatherAPI


def main() -> int:
    import tkinter as tk
    try:
        # Display erişilebilir mi?
        deneme = tk.Tk()
        deneme.withdraw()
        deneme.destroy()
    except tk.TclError as e:
        print(f"⚠ Display yok, UI smoke test atlandı: {e}")
        return 0

    from ui.main_form import MainForm

    db = Database(config.DB_HOST, config.DB_PORT, config.DB_USER,
                  config.DB_PASSWORD, config.DB_NAME)
    db.connect()
    try:
        # Önce mevcut max HavaDurumu id'sini al
        once = db.fetch_one("SELECT COALESCE(MAX(id), 0) AS m FROM HavaDurumu")
        once_id = int(once["m"])
        print(f"Test öncesi max HavaDurumu.id = {once_id}")

        weather_api = WeatherAPI()
        location_service = LocationService(db)
        app = MainForm(db, weather_api, location_service)

        # Pencere açıldıktan 500ms sonra İzmit araması tetikle
        app.after(500, lambda: app.aramayi_calistir("İzmit"))

        # 8 saniye sonra pencereyi kapat (API + DB için yeterli süre)
        app.after(8000, app.destroy)

        app.mainloop()

        # DB kontrolü
        sonra = db.fetch_one("SELECT COALESCE(MAX(id), 0) AS m FROM HavaDurumu")
        sonra_id = int(sonra["m"])
        print(f"Test sonrası max HavaDurumu.id = {sonra_id}")

        assert sonra_id > once_id, (
            f"Aramadan sonra HavaDurumu tablosuna yeni kayıt eklenmedi "
            f"(önce={once_id}, sonra={sonra_id})"
        )

        # Son kaydı oku ve İzmit olduğunu doğrula
        son = db.fetch_one(
            "SELECT h.id, k.sehir, h.sicaklik, h.olcum_tarihi "
            "FROM HavaDurumu h JOIN Konumlar k ON h.konum_id=k.id "
            "WHERE h.id=%s",
            (sonra_id,),
        )
        assert son is not None
        print(f"  Son kayıt: id={son['id']} sehir={son['sehir']} "
              f"sicaklik={son['sicaklik']} olcum={son['olcum_tarihi']}")
        assert son["sehir"] == "İzmit"
        assert son["sicaklik"] is not None

        print("✓ Aşama 4 UI smoke test başarılı")
        return 0
    finally:
        db.disconnect()


if __name__ == "__main__":
    sys.exit(main())
