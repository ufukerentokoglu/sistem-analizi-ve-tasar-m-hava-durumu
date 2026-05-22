"""Risk uyarı pop-up — modal Toplevel."""
import tkinter as tk
from tkinter import ttk
from typing import Dict

from models.location import Location
from models.risk_zone import RiskZone


class RiskAlertForm(tk.Toplevel):
    """Risk uyarı pop-up."""

    SIDDET_RENKLERI: Dict[str, str] = {
        "dusuk": "#FFC107",   # sarı
        "orta": "#FF9800",    # turuncu
        "yuksek": "#D32F2F",  # kırmızı
    }

    SIDDET_ETIKETLERI: Dict[str, str] = {
        "dusuk": "DÜŞÜK",
        "orta": "ORTA",
        "yuksek": "YÜKSEK",
    }

    RISK_BASLIKLARI: Dict[str, str] = {
        "firtina": "Fırtına Uyarısı",
        "asiri_sicak": "Aşırı Sıcak Uyarısı",
        "asiri_soguk": "Aşırı Soğuk Uyarısı",
        "siddetli_ruzgar": "Şiddetli Rüzgâr Uyarısı",
        "yogun_yagis": "Yoğun Yağış Uyarısı",
    }

    def __init__(self, parent: tk.Widget, risk: RiskZone, location: Location):
        super().__init__(parent)
        self.title("⚠ Hava Durumu Uyarısı")
        self.geometry("450x300")
        self.resizable(False, False)
        try:
            self.transient(parent)
        except tk.TclError:
            pass
        # Modal — odak ver
        try:
            self.grab_set()
        except tk.TclError:
            pass
        self._arayuzu_olustur(risk, location)
        self._merkezle(parent)

    def _arayuzu_olustur(self, risk: RiskZone, location: Location) -> None:
        renk = self.SIDDET_RENKLERI.get(risk.siddet, "#FF9800")
        siddet_etiket = self.SIDDET_ETIKETLERI.get(risk.siddet, risk.siddet.upper())
        baslik = self.RISK_BASLIKLARI.get(risk.risk_tipi, risk.risk_tipi.title())

        # Üst bant — şiddet rengiyle
        ust = tk.Frame(self, bg=renk, height=70)
        ust.pack(fill="x")
        ust.pack_propagate(False)
        tk.Label(ust, text="⚠ " + baslik,
                 font=("Helvetica", 16, "bold"),
                 fg="white", bg=renk).pack(pady=(15, 0))
        tk.Label(ust, text=f"Şiddet: {siddet_etiket}",
                 font=("Helvetica", 11),
                 fg="white", bg=renk).pack()

        # Gövde — konum + açıklama
        govde = tk.Frame(self, bg="white")
        govde.pack(fill="both", expand=True, padx=20, pady=15)

        konum_str = location.sehir
        if location.ilce:
            konum_str = f"{location.ilce} / {location.sehir}"
        tk.Label(govde, text=f"Konum: {konum_str}",
                 font=("Helvetica", 12, "bold"),
                 bg="white").pack(anchor="w", pady=(0, 8))

        if risk.aciklama:
            tk.Label(govde, text=risk.aciklama,
                     font=("Helvetica", 11),
                     bg="white", wraplength=400, justify="left").pack(anchor="w", pady=(0, 8))

        tk.Label(govde,
                 text="Lütfen tedbirli olun ve resmi açıklamaları takip edin.",
                 font=("Helvetica", 10),
                 fg="#546E7A", bg="white",
                 wraplength=400, justify="left").pack(anchor="w")

        # Alt — kapat butonu
        alt = tk.Frame(self)
        alt.pack(fill="x", pady=(0, 15))
        ttk.Button(alt, text="Anladım", command=self.destroy).pack()

    def _merkezle(self, parent: tk.Widget) -> None:
        """Pop-up'ı parent pencerenin ortasına yerleştirir."""
        try:
            self.update_idletasks()
            gen = self.winfo_width()
            yuk = self.winfo_height()
            px = parent.winfo_rootx() + (parent.winfo_width() - gen) // 2
            py = parent.winfo_rooty() + (parent.winfo_height() - yuk) // 2
            self.geometry(f"+{max(0, px)}+{max(0, py)}")
        except tk.TclError:
            pass
