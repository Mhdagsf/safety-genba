import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image as OpenpyxlImage
from openpyxl.drawing.spreadsheet_drawing import OneCellAnchor, AnchorMarker
from openpyxl.drawing.xdr import XDRPositiveSize2D
from openpyxl.utils.units import pixels_to_EMU
from PIL import Image as PILImage
import csv
import io
import os
import database

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')

def embed_image_to_cell(ws, filename, col_idx_0, row_idx_0, col_width_chars=32, target_w=205, target_h=110):
    """
    col_idx_0: 0-indexed column (0=A, 1=B, 2=C, 3=D, etc.)
    row_idx_0: 0-indexed row (0=row1, 1=row2, etc.)
    Centers image horizontally within the cell and sizes it to match Image 3.
    """
    if not filename:
        return False
    full_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.isfile(full_path):
        return False
    try:
        with PILImage.open(full_path) as pim:
            orig_w, orig_h = pim.size

        ratio = min(target_w / orig_w, target_h / orig_h)
        new_w = max(1, int(orig_w * ratio))
        new_h = max(1, int(orig_h * ratio))

        img = OpenpyxlImage(full_path)
        img.width = new_w
        img.height = new_h

        # Column width in pixels approximately = chars * 7.5 + 5
        cell_pixel_width = int(col_width_chars * 7.5) + 5
        offset_x = max(6, int((cell_pixel_width - new_w) / 2))
        offset_y = max(4, int((115 * 1.33 - new_h) / 2)) # row height 115pt ~ 150px

        marker = AnchorMarker(
            col=col_idx_0,
            colOff=pixels_to_EMU(offset_x),
            row=row_idx_0,
            rowOff=pixels_to_EMU(offset_y)
        )
        size = XDRPositiveSize2D(pixels_to_EMU(new_w), pixels_to_EMU(new_h))
        img.anchor = OneCellAnchor(_from=marker, ext=size)
        ws.add_image(img)
        return True
    except Exception as e:
        print(f"Error embedding image {filename}: {e}")
        return False

def export_findings_to_excel(line_filter='ALL', status_filter='ALL', search_query='', period_type='all', period_val=None, pic_filter='ALL'):
    rows = database.get_all_findings(
        line_filter=line_filter,
        status_filter=status_filter,
        search_query=search_query,
        period_type=period_type,
        period_val=period_val,
        pic_filter=pic_filter
    )

    wb = openpyxl.Workbook()

    # Borders & Styles
    thin_black = Side(style='thin', color='000000')
    cell_border = Border(left=thin_black, right=thin_black, top=thin_black, bottom=thin_black)
    
    header_gray = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")
    header_navy = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    ok_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
    not_ok_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")

    font_header = Font(name="Calibri", size=11, bold=True, color="000000")
    font_data = Font(name="Calibri", size=11, color="000000")
    font_bold = Font(name="Calibri", size=11, bold=True, color="000000")

    # =========================================================================
    # SHEET 1: TEMUAN Near miss (Format 2-Sub-Row Persis Sesuai Gambar 3)
    # =========================================================================
    ws1 = wb.active
    ws1.title = "TEMUAN Near miss (Genba)"

    lines_fb = ["FB 4", "FB 1", "FB 2", "FB 3", "FC 1", "FC 2", "FC 3", "FC 4"]
    current_row = 1

    active_lines = []
    seen = set()
    for r in rows:
        l = r['line'].strip()
        if l not in seen:
            seen.add(l)
            active_lines.append(l)
    for l in lines_fb:
        if l not in seen:
            active_lines.append(l)

    # Set column widths matching Image 3 (Fix width = 32, same as Temuan & Perbaikan)
    col_widths = {
        'A': 5,   # No
        'B': 13,  # Tgl
        'C': 8,   # Pos
        'D': 32,  # Temuan
        'E': 22,  # Potensi
        'F': 32,  # Perbaikan
        'G': 13,  # Dudate
        'H': 32,  # Fix (Equal width to Temuan and Perbaikan)
        'I': 13,  # PIC
        'J': 8    # Judg (O / X)
    }
    for col_letter, width in col_widths.items():
        ws1.column_dimensions[col_letter].width = width

    for line_name in active_lines:
        line_findings = [r for r in rows if r['line'].strip().upper() == line_name.upper()]
        
        # Section Title: "TEMUAN Near miss FB 4"
        ws1.cell(row=current_row, column=1, value=f"TEMUAN Near miss {line_name}").font = Font(name="Calibri", size=11, bold=True, color="000000")
        current_row += 1

        # Table Header
        headers = ["No", "Tgl", "Pos", "Temuan", "Potensi", "Perbaikan", "Dudate", "Fix", "PIC", "Judg"]
        for c_idx, h in enumerate(headers, 1):
            cell = ws1.cell(row=current_row, column=c_idx, value=h)
            cell.fill = header_gray
            cell.font = font_header
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = cell_border
        
        ws1.row_dimensions[current_row].height = 26
        current_row += 1

        if not line_findings:
            # Empty rows placeholder
            for empty_idx in range(1, 3):
                r_top = current_row
                r_bot = current_row + 1
                ws1.row_dimensions[r_top].height = 30
                ws1.row_dimensions[r_bot].height = 115
                
                # Merge No, Tgl, Pos, Potensi, Dudate, PIC, Judg
                for col_m in [1, 2, 3, 5, 7, 9, 10]:
                    ws1.merge_cells(start_row=r_top, start_column=col_m, end_row=r_bot, end_column=col_m)
                    c = ws1.cell(row=r_top, column=col_m)
                    c.alignment = Alignment(horizontal="center", vertical="center")
                    if col_m == 1:
                        c.value = empty_idx
                    for r_sub in range(r_top, r_bot + 1):
                        ws1.cell(row=r_sub, column=col_m).border = cell_border

                for col_s in [4, 6, 8]:
                    ws1.cell(row=r_top, column=col_s).border = cell_border
                    ws1.cell(row=r_bot, column=col_s).border = cell_border

                current_row += 2
            current_row += 1
            continue

        # Render 2-sub-row entries per finding (Exact layout of Image 3)
        for f_no, fr in enumerate(line_findings, 1):
            r_top = current_row
            r_bot = current_row + 1

            # Exact row heights from Image 3
            ws1.row_dimensions[r_top].height = 30
            ws1.row_dimensions[r_bot].height = 115

            # 1. Col No (Merged vertically)
            ws1.merge_cells(start_row=r_top, start_column=1, end_row=r_bot, end_column=1)
            c_no = ws1.cell(row=r_top, column=1, value=f_no)
            c_no.alignment = Alignment(horizontal="center", vertical="center")
            c_no.font = font_data

            # 2. Col Tgl (Merged vertically)
            ws1.merge_cells(start_row=r_top, start_column=2, end_row=r_bot, end_column=2)
            c_tgl = ws1.cell(row=r_top, column=2, value=fr['tanggal'])
            c_tgl.alignment = Alignment(horizontal="center", vertical="center")
            c_tgl.font = font_data

            # 3. Col Pos (Merged vertically)
            ws1.merge_cells(start_row=r_top, start_column=3, end_row=r_bot, end_column=3)
            c_pos = ws1.cell(row=r_top, column=3, value=fr['pos'])
            c_pos.alignment = Alignment(horizontal="center", vertical="center")
            c_pos.font = font_data

            # 4. Col Temuan:
            # - Upper row: text description
            c_tem_top = ws1.cell(row=r_top, column=4, value=fr['temuan'])
            c_tem_top.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
            c_tem_top.font = font_data
            # - Lower row: embedded photo Before (centered & enlarged)
            c_tem_bot = ws1.cell(row=r_bot, column=4, value="")
            if fr['foto_sebelum']:
                embed_image_to_cell(
                    ws=ws1,
                    filename=fr['foto_sebelum'],
                    col_idx_0=3, # Column D
                    row_idx_0=r_bot - 1,
                    col_width_chars=32,
                    target_w=205,
                    target_h=110
                )

            # 5. Col Potensi (Merged vertically)
            ws1.merge_cells(start_row=r_top, start_column=5, end_row=r_bot, end_column=5)
            c_pot = ws1.cell(row=r_top, column=5, value=fr['potensi'])
            c_pot.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
            c_pot.font = font_data

            # 6. Col Perbaikan:
            # - Upper row: text countermeasure
            c_per_top = ws1.cell(row=r_top, column=6, value=fr['perbaikan'])
            c_per_top.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
            c_per_top.font = font_data
            # - Lower row: embedded photo After OR "ON PROGRESS" text centered
            c_per_bot = ws1.cell(row=r_bot, column=6)
            c_per_bot.font = font_bold
            if fr['foto_sesudah']:
                embed_image_to_cell(
                    ws=ws1,
                    filename=fr['foto_sesudah'],
                    col_idx_0=5, # Column F
                    row_idx_0=r_bot - 1,
                    col_width_chars=32,
                    target_w=205,
                    target_h=110
                )
            else:
                c_per_bot.value = "ON PROGRESS"
                c_per_bot.alignment = Alignment(horizontal="center", vertical="center")

            # 7. Col Dudate (Merged vertically)
            ws1.merge_cells(start_row=r_top, start_column=7, end_row=r_bot, end_column=7)
            c_du = ws1.cell(row=r_top, column=7, value=fr['dudate'])
            c_du.alignment = Alignment(horizontal="center", vertical="center")
            c_du.font = font_data

            # 8. Col Fix (Equal width to Temuan & Perbaikan, with horizontal line dividing upper & lower sub-row)
            c_fix_top = ws1.cell(row=r_top, column=8, value=fr['fix_date'])
            c_fix_top.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
            c_fix_top.font = font_data
            c_fix_bot = ws1.cell(row=r_bot, column=8, value="")
            foto_fix_val = fr['foto_fix'] if ('foto_fix' in fr.keys() and fr['foto_fix']) else ''
            if foto_fix_val:
                embed_image_to_cell(
                    ws=ws1,
                    filename=foto_fix_val,
                    col_idx_0=7, # Column H (Fix)
                    row_idx_0=r_bot - 1,
                    col_width_chars=32,
                    target_w=205,
                    target_h=110
                )

            # 9. Col PIC (Merged vertically)
            ws1.merge_cells(start_row=r_top, start_column=9, end_row=r_bot, end_column=9)
            c_pic = ws1.cell(row=r_top, column=9, value=fr['pic'])
            c_pic.alignment = Alignment(horizontal="center", vertical="center")
            c_pic.font = font_data

            # 10. Col Judg (O or X) (Merged vertically)
            # O if OK / O, X if not OK / ON PROGRESS / X
            judg_symbol = "O" if fr['judg'] in ('O', 'OK') else "X"
            ws1.merge_cells(start_row=r_top, start_column=10, end_row=r_bot, end_column=10)
            c_judg = ws1.cell(row=r_top, column=10, value=judg_symbol)
            c_judg.alignment = Alignment(horizontal="center", vertical="center")
            c_judg.font = Font(name="Calibri", size=11, bold=True, color="166534" if judg_symbol == "O" else "991B1B")
            if judg_symbol == "O":
                c_judg.fill = ok_fill
            else:
                c_judg.fill = not_ok_fill

            # Apply full borders to all sub-cells
            for r_k in [r_top, r_bot]:
                for c_k in range(1, 11):
                    ws1.cell(row=r_k, column=c_k).border = cell_border

            current_row += 2

        current_row += 1 # Spacing between lines

    # =========================================================================
    # SHEET 2: REKAP KESELURUHAN (Master Tabular View)
    # =========================================================================
    ws2 = wb.create_sheet(title="Rekap Temuan Keseluruhan")

    ws2.merge_cells("A1:M1")
    ws2["A1"] = "PT. FUJISEAT INDONESIA - REKAP DATA TEMUAN SAFETY & NEAR MISS"
    ws2["A1"].font = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
    ws2["A1"].alignment = Alignment(horizontal="left", vertical="center")

    master_headers = [
        "No", "Tanggal", "Line", "Pos / Stasiun", "Deskripsi Temuan",
        "Potensi Bahaya", "Tindakan Perbaikan", "Due Date", "Fix (Deskripsi Perbaikan)",
        "PIC", "Judgement (O/X)", "Foto Temuan (Before)", "Foto Perbaikan (After)"
    ]

    ws2.row_dimensions[3].height = 28
    for c_idx, mh in enumerate(master_headers, 1):
        cell = ws2.cell(row=3, column=c_idx, value=mh)
        cell.fill = header_navy
        cell.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = cell_border

    row_m = 4
    for idx, r in enumerate(rows, 1):
        has_sebelum = bool(r['foto_sebelum'])
        has_sesudah = bool(r['foto_sesudah'])
        needs_large = has_sebelum or has_sesudah

        ws2.row_dimensions[row_m].height = 95 if needs_large else 26

        ws2.cell(row=row_m, column=1, value=idx).alignment = Alignment(horizontal="center", vertical="center")
        ws2.cell(row=row_m, column=2, value=r['tanggal']).alignment = Alignment(horizontal="center", vertical="center")
        ws2.cell(row=row_m, column=3, value=r['line']).alignment = Alignment(horizontal="center", vertical="center")
        ws2.cell(row=row_m, column=4, value=r['pos']).alignment = Alignment(horizontal="center", vertical="center")
        
        c_tem = ws2.cell(row=row_m, column=5, value=r['temuan'])
        c_tem.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        
        c_pot = ws2.cell(row=row_m, column=6, value=r['potensi'])
        c_pot.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        
        c_per = ws2.cell(row=row_m, column=7, value=r['perbaikan'])
        c_per.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        
        ws2.cell(row=row_m, column=8, value=r['dudate']).alignment = Alignment(horizontal="center", vertical="center")
        c_fix = ws2.cell(row=row_m, column=9, value=r['fix_date'])
        c_fix.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        ws2.cell(row=row_m, column=10, value=r['pic']).alignment = Alignment(horizontal="center", vertical="center")

        for c_k in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
            ws2.cell(row=row_m, column=c_k).font = font_data
        
        # O or X judgement
        judg_val = "O" if r['judg'] in ('O', 'OK') else "X"
        c_judg = ws2.cell(row=row_m, column=11, value=judg_val)
        c_judg.alignment = Alignment(horizontal="center", vertical="center")
        c_judg.font = Font(name="Calibri", size=11, bold=True, color="166534" if judg_val == "O" else "991B1B")
        if judg_val == "O":
            c_judg.fill = ok_fill
        else:
            c_judg.fill = not_ok_fill

        # Embed Foto Sebelum in Col L
        c_l = ws2.cell(row=row_m, column=12, value="" if has_sebelum else "-")
        c_l.alignment = Alignment(horizontal="center", vertical="center")
        c_l.font = font_data
        if has_sebelum:
            embed_image_to_cell(
                ws=ws2,
                filename=r['foto_sebelum'],
                col_idx_0=11,
                row_idx_0=row_m - 1,
                col_width_chars=22,
                target_w=140,
                target_h=85
            )

        # Embed Foto Sesudah in Col M
        c_m = ws2.cell(row=row_m, column=13, value="" if has_sesudah else "-")
        c_m.alignment = Alignment(horizontal="center", vertical="center")
        c_m.font = font_data
        if has_sesudah:
            embed_image_to_cell(
                ws=ws2,
                filename=r['foto_sesudah'],
                col_idx_0=12,
                row_idx_0=row_m - 1,
                col_width_chars=22,
                target_w=140,
                target_h=85
            )

        for c_k in range(1, 14):
            ws2.cell(row=row_m, column=c_k).border = cell_border
            if c_k != 11:
                ws2.cell(row=row_m, column=c_k).font = font_data

        row_m += 1

    # Auto-adjust column widths for Sheet 2
    for col in ws2.columns:
        col_letter = get_column_letter(col[0].column)
        if col_letter in ['L', 'M']:
            ws2.column_dimensions[col_letter].width = 22
        elif col_letter in ['E', 'G']:
            ws2.column_dimensions[col_letter].width = 30
        elif col_letter in ['F']:
            ws2.column_dimensions[col_letter].width = 24
        else:
            ws2.column_dimensions[col_letter].width = 14

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

def import_findings_from_file(file_storage):
    filename = file_storage.filename.lower()
    imported_count = 0

    if filename.endswith('.csv'):
        stream = io.StringIO(file_storage.stream.read().decode("utf-8", errors="ignore"))
        reader = csv.reader(stream)
        for row in reader:
            if not row or len(row) < 4:
                continue
            if row[0].strip().isdigit() or (len(row) > 1 and any(char.isdigit() for char in row[1])):
                tgl = row[1].strip() if len(row) > 1 else ""
                pos_or_line = row[2].strip() if len(row) > 2 else ""
                temuan = row[3].strip() if len(row) > 3 else ""
                if not temuan or temuan.lower() in ['temuan', 'deskripsi']:
                    continue

                potensi = row[4].strip() if len(row) > 4 else ""
                perbaikan = row[5].strip() if len(row) > 5 else ""
                dudate = row[6].strip() if len(row) > 6 else ""
                fix_date = row[7].strip() if len(row) > 7 else ""
                pic = row[8].strip() if len(row) > 8 else ""
                raw_judg = row[9].strip() if len(row) > 9 else ""
                
                # Support O and X
                if raw_judg.upper() in ['O', 'OK']:
                    judg = 'O'
                else:
                    judg = 'X'

                line = "FB 4"
                for l in ["FB 1", "FB 2", "FB 3", "FB 4", "FC 1", "FC 2", "FC 3", "FC 4"]:
                    if l.replace(" ", "").lower() in pos_or_line.lower():
                        line = l
                        break

                database.insert_finding({
                    'tanggal': tgl,
                    'line': line,
                    'pos': pos_or_line,
                    'temuan': temuan,
                    'potensi': potensi,
                    'perbaikan': perbaikan,
                    'dudate': dudate,
                    'fix_date': fix_date,
                    'pic': pic,
                    'judg': judg
                })
                imported_count += 1

    elif filename.endswith('.xlsx') or filename.endswith('.xls'):
        wb = openpyxl.load_workbook(file_storage, data_only=True)
        for sheet in wb.worksheets:
            for row in sheet.iter_rows(values_only=True):
                if not row or len(row) < 4:
                    continue
                r_str = [str(cell).strip() if cell is not None else "" for cell in row]

                has_finding = False
                temuan_val = ""
                tgl_val = ""
                line_val = "FB 4"
                pos_val = ""
                potensi_val = ""
                perbaikan_val = ""
                dudate_val = ""
                fix_val = ""
                pic_val = ""
                judg_val = "X"

                if len(r_str) >= 5 and (r_str[0].isdigit() or (r_str[1] and ('-' in r_str[1] or '.' in r_str[1]))):
                    if len(r_str) >= 10 and ("FB" in r_str[2] or "FC" in r_str[2]):
                        tgl_val = r_str[1]
                        line_val = r_str[2]
                        pos_val = r_str[3]
                        temuan_val = r_str[4]
                        potensi_val = r_str[5]
                        perbaikan_val = r_str[6]
                        dudate_val = r_str[7]
                        fix_val = r_str[8]
                        pic_val = r_str[9]
                        raw_judg = r_str[10] if len(r_str) > 10 else ""
                        judg_val = 'O' if raw_judg.upper() in ['O', 'OK'] else 'X'
                        has_finding = True
                    elif len(r_str) >= 5 and r_str[3]:
                        tgl_val = r_str[1]
                        pos_val = r_str[2]
                        temuan_val = r_str[3]
                        potensi_val = r_str[4] if len(r_str) > 4 else ""
                        perbaikan_val = r_str[5] if len(r_str) > 5 else ""
                        dudate_val = r_str[6] if len(r_str) > 6 else ""
                        fix_val = r_str[7] if len(r_str) > 7 else ""
                        pic_val = r_str[8] if len(r_str) > 8 else ""
                        raw_judg = r_str[9] if len(r_str) > 9 else ""
                        judg_val = 'O' if raw_judg.upper() in ['O', 'OK'] else 'X'
                        has_finding = True

                if has_finding and temuan_val and temuan_val.lower() not in ['temuan', 'deskripsi temuan', 'none']:
                    database.insert_finding({
                        'tanggal': tgl_val,
                        'line': line_val,
                        'pos': pos_val,
                        'temuan': temuan_val,
                        'potensi': potensi_val,
                        'perbaikan': perbaikan_val,
                        'dudate': dudate_val,
                        'fix_date': fix_val,
                        'pic': pic_val,
                        'judg': judg_val
                    })
                    imported_count += 1

    return imported_count
