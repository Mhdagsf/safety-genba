-- ============================================
-- SAFETY GENBA - Database Schema (MySQL)
-- PT. FUJISEAT INDONESIA - Sistem Monitoring Temuan Safety & Genba D26A
-- Version: 1.0
-- ============================================
--
-- Deskripsi:
-- File SQL ini merupakan hasil konversi dari database safety_genba
-- (SQLite / database.py) ke format MySQL / MariaDB (XAMPP).
-- Mencakup struktur tabel `findings` beserta 19 data temuan awal (seed data).
-- ============================================

-- Hapus database lama jika diperlukan (opsional, hati-hati di production!)
-- DROP DATABASE IF EXISTS safety_genba;

-- Buat database
CREATE DATABASE IF NOT EXISTS safety_genba
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE safety_genba;

-- ============================================
-- TABLE 1: findings
-- Menyimpan data temuan safety (unsafe conditions / near miss),
-- tindak lanjut perbaikan, penilaian (judgement), dan dokumentasi foto
-- ============================================
DROP TABLE IF EXISTS findings;

CREATE TABLE findings (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tanggal VARCHAR(20) NOT NULL COMMENT 'Tanggal temuan (Format: YYYY-MM-DD)',
    line VARCHAR(20) NOT NULL COMMENT 'Area Line produksi: FB 1-4, FC 1-4',
    pos VARCHAR(100) NOT NULL DEFAULT '' COMMENT 'Pos / Stasiun Kerja / Nomor Mesin / QC',
    temuan TEXT NOT NULL COMMENT 'Deskripsi temuan unsafe condition / near miss',
    potensi TEXT NULL COMMENT 'Potensi bahaya yang ditimbulkan',
    perbaikan TEXT NULL COMMENT 'Rencana / tindakan perbaikan',
    dudate VARCHAR(20) NOT NULL DEFAULT '' COMMENT 'Target tanggal selesai (Due Date)',
    fix_date TEXT NULL COMMENT 'Deskripsi realisasi / keterangan selesai perbaikan',
    pic VARCHAR(100) NOT NULL DEFAULT '' COMMENT 'Penanggung jawab (PIC)',
    judg VARCHAR(20) NOT NULL DEFAULT 'X' COMMENT 'Status Judgement: O = OK (Selesai), X = On Progress',
    foto_sebelum VARCHAR(255) NOT NULL DEFAULT '' COMMENT 'Nama file foto kondisi awal (Before)',
    foto_sesudah VARCHAR(255) NOT NULL DEFAULT '' COMMENT 'Nama file foto hasil perbaikan (After)',
    foto_fix VARCHAR(255) NOT NULL DEFAULT '' COMMENT 'Nama file foto bukti verifikasi (Fix)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Waktu pencatatan data',

    -- Indexes untuk optimasi filter & pencarian dashboard
    INDEX idx_tanggal (tanggal),
    INDEX idx_line (line),
    INDEX idx_pic (pic),
    INDEX idx_judg (judg),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Data temuan safety & verifikasi Genba D26A';

-- ============================================
-- SEED DATA: findings
-- Data awal temuan Near Miss (Line FB 1 & FB 4)
-- ============================================

-- --------------------------------------------
-- TEMUAN Near Miss Line FB 1
-- --------------------------------------------
INSERT INTO findings (tanggal, line, pos, temuan, potensi, perbaikan, dudate, fix_date, pic, judg, foto_sebelum, foto_sesudah, foto_fix) VALUES
('2026-09-02', 'FB 1', '', 'Karet pelindung kaki mesin tidak ada', 'Mesin bergeser & getaran', 'Pemasangan karet pelindung', '2026-09-10', 'Karet pelindung telah dipasang pada kaki mesin', 'Mtc', 'O', '', '', ''),
('2026-09-02', 'FB 1', '', 'Plat dudukan meja tambahan tidak sesajar', 'Material tersangkut', 'Penyesuaian posisi plat dudukan', '2026-09-10', 'Plat dudukan meja telah disesuaikan dan sejajar', 'Mtc', 'O', '', '', ''),
('2026-09-02', 'FB 1', '', 'Rak part miring ke depan', 'Part berjatuhan mengenai MP', 'Perkuatan dan perataan rak part', '2026-09-10', '', 'Mtc', 'X', '', '', ''),
('2026-10-12', 'FB 1', 'Pos 10, Mesin 2, QC', 'Tidak ada dudukannya', 'Air tumpah & MP terpleset', 'Baut copot', '2026-10-21', 'Dudukan telah dipasang dan baut dikencangkan', 'Rostika', 'O', '', '', '');

-- --------------------------------------------
-- TEMUAN Near Miss Line FB 4
-- --------------------------------------------
INSERT INTO findings (tanggal, line, pos, temuan, potensi, perbaikan, dudate, fix_date, pic, judg, foto_sebelum, foto_sesudah, foto_fix) VALUES
('2026-10-01', 'FB 4', 'Pos 10', 'Tas pribadi di area bawah mesin', 'Konsleting listrik', 'Penyimpanan tas pribadi berada di loker', '2026-10-01', 'Tas pribadi telah dipindahkan dan disimpan rapi di loker', 'Rostika', 'O', 'sample_row1_before.jpg', 'sample_row1_after.jpg', ''),
('2026-10-01', 'FB 4', 'Pos 9', 'Tempat minum terbalik, botol dilantai', 'Air tumpah & MP terpleset', 'Baut pada besi tempat minum di kencangkan', '2026-10-01', '', 'Rostika', 'X', 'sample_row2_before.jpg', 'sample_row2_after.jpg', ''),
('2026-10-01', 'FB 4', 'Pos 6', 'Kabel mengelupas', 'Konsleting listrik', 'Pemasangan solatip pada bagian kabel yang terkelupas', '2026-10-05', '', 'Mtc', 'X', 'sample_row3_before.jpg', '', ''),
('2026-10-01', 'FB 4', '', 'Kabel mesin berantakan', 'Konsleting listrik', 'Perbaikan dengan pemasangan kabel tis oleh MTc', '2026-10-05', '', 'MTc', 'X', '', '', ''),
('2026-10-01', 'FB 4', 'Pos 8', 'Baud berada di atas meja', 'MP tergores', 'Baut pada meja dicopot dan pinggir meja yang tajam', '2026-10-01', 'Baut pada meja telah dicopot dan pinggiran tajam dirapikan', 'Rostika', 'O', '', '', ''),
('2026-10-01', 'FB 4', 'Pos 8', 'Kawat tajam di bawah mesin', 'MP tergores', 'kawat yang berada dimesin di copot', '2026-10-01', 'Kawat tajam pada mesin telah dicopot', 'Rostika', 'O', '', '', ''),
('2026-10-01', 'FB 4', 'Pos 8', 'Kabel tidak terpakai', 'Konsleting listrik', 'Perbaikan dengan pemasangan kabel tis oleh MTc', '2026-10-01', 'Kabel tidak terpakai telah dirapikan menggunakan kabel tis', 'Rostika', 'O', '', '', ''),
('2026-10-01', 'FB 4', 'Pos 8', 'Gunting tidak diikat dengan tali, barang pribadi berada di area mesin', 'Gunting terjatuh ,mengenai kaki MP', 'Pemasangan tali gunting dan perapihan barang pribadi', '2026-10-01', 'Tali pengikat gunting telah dipasang dan barang pribadi dirapikan', 'Rostika', 'O', '', '', ''),
('2026-10-02', 'FB 4', '', 'Penyimpanan tombol SPT dekat pengisian spul', 'MP tergores', 'Perbaikan penempatan tombol SPT disamping mesin', '2026-10-10', '', 'MTc', 'X', '', '', ''),
('2026-10-02', 'FB 4', 'Pos 9', 'Sambungan mesinn berdekatan', 'Konsleting listrik', 'Perbaikan oleh tim mtc', '2026-10-10', '', 'MTc', 'X', '', '', ''),
('2026-10-02', 'FB 4', 'Pos 7', 'Baud tajam', 'MP tergores', 'Baut Di copot', '2026-10-01', 'Baut tajam telah dicopot', 'Rostika', 'O', '', '', ''),
('2026-10-02', 'FB 4', 'Pos 3', 'Tombol stick balik menggantung', 'Tangan MP tergores', 'Perbaikan oleh tim mtc', '2026-10-10', '', 'MTc', 'X', '', '', ''),
('2026-10-02', 'FB 4', '', 'Penutup roda mesin tidak ada', 'Mesin terjatuh ,mengenai MP', 'Request kakeibo penutup roda mesin', '2026-10-15', '', 'MTc', 'X', '', '', ''),
('2026-10-02', 'FB 4', '', 'Cover colokan mesin terbuka', 'MP tersetrum', 'perbaikan cover colokan di tutup', '2026-10-01', 'Cover colokan telah ditutup rapat dan aman', 'Rostika', 'O', '', '', ''),
('2026-10-02', 'FB 4', 'QC', 'Kabel melintir', 'Konsleting listrik', 'kabel dirapihkan dengan kabel tis', '2026-10-01', 'Kabel telah dirapikan menggunakan kabel tis', 'Rostika', 'O', '', '', '');

-- ============================================
-- TABLE 2: uploaded_photos
-- Menyimpan backup biner foto temuan di database agar tidak pernah hilang/hitam
-- saat dijalankan di Cloud Hosting (Render / Railway / dsb.)
-- ============================================
CREATE TABLE IF NOT EXISTS uploaded_photos (
    filename VARCHAR(255) NOT NULL PRIMARY KEY,
    mime_type VARCHAR(64) NOT NULL DEFAULT 'image/jpeg',
    file_data LONGBLOB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
