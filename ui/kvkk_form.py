"""İlk açılışta konum izni ve KVKK onayı dialog'u."""
import logging
import tkinter as tk
from tkinter import ttk

from database.db_manager import Database

logger = logging.getLogger(__name__)


class KVKKForm(tk.Toplevel):
    """İlk açılışta konum izni ve KVKK onayı dialog'u."""

    KVKK_METNI = (
        "6698 sayılı Kişisel Verilerin Korunması Kanunu kapsamında bilgilendirme:\n\n"
        "• Uygulamamız konum bilginizi (IP üzerinden) yalnızca hava durumu sorgulaması\n"
        "  amacıyla kullanır.\n"
        "• Verileriniz yerel MySQL veritabanınızda saklanır, hiçbir üçüncü tarafla\n"
        "  paylaşılmaz.\n"
        "• Bildirim için verdiğiniz telefon ve e-posta bilgileri sadece tarafınıza\n"
        "  uyarı göndermek için kullanılır.\n"
        "• İstediğiniz zaman Ayarlar ekranından bildirimleri kapatabilirsiniz.\n\n"
        "\"Onaylıyorum\" diyerek bu şartları kabul etmiş sayılırsınız."
    )

    def __init__(self, parent: tk.Misc, db: Database, kullanici_id: int = 1):
        super().__init__(parent)
        self.db = db
        self.kullanici_id = kullanici_id
        self.onaylandi: bool = False
        self.title("Konum İzni ve KVKK")
        self.geometry("620x520")
        self.resizable(False, False)
        self.configure(bg="white")
        # Tutarlı render için clam tema (aqua'da tk widgetlarıyla karışım sorunlu)
        try:
            ttk.Style(self).theme_use("clam")
        except tk.TclError:
            pass
        try:
            self.transient(parent)
        except tk.TclError:
            pass
        self._arayuzu_olustur()
        self.update_idletasks()
        self._merkezle(parent)
        # macOS'ta önceki Toplevel kapanınca yeni Toplevel arkaya düşebiliyor —
        # öne çek + odakla, sonra topmost'u bırak.
        try:
            self.deiconify()
            self.lift()
            self.focus_force()
            self.attributes("-topmost", True)
            self.after(200, lambda: self.attributes("-topmost", False))
        except tk.TclError:
            pass
        try:
            self.grab_set()
        except tk.TclError:
            pass

    def _arayuzu_olustur(self) -> None:
        # 1) Üst başlık şeridi
        ust = tk.Frame(self, bg="#1E88E5", height=60)
        ust.pack(side="top", fill="x")
        ust.pack_propagate(False)
        tk.Label(ust, text="📋 KVKK Aydınlatma Metni",
                 font=("Helvetica", 16, "bold"),
                 fg="white", bg="#1E88E5").pack(pady=15)

        # 2) Alt buton şeridi — gövdeden ÖNCE pack edilmeli ki yer kapsın
        alt = tk.Frame(self, bg="white")
        alt.pack(side="bottom", fill="x", pady=(0, 15), padx=15)
        ttk.Button(alt, text="Reddet (Konum izni vermeden devam)",
                   command=self._reddet).pack(side="right", padx=(8, 0))
        ttk.Button(alt, text="Onaylıyorum",
                   command=self._onayla).pack(side="right")
        ttk.Label(alt, text="Reddedersen uygulama açılır ama IP ile konum bulunamaz.",
                  background="white", foreground="#555",
                  font=("Helvetica", 9)).pack(side="left")

        # 3) Gövde — KVKK metni (ttk.Label ile, fg/bg açıkça)
        govde = tk.Frame(self, bg="white")
        govde.pack(side="top", fill="both", expand=True, padx=20, pady=15)
        tk.Label(govde, text=self.KVKK_METNI,
                 font=("Helvetica", 11),
                 fg="black", bg="white",
                 justify="left", anchor="nw"
                 ).pack(fill="both", expand=True)

    def _onayla(self) -> None:
        """KVKK'yı onayla, DB'ye yaz, dialog'u kapat."""
        try:
            user = self.db.kullanici_getir(self.kullanici_id)
            if user is None:
                logger.error("KVKK onayı için kullanıcı bulunamadı (id=%s).",
                             self.kullanici_id)
                self.onaylandi = False
                self.destroy()
                return
            user.kvkk_onay = True
            self.db.kullanici_guncelle(user)
            self.onaylandi = True
        except Exception as e:
            logger.error("KVKK onayı yazılırken hata: %s", e)
            self.onaylandi = False
        self.destroy()

    def _reddet(self) -> None:
        """Onaylamadan kapat."""
        self.onaylandi = False
        self.destroy()

    def _merkezle(self, parent: tk.Misc) -> None:
        try:
            self.update_idletasks()
            gen = self.winfo_width()
            yuk = self.winfo_height()
            if hasattr(parent, "winfo_rootx"):
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
