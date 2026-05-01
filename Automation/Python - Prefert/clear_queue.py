"""
Script untuk clear data di VALIDATION_QUEUE (baris 3 ke bawah)
agar pipeline bisa kirim email notifikasi sebagai test.
Jalankan: python clear_queue.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import gspread
from google.oauth2.service_account import Credentials
from config import CONFIG, SCOPES

creds  = Credentials.from_service_account_file(CONFIG["CREDENTIALS_FILE"], scopes=SCOPES)
client = gspread.authorize(creds)
ss     = client.open_by_key(CONFIG["SPREADSHEET_ID"])

ws         = ss.worksheet(CONFIG["SHEET_QUEUE"])
all_values = ws.get_all_values()

if len(all_values) > 2:
    ws.delete_rows(3, len(all_values))
    print(f"✓ VALIDATION_QUEUE: {len(all_values) - 2} baris data dihapus (baris 1-2 tetap)")
else:
    print("VALIDATION_QUEUE sudah kosong")
