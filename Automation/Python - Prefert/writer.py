"""
WasteX Pipeline — Tasks: Google Sheets Writer
===============================================
Task untuk menulis semua output ke Google Sheets:
  - write_cleaned_sheets   : tulis 4 CLEANED sheets
  - write_validation_queue : tulis anomali ke VALIDATION_QUEUE
  - write_automation_log   : tulis log per run ke AUTOMATION_LOG
"""

import gspread
from datetime import datetime
from prefect import task, get_run_logger

from config import CONFIG, SCOPES
from loader import get_spreadsheet


# ─────────────────────────────────────────────────────────
# TASK 15 — WRITE CLEANED SHEETS
# ─────────────────────────────────────────────────────────
@task(
    name="write-cleaned-sheets",
    description="Tulis cleaned data ke 4 CLEANED sheets di Google Sheets",
    retries=CONFIG["TASK_RETRIES"],
    retry_delay_seconds=CONFIG["TASK_RETRY_DELAY_SEC"],
    timeout_seconds=CONFIG["TASK_TIMEOUT_SEC"],
    tags=["io", "google-sheets"],
)
def write_cleaned_sheets(cleaned: dict) -> None:
    """
    Tulis 4 CLEANED sheets ke Google Sheets.
    Logika penulisan:
    1. Ambil header dari keys data (bukan dari baris pertama sheet)
    2. Clear seluruh sheet
    3. Tulis header di baris 1
    4. Tulis data mulai baris 2
    """
    log = get_run_logger()
    log.info("Writing CLEANED sheets ke Google Sheets...")

    ss = get_spreadsheet()

    sheet_map = {
        "biochar_prod" : CONFIG["SHEET_CLEANED_PROD"],
        "bag_prod"     : CONFIG["SHEET_CLEANED_BAG"],
        "biochar_app"  : CONFIG["SHEET_CLEANED_APP"],
        "bag_app"      : CONFIG["SHEET_CLEANED_BAGAPP"],
    }

    # Definisi kolom per sheet — sesuai persis kolom di source sheet
    SHEET_COLUMNS = {
        "biochar_prod": ["Timestamp","username","activity_id","biochar_amount_kg","number_of_bags",
                         "carbon_content_%","feedstock_type","feedstock_amount","fuel_amount",
                         "feedstock_humidity","feedstock_size","co2e_persistent","co2e_100","ch4",
                         "spc","margin_of_safety","electricity_emission","actual_start_time",
                         "actual_finish_time","temp_1","temp_2","temp_3","notes"],
        "bag_prod":     ["Timestamp","username","bag_id","production_id","weight","co2e_persistent",
                         "co2e_100","ch4","spc","margin_of_safety","electricity_emission","feedstock_type"],
        "biochar_app":  ["Timestamp","username","activity_id","application_type","total_weight",
                         "application_date","number_of_bags","location","purpose","charging_material",
                         "charging_amount","co2e_persistent_exc_transport","co2e_100_exc_transport",
                         "ch4","spc","biomass_transport_emission","biochar_transport_emission",
                         "margin_of_safety","emission_electricity","methane_compensation","notes"],
        "bag_app":      ["Timestamp","username","application_id","bag_id","production_id","bag_weight",
                         "co2e_persistent_excl_transport","co2e_100_excl_transport","ch4","spc",
                         "biomass_emission_transport","biochar_emission_transport","margin_of_safety",
                         "emission_electricity","feedstock_type"],
    }

    for data_key, sheet_name in sheet_map.items():
        rows    = cleaned.get(data_key, [])
        headers = SHEET_COLUMNS[data_key]
        try:
            ws = ss.worksheet(sheet_name)

            # Baris 1 = deskripsi (tidak diubah), tulis header di baris 2, data mulai baris 3
            # Hapus data lama dari baris 3 ke bawah
            all_vals = ws.get_all_values()
            if len(all_vals) >= 2:
                ws.delete_rows(2, max(len(all_vals), 2))

            # Tulis header di baris 2
            ws.update("A2", [headers])

            # Tulis data mulai baris 3
            if rows:
                output = []
                for row in rows:
                    output_row = []
                    for h in headers:
                        val = row.get(h, "")
                        if isinstance(val, datetime):
                            val = val.strftime("%Y-%m-%d %H:%M:%S")
                        output_row.append(val if val is not None else "")
                    output.append(output_row)
                ws.insert_rows(output, row=3)

            log.info(f"  ✓ {sheet_name}: {len(rows)} rows ditulis")

        except gspread.WorksheetNotFound:
            log.error(f"  Sheet tidak ditemukan: {sheet_name}")
            raise



# ─────────────────────────────────────────────────────────
# TASK 16 — WRITE VALIDATION QUEUE
# ─────────────────────────────────────────────────────────
@task(
    name="write-validation-queue",
    description="Tulis anomali baru ke VALIDATION_QUEUE (skip duplikat dari run sebelumnya)",
    retries=CONFIG["TASK_RETRIES"],
    retry_delay_seconds=CONFIG["TASK_RETRY_DELAY_SEC"],
    timeout_seconds=CONFIG["TASK_TIMEOUT_SEC"],
    tags=["io", "google-sheets"],
)
def write_validation_queue(all_anomalies: list[dict]) -> int:
    """
    Tulis anomali ke VALIDATION_QUEUE dengan deduplication.

    Dedup logic: cek kombinasi Sheet + anomaly_type + Record_ID.
    Kalau kombinasi ini sudah ada di queue → skip (tidak ditulis ulang).
    Ini penting supaya run harian tidak mengisi queue dengan anomali yang sama
    berulang-ulang sampai ada yang me-resolve.

    Kolom output VALIDATION_QUEUE:
      Sheet, anomaly_type, description, Field,
      original_value, suggested_fix, action, Record_ID,
      detected_at, Reviewed_By, Resolution, Resolved_At

    Return: jumlah anomali baru yang berhasil ditulis
    """
    log = get_run_logger()
    log.info("Writing ke VALIDATION_QUEUE...")

    ss = get_spreadsheet()
    ws = ss.worksheet(CONFIG["SHEET_QUEUE"])

    # Header sesuai persis kolom VALIDATION_QUEUE
    headers = [
        "Sheet", "anomaly_type", "description", "Field",
        "original_value", "suggested_fix", "action", "Record_ID",
        "detected_at", "Reviewed_By", "Resolution", "Resolved_At",
    ]

    # Baris 1 = deskripsi (tidak diubah), tulis header di baris 2
    ws.update("A2", [headers])
    log.info("  Header VALIDATION_QUEUE ditulis di baris 2")

    # Ambil semua baris mulai baris 3 untuk cek duplikat
    all_values = ws.get_all_values()
    existing_keys = set()
    existing_count = 0
    if len(all_values) > 2:
        for row in all_values[2:]:  # skip baris 1 (deskripsi) dan baris 2 (header)
            # Skip baris kosong
            if not any(c.strip() for c in row):
                continue
            existing_count += 1
            if len(row) > 7:
                key = f"{row[0]}|{row[1]}|{row[7]}"  # Sheet|anomaly_type|Record_ID
                existing_keys.add(key)
    log.info(f"  Existing records di queue: {existing_count}")

    # Filter anomali baru saja
    new_anomalies = [
        a for a in all_anomalies
        if f"{a['Sheet']}|{a['anomaly_type']}|{a['Record_ID']}" not in existing_keys
    ]

    if new_anomalies:
        rows_to_write = [[a.get(h, "") for h in headers] for a in new_anomalies]
        last_row = existing_count + 3   # +3: baris 1 deskripsi + baris 2 header + 1-based
        ws.insert_rows(rows_to_write, row=last_row)
        log.info(f"  ✓ {len(new_anomalies)} anomali baru ditulis ke VALIDATION_QUEUE")
    else:
        log.info("  Tidak ada anomali baru — VALIDATION_QUEUE tidak berubah")

    return len(new_anomalies)


# ─────────────────────────────────────────────────────────
# TASK 17 — WRITE AUTOMATION LOG
# ─────────────────────────────────────────────────────────
@task(
    name="write-automation-log",
    description="Tulis satu baris log per sheet ke AUTOMATION_LOG sesuai struktur sheet WasteX",
    retries=CONFIG["TASK_RETRIES"],
    retry_delay_seconds=CONFIG["TASK_RETRY_DELAY_SEC"],
    tags=["io", "google-sheets", "logging"],
)
def write_automation_log(
    start_time    : datetime,
    end_time      : datetime,
    data          : dict,
    cleaned       : dict,
    all_anomalies : list[dict],
    status        : str,
    error_msg     : str,
) -> None:
    """
    Tulis 1 baris log per sheet ke AUTOMATION_LOG.

    Kolom sesuai persis struktur sheet WasteX:
      Run_Timestamp, Sheet_Processed, Records_In, Records_Clean,
      Records_Flagged, Errors_Comma_Decimal, Errors_Negative,
      Errors_Missing_Critical, Errors_Duplicate_Bag, Errors_Orphan_Bag,
      Errors_Weight_Discrepancy, Errors_Future_Date,
      Errors_Invalid_Category, Action_Taken, Notes

    Note: TYPE 9 (batch sum mismatch) dan TYPE 10 (bag multi-application)
    tidak punya kolom khusus di sheet → masuk ke kolom Notes.
    """
    log = get_run_logger()
    log.info("Writing ke AUTOMATION_LOG...")

    ss = get_spreadsheet()
    ws = ss.worksheet(CONFIG["SHEET_LOG"])

    # Header sesuai persis struktur sheet yang diminta
    headers = [
        "Run_Timestamp",
        "Sheet_Processed",
        "Records_In",
        "Records_Clean",
        "Records_Flagged",
        "Errors_Comma_Decimal",
        "Errors_Negative",
        "Errors_Missing_Critical",
        "Errors_Duplicate_Bag",
        "Errors_Orphan_Bag",
        "Errors_Weight_Discrepancy",
        "Errors_Future_Date",
        "Errors_Invalid_Category",
        "Action_Taken",
        "Notes",
    ]

    # Baris 1 = deskripsi (tidak diubah), tulis header di baris 2
    ws.update("A2", [headers])
    log.info("  Header AUTOMATION_LOG ditulis di baris 2")

    # Mapping sheet name → data key
    sheet_configs = [
        ("biochar_production",  data.get("biochar_prod", []),  cleaned.get("biochar_prod", [])),
        ("bag_production",      data.get("bag_prod", []),      cleaned.get("bag_prod", [])),
        ("biochar_application", data.get("biochar_app", []),   cleaned.get("biochar_app", [])),
        ("bag_application",     data.get("bag_app", []),       cleaned.get("bag_app", [])),
    ]

    log_rows = []
    for sheet_name, raw_rows, clean_rows in sheet_configs:
        # Filter anomali yang berasal dari sheet ini
        sheet_anom = [a for a in all_anomalies if a["Sheet"].startswith(sheet_name)]

        def count_type(t: str) -> int:
            return len([a for a in sheet_anom if a["anomaly_type"] == t])

        # Hitung records
        records_in      = len(raw_rows)
        records_clean   = len(clean_rows)
        records_flagged = len([a for a in sheet_anom if a["anomaly_type"] != "TYPE 1"])

        # Hitung per tipe anomali sesuai kolom sheet
        err_comma_decimal    = count_type("TYPE 1")
        err_negative         = count_type("TYPE 2")
        err_missing_critical = count_type("TYPE 3")
        err_duplicate_bag    = count_type("TYPE 4")
        err_future_date      = count_type("TYPE 5")
        err_invalid_category = count_type("TYPE 6")
        err_orphan_bag       = count_type("TYPE 7")
        err_weight_disc      = count_type("TYPE 8")
        # TYPE 9 dan TYPE 10 tidak ada kolom → masuk Notes
        err_batch_mismatch   = count_type("TYPE 9")
        err_multi_app        = count_type("TYPE 10")

        # Action taken: ringkasan tindakan
        actions = []
        if err_comma_decimal > 0:
            actions.append(f"{err_comma_decimal} comma decimal auto-fixed")
        if records_flagged > 0:
            actions.append(f"{records_flagged} rows flagged ke VALIDATION_QUEUE")
        if records_in - records_clean > 0:
            actions.append(f"{records_in - records_clean} rows excluded dari CLEANED")
        if status == "ERROR":
            actions.append(f"ERROR: {error_msg}")
        action_taken = "; ".join(actions) if actions else "No anomalies — data passed clean"

        # Notes: TYPE 9 dan 10 di sini
        notes_parts = []
        if err_batch_mismatch > 0:
            notes_parts.append(f"TYPE 9 batch sum mismatch: {err_batch_mismatch} finding(s)")
        if err_multi_app > 0:
            notes_parts.append(f"TYPE 10 bag multi-application: {err_multi_app} finding(s)")
        notes = "; ".join(notes_parts) if notes_parts else ""

        log_rows.append([
            start_time.strftime("%Y-%m-%d %H:%M:%S"),
            sheet_name,
            records_in,
            records_clean,
            records_flagged,
            err_comma_decimal,
            err_negative,
            err_missing_critical,
            err_duplicate_bag,
            err_orphan_bag,
            err_weight_disc,
            err_future_date,
            err_invalid_category,
            action_taken,
            notes,
        ])

        log.info(
            f"  {sheet_name}: in={records_in} clean={records_clean} "
            f"flagged={records_flagged}"
        )

    if log_rows:
        all_values = ws.get_all_values()
        # Hitung baris non-kosong setelah baris 2 (header)
        data_rows = [r for r in all_values[2:] if any(c.strip() for c in r)]
        next_row  = len(data_rows) + 3  # +3: baris 1 deskripsi + baris 2 header + 1-based
        ws.insert_rows(log_rows, row=next_row)

    log.info(f"  \u2713 {len(log_rows)} baris log ditulis ke AUTOMATION_LOG")
