import io
import os
import uuid
import re
import mimetypes
from datetime import datetime
from PIL import Image as PILImage
from flask import Flask, render_template, request, redirect, url_for, send_file, flash, send_from_directory, abort, session
from werkzeug.utils import secure_filename

import database
import excel_handler

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fujiseat_safety_secret_key_2026')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IS_VERCEL = os.environ.get('VERCEL') == '1'
UPLOAD_FOLDER = '/tmp/uploads' if IS_VERCEL else os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize DB safely (prevents serverless cold-start crash if DB env vars are not set yet)
try:
    database.init_db()
except Exception as e:
    print(f"Warning: Database initialization skipped/failed: {e}")


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file_storage):
    """
    Save uploaded image to local disk AND persist compressed binary to MySQL `uploaded_photos`.
    This guarantees photos never disappear or turn black on Render when the container sleeps/restarts.
    """
    if not file_storage or file_storage.filename == '':
        return ''
    if allowed_file(file_storage.filename):
        ext = file_storage.filename.rsplit('.', 1)[1].lower()
        unique_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)

        raw_bytes = file_storage.read()
        mime_type = mimetypes.guess_type(unique_name)[0] or 'image/jpeg'

        # Optimize large photos using Pillow so DB storage is fast and under max_allowed_packet limits
        try:
            with PILImage.open(io.BytesIO(raw_bytes)) as img:
                max_dim = 1280
                if max(img.size) > max_dim or len(raw_bytes) > 350 * 1024:
                    img.thumbnail((max_dim, max_dim), PILImage.Resampling.LANCZOS)
                    out_buf = io.BytesIO()
                    if ext in ('jpg', 'jpeg') or img.mode in ('RGBA', 'P'):
                        rgb_img = img.convert('RGB')
                        rgb_img.save(out_buf, format='JPEG', quality=82, optimize=True)
                        mime_type = 'image/jpeg'
                    elif ext == 'webp':
                        img.save(out_buf, format='WEBP', quality=82)
                        mime_type = 'image/webp'
                    else:
                        img.save(out_buf, format='PNG', optimize=True)
                        mime_type = 'image/png'
                    raw_bytes = out_buf.getvalue()
        except Exception:
            pass

        try:
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            with open(filepath, 'wb') as f:
                f.write(raw_bytes)
        except Exception:
            pass

        # Persist binary into MySQL `uploaded_photos` table
        database.save_photo_blob(unique_name, raw_bytes, mime_type)
        return unique_name
    return ''


def remove_uploaded_file_safely(filename):
    """Remove an uploaded image file from both disk and database if it is not a built-in sample image."""
    if not filename or filename.startswith('sample_'):
        return
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.isfile(filepath):
            os.remove(filepath)
    except Exception:
        pass
    database.delete_photo_blob(filename)


PICS = ["Elah hayati", "Yanti", "Rostika", "Maulidia", "Febi", "Novi", "Mtc"]
LINES = ["FB 1", "FB 2", "FB 3", "FB 4", "FC 1", "FC 2", "FC 3", "FC 4"]
LINE_POS_MAP = {
    "FB 1": [f"Pos {i}" for i in range(1, 9)] + ["QC"],        # 8 pos + QC
    "FB 2": [f"Pos {i}" for i in range(1, 10)] + ["QC"],       # 9 pos + QC
    "FB 3": [f"Pos {i}" for i in range(1, 11)] + ["QC"],       # 10 pos + QC
    "FB 4": [f"Pos {i}" for i in range(1, 11)] + ["QC"],       # 10 pos + QC
    "FC 1": [f"Pos {i}" for i in range(1, 11)] + ["QC"],       # 10 pos + QC
    "FC 2": [f"Pos {i}" for i in range(1, 12)] + ["QC"],       # 11 pos + QC (max 11)
    "FC 3": [f"Pos {i}" for i in range(1, 10)] + ["QC"],       # 9 pos + QC
    "FC 4": [f"Pos {i}" for i in range(1, 12)] + ["QC"],       # 11 pos + QC (max 11)
}


def _get_saved_filter_kwargs():
    """Return saved filter parameters from session so user stays in their chosen period."""
    saved = session.get('genba_filters', {})
    return {
        'period_type': saved.get('period_type', 'month'),
        'period_val': saved.get('period_val', ''),
        'line': saved.get('line', 'ALL'),
        'status': saved.get('status', 'ALL'),
        'pic': saved.get('pic', 'ALL'),
        'q': saved.get('q', ''),
        'view': saved.get('view', 'table')
    }


@app.route('/')
def index():
    saved = session.get('genba_filters', {})

    line_filter = request.args.get('line', saved.get('line', 'ALL'))
    status_filter = request.args.get('status', saved.get('status', 'ALL'))
    pic_filter = request.args.get('pic', saved.get('pic', 'ALL'))
    search_query = request.args.get('q', saved.get('q', '')).strip()
    view_mode = request.args.get('view', saved.get('view', 'table'))

    period_type = request.args.get('period_type', saved.get('period_type', 'month'))

    available_periods = database.get_available_periods()
    all_pics = database.get_distinct_pics(PICS)

    default_month = available_periods['months'][0] if available_periods['months'] else datetime.now().strftime('%Y-%m')
    default_year = available_periods['years'][0] if available_periods['years'] else datetime.now().strftime('%Y')
    default_week = datetime.now().strftime('%Y-%m-%d')

    raw_period_val = request.args.get('period_val', saved.get('period_val', ''))

    if period_type == 'month':
        period_val = raw_period_val if (raw_period_val and len(raw_period_val) == 7 and '-' in raw_period_val) else default_month
    elif period_type == 'year':
        period_val = raw_period_val if (raw_period_val and len(raw_period_val) == 4 and raw_period_val.isdigit()) else default_year
    elif period_type == 'week':
        period_val = raw_period_val if (raw_period_val and len(raw_period_val) == 10 and raw_period_val.count('-') == 2) else default_week
    else:
        period_type = 'all'
        period_val = ''

    # Persist current filter state in session so Detail, Edit, and Delete keep the same period
    session['genba_filters'] = {
        'period_type': period_type,
        'period_val': period_val,
        'line': line_filter,
        'status': status_filter,
        'pic': pic_filter,
        'q': search_query,
        'view': view_mode
    }

    findings = database.get_all_findings(line_filter, status_filter, search_query, period_type, period_val, pic_filter)
    stats = database.get_statistics(line_filter, status_filter, search_query, period_type, period_val, pic_filter)

    analytics = database.compute_analytics_data(findings, LINES)
    today_str = datetime.now().strftime('%Y-%m-%d')

    pct_closed = 0
    if stats['total'] > 0:
        pct_closed = round((stats['ok'] / stats['total']) * 100, 1)

    # Auto-heal index.html if an unsaved IDE diff buffer overwrites it
    idx_path = os.path.join(app.root_path, 'templates', 'index.html')
    bak_path = os.path.join(app.root_path, 'templates', 'dashboard_main.html')
    if os.path.exists(idx_path) and os.path.exists(bak_path) and os.path.getsize(idx_path) > 60000:
        import shutil
        shutil.copyfile(bak_path, idx_path)

    return render_template('index.html',
                           findings=findings,
                           stats=stats,
                           analytics=analytics,
                           today_str=today_str,
                           pct_closed=pct_closed,
                           line_filter=line_filter,
                           status_filter=status_filter,
                           pic_filter=pic_filter,
                           search_query=search_query,
                           view_mode=view_mode,
                           period_type=period_type,
                           period_val=period_val,
                           available_periods=available_periods,
                           lines=LINES,
                           pics=all_pics,
                           line_pos_map=LINE_POS_MAP)


@app.route('/analytics')
def analytics_dashboard():
    line_filter = request.args.get('line', 'ALL')
    pic_filter = request.args.get('pic', 'ALL')
    period_type = request.args.get('period_type', 'all')

    available_periods = database.get_available_periods()
    all_pics = database.get_distinct_pics(PICS)

    default_month = available_periods['months'][0] if available_periods['months'] else datetime.now().strftime('%Y-%m')
    default_year = available_periods['years'][0] if available_periods['years'] else datetime.now().strftime('%Y')

    raw_pval = request.args.get('period_val', '')
    if period_type == 'month':
        period_val = raw_pval if (raw_pval and len(raw_pval) == 7 and '-' in raw_pval) else default_month
    elif period_type == 'year':
        period_val = raw_pval if (raw_pval and len(raw_pval) == 4 and raw_pval.isdigit()) else default_year
    elif period_type == 'week':
        period_val = raw_pval if (raw_pval and len(raw_pval) == 10 and raw_pval.count('-') == 2) else datetime.now().strftime('%Y-%m-%d')
    else:
        period_val = ''

    findings = database.get_all_findings(line_filter, 'ALL', '', period_type, period_val, pic_filter)
    analytics = database.compute_analytics_data(findings, LINES)
    today_str = datetime.now().strftime('%Y-%m-%d')

    overdue_findings = [
        f for f in findings
        if (f.get('judg') or '').upper() not in ('O', 'OK')
        and f.get('dudate') and len(f.get('dudate')) == 10 and f.get('dudate') < today_str
    ]

    return render_template('analytics.html',
                           findings=findings,
                           overdue_findings=overdue_findings,
                           analytics=analytics,
                           today_str=today_str,
                           line_filter=line_filter,
                           pic_filter=pic_filter,
                           period_type=period_type,
                           period_val=period_val,
                           available_periods=available_periods,
                           lines=LINES,
                           pics=all_pics,
                           line_pos_map=LINE_POS_MAP)


@app.route('/input', methods=['GET', 'POST'])
def input_finding():
    if request.method == 'POST':
        tanggal = request.form.get('tanggal') or datetime.now().strftime('%Y-%m-%d')
        line = request.form.get('line', 'FB 4')
        pos = request.form.get('pos', '').strip()
        temuan = request.form.get('temuan', '').strip()
        potensi = request.form.get('potensi', '').strip()
        perbaikan = request.form.get('perbaikan', '').strip()
        dudate = request.form.get('dudate', '').strip()
        fix_date = request.form.get('fix_date', '').strip()
        pic = request.form.get('pic', '').strip()
        judg = request.form.get('judg', 'X')
        judg_clean = 'O' if judg.upper() in ['O', 'OK'] else 'X'

        clean_temuan = re.sub(r'[\s\-_.,]', '', temuan)
        if len(temuan) < 3 or len(clean_temuan) < 2:
            flash('Deskripsi temuan safety tidak boleh kosong dan harus jelas!', 'danger')
            return redirect(url_for('input_finding'))

        if not pos or len(pos) < 1:
            flash('Kolom Pos wajib diisi!', 'danger')
            return redirect(url_for('input_finding'))

        if not potensi or len(potensi) < 3:
            flash('Potensi bahaya minimal 3 karakter!', 'danger')
            return redirect(url_for('input_finding'))

        if not dudate:
            flash('Target tanggal (Due Date) wajib diisi!', 'danger')
            return redirect(url_for('input_finding'))

        if not pic or len(pic) < 2:
            flash('Nama PIC minimal 2 karakter!', 'danger')
            return redirect(url_for('input_finding'))

        foto_sebelum_file = request.files.get('foto_sebelum')
        foto_sebelum_name = save_uploaded_file(foto_sebelum_file)
        if not foto_sebelum_name:
            flash('Foto temuan safety (Before) wajib diisi / diunggah!', 'danger')
            return redirect(url_for('input_finding'))

        foto_sesudah_file = request.files.get('foto_sesudah')
        foto_sesudah_name = save_uploaded_file(foto_sesudah_file)

        foto_fix_file = request.files.get('foto_fix')
        foto_fix_name = save_uploaded_file(foto_fix_file)

        new_id = database.insert_finding({
            'tanggal': tanggal,
            'line': line,
            'pos': pos,
            'temuan': temuan,
            'potensi': potensi,
            'perbaikan': perbaikan,
            'dudate': dudate,
            'fix_date': fix_date,
            'pic': pic,
            'judg': judg_clean,
            'foto_sebelum': foto_sebelum_name,
            'foto_sesudah': foto_sesudah_name,
            'foto_fix': foto_fix_name
        })

        session.pop('_flashes', None)
        flash('Temuan safety berhasil disimpan!', 'success')
        return redirect(url_for('index', **_get_saved_filter_kwargs()))

    today_str = datetime.now().strftime('%Y-%m-%d')
    all_pics = database.get_distinct_pics(PICS)
    return render_template('input.html', lines=LINES, pics=all_pics, line_pos_map=LINE_POS_MAP, today_str=today_str)


@app.route('/edit/<int:finding_id>', methods=['GET', 'POST'])
def edit_finding(finding_id):
    finding = database.get_finding_by_id(finding_id)
    if not finding:
        flash('Temuan tidak ditemukan!', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        tanggal = request.form.get('tanggal')
        line = request.form.get('line')
        pos = request.form.get('pos', '').strip()
        temuan = request.form.get('temuan', '').strip()
        potensi = request.form.get('potensi', '').strip()
        perbaikan = request.form.get('perbaikan', '').strip()
        dudate = request.form.get('dudate', '').strip()
        fix_date = request.form.get('fix_date', '').strip()
        pic = request.form.get('pic', '').strip()
        judg = request.form.get('judg', 'X')
        clear_foto_fix = request.form.get('clear_foto_fix') == '1'

        clean_temuan = re.sub(r'[\s\-_.,]', '', temuan)
        if len(temuan) < 3 or len(clean_temuan) < 2:
            flash('Deskripsi temuan safety tidak boleh kosong dan harus jelas!', 'danger')
            return redirect(url_for('edit_finding', finding_id=finding_id))

        if not pos or len(pos) < 1:
            flash('Kolom Pos wajib diisi!', 'danger')
            return redirect(url_for('edit_finding', finding_id=finding_id))

        if not potensi or len(potensi) < 3:
            flash('Potensi bahaya minimal 3 karakter!', 'danger')
            return redirect(url_for('edit_finding', finding_id=finding_id))

        if not dudate:
            flash('Target tanggal (Due Date) wajib diisi!', 'danger')
            return redirect(url_for('edit_finding', finding_id=finding_id))

        if not pic or len(pic) < 2:
            flash('Nama PIC minimal 2 karakter!', 'danger')
            return redirect(url_for('edit_finding', finding_id=finding_id))

        judg_clean = 'O' if judg.upper() in ['O', 'OK'] else 'X'

        foto_sebelum_file = request.files.get('foto_sebelum')
        foto_sebelum_name = save_uploaded_file(foto_sebelum_file)
        if foto_sebelum_name and finding.get('foto_sebelum'):
            remove_uploaded_file_safely(finding.get('foto_sebelum'))

        foto_sesudah_file = request.files.get('foto_sesudah')
        foto_sesudah_name = save_uploaded_file(foto_sesudah_file)
        if foto_sesudah_name and finding.get('foto_sesudah'):
            remove_uploaded_file_safely(finding.get('foto_sesudah'))

        foto_fix_file = request.files.get('foto_fix')
        foto_fix_name = save_uploaded_file(foto_fix_file)
        if (foto_fix_name or clear_foto_fix) and finding.get('foto_fix'):
            remove_uploaded_file_safely(finding.get('foto_fix'))

        database.update_finding(finding_id, {
            'tanggal': tanggal,
            'line': line,
            'pos': pos,
            'temuan': temuan,
            'potensi': potensi,
            'perbaikan': perbaikan,
            'dudate': dudate,
            'fix_date': fix_date,
            'pic': pic,
            'judg': judg_clean,
            'foto_sebelum': foto_sebelum_name,
            'foto_sesudah': foto_sesudah_name,
            'foto_fix': foto_fix_name,
            'clear_foto_fix': clear_foto_fix
        })

        session.pop('_flashes', None)
        flash('Data temuan berhasil diperbarui!', 'success')
        return redirect(url_for('index', **_get_saved_filter_kwargs()))

    all_pics = database.get_distinct_pics(PICS)
    return render_template('edit.html', finding=finding, lines=LINES, pics=all_pics, line_pos_map=LINE_POS_MAP)


@app.route('/detail/<int:finding_id>')
def detail_finding(finding_id):
    finding = database.get_finding_by_id(finding_id)
    if not finding:
        flash('Temuan tidak ditemukan!', 'danger')
        return redirect(url_for('index'))
    return render_template('detail.html', finding=finding)


@app.route('/delete/<int:finding_id>', methods=['POST'])
def delete_finding(finding_id):
    finding = database.get_finding_by_id(finding_id)
    if finding:
        remove_uploaded_file_safely(finding.get('foto_sebelum'))
        remove_uploaded_file_safely(finding.get('foto_sesudah'))
        remove_uploaded_file_safely(finding.get('foto_fix'))
    database.delete_finding(finding_id)
    session.pop('_flashes', None)
    flash('Temuan telah dihapus.', 'info')
    return redirect(url_for('index', **_get_saved_filter_kwargs()))


@app.route('/export-excel')
def export_excel():
    line_filter = request.args.get('line', 'ALL')
    status_filter = request.args.get('status', 'ALL')
    pic_filter = request.args.get('pic', 'ALL')
    search_query = request.args.get('q', '').strip()
    period_type = request.args.get('period_type', 'all')
    period_val = request.args.get('period_val', '')

    excel_stream = excel_handler.export_findings_to_excel(
        line_filter=line_filter,
        status_filter=status_filter,
        search_query=search_query,
        period_type=period_type,
        period_val=period_val,
        pic_filter=pic_filter
    )

    period_label = f"_{period_type}" if period_type != 'all' else ""
    if period_val:
        period_label += f"_{period_val}"
    if pic_filter != 'ALL':
        period_label += f"_{pic_filter.replace(' ', '_')}"

    filename = f"Genba_Safety_Report_Fujiseat{period_label}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(
        excel_stream,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename
    )


@app.route('/import-excel', methods=['POST'])
def import_excel():
    if 'file' not in request.files:
        flash('Tidak ada file yang dipilih.', 'danger')
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '':
        flash('Pilih file Excel (.xlsx / .csv) terlebih dahulu.', 'warning')
        return redirect(url_for('index'))

    try:
        count = excel_handler.import_findings_from_file(file)
        flash(f'Berhasil mengimpor {count} data temuan safety ke dalam sistem!', 'success')
    except Exception as e:
        flash(f'Gagal mengimpor file: {str(e)}', 'danger')

    return redirect(url_for('index'))


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """
    Serve uploaded photo from local `uploads/` folder.
    If the container was restarted on Render and local `uploads/` was wiped,
    automatically restore the photo from MySQL `uploaded_photos` table and serve it!
    """
    safe_name = os.path.basename(filename)
    local_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
    if os.path.isfile(local_path) and os.path.getsize(local_path) > 0:
        return send_from_directory(app.config['UPLOAD_FOLDER'], safe_name)

    # Restore from database if missing on disk
    if database.ensure_photo_on_disk(safe_name, app.config['UPLOAD_FOLDER']):
        return send_from_directory(app.config['UPLOAD_FOLDER'], safe_name)

    # Direct memory stream fallback if disk is read-only
    raw_bytes, mime_type = database.get_photo_blob(safe_name)
    if raw_bytes:
        return send_file(io.BytesIO(raw_bytes), mimetype=mime_type or 'image/jpeg')

    abort(404)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    print("=" * 60)
    print("PT. FUJISEAT INDONESIA - SAFETY GENBA D26A WEB SYSTEM")
    print(f"Akses aplikasi di browser: http://127.0.0.1:{port}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', '1') == '1')
