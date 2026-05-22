"""Bildirim servisi — SMS log simülasyonu + SMTP üzerinden gerçek e-posta."""
import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

import config
from models.location import Location
from models.risk_zone import RiskZone
from models.user import User

logger = logging.getLogger(__name__)


class NotificationService:
    """SMS simülasyonu + gerçek e-posta gönderimi."""

    # Şiddet → Türkçe etiket (mesaj metninde kullanılır)
    SIDDET_ETIKETLERI: dict[str, str] = {
        "dusuk": "düşük",
        "orta": "orta",
        "yuksek": "yüksek",
    }

    RISK_BASLIKLARI: dict[str, str] = {
        "firtina": "fırtına",
        "asiri_sicak": "aşırı sıcak",
        "asiri_soguk": "aşırı soğuk",
        "siddetli_ruzgar": "şiddetli rüzgâr",
        "yogun_yagis": "yoğun yağış",
    }

    def __init__(self, sms_log_path: Optional[Path] = None):
        # Log dosyası: spec'te logs/sms_log.txt
        self.sms_log_path = sms_log_path or Path(config.LOG_DIR) / "sms_log.txt"
        try:
            self.sms_log_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error("SMS log dizini oluşturulamadı: %s", e)

    # ----- SMS (simülasyon) -----
    def sms_gonder(self, telefon: str, mesaj: str) -> bool:
        """SMS gönderir (simülasyon: log dosyasına yazma)."""
        if not telefon:
            logger.warning("SMS gönderilemedi: telefon numarası boş.")
            return False
        satir = (f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                 f"TO: {telefon} | MSG: {mesaj}\n")
        try:
            with open(self.sms_log_path, "a", encoding="utf-8") as f:
                f.write(satir)
            logger.info("SMS log'a yazıldı: %s", telefon)
            return True
        except OSError as e:
            logger.error("SMS log'a yazılamadı: %s", e)
            return False

    # ----- E-posta (gerçek SMTP) -----
    def email_gonder(self, alici_email: str, konu: str, govde: str) -> bool:
        """SMTP üzerinden e-posta gönderir."""
        if not alici_email:
            logger.warning("E-posta gönderilemedi: alıcı adresi boş.")
            return False
        if not config.EMAIL_GONDERIMI_AKTIF:
            logger.warning("SMTP yapılandırılmadığı için e-posta atlanıyor (alıcı=%s).",
                           alici_email)
            return False

        mesaj = MIMEMultipart()
        mesaj["From"] = f"{config.SMTP_FROM_NAME} <{config.SMTP_USER}>"
        mesaj["To"] = alici_email
        mesaj["Subject"] = konu
        mesaj.attach(MIMEText(govde, "plain", "utf-8"))

        try:
            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=15) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.login(config.SMTP_USER, config.SMTP_PASSWORD)
                smtp.send_message(mesaj)
            logger.info("E-posta gönderildi: %s", alici_email)
            return True
        except (smtplib.SMTPException, OSError) as e:
            logger.error("E-posta gönderilemedi (%s): %s", alici_email, e)
            return False

    # ----- Bütünleşik risk bildirimi -----
    def risk_bildirimi_gonder(self, user: User, risk: RiskZone, location: Location,
                              sms_aktif: bool, email_aktif: bool) -> dict:
        """Hem SMS hem e-posta gönderir; sonuç: {'sms': bool, 'email': bool}."""
        mesaj = self._mesaj_olustur(risk, location)
        sonuc = {"sms": False, "email": False}

        if sms_aktif:
            if user.telefon:
                sonuc["sms"] = self.sms_gonder(user.telefon, mesaj)
            else:
                logger.info("SMS atlandı: kullanıcının telefon numarası yok.")

        if email_aktif:
            if user.email:
                konu = f"⚠ Hava Durumu Uyarısı: {location.sehir}"
                sonuc["email"] = self.email_gonder(user.email, konu, mesaj)
            else:
                logger.info("E-posta atlandı: kullanıcının e-posta adresi yok.")

        return sonuc

    # ----- Mesaj kurucu -----
    def _mesaj_olustur(self, risk: RiskZone, location: Location) -> str:
        """Risk için Türkçe mesaj metni oluşturur."""
        risk_etiket = self.RISK_BASLIKLARI.get(risk.risk_tipi, risk.risk_tipi)
        siddet_etiket = self.SIDDET_ETIKETLERI.get(risk.siddet, risk.siddet)
        konum_str = location.sehir
        if location.ilce:
            konum_str = f"{location.ilce}/{location.sehir}"
        parcalar = [
            f"⚠ {konum_str} için {risk_etiket} uyarısı!",
            f"Şiddet: {siddet_etiket}.",
        ]
        if risk.aciklama:
            parcalar.append(f"Detay: {risk.aciklama}.")
        parcalar.append("Lütfen tedbirli olun.")
        return " ".join(parcalar)
