import sqlite3

conn = sqlite3.connect('safety_genba.db')
c = conn.cursor()

# 1. Update Judgements to 'O' or 'X'
c.execute("UPDATE findings SET judg = 'O' WHERE judg = 'OK'")
c.execute("UPDATE findings SET judg = 'X' WHERE judg = 'ON PROGRESS' OR (judg != 'O' AND judg != 'OK')")

# 2. Update fix descriptions for resolved items (Judg = 'O')
fix_descriptions = {
    1: "Karet pelindung telah dipasang pada kaki mesin",
    2: "Plat dudukan meja telah disesuaikan dan sejajar",
    3: "",
    4: "Tas pribadi telah dipindahkan dan disimpan rapi di loker",
    5: "",
    6: "",
    7: "",
    8: "Baut pada meja telah dicopot dan pinggiran tajam dirapikan",
    9: "Kawat tajam pada mesin telah dicopot",
    10: "Kabel tidak terpakai telah dirapikan menggunakan kabel tis",
    11: "Tali pengikat gunting telah dipasang dan barang pribadi dirapikan",
    12: "",
    13: "",
    14: "Baut tajam telah dicopot",
    15: "",
    16: "",
    17: "Cover colokan telah ditutup rapat dan aman",
    18: "Kabel telah dirapikan menggunakan kabel tis",
    19: "Dudukan telah dipasang dan baut dikencangkan"
}

for fid, fix_desc in fix_descriptions.items():
    c.execute("UPDATE findings SET fix_date = ? WHERE id = ?", (fix_desc, fid))

# Set judgs specifically to match the fix status
c.execute("UPDATE findings SET judg = 'X' WHERE fix_date = ''")
c.execute("UPDATE findings SET judg = 'O' WHERE fix_date != ''")

conn.commit()

# Print verification
c.execute("SELECT id, line, pos, temuan, fix_date, judg FROM findings")
for row in c.fetchall():
    print(row)

conn.close()
print("Database migration successful!")
