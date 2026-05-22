"""Aşama 6 doğrulama testi — ChartForm 3 grafiği çiziyor, memory leak yok, %H:%M ekseni."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from database.db_manager import Database
from services.location_service import LocationService
from services.weather_api import WeatherAPI


def test_grafikler_ve_memory_leak():
    import tkinter as tk
    try:
        kontrol = tk.Tk()
        kontrol.withdraw()
        kontrol.destroy()
    except tk.TclError as e:
        print(f"⚠ Display yok, atlanıyor: {e}")
        return

    import matplotlib.pyplot as plt
    from ui.main_form import MainForm

    db = Database(config.DB_HOST, config.DB_PORT, config.DB_USER,
                  config.DB_PASSWORD, config.DB_NAME)
    db.connect()
    try:
        app = MainForm(db, WeatherAPI(), LocationService(db))

        durum = {"acik_figure_sayilari": []}

        def adim_ara():
            app.aramayi_calistir("Eskişehir")

        def adim_sicaklik():
            assert app.aktif_konum is not None, "Aktif konum yok"
            # ChartForm'un konumu ayarlanmış olmalı
            assert app.chart_form.aktif_konum is not None
            # Doğrudan synchronous çağır — UI thread'inde Open-Meteo'ya istek atıp çiziyor
            app.chart_form.sicaklik_grafigi(app.aktif_konum)
            durum["acik_figure_sayilari"].append(len(plt.get_fignums()))
            # X ekseni format kontrolü — bir tick etiketi içeriği %H:%M olmalı
            assert app.chart_form._figure is not None, "Figure oluşmadı"
            ax = app.chart_form._figure.axes[0]
            formatter = ax.xaxis.get_major_formatter()
            # DateFormatter.fmt = '%H:%M' (Türkçe spec)
            assert getattr(formatter, "fmt", "") == "%H:%M", (
                f"X ekseni formatı %H:%M değil: {getattr(formatter, 'fmt', None)!r}"
            )
            # Veri var mı?
            line = ax.lines[0]
            xs, ys = line.get_data()
            assert len(xs) > 0 and len(ys) > 0, "Sıcaklık grafiği boş"

        def adim_nem():
            app.chart_form.nem_grafigi(app.aktif_konum)
            durum["acik_figure_sayilari"].append(len(plt.get_fignums()))
            # Nem ekseni 0..100 olmalı
            ax = app.chart_form._figure.axes[0]
            y0, y1 = ax.get_ylim()
            assert y0 == 0 and y1 == 100, f"Nem ekseni 0..100 değil: {y0}..{y1}"

        def adim_ruzgar():
            app.chart_form.ruzgar_grafigi(app.aktif_konum)
            durum["acik_figure_sayilari"].append(len(plt.get_fignums()))

        def adim_tekrar_ciz():
            # Aynı butona 3 kez tekrar bas — figure sayısı birikmemeli
            app.chart_form.sicaklik_grafigi(app.aktif_konum)
            app.chart_form.nem_grafigi(app.aktif_konum)
            app.chart_form.ruzgar_grafigi(app.aktif_konum)
            durum["acik_figure_sayilari"].append(len(plt.get_fignums()))

        def adim_kapan():
            app.destroy()

        app.after(500, adim_ara)
        app.after(5500, adim_sicaklik)
        app.after(7500, adim_nem)
        app.after(9500, adim_ruzgar)
        app.after(11500, adim_tekrar_ciz)
        app.after(13500, adim_kapan)

        app.mainloop()

        # Doğrulamalar
        sayilar = durum["acik_figure_sayilari"]
        assert len(sayilar) == 4, f"Beklenen 4 ölçüm, {len(sayilar)} alındı"
        print(f"Her grafik sonrası açık figure sayıları: {sayilar}")
        # Her grafik sonrası 1 figure açık olmalı — birikme yoksa max 1
        for n in sayilar:
            assert n <= 1, f"Memory leak şüphesi: {n} açık figure"

        print("✓ Aşama 6 testleri başarılı")
    finally:
        db.disconnect()


def main():
    test_grafikler_ve_memory_leak()


if __name__ == "__main__":
    main()
