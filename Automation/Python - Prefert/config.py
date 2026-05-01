"""
WasteX Pipeline — Config
=========================
Semua setting terpusat di sini.
Ubah nilai di sini sesuai kebutuhan.

Tips keamanan:
- Jangan hardcode credentials di sini kalau mau push ke Git
- Pakai environment variables (os.getenv) untuk nilai sensitif
- Tambahkan config.py ke .gitignore
"""

import os

CONFIG = {

    # ── Google Sheets ─────────────────────────────────────
    # Ambil SPREADSHEET_ID dari URL Google Sheet:
    # https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
    "SPREADSHEET_ID"   : os.getenv("WASTEX_SPREADSHEET_ID", "1gBjAm5dDucndlevQElRatCD8XcX4G4DbvbbTtL3K_hg"),
    "CREDENTIALS_FILE" : os.getenv("WASTEX_CREDENTIALS_FILE", "credentials.json"),

    # ── Nama Sheet Sumber ─────────────────────────────────
    "SHEET_BIOCHAR_PROD"  : "biochar_production",
    "SHEET_BAG_PROD"      : "bag_production",
    "SHEET_BIOCHAR_APP"   : "biochar_application",
    "SHEET_BAG_APP"       : "bag_application",

    # ── Nama Sheet Output ─────────────────────────────────
    "SHEET_CLEANED_PROD"   : "CLEANED_prod_batch",
    "SHEET_CLEANED_BAG"    : "CLEANED_bag_prod",
    "SHEET_CLEANED_APP"    : "CLEANED_app_batch",
    "SHEET_CLEANED_BAGAPP" : "CLEANED_bag_app",
    "SHEET_QUEUE"          : "VALIDATION_QUEUE",
    "SHEET_LOG"            : "AUTOMATION_LOG",

    # ── Email Notifikasi ──────────────────────────────────
    "NOTIFICATION_EMAIL" : os.getenv("WASTEX_NOTIFY_EMAIL", "nurimammasri.01@gmail.com"),
    "EMAIL_SENDER"       : os.getenv("WASTEX_EMAIL_SENDER", "nurimammasri.01@gmail.com"),
    # Gunakan App Password Gmail, bukan password utama!
    # Cara buat: Google Account → Security → App Passwords
    "EMAIL_PASSWORD"     : os.getenv("WASTEX_EMAIL_PASSWORD", "qcexvgqfulcbaqzn"),

    # ── Prefect Task Settings ─────────────────────────────
    "TASK_RETRIES"         : 3,    # retry otomatis per task kalau gagal
    "TASK_RETRY_DELAY_SEC" : 30,   # tunggu 30 detik sebelum retry
    "TASK_TIMEOUT_SEC"     : 300,  # timeout 5 menit per task

    # ── Threshold Anomali ─────────────────────────────────
    # TYPE 5: maksimum hari application_date boleh lebih lambat dari Timestamp
    "MAX_APP_DATE_GAP_DAYS"  : 30,

    # TYPE 8: maksimum selisih berat antara bag_application dan bag_production
    "WEIGHT_DISCREPANCY_PCT" : 0.05,   # 5%

    # TYPE 9: toleransi selisih batch sum vs biochar_amount_kg (dalam kg)
    "BATCH_SUM_TOLERANCE_KG" : 0.01,

    # ── Nilai Valid application_type (TYPE 6) ─────────────
    "VALID_APP_TYPES" : [
        "Application-Pure Biochar",
        "Application-Charged Biochar",
        "Sale-Pure Biochar",
        "Sale-Charged Biochar",
    ],
}

# Google Sheets API scopes
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
