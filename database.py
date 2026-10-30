import os
import sqlite3
from datetime import datetime, timedelta

DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    # Render provides postgres://, SQLAlchemy/psycopg2 prefers postgresql://
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

IS_POSTGRES = bool(DATABASE_URL)

if IS_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'safety_genba.db')


class DBConnection:
    """Wrapper to provide consistent interface across SQLite and PostgreSQL"""
    def __init__(self):
        self.is_pg = IS_POSTGRES
        if self.is_pg:
            self.conn = psycopg2.connect(DATABASE_URL)
        else:
            self.conn = sqlite3.connect(DB_PATH)
            self.conn.row_factory = sqlite3.Row

    def cursor(self):
        if self.is_pg:
            return self.conn.cursor(cursor_factory=RealDictCursor)
        return self.conn.cursor()

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()


def get_db():
    return DBConnection()


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    if IS_POSTGRES:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS findings (
                id SERIAL PRIMARY KEY,
                tanggal VARCHAR(50) NOT NULL,
                line VARCHAR(50) NOT NULL,
                pos VARCHAR(100) DEFAULT '',
                temuan TEXT NOT NULL,
                potensi TEXT DEFAULT '',
                perbaikan TEXT DEFAULT '',
                dudate VARCHAR(50) DEFAULT '',
                fix_date TEXT DEFAULT '',
                pic VARCHAR(100) DEFAULT '',
                judg VARCHAR(20) DEFAULT 'X',
                foto_sebelum TEXT DEFAULT '',
                foto_sesudah TEXT DEFAULT '',
                foto_fix TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

        # Check if table is empty, then seed sample records
        cursor.execute("SELECT COUNT(*) as cnt FROM findings")
        res = cursor.fetchone()
        count = res['cnt'] if isinstance(res, dict) else res[0]
        if count == 0:
            seed_initial_data(cursor, is_pg=True)
            conn.commit()
    else:
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

        cursor.execute("PRAGMA table_info(findings)")
        existing_cols = [r[1] for r in cursor.fetchall()]
        if 'foto_fix' not in existing_cols:
            cursor.execute("ALTER TABLE findings ADD COLUMN foto_fix TEXT DEFAULT ''")
            conn.commit()

        cursor.execute('SELECT COUNT(*) FROM findings')
        count = cursor.fetchone()[0]
        if count == 0:
            seed_initial_data(cursor, is_pg=False)
            conn.commit()

    conn.close()


def seed_initial_data(cursor, is_pg=False):
    sample_records = [
        # TEMUAN Near miss FB 1
        ("2026-09-02", "FB 1", "", "Karet pelindung kaki mesin tidak ada", "Mesin bergeser & getaran", "Pemasangan karet pelindung", "2026-09-10", "Karet pelindung telah dipasang pada kaki mesin", "Mtc", "O", "", "", ""),
        ("2026-09-02", "FB 1", "", "Plat dudukan meja tambahan tidak sesajar", "Material tersangkut", "Penyesuaian posisi plat dudukan", "2026-09-10", "Plat dudukan meja telah disesuaikan dan sejajar", "Mtc", "O", "", "", ""),
        ("2026-09-02", "FB 1", "", "Rak part miring ke depan", "Part berjatuhan mengenai MP", "Perkuatan dan perataan rak part", "2026-09-10", "", "Mtc", "X", "", "", ""),
        ("2026-10-12", "FB 1", "Pos 10, Mesin 2, QC", "Tidak ada dudukannya", "Air tumpah & MP terpleset", "Baut copot", "2026-10-21", "Dudukan telah dipasang dan baut dikencangkan", "Rostika", "O", "", "", ""),
        
        # TEMUAN Near miss FB 4
        ("2026-10-01", "FB 4", "Pos 10", "Tas pribadi di area bawah mesin", "Konsleting listrik", "Penyimpanan tas pribadi berada di loker", "2026-10-01", "Tas pribadi telah dipindahkan dan disimpan rapi di loker", "Rostika", "O", "sample_row1_before.jpg", "sample_row1_after.jpg", ""),
        ("2026-10-01", "FB 4", "Pos 9", "Tempat minum terbalik, botol dilantai", "Air tumpah & MP terpleset", "Baut pada besi tempat minum di kencangkan", "2026-10-01", "", "Rostika", "X", "sample_row2_before.jpg", "sample_row2_after.jpg", ""),
        ("2026-10-01", "FB 4", "Pos 6", "Kabel mengelupas", "Konsleting listrik", "Pemasangan solatip pada bagian kabel yang terkelupas", "2026-10-05", "", "Mtc", "X", "sample_row3_before.jpg", "", ""),
        ("2026-10-01", "FB 4", "", "Kabel mesin berantakan", "Konsleting listrik", "Perbaikan dengan pemasangan kabel tis oleh MTc", "2026-10-05", "", "MTc", "X", "", "", ""),
        ("2026-10-01", "FB 4", "Pos 8", "Baud berada di atas meja", "MP tergores", "Baut pada meja dicopot dan pinggir meja yang tajam", "2026-10-01", "Baut pada meja telah dicopot dan pinggiran tajam dirapikan", "Rostika", "O", "", "", ""),
        ("2026-10-01", "FB 4", "Pos 8", "Kawat tajam di bawah mesin", "MP tergores", "kawat yang berada dimesin di copot", "2026-10-01", "Kawat tajam pada mesin telah dicopot", "Rostika", "O", "", ""),
        ("2026-10-01", "FB 4", "Pos 8", "Kabel tidak terpakai", "Konsleting listrik", "Perbaikan dengan pemasangan kabel tis oleh MTc", "2026-10-01", "Kabel tidak terpakai telah dirapikan menggunakan kabel tis", "Rostika", "O", "", ""),
        ("2026-10-01", "FB 4", "Pos 8", "Gunting tidak diikat dengan tali, barang pribadi berada di area mesin", "Gunting terjatuh ,mengenai kaki MP", "Pemasangan tali gunting dan perapihan barang pribadi", "2026-10-01", "Tali pengikat gunting telah dipasang dan barang pribadi dirapikan", "Rostika", "O", "", ""),
        ("2026-10-02", "FB 4", "", "Penyimpanan tombol SPT dekat pengisian spul", "MP tergores", "Perbaikan penempatan tombol SPT disamping mesin", "2026-10-10", "", "MTc", "X", "", "", ""),
        ("2026-10-02", "FB 4", "Pos 9", "Sambungan mesinn berdekatan", "Konsleting listrik", "Perbaikan oleh tim mtc", "2026-10-10", "", "MTc", "X", "", "", ""),
        ("2026-10-02", "FB 4", "Pos 7", "Baud tajam", "MP tergores", "Baut Di copot", "2026-10-01", "Baut tajam telah dicopot", "Rostika", "O", "", "", ""),
        ("2026-10-02", "FB 4", "Pos 3", "Tombol stick balik menggantung", "Tangan MP tergores", "Perbaikan oleh tim mtc", "2026-10-10", "", "MTc", "X", "", "", ""),
        ("2026-10-02", "FB 4", "", "Penutup roda mesin tidak ada", "Mesin terjatuh ,mengenai MP", "Request kakeibo penutup roda mesin", "2026-10-15", "", "MTc", "X", "", "", ""),
        ("2026-10-02", "FB 4", "", "Cover colokan mesin terbuka", "MP tersetrum", "perbaikan cover colokan di tutup", "2026-10-01", "Cover colokan telah ditutup rapat dan aman", "Rostika", "O", "", "", ""),
        ("2026-10-02", "FB 4", "QC", "Kabel melintir", "Konsleting listrik", "kabel dirapihkan dengan kabel tis", "2026-10-01", "Kabel telah dirapikan menggunakan kabel tis", "Rostika", "O", "", ""),
    ]

    sql = '''
        INSERT INTO findings (tanggal, line, pos, temuan, potensi, perbaikan, dudate, fix_date, pic, judg, foto_sebelum, foto_sesudah, foto_fix)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''' if is_pg else '''
        INSERT INTO findings (tanggal, line, pos, temuan, potensi, perbaikan, dudate, fix_date, pic, judg, foto_sebelum, foto_sesudah, foto_fix)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    cursor.executemany(sql, sample_records)


def get_available_periods():
    conn = get_db()
    cursor = conn.cursor()

    if IS_POSTGRES:
        cursor.execute("SELECT DISTINCT SUBSTRING(tanggal FROM 1 FOR 7) as ym FROM findings WHERE tanggal != '' ORDER BY ym DESC")
        months = [row['ym'] for row in cursor.fetchall() if row.get('ym') and len(row['ym']) == 7]

        cursor.execute("SELECT DISTINCT SUBSTRING(tanggal FROM 1 FOR 4) as y FROM findings WHERE tanggal != '' ORDER BY y DESC")
        years = [row['y'] for row in cursor.fetchall() if row.get('y') and len(row['y']) == 4]
    else:
        cursor.execute("SELECT DISTINCT substr(tanggal, 1, 7) as ym FROM findings WHERE tanggal != '' ORDER BY ym DESC")
        months = [row['ym'] for row in cursor.fetchall() if row['ym'] and len(row['ym']) == 7]

        cursor.execute("SELECT DISTINCT substr(tanggal, 1, 4) as y FROM findings WHERE tanggal != '' ORDER BY y DESC")
        years = [row['y'] for row in cursor.fetchall() if row['y'] and len(row['y']) == 4]

    conn.close()
    return {'months': months, 'years': years}


def build_filter_clauses(line_filter=None, status_filter=None, search_query=None, period_type='month', period_val=None, pic_filter=None):
    placeholder = "%s" if IS_POSTGRES else "?"
    query = " WHERE 1=1"
    params = []

    if line_filter and line_filter != 'ALL':
        query += f" AND line = {placeholder}"
        params.append(line_filter)

    if status_filter and status_filter != 'ALL':
        if status_filter in ('O', 'OK'):
            query += " AND (judg = 'O' OR judg = 'OK')"
        elif status_filter in ('X', 'ON PROGRESS'):
            query += " AND (judg = 'X' OR judg = 'ON PROGRESS')"
        else:
            query += f" AND judg = {placeholder}"
            params.append(status_filter)

    if pic_filter and pic_filter != 'ALL':
        query += f" AND pic = {placeholder}"
        params.append(pic_filter)

    if search_query:
        like_op = "ILIKE" if IS_POSTGRES else "LIKE"
        query += f" AND (temuan {like_op} {placeholder} OR potensi {like_op} {placeholder} OR pic {like_op} {placeholder} OR pos {like_op} {placeholder})"
        term = f"%{search_query}%"
        params.extend([term, term, term, term])

    # Period filters
    if period_type == 'month':
        val = period_val or datetime.now().strftime('%Y-%m')
        query += f" AND tanggal LIKE {placeholder}"
        params.append(f"{val}%")
    elif period_type == 'year':
        val = period_val or datetime.now().strftime('%Y')
        query += f" AND tanggal LIKE {placeholder}"
        params.append(f"{val}%")
    elif period_type == 'week':
        ref_date = datetime.now()
        if period_val and len(period_val) == 10:
            try:
                ref_date = datetime.strptime(period_val, '%Y-%m-%d')
            except:
                pass
        start_week = (ref_date - timedelta(days=ref_date.weekday())).strftime('%Y-%m-%d')
        end_week = (ref_date + timedelta(days=6 - ref_date.weekday())).strftime('%Y-%m-%d')
        query += f" AND tanggal >= {placeholder} AND tanggal <= {placeholder}"
        params.extend([start_week, end_week])

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
    placeholder = "%s" if IS_POSTGRES else "?"
    cursor.execute(f"SELECT * FROM findings WHERE id = {placeholder}", (finding_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def insert_finding(data):
    conn = get_db()
    cursor = conn.cursor()

    if IS_POSTGRES:
        cursor.execute('''
            INSERT INTO findings (tanggal, line, pos, temuan, potensi, perbaikan, dudate, fix_date, pic, judg, foto_sebelum, foto_sesudah, foto_fix)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
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
        res = cursor.fetchone()
        new_id = res['id'] if isinstance(res, dict) else res[0]
    else:
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
    p = "%s" if IS_POSTGRES else "?"

    sql = f'''
        UPDATE findings SET
            tanggal = {p},
            line = {p},
            pos = {p},
            temuan = {p},
            potensi = {p},
            perbaikan = {p},
            dudate = {p},
            fix_date = {p},
            pic = {p},
            judg = {p},
            foto_sebelum = CASE WHEN {p} != '' THEN {p} ELSE foto_sebelum END,
            foto_sesudah = CASE WHEN {p} != '' THEN {p} ELSE foto_sesudah END,
            foto_fix = CASE WHEN {p} != '' THEN {p} ELSE foto_fix END
        WHERE id = {p}
    '''
    cursor.execute(sql, (
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
    placeholder = "%s" if IS_POSTGRES else "?"
    cursor.execute(f"DELETE FROM findings WHERE id = {placeholder}", (finding_id,))
    conn.commit()
    conn.close()


def get_statistics(line_filter=None, status_filter=None, search_query=None, period_type='month', period_val=None, pic_filter=None):
    conn = get_db()
    cursor = conn.cursor()

    where_clause, params = build_filter_clauses(line_filter, status_filter, search_query, period_type, period_val, pic_filter)

    def extract_count(c):
        row = c.fetchone()
        if isinstance(row, dict):
            return list(row.values())[0]
        return row[0]

    cursor.execute("SELECT COUNT(*) as cnt FROM findings" + where_clause, params)
    total = extract_count(cursor)

    where_ok = where_clause + " AND (judg = 'O' OR judg = 'OK')"
    cursor.execute("SELECT COUNT(*) as cnt FROM findings" + where_ok, params)
    ok_count = extract_count(cursor)

    where_prog = where_clause + " AND (judg = 'X' OR judg = 'ON PROGRESS' OR (judg != 'O' AND judg != 'OK'))"
    cursor.execute("SELECT COUNT(*) as cnt FROM findings" + where_prog, params)
    on_progress_count = extract_count(cursor)

    conn.close()
    return {
        'total': total,
        'ok': ok_count,
        'on_progress': on_progress_count
    }
