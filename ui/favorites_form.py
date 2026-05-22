"""Favori bölgeler — liste, ekleme, silme, seçim."""
import logging
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Optional

from database.db_manager import Database
from models.location import Location
from services.weather_api import WeatherAPI

logger = logging.getLogger(__name__)


class FavoritesForm(ttk.Frame):
    """Favori bölgeler listesi + ekleme/silme."""

    def __init__(self, parent: tk.Widget, db: Database, weather_api: WeatherAPI,
                 kullanici_id: int = 1,
                 on_select: Optional[Callable[[Location], None]] = None):
        super().__init__(parent, padding=15)
        self.db = db
        self.weather_api = weather_api
        self.kullanici_id = kullanici_id
        self.on_select = on_select
        self._arayuzu_olustur()
        self.listeyi_yenile()

    # ----- Arayüz -----
    def _arayuzu_olustur(self) -> None:
        ttk.Label(self, text="Favori Bölgeler",
                  font=("Helvetica", 13, "bold")).pack(anchor="w", pady=(0, 10))

        # Tree (sütunlar: şehir, ilçe, son sıcaklık, ölçüm zamanı)
        cerceve = ttk.Frame(self)
        cerceve.pack(fill="both", expand=True)

        sutunlar = ("sehir", "ilce", "sicaklik", "olcum")
        self.tree = ttk.Treeview(cerceve, columns=sutunlar, show="headings", height=12)
        self.tree.heading("sehir", text="Şehir")
        self.tree.heading("ilce", text="İlçe")
        self.tree.heading("sicaklik", text="Son Sıcaklık")
        self.tree.heading("olcum", text="Ölçüm Zamanı")
        self.tree.column("sehir", width=180, anchor="w")
        self.tree.column("ilce", width=140, anchor="w")
        self.tree.column("sicaklik", width=120, anchor="center")
        self.tree.column("olcum", width=180, anchor="center")

        scroll = ttk.Scrollbar(cerceve, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # Çift tıklama: seçili favoriyi yükle
        self.tree.bind("<Double-1>", self._secileni_goster)

        # Alt butonlar
        butonlar = ttk.Frame(self)
        butonlar.pack(fill="x", pady=(10, 0))

        ttk.Button(butonlar, text="Seçileni Göster",
                   command=self._secileni_goster).pack(side="left")
        ttk.Button(butonlar, text="Seçileni Sil",
                   command=self._secileni_sil).pack(side="left", padx=(8, 0))
        ttk.Button(butonlar, text="Yenile",
                   command=self.listeyi_yenile).pack(side="left", padx=(8, 0))

        # _konum_haritasi: tree item iid → Location
        self._konum_haritasi: dict[str, Location] = {}

    # ----- Veri akışı -----
    def listeyi_yenile(self) -> None:
        """DB'den favorileri çek, listeyi yeniden doldur."""
        # Mevcut satırları sil
        for satir in self.tree.get_children():
            self.tree.delete(satir)
        self._konum_haritasi.clear()

        try:
            favoriler = self.db.favorileri_getir(self.kullanici_id)
        except Exception as e:
            logger.error("Favoriler okunamadı: %s", e)
            messagebox.showerror("DB hatası", f"Favoriler okunamadı: {e}")
            return

        for fav in favoriler:
            try:
                loc = self.db.konum_getir(fav.konum_id)
                if loc is None:
                    continue
                son = self.db.son_hava_durumu_getir(fav.konum_id)
            except Exception as e:
                logger.error("Favori için konum/hava okunamadı: %s", e)
                continue

            sicaklik_str = (f"{son.sicaklik:.1f}°C"
                            if son and son.sicaklik is not None else "—")
            olcum_str = (son.olcum_tarihi.strftime("%d.%m %H:%M")
                         if son and son.olcum_tarihi else "—")

            iid = self.tree.insert(
                "", "end",
                values=(loc.sehir, loc.ilce or "—", sicaklik_str, olcum_str),
            )
            self._konum_haritasi[iid] = loc

    def favori_ekle(self, konum_id: int) -> bool:
        """Konumu favoriye ekler. Zaten varsa True döner (DB unique nedeniyle hata yok)."""
        try:
            self.db.favori_ekle(self.kullanici_id, konum_id)
            self.listeyi_yenile()
            return True
        except Exception as e:
            logger.error("Favori eklenemedi: %s", e)
            messagebox.showerror("Favori hatası", f"Favori eklenemedi: {e}")
            return False

    def favori_sil(self, konum_id: int) -> bool:
        """Konumu favorilerden siler."""
        try:
            silindi = self.db.favori_sil(self.kullanici_id, konum_id)
            self.listeyi_yenile()
            return silindi
        except Exception as e:
            logger.error("Favori silinemedi: %s", e)
            messagebox.showerror("Favori hatası", f"Favori silinemedi: {e}")
            return False

    # ----- İç -----
    def _secileni_goster(self, event=None) -> None:
        """Seçili veya çift tıklanan favoriyi callback'e yollar."""
        secim = self.tree.selection()
        if not secim:
            return
        loc = self._konum_haritasi.get(secim[0])
        if loc is None or self.on_select is None:
            return
        try:
            self.on_select(loc)
        except Exception as e:  # noqa: BLE001
            logger.error("on_select callback hatası: %s", e)

    def _secileni_sil(self) -> None:
        """Seçili favoriyi onay sorarak siler."""
        secim = self.tree.selection()
        if not secim:
            return
        loc = self._konum_haritasi.get(secim[0])
        if loc is None or loc.id is None:
            return
        if not messagebox.askyesno(
            "Onay", f"'{loc.sehir}' favorilerden silinsin mi?"
        ):
            return
        self.favori_sil(loc.id)
