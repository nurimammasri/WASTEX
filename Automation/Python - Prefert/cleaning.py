"""
WasteX Pipeline — Tasks: Data Cleaning
=========================================
Task untuk:
  - merge_anomalies : gabungkan semua anomali dari 10 detection tasks
  - build_cleaned   : filter baris bermasalah, hasilkan cleaned dataset
"""

from collections import Counter
from prefect import task, get_run_logger


# ─────────────────────────────────────────────────────────
# TASK 13 — MERGE ALL ANOMALIES
# ─────────────────────────────────────────────────────────
@task(
    name="merge-all-anomalies",
    description="Gabungkan semua anomali dari 10 detection tasks menjadi satu list",
    tags=["aggregation"],
)
def merge_anomalies(*anomaly_lists) -> list[dict]:
    """
    Terima output dari semua detect_type* tasks dan gabungkan.
    Dipisah ke task sendiri supaya ada visibility di Prefect UI:
    bisa lihat berapa total anomali sebelum write ke sheet.

    Input : *anomaly_lists → variable args, bisa list atau tuple(list, fixed_data)
    Return: flat list semua anomali dari semua tipe
    """
    log           = get_run_logger()
    all_anomalies = []

    for item in anomaly_lists:
        # detect_type1 return tuple (anomalies, fixed_data) — ambil anomalies saja
        if isinstance(item, tuple):
            item = item[0]
        if isinstance(item, list):
            all_anomalies.extend(item)

    # Log ringkasan per tipe
    type_counts = Counter(a["anomaly_type"] for a in all_anomalies)
    log.info(f"TOTAL ANOMALI GABUNGAN: {len(all_anomalies)}")
    for atype, count in sorted(type_counts.items()):
        auto = " (auto-fixed)" if atype == "TYPE 1" else ""
        log.info(f"  {atype}: {count} finding(s){auto}")

    return all_anomalies


# ─────────────────────────────────────────────────────────
# TASK 14 — BUILD CLEANED DATA
# ─────────────────────────────────────────────────────────
@task(
    name="build-cleaned-data",
    description="Filter baris bermasalah dari data, build cleaned dataset untuk 4 CLEANED sheets",
    tags=["cleaning"],
)
def build_cleaned(
    data          : dict,
    fixed_bag_prod: list[dict],
    all_anomalies : list[dict],
) -> dict:
    """
    Build cleaned dataset dengan logika routing:
      - TYPE 1  → sudah auto-fixed di fixed_bag_prod, TETAP masuk CLEANED
      - TYPE 2–10 → EXCLUDE dari CLEANED, hanya masuk VALIDATION_QUEUE
      - TYPE 4  → keep first occurrence per bag_id (dedup)

    Cara kerja:
    1. Kumpulkan Record_ID yang di-flag TYPE 2-10 per sheet
    2. Map Record_ID ke _row_index di data
    3. Filter: hanya rows yang _row_index TIDAK ada di flagged set

    Return:
        {
            "biochar_prod": [...],  # rows yang lolos cleaning
            "bag_prod"    : [...],
            "biochar_app" : [...],
            "bag_app"     : [...],
        }
    """
    log = get_run_logger()
    log.info("Building cleaned dataset — filtering flagged rows...")

    # Map sheet name ke data key
    sheet_to_key = {
        "biochar_production" : "biochar_prod",
        "bag_production"     : "bag_prod",
        "biochar_application": "biochar_app",
        "bag_application"    : "bag_app",
    }

    # Kumpulkan _row_index yang di-flag per data key
    flagged: dict[str, set] = {key: set() for key in sheet_to_key.values()}

    for a in all_anomalies:
        if a["anomaly_type"] == "TYPE 1":
            continue  # TYPE 1 = auto-fixed, tetap masuk CLEANED

        for sheet_prefix, data_key in sheet_to_key.items():
            if a["Sheet"].startswith(sheet_prefix):
                rid  = str(a["Record_ID"])
                # Gunakan fixed_bag_prod untuk bag_production
                rows = fixed_bag_prod if data_key == "bag_prod" else data.get(data_key, [])
                for row in rows:
                    row_id = str(row.get("bag_id") or row.get("activity_id") or "")
                    if row_id == rid:
                        flagged[data_key].add(row.get("_row_index"))

    # TYPE 4: keep only first occurrence per bag_id (dedup)
    seen_bag_ids: set[str] = set()
    for row in fixed_bag_prod:
        bid = str(row.get("bag_id", ""))
        if bid in seen_bag_ids:
            flagged["bag_prod"].add(row.get("_row_index"))
        else:
            seen_bag_ids.add(bid)

    # Build cleaned: exclude flagged rows
    raw_bag_prod = fixed_bag_prod  # pakai yang sudah di-fix TYPE 1
    cleaned = {
        "biochar_prod": [r for r in data["biochar_prod"] if r.get("_row_index") not in flagged["biochar_prod"]],
        "bag_prod"    : [r for r in raw_bag_prod          if r.get("_row_index") not in flagged["bag_prod"]],
        "biochar_app" : [r for r in data["biochar_app"]   if r.get("_row_index") not in flagged["biochar_app"]],
        "bag_app"     : [r for r in data["bag_app"]       if r.get("_row_index") not in flagged["bag_app"]],
    }

    # Log hasil per sheet
    log.info(f"  CLEANED_prod_batch : {len(cleaned['biochar_prod'])}/{len(data['biochar_prod'])} rows")
    log.info(f"  CLEANED_bag_prod   : {len(cleaned['bag_prod'])}/{len(raw_bag_prod)} rows")
    log.info(f"  CLEANED_app_batch  : {len(cleaned['biochar_app'])}/{len(data['biochar_app'])} rows")
    log.info(f"  CLEANED_bag_app    : {len(cleaned['bag_app'])}/{len(data['bag_app'])} rows")

    return cleaned
