"""MySQL veritabanı yöneticisi — tüm CRUD operasyonları burada."""
import hashlib
import hmac
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Optional

import mysql.connector
from mysql.connector import Error

from models.favorite import Favorite
from models.location import Location
from models.notification_setting import NotificationSetting
from models.risk_zone import RiskZone
from models.user import User
from models.weather import Weather

logger = logging.getLogger(__name__)


class Database:
    """MySQL bağlantısı ve CRUD operasyonlarını yöneten sınıf."""

    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        # Bağlantı bilgileri sabit tutulur; connect() çağrılınca _baglanti dolar.
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self._baglanti: Optional[mysql.connector.MySQLConnection] = None

    # ----- Bağlantı yönetimi -----
    def connect(self) -> None:
        """MySQL sunucusuna bağlanır. Hata olursa loglar ve yeniden fırlatır."""
        try:
            self._baglanti = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset="utf8mb4",
                collation="utf8mb4_unicode_ci",
                autocommit=True,
            )
            logger.info("Veritabanına bağlanıldı: %s@%s:%s/%s",
                        self.user, self.host, self.port, self.database)
        except Error as e:
            logger.error("Veritabanı bağlantı hatası: %s", e)
            raise
        # Çok kullanıcılı yapıya geçiş — eski şema kalıntılarını idempotent şekilde düzelt.
        try:
            self._migrate_schema()
        except Error as e:
            logger.warning("Otomatik şema migrasyonu sırasında uyarı: %s", e)

    def _migrate_schema(self) -> None:
        """Idempotent migrasyon: eksik kolon ekler, eski seed/kullanici_adi temizler, UNIQUE koyar."""
        sema = self.database

        # 1) sifre_hash kolonu yoksa ekle (önce NULL'a izin ver — mevcut satırlar için)
        satir = self.fetch_one(
            "SELECT COUNT(*) AS c FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA=%s AND TABLE_NAME='Kullanicilar' AND COLUMN_NAME='sifre_hash'",
            (sema,),
        )
        if satir and int(satir.get("c") or 0) == 0:
            self.execute("ALTER TABLE Kullanicilar ADD COLUMN sifre_hash VARCHAR(255) NULL")
            logger.info("Şema migrasyonu: 'sifre_hash' kolonu eklendi.")

        # 2) Eski seed kaydı (sifre_hash boş/NULL olan id=1) → sil
        try:
            self.execute(
                "DELETE FROM Kullanicilar WHERE id=1 AND (sifre_hash IS NULL OR sifre_hash='')"
            )
        except Error as e:
            logger.warning("Eski seed kaydı silinemedi: %s", e)

        # 3) Önceki denemeden kalan 'kullanici_adi' kolonu varsa kaldır
        satir = self.fetch_one(
            "SELECT COUNT(*) AS c FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA=%s AND TABLE_NAME='Kullanicilar' AND COLUMN_NAME='kullanici_adi'",
            (sema,),
        )
        if satir and int(satir.get("c") or 0) > 0:
            try:
                self.execute("ALTER TABLE Kullanicilar DROP COLUMN kullanici_adi")
                logger.info("Şema migrasyonu: 'kullanici_adi' kolonu kaldırıldı.")
            except Error as e:
                logger.warning("'kullanici_adi' kolonu kaldırılamadı: %s", e)

        # 4) 'ad' kolonu UNIQUE değilse UNIQUE yap (mükerrer kayıt varsa atla)
        satir = self.fetch_one(
            "SELECT COUNT(*) AS c FROM INFORMATION_SCHEMA.STATISTICS "
            "WHERE TABLE_SCHEMA=%s AND TABLE_NAME='Kullanicilar' AND COLUMN_NAME='ad' "
            "AND NON_UNIQUE=0",
            (sema,),
        )
        if satir and int(satir.get("c") or 0) == 0:
            try:
                self.execute("ALTER TABLE Kullanicilar ADD UNIQUE KEY uniq_ad (ad)")
                logger.info("Şema migrasyonu: 'ad' alanına UNIQUE constraint eklendi.")
            except Error as e:
                # Mükerrer kayıt varsa burası patlar — uygulama yine çalışır, ama kayıtta
                # benzersizlik kontrolü uygulama katmanında yapılıyor zaten.
                logger.warning("'ad' UNIQUE constraint eklenemedi: %s", e)

    def disconnect(self) -> None:
        """Açık bağlantıyı kapatır."""
        try:
            if self._baglanti is not None and self._baglanti.is_connected():
                self._baglanti.close()
                logger.info("Veritabanı bağlantısı kapatıldı.")
        except Error as e:
            logger.warning("Bağlantı kapatılırken hata: %s", e)
        finally:
            self._baglanti = None

    def is_connected(self) -> bool:
        """Aktif bağlantı varsa True döner."""
        try:
            return self._baglanti is not None and self._baglanti.is_connected()
        except Error:
            return False

    def __enter__(self) -> "Database":
        # Context manager girişinde otomatik bağlanır.
        if not self.is_connected():
            self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        # Context manager çıkışında garantili kapanış.
        self.disconnect()

    # ----- Düşük seviye -----
    def execute(self, query: str, params: tuple | None = None) -> int:
        """Sorguyu çalıştırır. INSERT'te lastrowid, diğer yazma işlemlerinde rowcount döner."""
        if not self.is_connected():
            raise RuntimeError("Veritabanı bağlantısı yok. Önce connect() çağrılmalı.")
        cursor = self._baglanti.cursor()
        try:
            cursor.execute(query, params or ())
            # INSERT için lastrowid > 0 olur; UPDATE/DELETE için rowcount uygundur
            if cursor.lastrowid:
                return int(cursor.lastrowid)
            return int(cursor.rowcount)
        except Error as e:
            logger.error("Sorgu hatası (%s): %s | params=%s", query.split()[0], e, params)
            raise
        finally:
            cursor.close()

    def fetch_one(self, query: str, params: tuple | None = None) -> Optional[dict]:
        """Tek bir satır döner (dict). Sonuç yoksa None."""
        if not self.is_connected():
            raise RuntimeError("Veritabanı bağlantısı yok. Önce connect() çağrılmalı.")
        cursor = self._baglanti.cursor(dictionary=True)
        try:
            cursor.execute(query, params or ())
            satir = cursor.fetchone()
            # Birden fazla satır geldiyse fazlasını tüket (cursor temizliği için)
            while cursor.fetchone() is not None:
                pass
            return satir
        except Error as e:
            logger.error("fetch_one hatası: %s | params=%s", e, params)
            raise
        finally:
            cursor.close()

    def fetch_all(self, query: str, params: tuple | None = None) -> list[dict]:
        """Tüm satırları dict listesi olarak döner."""
        if not self.is_connected():
            raise RuntimeError("Veritabanı bağlantısı yok. Önce connect() çağrılmalı.")
        cursor = self._baglanti.cursor(dictionary=True)
        try:
            cursor.execute(query, params or ())
            return list(cursor.fetchall())
        except Error as e:
            logger.error("fetch_all hatası: %s | params=%s", e, params)
            raise
        finally:
            cursor.close()

    # ----- Kullanıcı -----
    _PBKDF2_ITER = 200_000
    _PBKDF2_ALGO = "sha256"

    @staticmethod
    def _sifre_hashle(sifre: str) -> str:
        """PBKDF2-SHA256 ile şifreyi hashler. Format: algo$iter$salt_hex$hash_hex."""
        salt = os.urandom(16)
        turetilmis = hashlib.pbkdf2_hmac(
            Database._PBKDF2_ALGO, sifre.encode("utf-8"), salt, Database._PBKDF2_ITER
        )
        return f"pbkdf2_{Database._PBKDF2_ALGO}${Database._PBKDF2_ITER}${salt.hex()}${turetilmis.hex()}"

    @staticmethod
    def _sifre_dogrula(sifre: str, sifre_hash: str) -> bool:
        """Verilen düz şifreyi saklı hash ile sabit zamanlı karşılaştırır."""
        try:
            algo_etiketi, iter_str, salt_hex, hash_hex = sifre_hash.split("$")
            if not algo_etiketi.startswith("pbkdf2_"):
                return False
            algo = algo_etiketi.split("_", 1)[1]
            iterasyon = int(iter_str)
            salt = bytes.fromhex(salt_hex)
            beklenen = bytes.fromhex(hash_hex)
        except (ValueError, AttributeError):
            return False
        turetilmis = hashlib.pbkdf2_hmac(algo, sifre.encode("utf-8"), salt, iterasyon)
        return hmac.compare_digest(turetilmis, beklenen)

    def ad_var_mi(self, ad: str) -> bool:
        """Verilen ad kayıtlı mı?"""
        satir = self.fetch_one(
            "SELECT id FROM Kullanicilar WHERE ad = %s",
            ((ad or "").strip(),),
        )
        return satir is not None

    def kullanici_kayit(self, ad: str, sifre: str,
                        email: Optional[str] = None,
                        telefon: Optional[str] = None) -> User:
        """Yeni kullanıcı kaydeder; default bildirim ayarını da otomatik oluşturur."""
        ad = (ad or "").strip()
        if not ad or not sifre:
            raise ValueError("Ad ve şifre boş olamaz.")
        if self.ad_var_mi(ad):
            raise ValueError("Bu ad zaten kayıtlı.")
        sifre_hash = self._sifre_hashle(sifre)
        yeni_id = self.execute(
            "INSERT INTO Kullanicilar (ad, sifre_hash, email, telefon) "
            "VALUES (%s, %s, %s, %s)",
            (ad, sifre_hash, email, telefon),
        )
        # Default bildirim ayarını da ekle (şema seed'i çok kullanıcıda yok)
        self.execute(
            "INSERT INTO BildirimAyarlari (kullanici_id) VALUES (%s)",
            (int(yeni_id),),
        )
        kullanici = self.kullanici_getir(int(yeni_id))
        if kullanici is None:
            raise RuntimeError("Kullanıcı eklendi ancak geri okunamadı.")
        return kullanici

    def kullanici_dogrula(self, ad: str, sifre: str) -> Optional[User]:
        """Ad + şifre eşleşirse User döner, aksi halde None."""
        satir = self.fetch_one(
            "SELECT id, sifre_hash, ad, email, telefon, kvkk_onay, kayit_tarihi "
            "FROM Kullanicilar WHERE ad = %s",
            ((ad or "").strip(),),
        )
        if not satir:
            return None
        if not self._sifre_dogrula(sifre, satir.get("sifre_hash") or ""):
            return None
        return self._row_to_user(satir)

    def kullanici_getir(self, kullanici_id: int) -> Optional[User]:
        """Kullanıcıyı id ile getirir. Yoksa None."""
        satir = self.fetch_one(
            "SELECT id, sifre_hash, ad, email, telefon, kvkk_onay, kayit_tarihi "
            "FROM Kullanicilar WHERE id = %s",
            (kullanici_id,),
        )
        return self._row_to_user(satir) if satir else None

    def kullanici_guncelle(self, user: User) -> bool:
        """Kullanıcının ad/email/telefon/kvkk_onay alanlarını günceller."""
        if user.id is None:
            raise ValueError("kullanici_guncelle: user.id zorunludur.")
        etkilenen = self.execute(
            "UPDATE Kullanicilar SET ad=%s, email=%s, telefon=%s, kvkk_onay=%s "
            "WHERE id=%s",
            (user.ad, user.email, user.telefon, bool(user.kvkk_onay), user.id),
        )
        return etkilenen > 0

    # ----- Konum -----
    def konum_ekle(self, location: Location) -> int:
        """Var olan (sehir, ilce, ulke) ise mevcut id döner, yoksa ekleyip yeni id verir."""
        # Önce mevcut kayıt var mı kontrol et — unique key çakışmasından kaçınmak için.
        mevcut = self.fetch_one(
            "SELECT id FROM Konumlar "
            "WHERE sehir=%s AND ((ilce IS NULL AND %s IS NULL) OR ilce=%s) AND ulke=%s",
            (location.sehir, location.ilce, location.ilce, location.ulke),
        )
        if mevcut:
            return int(mevcut["id"])

        yeni_id = self.execute(
            "INSERT INTO Konumlar (sehir, ilce, ulke, latitude, longitude) "
            "VALUES (%s, %s, %s, %s, %s)",
            (location.sehir, location.ilce, location.ulke,
             float(location.latitude), float(location.longitude)),
        )
        return int(yeni_id)

    def konum_getir(self, konum_id: int) -> Optional[Location]:
        """Konumu id ile getirir."""
        satir = self.fetch_one(
            "SELECT id, sehir, ilce, ulke, latitude, longitude, olusturma_tarihi "
            "FROM Konumlar WHERE id=%s",
            (konum_id,),
        )
        return self._row_to_location(satir) if satir else None

    def konum_ara(self, sehir: str, ilce: Optional[str] = None) -> Optional[Location]:
        """Şehir (ve opsiyonel ilçe) ile konum arar; ilk eşleşeni döner."""
        if ilce is None:
            satir = self.fetch_one(
                "SELECT id, sehir, ilce, ulke, latitude, longitude, olusturma_tarihi "
                "FROM Konumlar WHERE LOWER(sehir)=LOWER(%s) AND ilce IS NULL LIMIT 1",
                (sehir,),
            )
            # İlçe NULL kaydı yoksa, ilk eşleşen şehri dene
            if not satir:
                satir = self.fetch_one(
                    "SELECT id, sehir, ilce, ulke, latitude, longitude, olusturma_tarihi "
                    "FROM Konumlar WHERE LOWER(sehir)=LOWER(%s) LIMIT 1",
                    (sehir,),
                )
        else:
            satir = self.fetch_one(
                "SELECT id, sehir, ilce, ulke, latitude, longitude, olusturma_tarihi "
                "FROM Konumlar WHERE LOWER(sehir)=LOWER(%s) AND LOWER(ilce)=LOWER(%s) LIMIT 1",
                (sehir, ilce),
            )
        return self._row_to_location(satir) if satir else None

    def tum_konumlari_getir(self) -> list[Location]:
        """Tüm konumları döner."""
        satirlar = self.fetch_all(
            "SELECT id, sehir, ilce, ulke, latitude, longitude, olusturma_tarihi "
            "FROM Konumlar ORDER BY sehir, ilce"
        )
        return [self._row_to_location(r) for r in satirlar]

    # ----- Hava Durumu -----
    def hava_durumu_ekle(self, weather: Weather) -> int:
        """Yeni hava durumu ölçümü ekler; eklenen kaydın id'sini döner."""
        yeni_id = self.execute(
            "INSERT INTO HavaDurumu "
            "(konum_id, olcum_tarihi, sicaklik, hissedilen_sicaklik, nem, "
            " ruzgar_hizi, ruzgar_yonu, basinc, yagis_mm, durum_kodu, "
            " durum_aciklamasi, kaynak_api) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                weather.konum_id,
                weather.olcum_tarihi,
                weather.sicaklik,
                weather.hissedilen_sicaklik,
                weather.nem,
                weather.ruzgar_hizi,
                weather.ruzgar_yonu,
                weather.basinc,
                weather.yagis_mm,
                weather.durum_kodu,
                weather.durum_aciklamasi,
                weather.kaynak_api,
            ),
        )
        return int(yeni_id)

    def son_hava_durumu_getir(self, konum_id: int) -> Optional[Weather]:
        """Konum için en güncel ölçümü döner."""
        satir = self.fetch_one(
            "SELECT * FROM HavaDurumu WHERE konum_id=%s "
            "ORDER BY olcum_tarihi DESC, id DESC LIMIT 1",
            (konum_id,),
        )
        return self._row_to_weather(satir) if satir else None

    def hava_durumu_gecmisi(self, konum_id: int, gun_sayisi: int = 7) -> list[Weather]:
        """Son N gündeki ölçümleri eski→yeni sırayla döner."""
        esik = datetime.now() - timedelta(days=gun_sayisi)
        satirlar = self.fetch_all(
            "SELECT * FROM HavaDurumu WHERE konum_id=%s AND olcum_tarihi >= %s "
            "ORDER BY olcum_tarihi ASC, id ASC",
            (konum_id, esik),
        )
        return [self._row_to_weather(r) for r in satirlar]

    def eski_kayitlari_temizle(self, gun_sayisi: int = 30) -> int:
        """N günden eski hava durumu kayıtlarını siler; silinen satır sayısı döner."""
        esik = datetime.now() - timedelta(days=gun_sayisi)
        return self.execute(
            "DELETE FROM HavaDurumu WHERE olcum_tarihi < %s",
            (esik,),
        )

    # ----- Favoriler -----
    def favori_ekle(self, kullanici_id: int, konum_id: int) -> int:
        """Favori ekler; varsa mevcut id döner (unique constraint nedeniyle çakışmaz)."""
        mevcut = self.fetch_one(
            "SELECT id FROM Favoriler WHERE kullanici_id=%s AND konum_id=%s",
            (kullanici_id, konum_id),
        )
        if mevcut:
            return int(mevcut["id"])
        yeni_id = self.execute(
            "INSERT INTO Favoriler (kullanici_id, konum_id) VALUES (%s, %s)",
            (kullanici_id, konum_id),
        )
        return int(yeni_id)

    def favori_sil(self, kullanici_id: int, konum_id: int) -> bool:
        """Favoriyi siler; en az 1 satır etkilendiyse True."""
        etkilenen = self.execute(
            "DELETE FROM Favoriler WHERE kullanici_id=%s AND konum_id=%s",
            (kullanici_id, konum_id),
        )
        return etkilenen > 0

    def favorileri_getir(self, kullanici_id: int) -> list[Favorite]:
        """Kullanıcının favori listesi (sira artan)."""
        satirlar = self.fetch_all(
            "SELECT id, kullanici_id, konum_id, sira, eklenme_tarihi "
            "FROM Favoriler WHERE kullanici_id=%s ORDER BY sira ASC, id ASC",
            (kullanici_id,),
        )
        return [self._row_to_favorite(r) for r in satirlar]

    def favori_mi(self, kullanici_id: int, konum_id: int) -> bool:
        """Verilen konum kullanıcının favorisinde mi?"""
        satir = self.fetch_one(
            "SELECT id FROM Favoriler WHERE kullanici_id=%s AND konum_id=%s",
            (kullanici_id, konum_id),
        )
        return satir is not None

    # ----- Bildirim Ayarları -----
    def bildirim_ayari_getir(self, kullanici_id: int) -> Optional[NotificationSetting]:
        """Kullanıcının bildirim ayarını döner."""
        satir = self.fetch_one(
            "SELECT id, kullanici_id, sms_aktif, email_aktif, risk_esigi, "
            "       bildirim_tipi, guncelleme_tarihi "
            "FROM BildirimAyarlari WHERE kullanici_id=%s",
            (kullanici_id,),
        )
        return self._row_to_notification_setting(satir) if satir else None

    def bildirim_ayari_guncelle(self, setting: NotificationSetting) -> bool:
        """Bildirim ayarını günceller; yoksa ekler (upsert)."""
        # Önce var mı kontrol et
        mevcut = self.fetch_one(
            "SELECT id FROM BildirimAyarlari WHERE kullanici_id=%s",
            (setting.kullanici_id,),
        )
        if mevcut:
            etkilenen = self.execute(
                "UPDATE BildirimAyarlari SET sms_aktif=%s, email_aktif=%s, "
                "risk_esigi=%s, bildirim_tipi=%s WHERE kullanici_id=%s",
                (bool(setting.sms_aktif), bool(setting.email_aktif),
                 setting.risk_esigi, setting.bildirim_tipi, setting.kullanici_id),
            )
            return etkilenen >= 0  # UPDATE rowcount 0 olsa bile başarılı sayılır
        # Kayıt yoksa ekle
        self.execute(
            "INSERT INTO BildirimAyarlari (kullanici_id, sms_aktif, email_aktif, "
            "risk_esigi, bildirim_tipi) VALUES (%s, %s, %s, %s, %s)",
            (setting.kullanici_id, bool(setting.sms_aktif), bool(setting.email_aktif),
             setting.risk_esigi, setting.bildirim_tipi),
        )
        return True

    # ----- Riskli Bölgeler -----
    def riskli_bolge_ekle(self, risk: RiskZone) -> int:
        """Yeni risk olayı ekler; id döner."""
        yeni_id = self.execute(
            "INSERT INTO RiskliBolgeler (konum_id, risk_tipi, siddet, baslangic, "
            "bitis, aciklama) VALUES (%s, %s, %s, %s, %s, %s)",
            (risk.konum_id, risk.risk_tipi, risk.siddet, risk.baslangic,
             risk.bitis, risk.aciklama),
        )
        return int(yeni_id)

    def aktif_riskleri_getir(self, konum_id: Optional[int] = None) -> list[RiskZone]:
        """Aktif (bitis NULL veya gelecekte) riskleri döner."""
        simdi = datetime.now()
        if konum_id is None:
            satirlar = self.fetch_all(
                "SELECT id, konum_id, risk_tipi, siddet, baslangic, bitis, "
                "       aciklama, olusturma_tarihi "
                "FROM RiskliBolgeler WHERE bitis IS NULL OR bitis > %s "
                "ORDER BY baslangic DESC",
                (simdi,),
            )
        else:
            satirlar = self.fetch_all(
                "SELECT id, konum_id, risk_tipi, siddet, baslangic, bitis, "
                "       aciklama, olusturma_tarihi "
                "FROM RiskliBolgeler WHERE konum_id=%s AND (bitis IS NULL OR bitis > %s) "
                "ORDER BY baslangic DESC",
                (konum_id, simdi),
            )
        return [self._row_to_risk_zone(r) for r in satirlar]

    def riskli_bolge_kapat(self, risk_id: int) -> bool:
        """Risk olayını şimdi kapatır (bitis=NOW())."""
        etkilenen = self.execute(
            "UPDATE RiskliBolgeler SET bitis=%s WHERE id=%s AND bitis IS NULL",
            (datetime.now(), risk_id),
        )
        return etkilenen > 0

    # ----- Yardımcılar -----
    @staticmethod
    def _to_float(deger: Any) -> Optional[float]:
        """DECIMAL/None → float dönüşümü (None korunur)."""
        if deger is None:
            return None
        return float(deger)

    @staticmethod
    def _to_int(deger: Any) -> Optional[int]:
        """Sayı/None → int dönüşümü."""
        if deger is None:
            return None
        return int(deger)

    @staticmethod
    def _row_to_user(row: dict) -> User:
        """DB satırını User dataclass'ına çevirir."""
        return User(
            id=row.get("id"),
            ad=row.get("ad", "Kullanıcı"),
            email=row.get("email"),
            telefon=row.get("telefon"),
            kvkk_onay=bool(row.get("kvkk_onay", False)),
            kayit_tarihi=row.get("kayit_tarihi"),
            sifre_hash=row.get("sifre_hash"),
        )

    @staticmethod
    def _row_to_location(row: dict) -> Location:
        """DB satırını Location dataclass'ına çevirir."""
        return Location(
            id=row.get("id"),
            sehir=row["sehir"],
            ilce=row.get("ilce"),
            ulke=row.get("ulke", "Türkiye"),
            latitude=float(row["latitude"]),
            longitude=float(row["longitude"]),
            olusturma_tarihi=row.get("olusturma_tarihi"),
        )

    @staticmethod
    def _row_to_weather(row: dict) -> Weather:
        """DB satırını Weather dataclass'ına çevirir."""
        return Weather(
            id=row.get("id"),
            konum_id=int(row["konum_id"]),
            olcum_tarihi=row["olcum_tarihi"],
            sicaklik=Database._to_float(row.get("sicaklik")),
            hissedilen_sicaklik=Database._to_float(row.get("hissedilen_sicaklik")),
            nem=Database._to_int(row.get("nem")),
            ruzgar_hizi=Database._to_float(row.get("ruzgar_hizi")),
            ruzgar_yonu=Database._to_int(row.get("ruzgar_yonu")),
            basinc=Database._to_float(row.get("basinc")),
            yagis_mm=Database._to_float(row.get("yagis_mm")),
            durum_kodu=Database._to_int(row.get("durum_kodu")),
            durum_aciklamasi=row.get("durum_aciklamasi"),
            kaynak_api=row.get("kaynak_api", "Open-Meteo"),
            olusturma_tarihi=row.get("olusturma_tarihi"),
        )

    @staticmethod
    def _row_to_favorite(row: dict) -> Favorite:
        """DB satırını Favorite dataclass'ına çevirir."""
        return Favorite(
            id=row.get("id"),
            kullanici_id=int(row["kullanici_id"]),
            konum_id=int(row["konum_id"]),
            sira=int(row.get("sira") or 0),
            eklenme_tarihi=row.get("eklenme_tarihi"),
        )

    @staticmethod
    def _row_to_notification_setting(row: dict) -> NotificationSetting:
        """DB satırını NotificationSetting dataclass'ına çevirir."""
        return NotificationSetting(
            id=row.get("id"),
            kullanici_id=int(row["kullanici_id"]),
            sms_aktif=bool(row.get("sms_aktif", True)),
            email_aktif=bool(row.get("email_aktif", True)),
            risk_esigi=row.get("risk_esigi", "orta"),
            bildirim_tipi=row.get("bildirim_tipi", "tum"),
            guncelleme_tarihi=row.get("guncelleme_tarihi"),
        )

    @staticmethod
    def _row_to_risk_zone(row: dict) -> RiskZone:
        """DB satırını RiskZone dataclass'ına çevirir."""
        return RiskZone(
            id=row.get("id"),
            konum_id=int(row["konum_id"]),
            risk_tipi=row["risk_tipi"],
            siddet=row.get("siddet", "orta"),
            baslangic=row["baslangic"],
            bitis=row.get("bitis"),
            aciklama=row.get("aciklama"),
            olusturma_tarihi=row.get("olusturma_tarihi"),
        )
