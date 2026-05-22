"""Favorite dataclass — Favoriler tablosunun Python karşılığı."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Favorite:
    """Bir kullanıcının kaydettiği favori konum."""
    kullanici_id: int
    konum_id: int
    sira: int = 0
    id: Optional[int] = None
    eklenme_tarihi: Optional[datetime] = None
