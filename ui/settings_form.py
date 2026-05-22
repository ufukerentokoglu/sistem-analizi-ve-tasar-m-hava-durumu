"""Bildirim ayarları ekranı — SMS/email aktif, risk eşiği, telefon, e-posta."""
import logging
import re
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

from database.db_manager import Database
from models.notification_setting import NotificationSetting

logger = logging.getLogger(__name__)


class SettingsForm(ttk.Frame):
    """Bildirim tercihleri ekranı."""

    RISK_ESIK_SECENEKLERI = [("Düşük", "dusuk"), ("Orta", "orta"), ("Yüksek", "yuksek")]

    def __init__(self, parent: tk.Widget, db: Database, kullanici_id: int = 1):
        super().__init__(parent, padding=20)
        self.db = db
        self.kullanici_id = kullanici_id
        self._arayuzu_olustur()
        self._ayarlari_yukle()

    # ----- UI -----
    def _arayuzu_olustur(self) -> None:
        ttk.Label(self, text="Bildirim Ayarları",
                  font=("Helvetica", 14, "bold")).grid(row=0, column=0, columnspan=2,
                                                       sticky="w", pady=(0, 15))

        # SMS aktif
        self.var_sms = tk.BooleanVar(value=True)
        ttk.Checkbutton(self, text="SMS bildirimleri aktif",
                        variable=self.var_sms).grid(row=1, column=0, columnspan=2,
                                                     sticky="w", pady=4)

        # E-posta aktif
        self.var_email = tk.BooleanVar(value=True)
        ttk.Checkbutton(self, text="E-posta bildirimleri aktif",
                        variable=self.var_email).grid(row=2, column=0, columnspan=2,
                                                       sticky="w", pady=4)

        # Risk eşiği
        ttk.Label(self, text="Risk eşiği:").grid(row=3, column=0, sticky="w", pady=(15, 4))
        self.var_risk = tk.StringVar(value="orta")
        radyo_cerceve = ttk.Frame(self)
        radyo_cerceve.grid(row=3, column=1, sticky="w", pady=(15, 4))
        for etiket, deger in self.RISK_ESIK_SECENEKLERI:
            ttk.Radiobutton(radyo_cerceve, text=etiket, value=deger,
                            variable=self.var_risk).pack(side="left", padx=(0, 15))

        # Telefon
        ttk.Label(self, text="Telefon:").grid(row=4, column=0, sticky="w", pady=4)
        self.entry_telefon = ttk.Entry(self, width=30)
        self.entry_telefon.grid(row=4, column=1, sticky="w", pady=4)

        # E-posta
        ttk.Label(self, text="E-posta:").grid(row=5, column=0, sticky="w", pady=4)
        self.entry_email = ttk.Entry(self, width=30)
        self.entry_email.grid(row=5, column=1, sticky="w", pady=4)

        # Kaydet
        ttk.Button(self, text="Kaydet", command=self._kaydet).grid(
            row=6, column=0, columnspan=2, pady=(20, 0))

        # Bilgi etiketi (kaydet sonrası geri bildirim)
        self.lbl_durum = ttk.Label(self, text="", foreground="#1E88E5")
        self.lbl_durum.grid(row=7, column=0, columnspan=2, sticky="w", pady=(10, 0))

    # ----- Veri akışı -----
    def _ayarlari_yukle(self) -> None:
        """DB'den mevcut ayar + kullanıcı bilgilerini doldur."""
        try:
            ayar = self.db.bildirim_ayari_getir(self.kullanici_id)
        except Exception as e:
            logger.error("Bildirim ayarı okunamadı: %s", e)
            return
        if ayar is not None:
            self.var_sms.set(bool(ayar.sms_aktif))
            self.var_email.set(bool(ayar.email_aktif))
            self.var_risk.set(ayar.risk_esigi or "orta")

        # Kullanıcı bilgileri (telefon, email)
        try:
            user = self.db.kullanici_getir(self.kullanici_id)
        except Exception as e:
            logger.error("Kullanıcı okunamadı: %s", e)
            user = None
        if user is not None:
            self.entry_telefon.delete(0, "end")
            self.entry_telefon.insert(0, user.telefon or "")
            self.entry_email.delete(0, "end")
            self.entry_email.insert(0, user.email or "")

    def _kaydet(self) -> None:
        """Formdaki değerleri DB'ye yaz."""
        telefon = self.entry_telefon.get().strip() or None
        email = self.entry_email.get().strip() or None

        # Basit doğrulamalar
        if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            messagebox.showwarning("Geçersiz e-posta", "Lütfen geçerli bir e-posta adresi girin.")
            return
        if telefon and not re.match(r"^\+?\d{10,15}$", telefon.replace(" ", "")):
            messagebox.showwarning(
                "Geçersiz telefon",
                "Telefon numarası 10-15 rakam içermeli (opsiyonel + ile)."
            )
            return

        # Bildirim ayarı
        try:
            self.db.bildirim_ayari_guncelle(NotificationSetting(
                kullanici_id=self.kullanici_id,
                sms_aktif=self.var_sms.get(),
                email_aktif=self.var_email.get(),
                risk_esigi=self.var_risk.get(),
                bildirim_tipi="tum",
            ))
        except Exception as e:
            logger.error("Bildirim ayarı yazılamadı: %s", e)
            messagebox.showerror("DB hatası", f"Ayar kaydedilemedi: {e}")
            return

        # Kullanıcı (telefon/email)
        try:
            user = self.db.kullanici_getir(self.kullanici_id)
            if user is None:
                raise RuntimeError("Kullanıcı bulunamadı")
            user.telefon = telefon
            user.email = email
            self.db.kullanici_guncelle(user)
        except Exception as e:
            logger.error("Kullanıcı bilgisi yazılamadı: %s", e)
            messagebox.showerror("DB hatası", f"İletişim bilgisi kaydedilemedi: {e}")
            return

        self.lbl_durum.config(text="✓ Ayarlar kaydedildi.")
