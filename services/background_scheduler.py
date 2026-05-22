"""Arka plan periyodik görev çalıştırıcı — schedule + threading."""
import logging
import threading
import time
from typing import Callable, Optional

import schedule

logger = logging.getLogger(__name__)


class BackgroundScheduler:
    """schedule + threading ile periyodik görev çalıştırıcı."""

    def __init__(self, interval_minutes: int = 5):
        self.interval_minutes = max(1, int(interval_minutes))
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.gorevler: list[Callable] = []
        # schedule kütüphanesi global state taşır; her örnek kendi scheduler'ına sahip olmalı
        self._scheduler = schedule.Scheduler()

    def gorev_ekle(self, fn: Callable) -> None:
        """Periyodik çalıştırılacak görev ekle."""
        self.gorevler.append(fn)
        # Sarmalayıcı: tek bir görevin hatası diğerlerini durdurmasın
        def guvenli_calistir():
            try:
                fn()
            except Exception as e:  # noqa: BLE001
                logger.error("Periyodik görev hatası (%s): %s", fn.__name__, e)
        self._scheduler.every(self.interval_minutes).minutes.do(guvenli_calistir)

    def basla(self) -> None:
        """Arka plan thread'ini başlatır. İlk tetik interval kadar sonra olur."""
        if self.thread is not None and self.thread.is_alive():
            logger.warning("Scheduler zaten çalışıyor.")
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._calistir, daemon=True)
        self.thread.start()
        logger.info("Arka plan scheduler başlatıldı (her %d dk).", self.interval_minutes)

    def durdur(self) -> None:
        """Thread'i bir sonraki tick'te durdur; biraz bekle."""
        self.stop_event.set()
        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=3)
        # schedule kuyruğunu temizle ki yeniden başlatma idempotent olsun
        self._scheduler.clear()
        self.thread = None
        logger.info("Arka plan scheduler durduruldu.")

    def _calistir(self) -> None:
        """Thread döngüsü — stop_event set edilene kadar her saniye kontrol."""
        while not self.stop_event.is_set():
            try:
                self._scheduler.run_pending()
            except Exception as e:  # noqa: BLE001
                logger.error("Scheduler tick hatası: %s", e)
            # 1 saniye uyu, ama stop sinyalinde hemen çık
            self.stop_event.wait(timeout=1.0)
