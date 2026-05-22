"""Şehir/ilçe arama formu — üst şeride gömülür."""
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional


class SearchForm(ttk.Frame):
    """Şehir/ilçe arama formu (üst şeritte gömülü)."""

    def __init__(self, parent: tk.Widget,
                 on_search: Callable[[str, Optional[str]], None]):
        super().__init__(parent)
        self.on_search = on_search
        self._arayuzu_olustur()

    def _arayuzu_olustur(self) -> None:
        ttk.Label(self, text="Şehir:").grid(row=0, column=0, padx=(0, 5))
        self.entry_sehir = ttk.Entry(self, width=18)
        self.entry_sehir.grid(row=0, column=1, padx=(0, 10))
        self.entry_sehir.bind("<Return>", lambda _e: self._arama_tetikle())

        ttk.Label(self, text="İlçe (ops.):").grid(row=0, column=2, padx=(0, 5))
        self.entry_ilce = ttk.Entry(self, width=15)
        self.entry_ilce.grid(row=0, column=3, padx=(0, 10))
        self.entry_ilce.bind("<Return>", lambda _e: self._arama_tetikle())

        self.btn_ara = ttk.Button(self, text="Ara", command=self._arama_tetikle)
        self.btn_ara.grid(row=0, column=4)

    def _arama_tetikle(self) -> None:
        """Entry'lerdeki değerleri okuyup callback'i çağırır."""
        sehir = self.entry_sehir.get().strip()
        ilce = self.entry_ilce.get().strip() or None
        if not sehir:
            return  # Boş arama yok
        self.on_search(sehir, ilce)
