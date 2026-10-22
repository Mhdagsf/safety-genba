import os
import database
import excel_handler

print("1. Testing database initialization and seeding...")
database.init_db()
stats = database.get_statistics()
print(f"Stats loaded: Total={stats['total']}, OK={stats['ok']}, OnProgress={stats['on_progress']}")
assert stats['total'] > 0, "Database should have seeded records"

findings = database.get_all_findings()
print(f"Total findings retrieved: {len(findings)}")
print(f"First finding: Line={findings[0]['line']}, Temuan={findings[0]['temuan']}")

print("2. Testing Excel export...")
stream = excel_handler.export_findings_to_excel()
size = len(stream.getvalue())
print(f"Excel generated successfully! File size: {size} bytes")
assert size > 1000, "Excel output should not be empty"

print("3. Testing Flask test client...")
from app import app
client = app.test_client()

resp = client.get('/')
print(f"GET / status: {resp.status_code}")
assert resp.status_code == 200

resp = client.get('/input')
print(f"GET /input status: {resp.status_code}")
assert resp.status_code == 200

resp = client.get(f'/detail/{findings[0]["id"]}')
print(f"GET /detail/{findings[0]['id']} status: {resp.status_code}")
assert resp.status_code == 200

resp = client.get('/export-excel')
print(f"GET /export-excel status: {resp.status_code}")
assert resp.status_code == 200
print("ALL TESTS PASSED SUCCESSFULLY!")
