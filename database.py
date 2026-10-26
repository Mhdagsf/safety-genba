import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'safety_genba.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tanggal TEXT NOT NULL,
            line TEXT NOT NULL,
            pos TEXT DEFAULT '',
            temuan TEXT NOT NULL,
            potensi TEXT DEFAULT '',
            perbaikan TEXT DEFAULT '',
            dudate TEXT DEFAULT '',
            fix_date TEXT DEFAULT '',
            pic TEXT DEFAULT '',
            judg TEXT DEFAULT 'X',
            foto_sebelum TEXT DEFAULT '',
            foto_sesudah TEXT DEFAULT '',
            foto_fix TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

    # Ensure foto_fix column exists for existing tables
    cursor.execute("PRAGMA table_info(findings)")
    existing_cols = [r[1] for r in cursor.fetchall()]
    if 'foto_fix' not in existing_cols:
        cursor.execute("ALTER TABLE findings ADD COLUMN foto_fix TEXT DEFAULT ''")
        conn.commit()

    # Check if empty, then seed with existing data from Excel
    cursor.execute('SELECT COUNT(*) FROM findings')
    count = cursor.fetchone()[0]
    if count == 0:
        seed_initial_data(cursor)
        conn.commit()
    conn.close()

def seed_initial_data(cursor):
    sample_records = [
        # TEMUAN Near miss FB 1
        ("2026-09-02", "FB 1", "", "Karet pelindung kaki mesin tidak ada", "Mesin bergeser & getaran", "Pemasangan karet pelindung", "2026-09-10", "Karet pelindung telah dipasang pada kaki mesin", "Mtc", "O", "", ""),
        ("2026-09-02", "FB 1", "", "Plat dudukan meja tambahan tidak sesajar", "Material tersangkut", "Penyesuaian posisi plat dudukan", "2026-09-10", "Plat dudukan meja telah disesuaikan dan sejajar", "Mtc", "O", "", ""),
        ("2026-09-02", "FB 1", "", "Rak part miring ke depan", "Part berjatuhan mengenai MP", "Perkuatan dan perataan rak part", "2026-09-10", "", "Mtc", "X", "", ""),
        ("2026-10-12", "FB 1", "Pos 10, Mesin 2, QC", "Tidak ada dudukannya", "Air tumpah & MP terpleset", "Baut copot", "2026-10-21", "Dudukan telah dipasang dan baut dikencangkan", "Rostika", "O", "", ""),
        
        # TEMUAN Near miss FB 4
        ("2026-10-01", "FB 4", "Pos 10", "Tas pribadi di area bawah mesin", "Konsleting listrik", "Penyimpanan tas pribadi berada di loker", "2026-10-01", "Tas pribadi telah dipindahkan dan disimpan rapi di loker", "Rostika", "O", "sample_row1_before.jpg", "sample_row1_after.jpg"),
        ("2026-10-01", "FB 4", "Pos 9", "Tempat minum terbalik, botol dilantai", "Air tumpah & MP terpleset", "Baut pada besi tempat minum di kencangkan", "2026-10-01", "", "Rostika", "X", "sample_row2_before.jpg", "sample_row2_after.jpg"),
        ("2026-10-01", "FB 4", "Pos 6", "Kabel mengelupas", "Konsleting listrik", "Pemasangan solatip pada bagian kabel yang terkelupas", "2026-10-05", "", "Mtc", "X", "sample_row3_before.jpg", ""),
        ("2026-10-01", "FB 4", "", "Kabel mesin berantakan", "Konsleting listrik", "Perbaikan dengan pemasangan kabel tis oleh MTc", "2026-10-05", "", "MTc", "X", "", ""),
        ("2026-10-01", "FB 4", "Pos 8", "Baud berada di atas meja", "MP tergores", "Baut pada meja dicopot dan pinggir meja yang tajam", "2026-10-01", "Baut pada meja telah dicopot dan pinggiran tajam dirapikan", "Rostika", "O", "", ""),
        ("2026-10-01", "FB 4", "Pos 8", "Kawat tajam di bawah mesin", "MP tergores", "kawat yang berada dimesin di copot", "2026-10-01", "Kawat tajam pada mesin telah dicopot", "Rostika", "O", "", ""),
        ("2026-10-01", "FB 4", "Pos 8", "Kabel tidak terpakai", "Konsleting listrik", "Perbaikan dengan pemasangan kabel tis oleh MTc", "2026-10-01", "Kabel tidak terpakai telah dirapikan menggunakan kabel tis", "Rostika", "O", "", ""),
        ("2026-10-01", "FB 4", "Pos 8", "Gunting tidak diikat dengan tali, barang pribadi berada di area mesin", "Gunting terjatuh ,mengenai kaki MP", "Pemasangan tali gunting dan perapihan barang pribadi", "2026-10-01", "Tali pengikat gunting telah dipasang dan barang pribadi dirapikan", "Rostika", "O", "", ""),
        ("2026-10-02", "FB 4", "", "Penyimpanan tombol SPT dekat pengisian spul", "MP tergores", "Perbaikan penempatan tombol SPT disamping mesin", "2026-10-10", "", "MTc", "X", "", ""),
        ("2026-10-02", "FB 4", "Pos 9", "Sambungan mesinn berdekatan", "Konsleting listrik", "Perbaikan oleh tim mtc", "2026-10-10", "", "MTc", "X", "", ""),
        ("2026-10-02", "FB 4", "Pos 7", "Baud tajam", "MP tergores", "Baut Di copot", "2026-10-01", "Baut tajam telah dicopot", "Rostika", "O", "", ""),
        ("2026-10-02", "FB 4", "Pos 3", "Tombol stick balik menggantung", "Tangan MP tergores", "Perbaikan oleh tim mtc", "2026-10-10", "", "MTc", "X", "", ""),
        ("2026-10-02", "FB 4", "", "Penutup roda mesin tidak ada", "Mesin terjatuh ,mengenai MP", "Request kakeibo penutup roda mesin", "2026-10-15", "", "MTc", "X", "", ""),
        ("2026-10-02", "FB 4", "", "Cover colokan mesin terbuka", "MP tersetrum", "perbaikan cover colokan di tutup", "2026-10-01", "Cover colokan telah ditutup rapat dan aman", "Rostika", "O", "", ""),
        ("2026-10-02", "FB 4", "QC", "Kabel melintir", "Konsleting listrik", "kabel dirapihkan dengan kabel tis", "2026-10-01", "Kabel telah dirapikan menggunakan kabel tis", "Rostika", "O", "", ""),
    ]
    cursor.executemany('''
        INSERT INTO findings (tanggal, line, pos, temuan, potensi, perbaikan, dudate, fix_date, pic, judg, foto_sebelum, foto_sesudah)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', sample_records)

def get_available_periods():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT substr(tanggal, 1, 7) as ym FROM findings WHERE tanggal != '' ORDER BY ym DESC")
    months = [row['ym'] for row in cursor.fetchall() if row['ym'] and len(row['ym']) == 7]
    
    cursor.execute("SELECT DISTINCT substr(tanggal, 1, 4) as y FROM findings WHERE tanggal != '' ORDER BY y DESC")
    years = [row['y'] for row in cursor.fetchall() if row['y'] and len(row['y']) == 4]
    
    conn.close()
    return {'months': months, 'years': years}

def build_filter_clauses(line_filter=None, status_filter=None, search_query=None, period_type='month', period_val=None, pic_filter=None):
    query = " WHERE 1=1"
    params = []

    if line_filter and line_filter != 'ALL':
        query += " AND line = ?"
        params.append(line_filter)
    
    if status_filter and status_filter != 'ALL':
        if status_filter in ('O', 'OK'):
            query += " AND (judg = 'O' OR judg = 'OK')"
        elif status_filter in ('X', 'ON PROGRESS'):
            query += " AND (judg = 'X' OR judg = 'ON PROGRESS')"
        else:
            query += " AND judg = ?"
            params.append(status_filter)

    if pic_filter and pic_filter != 'ALL':
        query += " AND pic = ?"
        params.append(pic_filter)
        
    if search_query:
        query += " AND (temuan LIKE ? OR potensi LIKE ? OR pic LIKE ? OR pos LIKE ?)"
        term = f"%{search_query}%"
        params.extend([term, term, term, term])

    # Period filters
    if period_type == 'month':
        val = period_val or datetime.now().strftime('%Y-%m')
        query += " AND tanggal LIKE ?"
        params.append(f"{val}%")
    elif period_type == 'year':
        val = period_val or datetime.now().strftime('%Y')
        query += " AND tanggal LIKE ?"
        params.append(f"{val}%")
    elif period_type == 'week':
        # If specific date given or default to current week
        ref_date = datetime.now()
        if period_val and len(period_val) == 10:
            try:
                ref_date = datetime.strptime(period_val, '%Y-%m-%d')
            except:
                pass
        start_week = (ref_date - timedelta(days=ref_date.weekday())).strftime('%Y-%m-%d')
        end_week = (ref_date + timedelta(days=6 - ref_date.weekday())).strftime('%Y-%m-%d')
        query += " AND tanggal >= ? AND tanggal <= ?"
        params.extend([start_week, end_week])
    # if 'all', no date filter

    return query, params

def get_all_findings(line_filter=None, status_filter=None, search_query=None, period_type='month', period_val=None, pic_filter=None):
    conn = get_db()
    cursor = conn.cursor()
    base_query = "SELECT * FROM findings"
    where_clause, params = build_filter_clauses(line_filter, status_filter, search_query, period_type, period_val, pic_filter)
    full_query = base_query + where_clause + " ORDER BY id DESC"
    
    cursor.execute(full_query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_finding_by_id(finding_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM findings WHERE id = ?", (finding_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def insert_finding(data):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO findings (tanggal, line, pos, temuan, potensi, perbaikan, dudate, fix_date, pic, judg, foto_sebelum, foto_sesudah, foto_fix)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('tanggal'),
        data.get('line'),
        data.get('pos', ''),
        data.get('temuan'),
        data.get('potensi', ''),
        data.get('perbaikan', ''),
        data.get('dudate', ''),
        data.get('fix_date', ''),
        data.get('pic', ''),
        data.get('judg', 'X'),
        data.get('foto_sebelum', ''),
        data.get('foto_sesudah', ''),
        data.get('foto_fix', '')
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def update_finding(finding_id, data):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE findings SET
            tanggal = ?,
            line = ?,
            pos = ?,
            temuan = ?,
            potensi = ?,
            perbaikan = ?,
            dudate = ?,
            fix_date = ?,
            pic = ?,
            judg = ?,
            foto_sebelum = CASE WHEN ? != '' THEN ? ELSE foto_sebelum END,
            foto_sesudah = CASE WHEN ? != '' THEN ? ELSE foto_sesudah END,
            foto_fix = CASE WHEN ? != '' THEN ? ELSE foto_fix END
        WHERE id = ?
    ''', (
        data.get('tanggal'),
        data.get('line'),
        data.get('pos', ''),
        data.get('temuan'),
        data.get('potensi', ''),
        data.get('perbaikan', ''),
        data.get('dudate', ''),
        data.get('fix_date', ''),
        data.get('pic', ''),
        data.get('judg'),
        data.get('foto_sebelum', ''),
        data.get('foto_sebelum', ''),
        data.get('foto_sesudah', ''),
        data.get('foto_sesudah', ''),
        data.get('foto_fix', ''),
        data.get('foto_fix', ''),
        finding_id
    ))
    conn.commit()
    conn.close()

def delete_finding(finding_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM findings WHERE id = ?", (finding_id,))
    conn.commit()
    conn.close()

def get_statistics(line_filter=None, status_filter=None, search_query=None, period_type='month', period_val=None, pic_filter=None):
    conn = get_db()
    cursor = conn.cursor()
    
    where_clause, params = build_filter_clauses(line_filter, status_filter, search_query, period_type, period_val, pic_filter)
    
    cursor.execute("SELECT COUNT(*) FROM findings" + where_clause, params)
    total = cursor.fetchone()[0]
    
    where_ok = where_clause + " AND (judg = 'O' OR judg = 'OK')"
    cursor.execute("SELECT COUNT(*) FROM findings" + where_ok, params)
    ok_count = cursor.fetchone()[0]
    
    where_prog = where_clause + " AND (judg = 'X' OR judg = 'ON PROGRESS' OR (judg != 'O' AND judg != 'OK'))"
    cursor.execute("SELECT COUNT(*) FROM findings" + where_prog, params)
    on_progress_count = cursor.fetchone()[0]
    
    conn.close()
    return {
        'total': total,
        'ok': ok_count,
        'on_progress': on_progress_count
    }
