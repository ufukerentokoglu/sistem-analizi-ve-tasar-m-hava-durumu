"""Aşama 8 — KVKK akışı + SettingsForm persist testleri."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from database.db_manager import Database


def test_kvkk_reddedince_onaylandi_false():
    import tkinter as tk
    try:
        kontrol = tk.Tk()
        kontrol.withdraw()
        kontrol.destroy()
    except tk.TclError as e:
        print(f"⚠ Display yok, atlanıyor: {e}")
        return

    from ui.kvkk_form import KVKKForm

    db = Database(config.DB_HOST, config.DB_PORT, config.DB_USER,
                  config.DB_PASSWORD, config.DB_NAME)
    db.connect()
    try:
        # Test öncesi kvkk_onay'ı false yap
        user = db.kullanici_getir(1)
        assert user is not None
        user.kvkk_onay = False
        db.kullanici_guncelle(user)

        kok = tk.Tk()
        kok.withdraw()
        kvkk = KVKKForm(kok, db)
        # Reddet'i programatik tetikle
        kvkk.after(300, kvkk._reddet)
        kok.wait_window(kvkk)
        kok.destroy()
        assert kvkk.onaylandi is False
        user_sonra = db.kullanici_getir(1)
        assert user_sonra.kvkk_onay is False, "Reddedildiğinde DB değişmemeli"
    finally:
        db.disconnect()


def test_kvkk_onaylayinca_db_ye_yaziliyor():
    import tkinter as tk
    try:
        kontrol = tk.Tk()
        kontrol.withdraw()
        kontrol.destroy()
    except tk.TclError as e:
        print(f"⚠ Display yok, atlanıyor: {e}")
        return

    from ui.kvkk_form import KVKKForm

    db = Database(config.DB_HOST, config.DB_PORT, config.DB_USER,
                  config.DB_PASSWORD, config.DB_NAME)
    db.connect()
    try:
        user = db.kullanici_getir(1)
        user.kvkk_onay = False
        db.kullanici_guncelle(user)

        kok = tk.Tk()
        kok.withdraw()
        kvkk = KVKKForm(kok, db)
        kvkk.after(300, kvkk._onayla)
        kok.wait_window(kvkk)
        kok.destroy()
        assert kvkk.onaylandi is True
        user_sonra = db.kullanici_getir(1)
        assert user_sonra.kvkk_onay is True
    finally:
        db.disconnect()


def test_settings_form_persist():
    import tkinter as tk
    try:
        kontrol = tk.Tk()
        kontrol.withdraw()
        kontrol.destroy()
    except tk.TclError as e:
        print(f"⚠ Display yok, atlanıyor: {e}")
        return

    from ui.settings_form import SettingsForm

    db = Database(config.DB_HOST, config.DB_PORT, config.DB_USER,
                  config.DB_PASSWORD, config.DB_NAME)
    db.connect()
    try:
        kok = tk.Tk()
        kok.withdraw()
        form = SettingsForm(kok, db)
        # Değerleri değiştir
        form.var_sms.set(False)
        form.var_email.set(True)
        form.var_risk.set("yuksek")
        form.entry_telefon.delete(0, "end")
        form.entry_telefon.insert(0, "+905001112233")
        form.entry_email.delete(0, "end")
        form.entry_email.insert(0, "test@example.com")
        form._kaydet()
        kok.destroy()

        # DB'den okuyup doğrula
        ayar = db.bildirim_ayari_getir(1)
        assert ayar is not None
        assert ayar.sms_aktif is False
        assert ayar.email_aktif is True
        assert ayar.risk_esigi == "yuksek"
        user = db.kullanici_getir(1)
        assert user.telefon == "+905001112233"
        assert user.email == "test@example.com"

        # Yeni bir SettingsForm oluştur, değerleri yüklediğini doğrula
        kok2 = tk.Tk()
        kok2.withdraw()
        form2 = SettingsForm(kok2, db)
        assert form2.var_sms.get() is False
        assert form2.var_email.get() is True
        assert form2.var_risk.get() == "yuksek"
        assert form2.entry_telefon.get() == "+905001112233"
        assert form2.entry_email.get() == "test@example.com"
        kok2.destroy()
    finally:
        # Test sonrası: kullanıcı bilgilerini temizle, bildirim ayarını default'a döndür
        # (diğer testlerin sms_aktif=True varsaymasını bozmayalım).
        try:
            user_t = db.kullanici_getir(1)
            if user_t:
                user_t.telefon = None
                user_t.email = None
                db.kullanici_guncelle(user_t)
            from models.notification_setting import NotificationSetting
            db.bildirim_ayari_guncelle(NotificationSetting(
                kullanici_id=1,
                sms_aktif=True,
                email_aktif=True,
                risk_esigi="orta",
                bildirim_tipi="tum",
            ))
        except Exception:
            pass
        db.disconnect()


def main():
    test_kvkk_reddedince_onaylandi_false()
    test_kvkk_onaylayinca_db_ye_yaziliyor()
    test_settings_form_persist()
    print("✓ Aşama 8 (KVKK + Ayarlar) testleri başarılı")


if __name__ == "__main__":
    main()
