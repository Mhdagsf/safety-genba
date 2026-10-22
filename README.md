# 🛡️ PT. FUJISEAT INDONESIA - Sistem Monitoring Temuan Safety & Genba D26A

Aplikasi berbasis web untuk pencatatan temuan safety (*unsafe conditions / near miss*), dokumentasi foto sebelum dan sesudah perbaikan (*Before & After*), integrasi ekspor/impor Excel, dan lembar verifikasi Genba.

---

## 🚀 Cara Menjalankan Aplikasi

### Opsi 1: Satu Klik (Windows)
Cukup klik ganda file **`run.bat`** di dalam folder ini. Browser akan otomatis terbuka ke alamat `http://127.0.0.1:5050`.

### Opsi 2: Lewat Terminal / Command Prompt
```bash
cd "C:\Project\safety_genba_system"
python app.py
```
Lalu buka browser di: **`http://127.0.0.1:5050`**

---

## ✨ Fitur-Fitur Utama

1. **📸 Foto Temuan Langsung (Kamera HP / Upload File)**:
   - Tombol **"Buka Kamera HP"** langsung memicu kamera belakang smartphone saat melakukan inspeksi Genba di lantai pabrik.
   - Pilihan ambil dari galeri / folder laptop untuk pengunggahan di PC.
   - Preview visual instan sebelum disimpan.

2. **📝 Input Cepat Temuan & Potensi Bahaya**:
   - Pemilihan Line: **FB 1, FB 2, FB 3, FB 4** & **FC 1, FC 2, FC 3, FC 4**.
   - Input Pos / Stasiun Kerja / Nomor Mesin (contoh: *Pos 10, Pos 9, QC*).
   - *Quick Chips* untuk Potensi Bahaya: sekali klik untuk memilih (*Konsleting listrik, MP tergores, MP terpleset, Mesin terjatuh, MP tersetrum*).
   - Target tanggal selesai (*Due Date*), PIC (*Penanggung Jawab*), dan status awal (*ON PROGRESS*).

3. **🔄 Tindak Lanjut & Foto Sesudah Perbaikan (*After*)**:
   - Update temuan saat perbaikan selesai.
   - Unggah foto bukti kondisi setelah diperbaiki (*After*).
   - Perubahan status otomatis menjadi **OK (SELESAI)** dan pencatatan tanggal realisasi (*Fix Date*).

4. **📊 Dashboard & Monitoring Real-time**:
   - Ringkasan indikator: **Total Temuan**, **On Progress**, **OK (Selesai)**, dan persentase penyelesaian.
   - Filter interaktif berdasarkan **Line** dan **Status**, serta kolom pencarian kata kunci.
   - Pilihan tampilan: **Tampilan Kartu Visual (Card View)** dengan foto Before-After atau **Tampilan Tabel Spreadsheet (Table View)**.

5. **📑 Export ke Format Excel Asli (PT. FUJISEAT INDONESIA)**:
   - Menghasilkan file Excel `.xlsx` dengan 2 Sheet:
     - **Sheet 1 (`Rekap Temuan Safety`)**: Tabel lengkap dengan status dan indikator foto.
     - **Sheet 2 (`FORMAT GENBA D26A`)**: Format kolom bersanding (FB 1-4 & FC 1-4) persis sesuai template laporan pabrik.

6. **📥 Import dari Excel / CSV**:
   - Fitur unggah file Excel untuk memasukkan data temuan lama secara otomatis ke dalam sistem database.

7. **🖨️ Lembar Verifikasi & Cetak PDF**:
   - Halaman detail temuan siap cetak format A4 lengkap dengan kolom verifikasi tanda tangan: **Auditor Genba**, **PIC Perbaikan**, dan **Safety Section Head**.

---

## 📁 Struktur Folder Proyek

```text
safety_genba_system/
│
├── app.py                 # Server Flask dan routing aplikasi
├── database.py            # SQLite database helper & schema
├── excel_handler.py       # Modul ekspor dan impor Excel (openpyxl)
├── test_app.py            # Script pengujian otomatis sistem
├── run.bat                # Shortcut peluncuran aplikasi satu klik
├── safety_genba.db        # Database lokal SQLite (berisi 18 data awal dari Excel)
│
├── uploads/               # Direktori penyimpanan foto Before & After
│
└── templates/             # Template antarmuka web (Tailwind CSS)
    ├── base.html          # Layout utama dan navigasi responsif
    ├── index.html         # Dashboard temuan, statistik, dan filter
    ├── input.html         # Form input temuan + kamera HP
    ├── edit.html          # Form tindak lanjut & upload foto After
    └── detail.html        # Lembar verifikasi cetak Genba
```
