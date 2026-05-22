"""Weather dataclass — HavaDurumu tablosunun Python karşılığı."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Weather:
    """Belirli bir konum ve zamana ait meteorolojik ölçüm/tahmin."""
    konum_id: int
    olcum_tarihi: datetime
    sicaklik: Optional[float] = None
    hissedilen_sicaklik: Optional[float] = None
    nem: Optional[int] = None
    ruzgar_hizi: Optional[float] = None
    ruzgar_yonu: Optional[int] = None
    basinc: Optional[float] = None
    yagis_mm: Optional[float] = None
    durum_kodu: Optional[int] = None
    durum_aciklamasi: Optional[str] = None
    kaynak_api: str = "Open-Meteo"
    id: Optional[int] = None
    olusturma_tarihi: Optional[datetime] = None
