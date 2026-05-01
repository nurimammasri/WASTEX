"""
Script diagnostik — lihat nama kolom (headers) di semua sheet Google Sheets
Jalankan: python check_headers.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import gspread
from google.oauth2.service_account import Credentials
from config import CONFIG, SCOPES

creds  = Credentials.from_service_account_file(CONFIG["CREDENTIALS_FILE"], scopes=SCOPES)
client = gspread.authorize(creds)
ss     = client.open_by_key(CONFIG["SPREADSHEET_ID"])

print("=" * 60)
print("SHEET HEADERS DIAGNOSTIC")
print("=" * 60)

for ws in ss.worksheets():
    print(f"\n[{ws.title}]")
    all_vals = ws.get_all_values()
    if not all_vals:
        print("  (kosong)")
        continue
    print(f"  Row 1: {all_vals[0]}")
    if len(all_vals) > 1:
        print(f"  Row 2: {all_vals[1]}")
    print(f"  Total rows: {len(all_vals)}")
