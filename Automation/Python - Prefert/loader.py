"""
WasteX Pipeline — Tasks: Data Loading
=======================================
Task untuk:
  - load_data       : baca 4 sheet sumber dari Google Sheets
  - build_lookup_maps : siapkan lookup dict untuk cross-sheet checks
"""

import gspread
from google.oauth2.service_account import Credentials
from collections import Counter, defaultdict
from prefect import task, get_run_logger

from config import CONFIG, SCOPES
from helpers import to_float


# ─────────────────────────────────────────────────────────
# KONEKSI GOOGLE SHEETS
# ─────────────────────────────────────────────────────────
def get_spreadsheet():
    """
    Buat koneksi ke Google Sheets menggunakan Service Account.
    Dipanggil fresh setiap task yang butuh akses — tidak di-share
    antar task karena Prefect bisa run task di worker berbeda.
    """
    creds  = Credentials.from_service_account_file(CONFIG["CREDENTIALS_FILE"], scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(CONFIG["SPREADSHEET_ID"])


# ─────────────────────────────────────────────────────────
# TASK 1 — LOAD DATA
# ─────────────────────────────────────────────────────────
@task(
    name="load-google-sheets-data",
    description="Baca 4 sheet sumber dari Google Sheets",
    retries=CONFIG["TASK_RETRIES"],
    retry_delay_seconds=CONFIG["TASK_RETRY_DELAY_SEC"],
    timeout_seconds=CONFIG["TASK_TIMEOUT_SEC"],
    tags=["io", "google-sheets"],
)
def load_data() -> dict:
    """
    Baca biochar_production, bag_production, biochar_application,
    bag_application dari Google Sheets.

    Return:
        {
            "biochar_prod": [...],  # list of dicts, setiap dict = 1 row
            "bag_prod"    : [...],
            "biochar_app" : [...],
            "bag_app"     : [...],
        }

    Setiap row dict punya key tambahan _row_index (nomor baris di sheet)
    untuk referensi saat filtering ke CLEANED sheets.
    """
    log = get_run_logger()
    log.info("Connecting ke Google Sheets...")

    ss = get_spreadsheet()

    def sheet_to_dicts(sheet_name: str) -> list[dict]:
        ws      = ss.worksheet(sheet_name)
        records = ws.get_all_records()
        # Tambah _row_index: referensi baris asli di sheet (baris 1 = header)
        for i, row in enumerate(records):
            row["_row_index"] = i + 2
        log.info(f"  ✓ {sheet_name}: {len(records)} rows di-load")
        return records

    data = {
        "biochar_prod" : sheet_to_dicts(CONFIG["SHEET_BIOCHAR_PROD"]),
        "bag_prod"     : sheet_to_dicts(CONFIG["SHEET_BAG_PROD"]),
        "biochar_app"  : sheet_to_dicts(CONFIG["SHEET_BIOCHAR_APP"]),
        "bag_app"      : sheet_to_dicts(CONFIG["SHEET_BAG_APP"]),
    }

    total = sum(len(v) for v in data.values())
    log.info(f"Total rows di-load: {total}")
    return data


# ─────────────────────────────────────────────────────────
# TASK 2 — BUILD LOOKUP MAPS
# ─────────────────────────────────────────────────────────
@task(
    name="build-lookup-maps",
    description="Build lookup dict dari bag_production untuk cross-sheet checks (TYPE 7,8,9,10)",
    tags=["preprocessing"],
)
def build_lookup_maps(data: dict) -> dict:
    """
    Build semua lookup map yang dibutuhkan untuk cross-sheet validation.
    Dipisah ke task sendiri supaya tidak di-compute ulang di setiap anomaly task.

    Lookup yang dihasilkan:
        bag_prod_weight_map : { bag_id → weight_float }      → TYPE 8
        bag_prod_id_set     : [ bag_id, ... ]                → TYPE 7
        bag_id_count        : { bag_id → jumlah_muncul }     → TYPE 4
        bag_app_map         : { bag_id → [application_id] }  → TYPE 10
        batch_sums          : { production_id → sum_weight } → TYPE 9

    Note: set dan dict dengan set value tidak bisa di-serialize Prefect,
    jadi bag_prod_id_set disimpan sebagai list, bag_app_map sebagai dict of list.
    """
    log = get_run_logger()
    log.info("Building lookup maps dari bag_production dan bag_application...")

    bag_prod_weight_map : dict[str, float] = {}
    bag_prod_id_list    : list[str]        = []
    bag_id_count        : dict[str, int]   = {}
    bag_app_map         : dict[str, list]  = {}
    batch_sums          : dict[str, float] = {}

    # ── Dari bag_production ──
    for row in data["bag_prod"]:
        bid = str(row.get("bag_id", ""))
        w   = to_float(row.get("weight"))

        if bid:
            bag_prod_id_list.append(bid)
            bag_id_count[bid] = bag_id_count.get(bid, 0) + 1

        if bid and w is not None:
            bag_prod_weight_map[bid] = w
            prod_id = str(row.get("production_id", ""))
            if prod_id:
                batch_sums[prod_id] = batch_sums.get(prod_id, 0) + w

    # ── Dari bag_application ──
    for row in data["bag_app"]:
        bid = str(row.get("bag_id", ""))
        aid = str(row.get("application_id", ""))
        if bid and aid:
            if bid not in bag_app_map:
                bag_app_map[bid] = []
            if aid not in bag_app_map[bid]:
                bag_app_map[bid].append(aid)

    log.info(f"  bag_prod_id_set     : {len(set(bag_prod_id_list))} unique bag_ids")
    log.info(f"  bag_prod_weight_map : {len(bag_prod_weight_map)} entries")
    log.info(f"  batch_sums          : {len(batch_sums)} production batches")
    log.info(f"  bag_app_map         : {len(bag_app_map)} bags di bag_application")

    return {
        "bag_prod_weight_map" : bag_prod_weight_map,
        "bag_prod_id_set"     : list(set(bag_prod_id_list)),
        "bag_id_count"        : bag_id_count,
        "bag_app_map"         : bag_app_map,
        "batch_sums"          : batch_sums,
    }
