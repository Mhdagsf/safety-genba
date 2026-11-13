import os
import mimetypes
from urllib.parse import urlparse, unquote
from datetime import datetime, timedelta
import mysql.connector
from mysql.connector import Error

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQL_SCHEMA_PATH = os.path.join(BASE_DIR, 'safety_genba.sql')
ENV_PATH = os.path.join(BASE_DIR, '.env')
UPLOAD_DIR = '/tmp/uploads' if os.environ.get('VERCEL') == '1' else os.path.join(BASE_DIR, 'uploads')

if os.path.isfile(ENV_PATH):
    with open(ENV_PATH, 'r', encoding='utf-8') as _env_file:
        for _line in _env_file:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _v = _line.split('=', 1)
                os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))


def _build_db_config():
    """
    Build MySQL connection configuration.
    Supports:
    1. DATABASE_URL / MYSQL_URL (e.g. mysql://user:pass@host:port/dbname)
    2. Individual env vars: DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME, DB_SSL
    3. Local XAMPP defaults (localhost:3306, root, safety_genba)
    """
    db_url = os.environ.get('DATABASE_URL') or os.environ.get('MYSQL_URL') or ''
    host = os.environ.get('DB_HOST', 'localhost')
    user = os.environ.get('DB_USER', 'root')
    password = os.environ.get('DB_PASS', '')
    database = os.environ.get('DB_NAME', 'safety_genba')
    port = int(os.environ.get('DB_PORT', '3306'))
    ssl_mode = os.environ.get('DB_SSL', '').strip().lower()

    if db_url and db_url.startswith(('mysql://', 'mysql+pymysql://', 'mysql+mysqlconnector://')):
        parsed = urlparse(db_url)
        if parsed.hostname:
            host = parsed.hostname
        if parsed.port:
            port = int(parsed.port)
        if parsed.username:
            user = unquote(parsed.username)
        if parsed.password is not None:
            password = unquote(parsed.password)
        if parsed.path and parsed.path.strip('/'):
            database = parsed.path.strip('/')
        if 'ssl' in (parsed.query or '').lower():
            ssl_mode = 'true'

    cfg = {
        'host': host,
        'user': user,
        'password': password,
        'database': database,
        'port': port,
        'charset': 'utf8mb4',
        'collation': 'utf8mb4_unicode_ci',
        'autocommit': False,
        'connect_timeout': 10,
    }

    # Enable SSL automatically for cloud hosts (TiDB Cloud, Aiven, Railway, etc.) if DB_SSL=true or non-local host requires it
    if ssl_mode in ('1', 'true', 'yes', 'required'):
        cfg['ssl_disabled'] = False
    elif ssl_mode in ('0', 'false', 'no', 'disabled'):
        cfg['ssl_disabled'] = True

    return cfg


DB_CONFIG = _build_db_config()


def get_db():
    """Get a MySQL database connection."""
    return mysql.connector.connect(**_build_db_config())


def dict_cursor(conn):
    """Return a dictionary cursor for the connection."""
    return conn.cursor(dictionary=True)


def init_db():
    """
    Ensure the MySQL database, `findings` table, and `uploaded_photos` table exist.
    Works on both local XAMPP (where root can CREATE DATABASE) and Cloud MySQL on Render
    (where the database is pre-created by the provider).
    """
    current_cfg = _build_db_config()
    db_name = current_cfg['database']

    conn = None
    cursor = None
    try:
        # Attempt 1: Connect directly to the target database (works on Cloud MySQL & existing local DB)
        try:
            conn = mysql.connector.connect(**current_cfg)
            cursor = conn.cursor()
        except Error:
            # Attempt 2: Connect without database name and create it (works on fresh local XAMPP)
            config_no_db = {
                k: v for k, v in current_cfg.items()
                if k not in ('database', 'charset', 'collation', 'autocommit')
            }
            conn = mysql.connector.connect(**config_no_db)
            cursor = conn.cursor()
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            conn.commit()
            cursor.execute(f"USE `{db_name}`")

        # 1. Check if `findings` table already exists
        cursor.execute(
            """
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'findings'
            """,
            (db_name,)
        )
        table_exists = cursor.fetchone()[0] > 0

        if not table_exists and os.path.isfile(SQL_SCHEMA_PATH):
            with open(SQL_SCHEMA_PATH, 'r', encoding='utf-8') as f:
                sql_script = f.read()

            cleaned_lines = []
            for line in sql_script.splitlines():
                stripped = line.strip()
                if stripped.startswith('--'):
                    continue
                # Skip CREATE DATABASE / USE statements so Cloud MySQL with custom DB_NAME won't fail
                if stripped.upper().startswith('CREATE DATABASE') or stripped.upper().startswith('USE '):
                    continue
                cleaned_lines.append(line)

            for statement in '\n'.join(cleaned_lines).split(';'):
                stmt = statement.strip()
                if stmt:
                    cursor.execute(stmt)
            conn.commit()
        else:
            # Ensure foto_fix column exists for older installations
            cursor.execute(
                """
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'findings' AND COLUMN_NAME = 'foto_fix'
                """,
                (db_name,)
            )
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE `findings` ADD COLUMN foto_fix VARCHAR(255) NOT NULL DEFAULT ''")
                conn.commit()

        # 2. Ensure `uploaded_photos` table exists for persistent cloud image storage (Render/Cloud safe)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS `uploaded_photos` (
                `filename` VARCHAR(255) NOT NULL PRIMARY KEY,
                `mime_type` VARCHAR(64) NOT NULL DEFAULT 'image/jpeg',
                `file_data` LONGBLOB NOT NULL,
                `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )
        conn.commit()

        # 3. Sync any existing local images in uploads/ into `uploaded_photos` so sample/existing photos never go black
        if os.path.isdir(UPLOAD_DIR):
            cursor.execute("SELECT filename FROM uploaded_photos")
            existing_blobs = {r[0] for r in cursor.fetchall()}
            for fname in os.listdir(UPLOAD_DIR):
                if fname in existing_blobs or fname.startswith('.'):
                    continue
                fpath = os.path.join(UPLOAD_DIR, fname)
                if os.path.isfile(fpath) and os.path.getsize(fpath) < 16 * 1024 * 1024:
                    try:
                        mime_type = mimetypes.guess_type(fname)[0] or 'image/jpeg'
                        with open(fpath, 'rb') as img_f:
                            raw_bytes = img_f.read()
                        if raw_bytes:
                            cursor.execute(
                                """
                                INSERT IGNORE INTO uploaded_photos (filename, mime_type, file_data)
                                VALUES (%s, %s, %s)
                                """,
                                (fname, mime_type, raw_bytes)
                            )
                    except Exception:
                        pass
            conn.commit()

    except Error as e:
        print(f"Error initializing database: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# =====================================================================
# PERSISTENT PHOTO STORAGE HELPERS (PREVENTS BLACK/MISSING PHOTOS ON RENDER)
# =====================================================================

def save_photo_blob(filename, raw_bytes, mime_type=None):
    """Save or update an uploaded photo's binary content in MySQL so it survives container restarts."""
    if not filename or not raw_bytes:
        return
    if not mime_type:
        mime_type = mimetypes.guess_type(filename)[0] or 'image/jpeg'
    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO uploaded_photos (filename, mime_type, file_data)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE mime_type = VALUES(mime_type), file_data = VALUES(file_data)
            """,
            (filename, mime_type, raw_bytes)
        )
        conn.commit()
    except Exception as e:
        print(f"Warning: Failed to backup photo {filename} to database: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_photo_blob(filename):
    """Retrieve (file_data, mime_type) from MySQL for a given filename, or (None, None) if not found."""
    if not filename:
        return None, None
    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT file_data, mime_type FROM uploaded_photos WHERE filename = %s",
            (filename,)
        )
        row = cursor.fetchone()
        if row and row[0]:
            return bytes(row[0]), (row[1] or 'image/jpeg')
    except Exception as e:
        print(f"Warning: Failed to read photo {filename} from database: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return None, None


def ensure_photo_on_disk(filename, upload_folder=None):
    """
    Ensure `filename` exists in `upload_folder`.
    If missing on disk (e.g. after Render sleep/restart), restore it from `uploaded_photos` table.
    Returns True if the file is available on disk, False otherwise.
    """
    if not filename:
        return False
    target_dir = upload_folder or UPLOAD_DIR
    os.makedirs(target_dir, exist_ok=True)
    filepath = os.path.join(target_dir, filename)
    if os.path.isfile(filepath) and os.path.getsize(filepath) > 0:
        return True

    raw_bytes, _ = get_photo_blob(filename)
    if raw_bytes:
        try:
            with open(filepath, 'wb') as f:
                f.write(raw_bytes)
            return True
        except Exception:
            return False
    return False


def delete_photo_blob(filename):
    """Delete a photo from `uploaded_photos` when its finding or photo is removed."""
    if not filename or filename.startswith('sample_'):
        return
    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM uploaded_photos WHERE filename = %s", (filename,))
        conn.commit()
    except Exception:
        pass
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_available_periods():
    conn = get_db()
    cursor = dict_cursor(conn)
    cursor.execute("SELECT DISTINCT LEFT(tanggal, 7) AS ym FROM findings WHERE tanggal != '' ORDER BY ym DESC")
    months = [row['ym'] for row in cursor.fetchall() if row['ym'] and len(row['ym']) == 7]

    cursor.execute("SELECT DISTINCT LEFT(tanggal, 4) AS y FROM findings WHERE tanggal != '' ORDER BY y DESC")
    years = [row['y'] for row in cursor.fetchall() if row['y'] and len(row['y']) == 4]

    cursor.close()
    conn.close()
    return {'months': months, 'years': years}


def get_distinct_pics(default_pics=None):
    """Return combined list of default PICs and any distinct PICs in the database."""
    base = list(default_pics) if default_pics else []
    seen = {p.lower(): p for p in base}
    try:
        conn = get_db()
        cursor = dict_cursor(conn)
        cursor.execute("SELECT DISTINCT pic FROM findings WHERE pic IS NOT NULL AND TRIM(pic) != '' ORDER BY pic ASC")
        for row in cursor.fetchall():
            val = row['pic'].strip()
            if val and val.lower() not in seen:
                seen[val.lower()] = val
                base.append(val)
        cursor.close()
        conn.close()
    except Exception:
        pass
    return base


def build_filter_clauses(line_filter=None, status_filter=None, search_query=None, period_type='month', period_val=None, pic_filter=None):
    query = " WHERE 1=1"
    params = []

    if line_filter and line_filter != 'ALL':
        query += " AND line = %s"
        params.append(line_filter)

    if status_filter and status_filter != 'ALL':
        if status_filter in ('O', 'OK'):
            query += " AND (judg = 'O' OR judg = 'OK')"
        elif status_filter in ('X', 'ON PROGRESS'):
            query += " AND (judg = 'X' OR judg = 'ON PROGRESS')"
        elif status_filter == 'OVERDUE':
            today_str = datetime.now().strftime('%Y-%m-%d')
            query += " AND (judg != 'O' AND judg != 'OK') AND dudate != '' AND dudate < %s"
            params.append(today_str)
        else:
            query += " AND judg = %s"
            params.append(status_filter)

    if pic_filter and pic_filter != 'ALL':
        query += " AND LOWER(TRIM(pic)) = LOWER(TRIM(%s))"
        params.append(pic_filter)

    if search_query:
        query += " AND (temuan LIKE %s OR potensi LIKE %s OR pic LIKE %s OR pos LIKE %s)"
        term = f"%{search_query}%"
        params.extend([term, term, term, term])

    # Period filters
    if period_type == 'month':
        val = period_val or datetime.now().strftime('%Y-%m')
        query += " AND tanggal LIKE %s"
        params.append(f"{val}%")
    elif period_type == 'year':
        val = period_val or datetime.now().strftime('%Y')
        query += " AND tanggal LIKE %s"
        params.append(f"{val}%")
    elif period_type == 'week':
        ref_date = datetime.now()
        if period_val and len(period_val) == 10:
            try:
                ref_date = datetime.strptime(period_val, '%Y-%m-%d')
            except ValueError:
                pass
        start_week = (ref_date - timedelta(days=ref_date.weekday())).strftime('%Y-%m-%d')
        end_week = (ref_date + timedelta(days=6 - ref_date.weekday())).strftime('%Y-%m-%d')
        query += " AND tanggal >= %s AND tanggal <= %s"
        params.extend([start_week, end_week])

    return query, params


def get_all_findings(line_filter=None, status_filter=None, search_query=None, period_type='month', period_val=None, pic_filter=None):
    conn = get_db()
    cursor = dict_cursor(conn)
    base_query = "SELECT * FROM findings"
    where_clause, params = build_filter_clauses(line_filter, status_filter, search_query, period_type, period_val, pic_filter)
    full_query = base_query + where_clause + " ORDER BY id DESC"

    cursor.execute(full_query, params)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def get_finding_by_id(finding_id):
    conn = get_db()
    cursor = dict_cursor(conn)
    cursor.execute("SELECT * FROM findings WHERE id = %s", (finding_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row


def insert_finding(data):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO findings (tanggal, line, pos, temuan, potensi, perbaikan, dudate, fix_date, pic, judg, foto_sebelum, foto_sesudah, foto_fix)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
    cursor.close()
    conn.close()
    return new_id


def update_finding(finding_id, data):
    conn = get_db()
    cursor = conn.cursor()
    clear_fix = 1 if data.get('clear_foto_fix') else 0
    cursor.execute('''
        UPDATE findings SET
            tanggal = %s,
            line = %s,
            pos = %s,
            temuan = %s,
            potensi = %s,
            perbaikan = %s,
            dudate = %s,
            fix_date = %s,
            pic = %s,
            judg = %s,
            foto_sebelum = CASE WHEN %s != '' THEN %s ELSE foto_sebelum END,
            foto_sesudah = CASE WHEN %s != '' THEN %s ELSE foto_sesudah END,
            foto_fix = CASE WHEN %s = 1 THEN '' WHEN %s != '' THEN %s ELSE foto_fix END
        WHERE id = %s
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
        clear_fix,
        data.get('foto_fix', ''),
        data.get('foto_fix', ''),
        finding_id
    ))
    conn.commit()
    cursor.close()
    conn.close()


def delete_finding(finding_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM findings WHERE id = %s", (finding_id,))
    conn.commit()
    cursor.close()
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

    today_str = datetime.now().strftime('%Y-%m-%d')
    where_overdue = where_prog + " AND dudate != '' AND dudate < %s"
    cursor.execute("SELECT COUNT(*) FROM findings" + where_overdue, params + [today_str])
    overdue_count = cursor.fetchone()[0]

    cursor.close()
    conn.close()
    return {
        'total': total,
        'ok': ok_count,
        'on_progress': on_progress_count,
        'overdue': overdue_count
    }


def compute_analytics_data(findings, lines_order=None):
    """
    Compute comprehensive statistical datasets from a list of finding rows
    for rendering interactive charts and heatmaps.
    """
    import re
    if lines_order is None:
        lines_order = ["FB 1", "FB 2", "FB 3", "FB 4", "FC 1", "FC 2", "FC 3", "FC 4"]

    today_str = datetime.now().strftime('%Y-%m-%d')

    line_stats = {
        l: {'line': l, 'total': 0, 'ok': 0, 'on_progress': 0, 'overdue': 0, 'pct': 0.0}
        for l in lines_order
    }
    hazard_counts = {}
    hazard_display = {}
    pic_stats = {}
    date_stats = {}
    pos_hotspot = {l: {} for l in lines_order}

    total_count = len(findings)
    ok_total = 0
    prog_total = 0
    overdue_total = 0
    with_photo_after = 0

    for r in findings:
        line_name = (r.get('line') or '').strip()
        if line_name not in line_stats:
            line_stats[line_name] = {'line': line_name, 'total': 0, 'ok': 0, 'on_progress': 0, 'overdue': 0, 'pct': 0.0}
            pos_hotspot[line_name] = {}

        is_ok = (r.get('judg') or '').upper() in ('O', 'OK')
        dudate = (r.get('dudate') or '').strip()
        is_overdue = (not is_ok) and bool(dudate) and (len(dudate) == 10) and (dudate < today_str)

        if r.get('foto_sesudah') or r.get('foto_fix'):
            with_photo_after += 1

        if is_ok:
            ok_total += 1
        else:
            prog_total += 1
            if is_overdue:
                overdue_total += 1

        ls = line_stats[line_name]
        ls['total'] += 1
        if is_ok:
            ls['ok'] += 1
        else:
            ls['on_progress'] += 1
            if is_overdue:
                ls['overdue'] += 1

        raw_pos = (r.get('pos') or '').strip() or 'Tanpa Pos'
        pos_hotspot[line_name][raw_pos] = pos_hotspot[line_name].get(raw_pos, 0) + 1

        raw_potensi = (r.get('potensi') or '').strip()
        if raw_potensi:
            parts = [p.strip() for p in re.split(r'[,;&]+', raw_potensi) if p.strip()]
            for part in parts:
                key = part.lower()
                hazard_counts[key] = hazard_counts.get(key, 0) + 1
                if key not in hazard_display:
                    hazard_display[key] = part[0].upper() + part[1:] if len(part) > 1 else part.upper()

        raw_pic = (r.get('pic') or '').strip() or 'Tanpa PIC'
        pic_key = raw_pic.lower()
        if pic_key not in pic_stats:
            pic_stats[pic_key] = {
                'pic': raw_pic,
                'total': 0,
                'ok': 0,
                'on_progress': 0,
                'overdue': 0,
                'pct': 0.0
            }
        ps = pic_stats[pic_key]
        ps['total'] += 1
        if is_ok:
            ps['ok'] += 1
        else:
            ps['on_progress'] += 1
            if is_overdue:
                ps['overdue'] += 1

        tgl = (r.get('tanggal') or '').strip()
        if tgl:
            if tgl not in date_stats:
                date_stats[tgl] = {'date': tgl, 'total': 0, 'ok': 0, 'on_progress': 0}
            date_stats[tgl]['total'] += 1
            if is_ok:
                date_stats[tgl]['ok'] += 1
            else:
                date_stats[tgl]['on_progress'] += 1

    for l_val in line_stats.values():
        if l_val['total'] > 0:
            l_val['pct'] = round((l_val['ok'] / l_val['total']) * 100, 1)

    pic_list = list(pic_stats.values())
    for p_val in pic_list:
        if p_val['total'] > 0:
            p_val['pct'] = round((p_val['ok'] / p_val['total']) * 100, 1)
    pic_list.sort(key=lambda x: (-x['total'], x['pic']))

    hazard_list = [
        {
            'label': hazard_display[k],
            'count': cnt,
            'pct': round((cnt / total_count) * 100, 1) if total_count > 0 else 0
        }
        for k, cnt in sorted(hazard_counts.items(), key=lambda item: (-item[1], item[0]))
    ][:10]

    trend_list = [date_stats[d] for d in sorted(date_stats.keys())]
    most_findings_line = max(line_stats.values(), key=lambda x: x['total']) if line_stats else {'line': '-', 'total': 0}

    return {
        'summary': {
            'total': total_count,
            'ok': ok_total,
            'on_progress': prog_total,
            'overdue': overdue_total,
            'ontime_progress': max(0, prog_total - overdue_total),
            'pct_closed': round((ok_total / total_count) * 100, 1) if total_count > 0 else 0.0,
            'with_photo_after': with_photo_after,
            'top_line': most_findings_line['line'] if most_findings_line['total'] > 0 else '-',
            'top_line_count': most_findings_line['total'],
            'top_hazard': hazard_list[0]['label'] if hazard_list else '-',
            'top_hazard_count': hazard_list[0]['count'] if hazard_list else 0
        },
        'lines': list(line_stats.values()),
        'hazards': hazard_list,
        'pics': pic_list,
        'trend': trend_list,
        'pos_hotspot': pos_hotspot
    }
