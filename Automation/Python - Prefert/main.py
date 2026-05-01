"""
WasteX Data Pipeline — Main Flow (Prefect)
============================================
Entry point dan flow utama yang mengorkestrasi semua task.

Cara jalankan:
    # Test sekali langsung
    python main.py

    # Deploy ke Prefect Cloud dengan schedule harian jam 07:00
    prefect deploy main.py:wastex_pipeline \\
        --name "WasteX Daily Pipeline" \\
        --cron "0 7 * * *" \\
        --pool "default-agent-pool"

    # Jalankan worker (terminal terpisah)
    prefect worker start --pool "default-agent-pool"

Struktur task (19 task total):
    Task  1 : load_data
    Task  2 : build_lookup_maps
    Task  3 : detect_type1  (TYPE 1 — auto-fix)
    Task  4 : detect_type2  (TYPE 2 — negative values)
    Task  5 : detect_type3  (TYPE 3 — missing critical fields)
    Task  6 : detect_type4  (TYPE 4 — duplicate bag_id)
    Task  7 : detect_type5  (TYPE 5 — future timestamps)
    Task  8 : detect_type6  (TYPE 6 — invalid application_type)
    Task  9 : detect_type7  (TYPE 7 — orphan bag_id)
    Task 10 : detect_type8  (TYPE 8 — weight discrepancy)
    Task 11 : detect_type9  (TYPE 9 — batch sum mismatch)
    Task 12 : detect_type10 (TYPE 10 — bag multi-application)
    Task 13 : merge_anomalies
    Task 14 : build_cleaned
    Task 15 : write_cleaned_sheets
    Task 16 : write_validation_queue
    Task 17 : write_automation_log
    Task 18 : create_run_report
    Task 19 : send_email_notification
"""

from datetime import datetime
from prefect import flow, get_run_logger

from loader import load_data, build_lookup_maps
from detection import (
    detect_type1, detect_type2, detect_type3, detect_type4, detect_type5,
    detect_type6, detect_type7, detect_type8, detect_type9, detect_type10,
)
from cleaning import merge_anomalies, build_cleaned
from writer import write_cleaned_sheets, write_validation_queue, write_automation_log
from notifier import create_run_report, send_email_notification


# ─────────────────────────────────────────────────────────
# MAIN FLOW
# ─────────────────────────────────────────────────────────
@flow(
    name="wastex-daily-pipeline",
    description=(
        "WasteX biochar data cleaning pipeline. "
        "Deteksi 10 tipe anomali, tulis 4 CLEANED sheets, "
        "update VALIDATION_QUEUE, tulis AUTOMATION_LOG, "
        "kirim notifikasi email."
    ),
    log_prints=True,
)
def wastex_pipeline():
    """
    Flow utama — mengorkestrasi 19 task secara berurutan.

    Kenapa berurutan (bukan paralel)?
    - Task 3-12 bergantung pada output Task 1-2 (data + lookup)
    - Task 3 (TYPE 1) harus selesai dulu sebelum Task 4-12
      karena fixed_bag_prod dipakai oleh TYPE 2 dan TYPE 3
    - Task 13-19 bergantung pada semua task sebelumnya

    Prefect tetap memberikan monitoring, retry, dan logging
    per task meski dijalankan berurutan.
    """
    log        = get_run_logger()
    start_time = datetime.now()

    log.info("=" * 55)
    log.info(f"WasteX Pipeline dimulai: {start_time}")
    log.info("=" * 55)

    # ── Task 1: Load data dari Google Sheets ──────────────
    data = load_data()

    # ── Task 2: Build lookup maps untuk cross-sheet checks ─
    lookup = build_lookup_maps(data)

    # ── Task 3: TYPE 1 — Comma decimal (+ auto-fix) ───────
    # Return tuple: (anomalies, fixed_bag_prod)
    t1_result              = detect_type1(data)
    t1_anomalies           = t1_result[0]
    fixed_bag_prod         = t1_result[1]

    # ── Task 4-12: Deteksi TYPE 2 s/d TYPE 10 ─────────────
    # fixed_bag_prod dipakai TYPE 2 dan TYPE 3
    # lookup dipakai TYPE 4, 7, 8, 9, 10
    t2  = detect_type2(data, fixed_bag_prod)
    t3  = detect_type3(data, fixed_bag_prod)
    t4  = detect_type4(data, lookup)
    t5  = detect_type5(data)
    t6  = detect_type6(data)
    t7  = detect_type7(data, lookup)
    t8  = detect_type8(data, lookup)
    t9  = detect_type9(data, lookup)
    t10 = detect_type10(data, lookup)

    # ── Task 13: Gabungkan semua anomali ──────────────────
    all_anomalies = merge_anomalies(
        t1_anomalies, t2, t3, t4, t5, t6, t7, t8, t9, t10
    )

    # ── Task 14: Build cleaned dataset ────────────────────
    cleaned = build_cleaned(data, fixed_bag_prod, all_anomalies)

    # ── Task 15: Tulis 4 CLEANED sheets ───────────────────
    write_cleaned_sheets(cleaned)

    # ── Task 16: Tulis VALIDATION_QUEUE ───────────────────
    new_count = write_validation_queue(all_anomalies)

    # ── Task 17: Tulis AUTOMATION_LOG ─────────────────────
    end_time = datetime.now()
    write_automation_log(
        start_time    = start_time,
        end_time      = end_time,
        data          = data,
        cleaned       = cleaned,
        all_anomalies = all_anomalies,
        status        = "SUCCESS",
        error_msg     = "",
    )

    # ── Task 18: Buat laporan di Prefect UI ───────────────
    create_run_report(
        all_anomalies = all_anomalies,
        cleaned       = cleaned,
        data          = data,
        new_count     = new_count,
        start_time    = start_time,
        end_time      = end_time,
    )

    # ── Task 19: Kirim email notifikasi ───────────────────
    send_email_notification(
        all_anomalies = all_anomalies,
        new_count     = new_count,
        start_time    = start_time,
    )

    log.info("=" * 55)
    log.info(f"Pipeline selesai: {datetime.now()}")
    log.info(f"Total anomali   : {len(all_anomalies)}")
    log.info(f"Anomali baru    : {new_count}")
    log.info("=" * 55)


# ─────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    wastex_pipeline()
