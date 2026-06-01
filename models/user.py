"""User dataclass — Kullanicilar tablosunun Python karşılığı."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """Çok kullanıcılı modeldeki kullanıcı kaydı (ad + şifre ile giriş)."""
    ad: str = "Kullanıcı"
    email: Optional[str] = None
    telefon: Optional[str] = None
    kvkk_onay: bool = False
    id: Optional[int] = None
    kayit_tarihi: Optional[datetime] = None
    sifre_hash: Optional[str] = None
