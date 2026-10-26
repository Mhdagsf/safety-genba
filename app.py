import os
import uuid
import re
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_file, flash, send_from_directory
from werkzeug.utils import secure_filename

import database
import excel_handler

app = Flask(__name__)
app.secret_key = 'fujiseat_safety_secret_key_2026'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
IMAGES_FOLDER = os.path.join(BASE_DIR, 'images')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(IMAGES_FOLDER, exist_ok=True)

# Initialize DB
database.init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file_storage):
    if not file_storage or file_storage.filename == '':
        return ''
    if allowed_file(file_storage.filename):
        ext = file_storage.filename.rsplit('.', 1)[1].lower()
        unique_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        file_storage.save(filepath)
        return unique_name
    return ''

PICS = ["Elah hayati", "Yanti", "Rostika", "Maulidia", "Febi", "Novi"]
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

@app.route('/')
def index():
    line_filter = request.args.get('line', 'ALL')
    status_filter = request.args.get('status', 'ALL')
    pic_filter = request.args.get('pic', 'ALL')
    search_query = request.args.get('q', '').strip()
    view_mode = request.args.get('view', 'table') # 'table' or 'card'

    # Period filter: 'month', 'week', 'year', 'all'. Default is 'month' as requested!
    period_type = request.args.get('period_type', 'month')
    
    available_periods = database.get_available_periods()
    
    # Default period_val for month is the latest month available or current month
    default_month = available_periods['months'][0] if available_periods['months'] else datetime.now().strftime('%Y-%m')
    default_year = available_periods['years'][0] if available_periods['years'] else datetime.now().strftime('%Y')
    
    if period_type == 'month':
        period_val = request.args.get('period_val', default_month)
    elif period_type == 'year':
        period_val = request.args.get('period_val', default_year)
    elif period_type == 'week':
        period_val = request.args.get('period_val', datetime.now().strftime('%Y-%m-%d'))
    else:
        period_val = request.args.get('period_val', '')

    findings = database.get_all_findings(line_filter, status_filter, search_query, period_type, period_val, pic_filter)
    stats = database.get_statistics(line_filter, status_filter, search_query, period_type, period_val, pic_filter)
    
    pct_closed = 0
    if stats['total'] > 0:
        pct_closed = round((stats['ok'] / stats['total']) * 100, 1)

    return render_template('index.html',
                           findings=findings,
                           stats=stats,
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
                           pics=PICS,
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

        # Validasi server-side ketat
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

        flash(f'Temuan safety berhasil disimpan! (ID #{new_id})', 'success')
        return redirect(url_for('index'))

    today_str = datetime.now().strftime('%Y-%m-%d')
    return render_template('input.html', lines=LINES, pics=PICS, line_pos_map=LINE_POS_MAP, today_str=today_str)

@app.route('/edit/<int:finding_id>', methods=['GET', 'POST'])
def edit_finding(finding_id):
    finding = database.get_finding_by_id(finding_id)
    if not finding:
        flash('Temuan tidak ditemukan!', 'danger')
        return redirect(url_for('index'))

    lines = ["FB 1", "FB 2", "FB 3", "FB 4", "FC 1", "FC 2", "FC 3", "FC 4"]

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

        # Validasi server-side
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

        foto_sesudah_file = request.files.get('foto_sesudah')
        foto_sesudah_name = save_uploaded_file(foto_sesudah_file)

        foto_fix_file = request.files.get('foto_fix')
        foto_fix_name = save_uploaded_file(foto_fix_file)

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
            'foto_fix': foto_fix_name
        })

        flash(f'Data temuan #{finding_id} berhasil diperbarui oleh Group Leader!', 'success')
        return redirect(url_for('index'))

    return render_template('edit.html', finding=finding, lines=LINES, pics=PICS, line_pos_map=LINE_POS_MAP)

@app.route('/detail/<int:finding_id>')
def detail_finding(finding_id):
    finding = database.get_finding_by_id(finding_id)
    if not finding:
        flash('Temuan tidak ditemukan!', 'danger')
        return redirect(url_for('index'))
    return render_template('detail.html', finding=finding)

@app.route('/delete/<int:finding_id>', methods=['POST'])
def delete_finding(finding_id):
    database.delete_finding(finding_id)
    flash(f'Temuan #{finding_id} telah dihapus.', 'info')
    return redirect(url_for('index'))

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

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/images/<filename>')
def custom_images(filename):
    return send_from_directory(IMAGES_FOLDER, filename)

if __name__ == '__main__':
    print("=" * 60)
    print("PT. FUJISEAT INDONESIA - SAFETY GENBA D26A WEB SYSTEM")
    print("Akses aplikasi di browser: http://127.0.0.1:5050")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5050, debug=True)
