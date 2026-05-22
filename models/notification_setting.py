"""NotificationSetting dataclass — BildirimAyarlari tablosunun Python karşılığı."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class NotificationSetting:
    """Kullanıcının SMS/e-posta tercihleri ve risk eşiği."""
    kullanici_id: int
    sms_aktif: bool = True
    email_aktif: bool = True
    risk_esigi: str = "orta"   # 'dusuk' | 'orta' | 'yuksek'
    bildirim_tipi: str = "tum"
    id: Optional[int] = None
    guncelleme_tarihi: Optional[datetime] = None
