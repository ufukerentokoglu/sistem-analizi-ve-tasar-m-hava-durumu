"""Anlık hava durumu paneli — büyük sıcaklık, durum ve ölçüm kartları."""
import tkinter as tk
from tkinter import ttk
from typing import Optional

from models.location import Location
from models.weather import Weather

# Renk paleti (SPEC önerisi)
RENK_ANA = "#1E88E5"
RENK_KOYU = "#0D47A1"
RENK_ARKAPLAN = "#E3F2FD"
RENK_KART = "#FFFFFF"
RENK_METIN = "#212121"
RENK_IKINCIL = "#546E7A"


class WeatherDisplayForm(ttk.Frame):
    """Anlık hava durumu paneli."""

    def __init__(self, parent: tk.Widget):
        super().__init__(parent)
        self.configure(padding=20)
        self._arayuzu_olustur()

    def _arayuzu_olustur(self) -> None:
        """Sıcaklık (büyük), durum açıklaması, nem/rüzgar/basınç kartları."""
        # Üst bölge: konum + büyük sıcaklık + durum
        ust = tk.Frame(self, bg=RENK_ARKAPLAN)
        ust.pack(fill="x", pady=(0, 20))

        self.lbl_konum = tk.Label(
            ust, text="— Konum seçilmedi —",
            font=("Helvetica", 16, "bold"),
            fg=RENK_KOYU, bg=RENK_ARKAPLAN,
        )
        self.lbl_konum.pack(anchor="w")

        self.lbl_sicaklik = tk.Label(
            ust, text="--°C",
            font=("Helvetica", 72, "bold"),
            fg=RENK_ANA, bg=RENK_ARKAPLAN,
        )
        self.lbl_sicaklik.pack(anchor="w", pady=(10, 0))

        self.lbl_durum = tk.Label(
            ust, text="—",
            font=("Helvetica", 18),
            fg=RENK_METIN, bg=RENK_ARKAPLAN,
        )
        self.lbl_durum.pack(anchor="w")

        self.lbl_hissedilen = tk.Label(
            ust, text="Hissedilen: --°C",
            font=("Helvetica", 12),
            fg=RENK_IKINCIL, bg=RENK_ARKAPLAN,
        )
        self.lbl_hissedilen.pack(anchor="w", pady=(5, 0))

        # Kartlar bölgesi
        kartlar = tk.Frame(self, bg=RENK_ARKAPLAN)
        kartlar.pack(fill="both", expand=True)

        self.kart_nem = self._kart_olustur(kartlar, "Nem", "-- %")
        self.kart_ruzgar = self._kart_olustur(kartlar, "Rüzgâr", "-- km/h")
        self.kart_basinc = self._kart_olustur(kartlar, "Basınç", "-- hPa")
        self.kart_yagis = self._kart_olustur(kartlar, "Yağış", "-- mm")

        # Kartları yatay sıraya yerleştir
        for i, k in enumerate(
            [self.kart_nem, self.kart_ruzgar, self.kart_basinc, self.kart_yagis]
        ):
            k["frame"].grid(row=0, column=i, padx=10, pady=5, sticky="nsew")
            kartlar.columnconfigure(i, weight=1)

        # Alt: ölçüm zamanı
        self.lbl_zaman = tk.Label(
            self, text="",
            font=("Helvetica", 10),
            fg=RENK_IKINCIL, bg=RENK_ARKAPLAN,
        )
        self.lbl_zaman.pack(anchor="e", pady=(15, 0))

        # Frame arka planını da boyayalım (ttk.Frame default rengi pencereyle aynı olabilir)
        try:
            self.configure(style="WD.TFrame")
            stil = ttk.Style()
            stil.configure("WD.TFrame", background=RENK_ARKAPLAN)
        except tk.TclError:
            pass

    def _kart_olustur(self, parent: tk.Widget, baslik: str, ilk_deger: str) -> dict:
        """Tek bir ölçüm kartı (başlık + değer) oluşturur."""
        cerceve = tk.Frame(parent, bg=RENK_KART, bd=1, relief="solid", padx=15, pady=15)
        baslik_lbl = tk.Label(
            cerceve, text=baslik,
            font=("Helvetica", 11),
            fg=RENK_IKINCIL, bg=RENK_KART,
        )
        baslik_lbl.pack(anchor="w")
        deger_lbl = tk.Label(
            cerceve, text=ilk_deger,
            font=("Helvetica", 20, "bold"),
            fg=RENK_KOYU, bg=RENK_KART,
        )
        deger_lbl.pack(anchor="w", pady=(5, 0))
        return {"frame": cerceve, "baslik": baslik_lbl, "deger": deger_lbl}

    def veriyi_goster(self, location: Location, weather: Weather) -> None:
        """Verilen konum ve hava durumu nesnesini ekrana yansıtır."""
        konum_baslik = location.sehir
        if location.ilce:
            konum_baslik += f" / {location.ilce}"
        if location.ulke:
            konum_baslik += f", {location.ulke}"
        self.lbl_konum.config(text=konum_baslik)

        self.lbl_sicaklik.config(
            text=f"{weather.sicaklik:.0f}°C" if weather.sicaklik is not None else "--°C"
        )
        self.lbl_durum.config(text=weather.durum_aciklamasi or "—")
        self.lbl_hissedilen.config(
            text=(f"Hissedilen: {weather.hissedilen_sicaklik:.0f}°C"
                  if weather.hissedilen_sicaklik is not None else "Hissedilen: --°C")
        )

        self.kart_nem["deger"].config(
            text=f"{weather.nem} %" if weather.nem is not None else "-- %"
        )
        self.kart_ruzgar["deger"].config(
            text=f"{weather.ruzgar_hizi:.1f} km/h"
            if weather.ruzgar_hizi is not None else "-- km/h"
        )
        self.kart_basinc["deger"].config(
            text=f"{weather.basinc:.0f} hPa"
            if weather.basinc is not None else "-- hPa"
        )
        self.kart_yagis["deger"].config(
            text=f"{weather.yagis_mm:.1f} mm"
            if weather.yagis_mm is not None else "-- mm"
        )

        if weather.olcum_tarihi is not None:
            self.lbl_zaman.config(
                text=f"Ölçüm zamanı: {weather.olcum_tarihi.strftime('%d.%m.%Y %H:%M')}"
            )

    def temizle(self) -> None:
        """Tüm değerleri sıfırlar."""
        self.lbl_konum.config(text="— Konum seçilmedi —")
        self.lbl_sicaklik.config(text="--°C")
        self.lbl_durum.config(text="—")
        self.lbl_hissedilen.config(text="Hissedilen: --°C")
        self.kart_nem["deger"].config(text="-- %")
        self.kart_ruzgar["deger"].config(text="-- km/h")
        self.kart_basinc["deger"].config(text="-- hPa")
        self.kart_yagis["deger"].config(text="-- mm")
        self.lbl_zaman.config(text="")
