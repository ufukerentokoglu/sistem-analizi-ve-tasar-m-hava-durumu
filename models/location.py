"""Location dataclass — Konumlar tablosunun Python karşılığı."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Location:
    """Bir şehir/ilçe konumunu enlem-boylam ile temsil eder."""
    sehir: str
    latitude: float
    longitude: float
    ilce: Optional[str] = None
    ulke: str = "Türkiye"
    id: Optional[int] = None
    olusturma_tarihi: Optional[datetime] = None
