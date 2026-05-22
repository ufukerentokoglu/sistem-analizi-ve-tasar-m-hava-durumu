"""Matplotlib zaman serisi grafikleri — sıcaklık, nem, rüzgar."""
import logging
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

import matplotlib
matplotlib.use("TkAgg")  # Tkinter backend'i — pencere içine canvas için zorunlu
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.dates import DateFormatter
from matplotlib.figure import Figure

from database.db_manager import Database
from models.location import Location
from models.weather import Weather
from services.weather_api import WeatherAPI

logger = logging.getLogger(__name__)


class ChartForm(ttk.Frame):
    """Sıcaklık/nem/rüzgar zaman serisi grafikleri."""

    SAATLIK_VARSAYILAN = 24  # Saat

    def __init__(self, parent: tk.Widget, db: Database, weather_api: WeatherAPI):
        super().__init__(parent, padding=15)
        self.db = db
        self.weather_api = weather_api
        self.aktif_konum: Optional[Location] = None
        self._figure: Optional[Figure] = None
        self._canvas: Optional[FigureCanvasTkAgg] = None
        self._arayuzu_olustur()

    # ----- Arayüz -----
    def _arayuzu_olustur(self) -> None:
        """Üstte 3 buton: Sıcaklık | Nem | Rüzgar. Altında matplotlib canvas."""
        ust = ttk.Frame(self)
        ust.pack(fill="x", pady=(0, 10))

        ttk.Label(ust, text="Grafik:", font=("Helvetica", 11, "bold")).pack(side="left")

        self.btn_sicaklik = ttk.Button(
            ust, text="🌡 Sıcaklık",
            command=lambda: self._calistir(self.sicaklik_grafigi),
        )
        self.btn_sicaklik.pack(side="left", padx=(15, 5))

        self.btn_nem = ttk.Button(
            ust, text="💧 Nem",
            command=lambda: self._calistir(self.nem_grafigi),
        )
        self.btn_nem.pack(side="left", padx=5)

        self.btn_ruzgar = ttk.Button(
            ust, text="🌬 Rüzgâr",
            command=lambda: self._calistir(self.ruzgar_grafigi),
        )
        self.btn_ruzgar.pack(side="left", padx=5)

        # Bilgi etiketi (konum yokken kullanıcıyı yönlendir)
        self.lbl_bilgi = ttk.Label(
            ust, text="Önce bir konum seçin/arayın.",
            foreground="#546E7A",
        )
        self.lbl_bilgi.pack(side="right")

        # Canvas alanı (boş bir frame; figure çizildiğinde içine yerleşir)
        self.canvas_alani = ttk.Frame(self)
        self.canvas_alani.pack(fill="both", expand=True)

    # ----- API yönlü -----
    def konumu_ayarla(self, location: Optional[Location]) -> None:
        """Dışarıdan aktif konum bildirimi — etiketi günceller."""
        self.aktif_konum = location
        if location is None:
            self.lbl_bilgi.config(text="Önce bir konum seçin/arayın.")
        else:
            etiket = f"Konum: {location.sehir}"
            if location.ilce:
                etiket += f" / {location.ilce}"
            self.lbl_bilgi.config(text=etiket)

    def sicaklik_grafigi(self, location: Location,
                         saat_sayisi: int = SAATLIK_VARSAYILAN) -> None:
        """24 saatlik sıcaklık serisi."""
        veriler = self._saatlik_veri_cek(location, saat_sayisi)
        x = [w.olcum_tarihi for w in veriler]
        y = [w.sicaklik for w in veriler]
        self._figure_ciz(x, y,
                         baslik=f"{location.sehir} — Saatlik Sıcaklık ({saat_sayisi} saat)",
                         y_etiket="Sıcaklık (°C)",
                         renk="#D32F2F")

    def nem_grafigi(self, location: Location,
                    saat_sayisi: int = SAATLIK_VARSAYILAN) -> None:
        """24 saatlik nem serisi."""
        veriler = self._saatlik_veri_cek(location, saat_sayisi)
        x = [w.olcum_tarihi for w in veriler]
        y = [w.nem for w in veriler]
        self._figure_ciz(x, y,
                         baslik=f"{location.sehir} — Saatlik Nem ({saat_sayisi} saat)",
                         y_etiket="Nem (%)",
                         renk="#1976D2",
                         y_min=0, y_max=100)

    def ruzgar_grafigi(self, location: Location,
                       saat_sayisi: int = SAATLIK_VARSAYILAN) -> None:
        """24 saatlik rüzgâr hızı serisi."""
        veriler = self._saatlik_veri_cek(location, saat_sayisi)
        x = [w.olcum_tarihi for w in veriler]
        y = [w.ruzgar_hizi for w in veriler]
        self._figure_ciz(x, y,
                         baslik=f"{location.sehir} — Saatlik Rüzgâr ({saat_sayisi} saat)",
                         y_etiket="Rüzgâr Hızı (km/h)",
                         renk="#00897B")

    # ----- İç -----
    def _calistir(self, grafik_metodu) -> None:
        """Buton callback'i: aktif konum yoksa uyar; varsa thread'de veri çek."""
        if self.aktif_konum is None:
            messagebox.showinfo("Bilgi", "Önce bir konum seçin veya arayın.")
            return
        # Buton kilidi
        self._butonlari_kilitle(True)
        loc = self.aktif_konum

        def gorev():
            try:
                grafik_metodu(loc)
            except Exception as e:  # noqa: BLE001
                logger.error("Grafik çizilirken hata: %s", e)
                self.after(0, lambda: messagebox.showerror(
                    "Grafik hatası", f"Veri alınamadı: {e}"))
            finally:
                self.after(0, lambda: self._butonlari_kilitle(False))

        threading.Thread(target=gorev, daemon=True).start()

    def _butonlari_kilitle(self, kilitle: bool) -> None:
        durum = "disabled" if kilitle else "normal"
        for b in (self.btn_sicaklik, self.btn_nem, self.btn_ruzgar):
            b.config(state=durum)

    def _saatlik_veri_cek(self, location: Location, saat_sayisi: int) -> list[Weather]:
        """Open-Meteo'dan N saatlik tahmin döner. Konuma henüz id verilmediyse boş döner."""
        return self.weather_api.saatlik_tahmin_cek(location, saat_sayisi=saat_sayisi)

    def _canvas_temizle(self) -> None:
        """Eski matplotlib figure ve canvas'ını düzgünce yok eder (memory leak engeli)."""
        if self._canvas is not None:
            try:
                self._canvas.get_tk_widget().destroy()
            except tk.TclError:
                pass
            self._canvas = None
        if self._figure is not None:
            try:
                # Figure'ı kapat ki matplotlib'in açık figure listesinde birikmesin
                import matplotlib.pyplot as plt
                plt.close(self._figure)
            except Exception:
                pass
            self._figure = None

    def _figure_ciz(self, x_data, y_data, baslik: str, y_etiket: str,
                    renk: str = "#1E88E5",
                    y_min: Optional[float] = None,
                    y_max: Optional[float] = None) -> None:
        """Yeni figure oluşturup canvas'a yerleştirir. UI thread'inden çağrılır."""
        # Thread'den geldiyse UI thread'ine yönlendir
        if threading.current_thread() is not threading.main_thread():
            self.after(0, lambda: self._figure_ciz(
                x_data, y_data, baslik, y_etiket, renk, y_min, y_max))
            return

        self._canvas_temizle()

        fig = Figure(figsize=(9, 4.5), dpi=100)
        ax = fig.add_subplot(111)
        # None değerleri grafikten temizle
        temiz_x = [x for x, y in zip(x_data, y_data) if y is not None]
        temiz_y = [y for y in y_data if y is not None]
        ax.plot(temiz_x, temiz_y, color=renk, linewidth=2, marker="o", markersize=3)
        ax.fill_between(temiz_x, temiz_y, alpha=0.15, color=renk)
        ax.set_title(baslik, fontsize=13, pad=12)
        ax.set_xlabel("Saat")
        ax.set_ylabel(y_etiket)
        ax.grid(True, alpha=0.3)
        # X ekseni Türkçe saat formatı (%H:%M)
        ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
        # Etiketleri eğ
        for label in ax.get_xticklabels():
            label.set_rotation(45)
            label.set_ha("right")
        if y_min is not None and y_max is not None:
            ax.set_ylim(y_min, y_max)
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.canvas_alani)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

        self._figure = fig
        self._canvas = canvas

    # ----- Temizlik -----
    def destroy(self) -> None:
        """Widget yok edilirken figure'ı da kapat."""
        self._canvas_temizle()
        super().destroy()
