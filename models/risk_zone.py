"""RiskZone dataclass — RiskliBolgeler tablosunun Python karşılığı."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class RiskZone:
    """Bir konum için tespit edilen meteorolojik risk olayı."""
    konum_id: int
    risk_tipi: str
    baslangic: datetime
    siddet: str = "orta"        # 'dusuk' | 'orta' | 'yuksek'
    bitis: Optional[datetime] = None
    aciklama: Optional[str] = None
    id: Optional[int] = None
    olusturma_tarihi: Optional[datetime] = None
