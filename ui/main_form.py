"""Ana uygulama penceresi — sekmeli yapı, üst şerit (konum + arama + IP tespit)."""
import logging
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

from database.db_manager import Database
from models.location import Location
from models.weather import Weather
from services.background_scheduler import BackgroundScheduler
from services.location_service import LocationService
from services.notification_service import NotificationService
from services.risk_analyzer import RiskAnalyzer
from services.weather_api import WeatherAPI
from ui.chart_form import ChartForm
from ui.favorites_form import FavoritesForm
from ui.risk_alert_form import RiskAlertForm
from ui.search_form import SearchForm
from ui.settings_form import SettingsForm
from ui.weather_display_form import WeatherDisplayForm

logger = logging.getLogger(__name__)

# Renk paleti (SPEC önerisi)
RENK_ANA = "#1E88E5"
RENK_KOYU = "#0D47A1"
RENK_ARKAPLAN = "#E3F2FD"


class MainForm(tk.Tk):
    """Ana uygulama penceresi."""

    def __init__(self, db: Database, weather_api: WeatherAPI,
                 location_service: LocationService,
                 risk_analyzer: Optional[RiskAnalyzer] = None,
                 notification_service: Optional[NotificationService] = None,
                 scheduler: Optional[BackgroundScheduler] = None,
                 kullanici_id: int = 1,
                 konum_izni: bool = True):
        super().__init__()
        self.db = db
        self.weather_api = weather_api
        self.location_service = location_service
        self.kullanici_id = kullanici_id
        # KVKK reddedildiğinde False olur — "Konumumu Tespit Et" devre dışı tutulur
        self.konum_izni = konum_izni
        self.aktif_konum: Optional[Location] = None

        # Aşama 7 servisleri — dışarıdan inject edilebilir, yoksa default oluşur
        import config as _cfg
        self.risk_analyzer: RiskAnalyzer = risk_analyzer or RiskAnalyzer()
        self.notification_service: NotificationService = (
            notification_service or NotificationService()
        )
        self.scheduler: BackgroundScheduler = (
            scheduler or BackgroundScheduler(_cfg.BACKGROUND_INTERVAL_MINUTES)
        )
        # Aynı risk için kısa sürede tekrar pop-up açmamak için (konum_id, risk_tipi) cache
        self._son_risk_zamanlari: dict[tuple[int, str], float] = {}

        self.title("Hava Durumu Yazılımı")
        self.geometry("1100x700")
        self.configure(bg=RENK_ARKAPLAN)
        self._merkezle()
        self._stilleri_ayarla()
        self._arayuzu_olustur()

        # Periyodik görev + pencere kapanış kancası
        self.scheduler.gorev_ekle(self.periyodik_kontrol)
        self.scheduler.basla()
        self.protocol("WM_DELETE_WINDOW", self._kapat)

    # ----- Yerleşim -----
    def _merkezle(self) -> None:
        """Pencereyi ekranın ortasına alır."""
        self.update_idletasks()
        gen, yuk = 1100, 700
        ekran_gen = self.winfo_screenwidth()
        ekran_yuk = self.winfo_screenheight()
        x = max(0, (ekran_gen - gen) // 2)
        y = max(0, (ekran_yuk - yuk) // 2)
        self.geometry(f"{gen}x{yuk}+{x}+{y}")

    def _stilleri_ayarla(self) -> None:
        """ttk teması ve renkler."""
        stil = ttk.Style()
        # macOS'ta clam tema mevcut ve daha tutarlı render eder
        try:
            stil.theme_use("clam")
        except tk.TclError:
            pass
        stil.configure("TFrame", background=RENK_ARKAPLAN)
        stil.configure("TLabel", background=RENK_ARKAPLAN, foreground=RENK_KOYU)
        stil.configure("Header.TLabel", font=("Helvetica", 13, "bold"),
                       background=RENK_ARKAPLAN, foreground=RENK_KOYU)
        stil.configure("TButton", padding=6)
        stil.configure("Aksiyon.TButton", padding=8, foreground="white",
                       background=RENK_ANA)
        stil.map("Aksiyon.TButton",
                 background=[("active", RENK_KOYU)])

    def _arayuzu_olustur(self) -> None:
        """Üst şerit + notebook (4 sekme)."""
        kok = ttk.Frame(self)
        kok.pack(fill="both", expand=True, padx=10, pady=10)

        self._ust_seridi_olustur(kok)
        self._sekmeleri_olustur(kok)
        self._durum_cubugu_olustur(kok)

    def _ust_seridi_olustur(self, parent: tk.Widget) -> None:
        """Aktif konum etiketi + Konumumu Tespit Et + arama kutusu."""
        serit = ttk.Frame(parent, padding=(5, 5, 5, 10))
        serit.pack(fill="x")

        self.lbl_aktif_konum = ttk.Label(
            serit, text="Aktif konum: —", style="Header.TLabel"
        )
        self.lbl_aktif_konum.pack(side="left")

        # Sağa hizalı butonlar/arama
        sag = ttk.Frame(serit)
        sag.pack(side="right")

        self.btn_tespit = ttk.Button(
            sag, text="📍 Konumumu Tespit Et",
            style="Aksiyon.TButton",
            command=self.konumu_tespit_et,
            state=("normal" if self.konum_izni else "disabled"),
        )
        self.btn_tespit.pack(side="left", padx=(0, 10))

        # Favorilere ekle butonu — aktif konum yokken devre dışı
        self.btn_favori_ekle = ttk.Button(
            sag, text="★ Favorilere Ekle",
            command=self.aktif_konumu_favoriye_ekle,
            state="disabled",
        )
        self.btn_favori_ekle.pack(side="left", padx=(0, 15))

        self.search_form = SearchForm(sag, on_search=self.aramayi_calistir)
        self.search_form.pack(side="left")

    def _sekmeleri_olustur(self, parent: tk.Widget) -> None:
        """Notebook ve 4 sekme (Anlık, Tahmin, Favoriler, Ayarlar)."""
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill="both", expand=True)

        # Anlık (WeatherDisplayForm)
        self.weather_display = WeatherDisplayForm(self.notebook)
        self.notebook.add(self.weather_display, text="Anlık")

        # Tahmin (matplotlib grafikleri)
        self.chart_form = ChartForm(self.notebook, self.db, self.weather_api)
        self.notebook.add(self.chart_form, text="Tahmin")

        # Favoriler
        self.favorites_form = FavoritesForm(
            self.notebook, self.db, self.weather_api,
            kullanici_id=self.kullanici_id,
            on_select=self._favoriden_yukle,
        )
        self.notebook.add(self.favorites_form, text="Favoriler")

        # Ayarlar (bildirim tercihleri)
        self.settings_form = SettingsForm(self.notebook, self.db,
                                          kullanici_id=self.kullanici_id)
        self.notebook.add(self.settings_form, text="Ayarlar")

    def _durum_cubugu_olustur(self, parent: tk.Widget) -> None:
        """Alt durum çubuğu (kısa mesajlar)."""
        self.lbl_durum = ttk.Label(parent, text="Hazır.", anchor="w")
        self.lbl_durum.pack(fill="x", pady=(8, 0))

    # ----- Etkileşim -----
    def _btn_tespit_durumu(self, etkin: bool) -> None:
        """Tespit butonunu KVKK iznine göre yönetir — izin yoksa hep disabled."""
        if not self.konum_izni:
            self.btn_tespit.config(state="disabled")
            return
        self.btn_tespit.config(state="normal" if etkin else "disabled")

    def konumu_tespit_et(self) -> None:
        """IP geolocation tetikler. Sonucu UI thread'e geri yansıtır."""
        if not self.konum_izni:
            self._durum_yaz("KVKK onayı verilmediği için IP konum tespiti devre dışı. "
                            "Arama kutusundan şehir adıyla arayabilirsiniz.")
            return
        self._durum_yaz("Konum tespit ediliyor…")
        self._btn_tespit_durumu(False)

        def gorev():
            try:
                loc = self.location_service.otomatik_konum_tespit()
            except Exception as e:  # noqa: BLE001 — UI thread için kapsayıcı yakala
                logger.error("Konum tespit edilirken hata: %s", e)
                self.after(0, lambda: self._hata("Konum tespit edilemedi.", str(e)))
                return
            if loc is None:
                self.after(0, lambda: self._hata(
                    "Konum tespit edilemedi.",
                    "İnternet bağlantınızı kontrol edip tekrar deneyin."))
                return
            # DB'ye yaz, sonra hava durumunu çek
            try:
                konum_id = self.db.konum_ekle(loc)
                loc.id = konum_id
            except Exception as e:
                logger.error("Konum DB'ye eklenirken hata: %s", e)
                self.after(0, lambda: self._hata("DB hatası", str(e)))
                return
            self.after(0, lambda: self._hava_durumunu_yukle(loc))

        threading.Thread(target=gorev, daemon=True).start()

    def aramayi_calistir(self, sehir: str, ilce: Optional[str] = None) -> None:
        """Manuel arama — LocationService üzerinden çözüp hava durumunu yükler."""
        self._durum_yaz(f"'{sehir}' aranıyor…")

        def gorev():
            try:
                loc = self.location_service.manuel_konum_ara(sehir, ilce)
            except Exception as e:  # noqa: BLE001
                logger.error("Konum aranırken hata: %s", e)
                self.after(0, lambda: self._hata("Arama hatası", str(e)))
                return
            if loc is None:
                self.after(0, lambda: self._hata(
                    "Konum bulunamadı.",
                    f"'{sehir}' için kayıt ya da bilinen koordinat yok."))
                return
            self.after(0, lambda: self._hava_durumunu_yukle(loc))

        threading.Thread(target=gorev, daemon=True).start()

    def aktif_konumu_guncelle(self, location: Location) -> None:
        """Üst şerit ve dahili durum: aktif konumu set eder."""
        self.aktif_konum = location
        etiket = f"Aktif konum: {location.sehir}"
        if location.ilce:
            etiket += f" / {location.ilce}"
        self.lbl_aktif_konum.config(text=etiket)
        # Aktif konum varsa favoriye ekleme butonu aktif olmalı
        if location.id is not None:
            self.btn_favori_ekle.config(state="normal")
        # ChartForm'a aktif konumu bildir (grafik butonları artık o konuma çalışacak)
        try:
            self.chart_form.konumu_ayarla(location)
        except AttributeError:
            # chart_form henüz oluşmamış olabilir (init sırası garantili olsa da güvenlik)
            pass

    def aktif_konumu_favoriye_ekle(self) -> None:
        """Aktif konumu (varsa) favoriye ekler, Favoriler sekmesini yeniler."""
        if self.aktif_konum is None or self.aktif_konum.id is None:
            messagebox.showinfo("Bilgi", "Önce bir konum seçin veya arayın.")
            return
        # DB unique constraint zaten duplicate'i engelliyor; favori_ekle idempotent.
        eklendi = self.favorites_form.favori_ekle(self.aktif_konum.id)
        if eklendi:
            self._durum_yaz(f"'{self.aktif_konum.sehir}' favorilere eklendi.")

    def _favoriden_yukle(self, location: Location) -> None:
        """Favoriler sekmesinde tıklanan konumu Anlık'a yükler."""
        self._hava_durumunu_yukle(location)

    # ----- İç yardımcılar -----
    def _hava_durumunu_yukle(self, loc: Location) -> None:
        """Verilen konum için Open-Meteo'dan anlık veri çeker, ekrana basar, DB'ye yazar.

        UI thread'inden çağrılır — API isteği için yine ayrı bir thread açılır.
        """
        self._btn_tespit_durumu(False)
        self._durum_yaz(f"{loc.sehir} için hava durumu alınıyor…")
        self.aktif_konumu_guncelle(loc)

        def gorev():
            try:
                w = self.weather_api.anlik_veri_cek(loc)
            except Exception as e:  # noqa: BLE001
                logger.error("Hava durumu çekilirken hata: %s", e)
                self.after(0, lambda: self._hata("API hatası", str(e)))
                self.after(0, lambda: self._btn_tespit_durumu(True))
                return
            # Çekilen veriye konum_id ata ve DB'ye yaz
            w.konum_id = loc.id or 0
            try:
                if w.konum_id:
                    self.db.hava_durumu_ekle(w)
            except Exception as e:
                logger.error("Hava durumu DB'ye yazılamadı: %s", e)
                # Yazılamasa da kullanıcıya veriyi göster
            self.after(0, lambda: self._veriyi_yansit(loc, w))

        threading.Thread(target=gorev, daemon=True).start()

    def _veriyi_yansit(self, loc: Location, weather: Weather) -> None:
        """UI thread: WeatherDisplayForm'a veriyi basar."""
        self.weather_display.veriyi_goster(loc, weather)
        self.notebook.select(0)  # "Anlık" sekmesini öne al
        self._durum_yaz(f"{loc.sehir} için veri güncellendi.")
        self._btn_tespit_durumu(True)
        # Favori listesi açıksa son sıcaklığı yansıt
        try:
            self.favorites_form.listeyi_yenile()
        except Exception:
            pass
        # Risk değerlendirmesi — yeni veri her geldiğinde
        self._risk_kontrol_et(loc, weather, kullanici_etkilesimi=True)

    def _durum_yaz(self, mesaj: str) -> None:
        self.lbl_durum.config(text=mesaj)

    def _hata(self, baslik: str, mesaj: str) -> None:
        self._durum_yaz(baslik)
        self._btn_tespit_durumu(True)
        messagebox.showerror(baslik, mesaj)

    # ----- Risk + arka plan -----
    def periyodik_kontrol(self) -> None:
        """Scheduler thread'inde çalışır: aktif konum + favoriler için veri çek, risk değerlendir."""
        logger.info("Periyodik kontrol başlıyor…")
        konumlar: list[Location] = []
        if self.aktif_konum is not None:
            konumlar.append(self.aktif_konum)
        try:
            favoriler = self.db.favorileri_getir(1)
            for fav in favoriler:
                loc = self.db.konum_getir(fav.konum_id)
                if loc is None:
                    continue
                # Aktif konumla aynıysa eklemeden geç
                if any(k.id == loc.id for k in konumlar):
                    continue
                konumlar.append(loc)
        except Exception as e:
            logger.error("Favoriler okunamadı (periyodik): %s", e)

        for loc in konumlar:
            try:
                w = self.weather_api.anlik_veri_cek(loc)
                if loc.id:
                    w.konum_id = loc.id
                    try:
                        self.db.hava_durumu_ekle(w)
                    except Exception as e:
                        logger.error("Periyodik DB yazımı başarısız: %s", e)
                # Risk değerlendirmesini UI thread'inde yap (pop-up için)
                self.after(0, lambda l=loc, ww=w: self._risk_kontrol_et(l, ww,
                                                                         kullanici_etkilesimi=False))
            except Exception as e:
                logger.error("Periyodik veri çekimi (%s) başarısız: %s", loc.sehir, e)
        logger.info("Periyodik kontrol tamamlandı (%d konum).", len(konumlar))

    def _risk_kontrol_et(self, loc: Location, weather: Weather,
                         kullanici_etkilesimi: bool) -> None:
        """Verilen ölçüm için RiskAnalyzer çalıştırır; risk varsa DB+bildirim+pop-up."""
        try:
            risk = self.risk_analyzer.degerlendir(weather, loc)
        except Exception as e:
            logger.error("Risk analizi hatası: %s", e)
            return
        if risk is None:
            return

        # Aynı (konum, risk_tipi) için 1 saat içinde tekrar bildirme
        import time
        anahtar = (loc.id or 0, risk.risk_tipi)
        son = self._son_risk_zamanlari.get(anahtar, 0.0)
        simdi = time.time()
        if simdi - son < 3600 and not kullanici_etkilesimi:
            logger.info("Risk (%s/%s) son 1 saatte zaten bildirildi; tekrar atlanıyor.",
                        loc.sehir, risk.risk_tipi)
            return
        self._son_risk_zamanlari[anahtar] = simdi

        # DB'ye risk kaydı
        try:
            if loc.id is not None:
                risk.konum_id = loc.id
                self.db.riskli_bolge_ekle(risk)
        except Exception as e:
            logger.error("RiskZone DB'ye yazılamadı: %s", e)

        # Kullanıcı + bildirim ayarı
        try:
            user = self.db.kullanici_getir(self.kullanici_id)
            ayar = self.db.bildirim_ayari_getir(self.kullanici_id)
        except Exception as e:
            logger.error("Kullanıcı/bildirim ayarı okunamadı: %s", e)
            user, ayar = None, None

        if user is not None:
            sms_aktif = ayar.sms_aktif if ayar else True
            email_aktif = ayar.email_aktif if ayar else True
            try:
                self.notification_service.risk_bildirimi_gonder(
                    user, risk, loc, sms_aktif=sms_aktif, email_aktif=email_aktif
                )
            except Exception as e:
                logger.error("Risk bildirimi gönderilemedi: %s", e)

        # Pop-up — UI thread'de
        try:
            RiskAlertForm(self, risk, loc)
        except Exception as e:
            logger.error("RiskAlertForm açılamadı: %s", e)

    def _kapat(self) -> None:
        """Pencere kapatma kancası — scheduler'ı temiz durdur, sonra destroy."""
        logger.info("Kapanış: scheduler durduruluyor…")
        try:
            self.scheduler.durdur()
        except Exception as e:
            logger.error("Scheduler durdurma hatası: %s", e)
        self.destroy()
