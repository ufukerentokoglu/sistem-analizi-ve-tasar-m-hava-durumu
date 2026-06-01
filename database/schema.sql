-- Hava Durumu Yazılımı — Veritabanı Şeması
-- Idempotent: tekrar tekrar çalıştırılabilir, mevcut yapıyı bozmaz.

CREATE DATABASE IF NOT EXISTS havadurumu
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE havadurumu;

-- 1) Kullanicilar (çok kullanıcılı — ad UNIQUE, ad+şifre ile giriş)
CREATE TABLE IF NOT EXISTS Kullanicilar (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ad VARCHAR(100) NOT NULL UNIQUE,
    sifre_hash VARCHAR(255) NOT NULL,
    email VARCHAR(150),
    telefon VARCHAR(20),
    kvkk_onay BOOLEAN NOT NULL DEFAULT FALSE,
    kayit_tarihi TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2) Konumlar
CREATE TABLE IF NOT EXISTS Konumlar (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sehir VARCHAR(100) NOT NULL,
    ilce VARCHAR(100),
    ulke VARCHAR(100) NOT NULL DEFAULT 'Türkiye',
    latitude DECIMAL(10, 7) NOT NULL,
    longitude DECIMAL(10, 7) NOT NULL,
    olusturma_tarihi TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uniq_konum (sehir, ilce, ulke)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3) Hava Durumu Ölçümleri
CREATE TABLE IF NOT EXISTS HavaDurumu (
    id INT AUTO_INCREMENT PRIMARY KEY,
    konum_id INT NOT NULL,
    olcum_tarihi DATETIME NOT NULL,
    sicaklik DECIMAL(5,2),
    hissedilen_sicaklik DECIMAL(5,2),
    nem INT,
    ruzgar_hizi DECIMAL(5,2),
    ruzgar_yonu INT,
    basinc DECIMAL(7,2),
    yagis_mm DECIMAL(5,2),
    durum_kodu INT,
    durum_aciklamasi VARCHAR(100),
    kaynak_api VARCHAR(50) NOT NULL DEFAULT 'Open-Meteo',
    olusturma_tarihi TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (konum_id) REFERENCES Konumlar(id) ON DELETE CASCADE,
    INDEX idx_konum_tarih (konum_id, olcum_tarihi DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4) Favoriler
CREATE TABLE IF NOT EXISTS Favoriler (
    id INT AUTO_INCREMENT PRIMARY KEY,
    kullanici_id INT NOT NULL,
    konum_id INT NOT NULL,
    sira INT NOT NULL DEFAULT 0,
    eklenme_tarihi TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (kullanici_id) REFERENCES Kullanicilar(id) ON DELETE CASCADE,
    FOREIGN KEY (konum_id) REFERENCES Konumlar(id) ON DELETE CASCADE,
    UNIQUE KEY uniq_favori (kullanici_id, konum_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5) Bildirim Ayarları
CREATE TABLE IF NOT EXISTS BildirimAyarlari (
    id INT AUTO_INCREMENT PRIMARY KEY,
    kullanici_id INT NOT NULL UNIQUE,
    sms_aktif BOOLEAN NOT NULL DEFAULT TRUE,
    email_aktif BOOLEAN NOT NULL DEFAULT TRUE,
    risk_esigi ENUM('dusuk', 'orta', 'yuksek') NOT NULL DEFAULT 'orta',
    bildirim_tipi VARCHAR(50) NOT NULL DEFAULT 'tum',
    guncelleme_tarihi TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (kullanici_id) REFERENCES Kullanicilar(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6) Riskli Bölgeler
CREATE TABLE IF NOT EXISTS RiskliBolgeler (
    id INT AUTO_INCREMENT PRIMARY KEY,
    konum_id INT NOT NULL,
    risk_tipi VARCHAR(50) NOT NULL,
    siddet ENUM('dusuk', 'orta', 'yuksek') NOT NULL DEFAULT 'orta',
    baslangic DATETIME NOT NULL,
    bitis DATETIME,
    aciklama TEXT,
    olusturma_tarihi TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (konum_id) REFERENCES Konumlar(id) ON DELETE CASCADE,
    INDEX idx_aktif_riskler (konum_id, baslangic, bitis)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Çok kullanıcılı yapı: seed kaydı yok. Kullanıcılar kayıt formundan eklenir.
-- BildirimAyarlari, yeni kullanıcı kayıt olurken otomatik oluşturulur (db_manager.kullanici_kayit).
