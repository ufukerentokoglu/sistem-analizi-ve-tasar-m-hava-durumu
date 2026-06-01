"""Kullanıcı giriş / kayıt formu — uygulama açılışında çağrılır."""
import logging
import tkinter as tk
from tkinter import ttk
from typing import Optional

from database.db_manager import Database
from models.user import User

logger = logging.getLogger(__name__)


class LoginForm(tk.Toplevel):
    """Sekmeli giriş/kayıt dialog'u. Başarılı girişte self.user dolar."""

    def __init__(self, parent: tk.Misc, db: Database):
        super().__init__(parent)
        self.db = db
        self.user: Optional[User] = None
        self.title("Giriş Yap")
        self.geometry("420x440")
        self.resizable(False, False)
        self.configure(bg="white")
        # macOS aqua teması ttk.Notebook içindeki tk.Frame çocuklarını gizleyebiliyor —
        # clam temasına geçmek tutarlı render sağlıyor.
        try:
            ttk.Style(self).theme_use("clam")
        except tk.TclError:
            pass
        try:
            self.transient(parent)
        except tk.TclError:
            pass
        self._arayuzu_olustur()
        self.protocol("WM_DELETE_WINDOW", self._iptal)
        self.update_idletasks()
        self._merkezle(parent)
        self.deiconify()
        self.lift()
        try:
            self.grab_set()
        except tk.TclError:
            pass
        # İlk açılışta giriş alanına odak
        try:
            self.giris_ad.focus_set()
        except tk.TclError:
            pass

    # ----- UI -----
    def _arayuzu_olustur(self) -> None:
        ust = tk.Frame(self, bg="#1E88E5", height=60)
        ust.pack(fill="x")
        ust.pack_propagate(False)
        tk.Label(ust, text="🔐 Hava Durumu — Giriş",
                 font=("Helvetica", 16, "bold"),
                 fg="white", bg="#1E88E5").pack(pady=15)

        sekmeler = ttk.Notebook(self)
        sekmeler.pack(fill="both", expand=True, padx=15, pady=15)
        sekmeler.add(self._giris_sekmesi(sekmeler), text="Giriş Yap")
        sekmeler.add(self._kayit_sekmesi(sekmeler), text="Kayıt Ol")
        sekmeler.select(0)
        self.sekmeler = sekmeler

    def _giris_sekmesi(self, parent: ttk.Notebook) -> ttk.Frame:
        cerceve = ttk.Frame(parent, padding=20)

        ttk.Label(cerceve, text="Ad:",
                  font=("Helvetica", 10)).pack(anchor="w", pady=(10, 2))
        self.giris_ad = ttk.Entry(cerceve, width=32)
        self.giris_ad.pack(fill="x")

        ttk.Label(cerceve, text="Şifre:",
                  font=("Helvetica", 10)).pack(anchor="w", pady=(15, 2))
        self.giris_sifre = ttk.Entry(cerceve, width=32, show="•")
        self.giris_sifre.pack(fill="x")
        self.giris_sifre.bind("<Return>", lambda _e: self._giris_yap())

        self.giris_durum = ttk.Label(cerceve, text="",
                                     foreground="#C62828",
                                     font=("Helvetica", 9))
        self.giris_durum.pack(anchor="w", pady=(10, 0))

        ttk.Button(cerceve, text="Giriş Yap", command=self._giris_yap
                   ).pack(fill="x", pady=(20, 0))
        return cerceve

    def _kayit_sekmesi(self, parent: ttk.Notebook) -> ttk.Frame:
        cerceve = ttk.Frame(parent, padding=(20, 15))

        ttk.Label(cerceve, text="Ad: *",
                  font=("Helvetica", 10)).pack(anchor="w", pady=(5, 2))
        self.kayit_ad = ttk.Entry(cerceve, width=32)
        self.kayit_ad.pack(fill="x")

        ttk.Label(cerceve, text="Şifre: *",
                  font=("Helvetica", 10)).pack(anchor="w", pady=(15, 2))
        self.kayit_sifre = ttk.Entry(cerceve, width=32, show="•")
        self.kayit_sifre.pack(fill="x")

        ttk.Label(cerceve, text="Şifre (tekrar): *",
                  font=("Helvetica", 10)).pack(anchor="w", pady=(15, 2))
        self.kayit_sifre2 = ttk.Entry(cerceve, width=32, show="•")
        self.kayit_sifre2.pack(fill="x")
        self.kayit_sifre2.bind("<Return>", lambda _e: self._kayit_ol())

        self.kayit_durum = ttk.Label(cerceve, text="",
                                     foreground="#C62828",
                                     font=("Helvetica", 9))
        self.kayit_durum.pack(anchor="w", pady=(10, 0))

        ttk.Button(cerceve, text="Kayıt Ol ve Giriş Yap",
                   command=self._kayit_ol).pack(fill="x", pady=(20, 0))
        return cerceve

    # ----- Aksiyonlar -----
    def _giris_yap(self) -> None:
        ad = self.giris_ad.get().strip()
        sifre = self.giris_sifre.get()
        if not ad or not sifre:
            self.giris_durum.config(text="Ad ve şifre zorunlu.")
            return
        try:
            user = self.db.kullanici_dogrula(ad, sifre)
        except Exception as e:
            logger.error("Giriş sırasında hata: %s", e)
            self.giris_durum.config(text="Beklenmeyen bir hata oluştu.")
            return
        if user is None:
            self.giris_durum.config(text="Ad veya şifre hatalı.")
            return
        logger.info("Kullanıcı girişi başarılı: %s (id=%s)", user.ad, user.id)
        self.user = user
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()

    def _kayit_ol(self) -> None:
        ad = self.kayit_ad.get().strip()
        sifre = self.kayit_sifre.get()
        sifre2 = self.kayit_sifre2.get()
        if not ad or not sifre:
            self.kayit_durum.config(text="Ad ve şifre zorunlu.")
            return
        if len(sifre) < 6:
            self.kayit_durum.config(text="Şifre en az 6 karakter olmalı.")
            return
        if sifre != sifre2:
            self.kayit_durum.config(text="Şifreler eşleşmiyor.")
            return
        try:
            user = self.db.kullanici_kayit(ad, sifre)
        except ValueError as ve:
            self.kayit_durum.config(text=str(ve))
            return
        except Exception as e:
            logger.error("Kayıt sırasında hata: %s", e)
            self.kayit_durum.config(text="Kayıt sırasında bir hata oluştu.")
            return
        logger.info("Yeni kullanıcı kaydı: %s (id=%s)", user.ad, user.id)
        self.user = user
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()

    def _iptal(self) -> None:
        self.user = None
        self.destroy()

    # ----- Konumlandırma -----
    def _merkezle(self, parent: tk.Misc) -> None:
        try:
            self.update_idletasks()
            gen = self.winfo_width()
            yuk = self.winfo_height()
            if hasattr(parent, "winfo_rootx") and parent.winfo_width() > 1:
                px = parent.winfo_rootx() + (parent.winfo_width() - gen) // 2
                py = parent.winfo_rooty() + (parent.winfo_height() - yuk) // 2
            else:
                ekran_gen = self.winfo_screenwidth()
                ekran_yuk = self.winfo_screenheight()
                px = (ekran_gen - gen) // 2
                py = (ekran_yuk - yuk) // 2
            self.geometry(f"+{max(0, px)}+{max(0, py)}")
        except tk.TclError:
            pass
