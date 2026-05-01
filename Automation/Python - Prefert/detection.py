"""
WasteX Pipeline — Tasks: Anomaly Detection
============================================
10 task deteksi anomali, masing-masing 1 file section.
Setiap task independen dan bisa di-monitor terpisah di Prefect UI.

TYPE 1  — Comma decimal separator          (bag_production)
TYPE 2  — Negative values                  (bag_production, biochar_production)
TYPE 3  — Missing critical fields          (bag_production, biochar_production)
TYPE 4  — Duplicate bag_id                 (bag_production)
TYPE 5  — Future timestamps / dates        (all sheets)
TYPE 6  — Invalid application_type         (biochar_application)
TYPE 7  — Orphan bag_id                    (cross-sheet)
TYPE 8  — Weight discrepancy >5%           (cross-sheet)
TYPE 9  — Batch sum mismatch               (cross-sheet)
TYPE 10 — Bag in multiple application batches (cross-sheet)
"""

import copy
from datetime import date, datetime
from prefect import task, get_run_logger

from config import CONFIG
from helpers import to_float, to_date, is_empty, make_anomaly


# ─────────────────────────────────────────────────────────
# TASK 3 — TYPE 1: COMMA DECIMAL SEPARATOR
# ─────────────────────────────────────────────────────────
@task(
    name="detect-type1-comma-decimal",
    description="TYPE 1: Deteksi dan auto-fix comma decimal di bag_production.weight",
    retries=CONFIG["TASK_RETRIES"],
    retry_delay_seconds=CONFIG["TASK_RETRY_DELAY_SEC"],
    tags=["anomaly-detection", "auto-fix"],
)
def detect_type1(data: dict) -> tuple[list[dict], list[dict]]:
    """
    Scan bag_production.weight untuk nilai dengan koma sebagai desimal.
    Contoh: '18,15' seharusnya 18.15

    Auto-fix: nilai langsung diperbaiki di fixed_bag_prod.
    Record tetap masuk CLEANED sheets (tidak di-exclude).

    Return:
        anomalies     : list anomali untuk VALIDATION_QUEUE
        fixed_bag_prod: bag_production dengan weight sudah di-fix
    """
    log        = get_run_logger()
    anomalies  = []
    fixed_rows = copy.deepcopy(data["bag_prod"])

    log.info("TYPE 1 — Scanning comma decimal separator di bag_production.weight...")

    for i, row in enumerate(fixed_rows):
        w = str(row.get("weight", ""))
        if "," in w:
            fixed_w = float(w.replace(",", "."))
            anomalies.append(make_anomaly(
                "bag_production", "TYPE 1",
                f'Comma decimal separator: "{w}" → {fixed_w}',
                "weight", w, str(fixed_w),
                "AUTO-FIXED → CLEANED",
                row.get("bag_id", ""),
            ))
            fixed_rows[i]["weight"] = fixed_w
            log.info(f'  AUTO-FIXED: bag_id={row.get("bag_id")} weight "{w}" → {fixed_w}')

    log.info(f"TYPE 1: {len(anomalies)} finding(s) — semua di-auto-fix")
    return anomalies, fixed_rows


# ─────────────────────────────────────────────────────────
# TASK 4 — TYPE 2: NEGATIVE VALUES
# ─────────────────────────────────────────────────────────
@task(
    name="detect-type2-negative-values",
    description="TYPE 2: Deteksi nilai negatif di weight/co2e/spc",
    retries=CONFIG["TASK_RETRIES"],
    retry_delay_seconds=CONFIG["TASK_RETRY_DELAY_SEC"],
    tags=["anomaly-detection"],
)
def detect_type2(data: dict, fixed_bag_prod: list[dict]) -> list[dict]:
    """
    Field yang dicek:
      - bag_production      : weight, co2e_persistent, co2e_100, spc
      - biochar_production  : co2e_persistent, co2e_100, spc

    Semua field ini secara fisik tidak mungkin negatif.
    Nilai negatif = error input operator.
    """
    log       = get_run_logger()
    anomalies = []

    neg_fields_bag  = ["weight", "co2e_persistent", "co2e_100", "spc"]
    neg_fields_prod = ["co2e_persistent", "co2e_100", "spc"]

    log.info("TYPE 2 — Scanning negative values...")

    # Cek bag_production (pakai fixed_bag_prod supaya weight sudah di-fix TYPE 1)
    for row in fixed_bag_prod:
        for field in neg_fields_bag:
            val = to_float(row.get(field))
            if val is not None and val < 0:
                anomalies.append(make_anomaly(
                    "bag_production", "TYPE 2",
                    f"Negative value in non-negative field: {field}={val}",
                    field, val, "Requires human review — nilai tidak mungkin negatif",
                    "FLAGGED → VALIDATION_QUEUE",
                    row.get("bag_id", ""),
                ))
                log.warning(f'  bag_id={row.get("bag_id")} {field}={val}')

    # Cek biochar_production
    for row in data["biochar_prod"]:
        for field in neg_fields_prod:
            val = to_float(row.get(field))
            if val is not None and val < 0:
                anomalies.append(make_anomaly(
                    "biochar_production", "TYPE 2",
                    f"Negative value in non-negative field: {field}={val}",
                    field, val, "Requires human review — nilai tidak mungkin negatif",
                    "FLAGGED → VALIDATION_QUEUE",
                    row.get("activity_id", ""),
                ))
                log.warning(f'  activity_id={row.get("activity_id")} {field}={val}')

    log.info(f"TYPE 2: {len(anomalies)} finding(s)")
    return anomalies


# ─────────────────────────────────────────────────────────
# TASK 5 — TYPE 3: MISSING CRITICAL FIELDS
# ─────────────────────────────────────────────────────────
@task(
    name="detect-type3-missing-critical-fields",
    description="TYPE 3: Deteksi nilai kosong di weight dan carbon_content_%",
    retries=CONFIG["TASK_RETRIES"],
    retry_delay_seconds=CONFIG["TASK_RETRY_DELAY_SEC"],
    tags=["anomaly-detection"],
)
def detect_type3(data: dict, fixed_bag_prod: list[dict]) -> list[dict]:
    """
    Field yang wajib diisi (tidak boleh kosong):
      - bag_production.weight
      - biochar_production.carbon_content_%

    Kedua field ini kritikal untuk perhitungan CO2e dan carbon sequestration.
    Kosong = data tidak bisa diproses untuk reporting.
    """
    log       = get_run_logger()
    anomalies = []

    log.info("TYPE 3 — Scanning missing critical fields...")

    # bag_production.weight
    for row in fixed_bag_prod:
        if is_empty(row.get("weight")):
            anomalies.append(make_anomaly(
                "bag_production", "TYPE 3",
                "Missing critical field: weight is empty",
                "weight", "", "Requires human review — timbang ulang bag jika memungkinkan",
                "FLAGGED → VALIDATION_QUEUE",
                row.get("bag_id", ""),
            ))
            log.warning(f'  bag_id={row.get("bag_id")} weight is empty')

    # biochar_production.carbon_content_%
    for row in data["biochar_prod"]:
        if is_empty(row.get("carbon_content_%")):
            anomalies.append(make_anomaly(
                "biochar_production", "TYPE 3",
                "Missing critical field: carbon_content_% is empty",
                "carbon_content_%", "", "Requires human review — lakukan analisis lab ulang jika perlu",
                "FLAGGED → VALIDATION_QUEUE",
                row.get("activity_id", ""),
            ))
            log.warning(f'  activity_id={row.get("activity_id")} carbon_content_% is empty')

    log.info(f"TYPE 3: {len(anomalies)} finding(s)")
    return anomalies


# ─────────────────────────────────────────────────────────
# TASK 6 — TYPE 4: DUPLICATE BAG_ID
# ─────────────────────────────────────────────────────────
@task(
    name="detect-type4-duplicate-bag-id",
    description="TYPE 4: Deteksi bag_id yang muncul lebih dari sekali di bag_production",
    retries=CONFIG["TASK_RETRIES"],
    retry_delay_seconds=CONFIG["TASK_RETRY_DELAY_SEC"],
    tags=["anomaly-detection"],
)
def detect_type4(data: dict, lookup: dict) -> list[dict]:
    """
    Setiap bag_id di bag_production harus unik.
    bag_id yang sama muncul 2x kemungkinan:
      - Double scan oleh operator
      - Bag yang sama ditimbang dua kali dengan berat berbeda

    Routing: keep first occurrence di CLEANED, flag sisanya.
    """
    log          = get_run_logger()
    anomalies    = []
    bag_id_count = lookup["bag_id_count"]

    log.info("TYPE 4 — Scanning duplicate bag_id di bag_production...")

    for row in data["bag_prod"]:
        bid = str(row.get("bag_id", ""))
        if bag_id_count.get(bid, 0) > 1:
            anomalies.append(make_anomaly(
                "bag_production", "TYPE 4",
                f'Duplicate bag_id dengan weight={row.get("weight")}',
                "bag_id", bid,
                "Keep first occurrence; reconcile atau hapus duplikat",
                "FLAGGED → VALIDATION_QUEUE",
                bid,
            ))
            log.warning(f"  Duplicate: bag_id={bid} weight={row.get('weight')}")

    unique_dups = len({a["Record_ID"] for a in anomalies})
    log.info(f"TYPE 4: {len(anomalies)} finding(s) dari {unique_dups} unique bag_id duplikat")
    return anomalies


# ─────────────────────────────────────────────────────────
# TASK 7 — TYPE 5: FUTURE TIMESTAMPS / DATES
# ─────────────────────────────────────────────────────────
@task(
    name="detect-type5-future-timestamps",
    description="TYPE 5: Deteksi Timestamp > hari ini atau application_date suspicious",
    retries=CONFIG["TASK_RETRIES"],
    retry_delay_seconds=CONFIG["TASK_RETRY_DELAY_SEC"],
    tags=["anomaly-detection"],
)
def detect_type5(data: dict) -> list[dict]:
    """
    Dua pengecekan:

    1. Timestamp > today → future timestamp (tidak mungkin ada data masa depan)
       Dicek di semua 4 sheet.

    2. application_date lebih dari MAX_APP_DATE_GAP_DAYS hari setelah Timestamp
       → suspicious: operator tidak mungkin input data sekarang untuk kejadian
       yang baru akan terjadi jauh di masa depan.
       Dicek hanya di biochar_application (satu-satunya sheet dengan application_date).
    """
    log       = get_run_logger()
    anomalies = []
    today     = date.today()
    max_gap   = CONFIG["MAX_APP_DATE_GAP_DAYS"]

    log.info(f"TYPE 5 — Scanning future timestamps (today={today}, max_gap={max_gap}d)...")

    # Cek Timestamp > today di semua 4 sheet
    sheet_ts_configs = [
        ("biochar_production",  data["biochar_prod"], "activity_id"),
        ("bag_production",      data["bag_prod"],     "bag_id"),
        ("biochar_application", data["biochar_app"],  "activity_id"),
        ("bag_application",     data["bag_app"],      "bag_id"),
    ]
    for sheet_name, rows, id_field in sheet_ts_configs:
        for row in rows:
            ts = to_date(row.get("Timestamp"))
            if ts and ts > today:
                rid = row.get(id_field, "")
                anomalies.append(make_anomaly(
                    sheet_name, "TYPE 5",
                    f"Future Timestamp: {row.get('Timestamp')} (today={today})",
                    "Timestamp", str(row.get("Timestamp")),
                    "Requires human review — timestamp tidak boleh melewati hari ini",
                    "FLAGGED → VALIDATION_QUEUE",
                    rid,
                ))
                log.warning(f"  Future Timestamp di {sheet_name}: {row.get('Timestamp')} ({rid})")

    # Cek application_date di biochar_application
    for row in data["biochar_app"]:
        ad  = to_date(row.get("application_date"))
        ts  = to_date(row.get("Timestamp"))
        aid = row.get("activity_id", "")

        # Future application_date (lebih dari hari ini)
        if ad and ad > today:
            anomalies.append(make_anomaly(
                "biochar_application", "TYPE 5",
                f"Future application_date: {ad} (today={today})",
                "application_date", str(ad),
                "Requires human review — application_date tidak boleh melewati hari ini",
                "FLAGGED → VALIDATION_QUEUE",
                aid,
            ))
            log.warning(f"  Future application_date: {ad} ({aid})")

        # Suspicious: application_date jauh lebih lambat dari Timestamp
        if ad and ts:
            gap_days = (ad - ts).days
            if gap_days > max_gap:
                anomalies.append(make_anomaly(
                    "biochar_application", "TYPE 5",
                    (
                        f"Suspicious application_date: {ad} adalah {gap_days} hari "
                        f"setelah Timestamp {ts}. Operator tidak mungkin input data "
                        f"di {ts} untuk kejadian yang baru terjadi {gap_days} hari kemudian."
                    ),
                    "application_date", str(ad),
                    f"Konfirmasi ke operator: apakah application_date {ad} benar? "
                    f"Kemungkinan harusnya sekitar {ts}.",
                    "FLAGGED → VALIDATION_QUEUE",
                    aid,
                ))
                log.warning(f"  Suspicious application_date: {ad} gap={gap_days}d dari Timestamp {ts} ({aid})")

    log.info(f"TYPE 5: {len(anomalies)} finding(s)")
    return anomalies


# ─────────────────────────────────────────────────────────
# TASK 8 — TYPE 6: INVALID APPLICATION TYPE
# ─────────────────────────────────────────────────────────
@task(
    name="detect-type6-invalid-application-type",
    description="TYPE 6: Deteksi application_type yang tidak valid di biochar_application",
    retries=CONFIG["TASK_RETRIES"],
    retry_delay_seconds=CONFIG["TASK_RETRY_DELAY_SEC"],
    tags=["anomaly-detection"],
)
def detect_type6(data: dict) -> list[dict]:
    """
    application_type harus salah satu dari 4 nilai yang valid
    (didefinisikan di CONFIG['VALID_APP_TYPES']).

    Nilai lain = typo atau jenis baru yang belum terdaftar di sistem.
    """
    log         = get_run_logger()
    anomalies   = []
    valid_types = CONFIG["VALID_APP_TYPES"]

    log.info("TYPE 6 — Scanning invalid application_type di biochar_application...")
    log.info(f"  Valid types: {valid_types}")

    for row in data["biochar_app"]:
        at  = str(row.get("application_type", ""))
        aid = row.get("activity_id", "")
        if at not in valid_types:
            anomalies.append(make_anomaly(
                "biochar_application", "TYPE 6",
                f'Invalid application_type: "{at}"',
                "application_type", at,
                f"Harus salah satu dari: {valid_types}",
                "FLAGGED → VALIDATION_QUEUE",
                aid,
            ))
            log.warning(f'  activity_id={aid} application_type="{at}"')

    log.info(f"TYPE 6: {len(anomalies)} finding(s)")
    return anomalies


# ─────────────────────────────────────────────────────────
# TASK 9 — TYPE 7: ORPHAN BAG_ID
# ─────────────────────────────────────────────────────────
@task(
    name="detect-type7-orphan-bag-id",
    description="TYPE 7: Deteksi bag_id di bag_application yang tidak ada di bag_production",
    retries=CONFIG["TASK_RETRIES"],
    retry_delay_seconds=CONFIG["TASK_RETRY_DELAY_SEC"],
    tags=["anomaly-detection", "cross-sheet"],
)
def detect_type7(data: dict, lookup: dict) -> list[dict]:
    """
    Key Rule dari brief: bag_id di bag_application HARUS ada di bag_production.
    Kalau tidak ada = orphan bag = data aplikasi yang tidak punya produksi terkait.

    Kemungkinan penyebab:
      - Salah ketik bag_id saat input
      - Bag dari batch produksi yang belum diinput ke sistem
    """
    log             = get_run_logger()
    anomalies       = []
    bag_prod_id_set = set(lookup["bag_prod_id_set"])

    log.info("TYPE 7 — Scanning orphan bag_id di bag_application...")

    for row in data["bag_app"]:
        bid = str(row.get("bag_id", ""))
        if bid and bid not in bag_prod_id_set:
            anomalies.append(make_anomaly(
                "bag_application", "TYPE 7",
                f"Orphan bag_id: {bid} tidak ditemukan di bag_production",
                "bag_id", bid,
                "Tidak ada production record yang cocok — cek apakah bag_id salah ketik",
                "FLAGGED → VALIDATION_QUEUE",
                bid,
            ))
            log.warning(f"  Orphan bag_id={bid}")

    log.info(f"TYPE 7: {len(anomalies)} finding(s)")
    return anomalies


# ─────────────────────────────────────────────────────────
# TASK 10 — TYPE 8: WEIGHT DISCREPANCY
# ─────────────────────────────────────────────────────────
@task(
    name="detect-type8-weight-discrepancy",
    description="TYPE 8: Deteksi selisih berat >5% antara bag_application dan bag_production",
    retries=CONFIG["TASK_RETRIES"],
    retry_delay_seconds=CONFIG["TASK_RETRY_DELAY_SEC"],
    tags=["anomaly-detection", "cross-sheet"],
)
def detect_type8(data: dict, lookup: dict) -> list[dict]:
    """
    Bandingkan bag_weight di bag_application dengan weight di bag_production.
    Selisih > 5% = anomali.

    Berat bag seharusnya konsisten antara catatan produksi dan aplikasi.
    Selisih besar kemungkinan:
      - Timbangan berbeda di dua lokasi
      - Human error saat input
      - Sebagian isi bag tumpah/berkurang saat transport
    """
    log                 = get_run_logger()
    anomalies           = []
    bag_prod_weight_map = lookup["bag_prod_weight_map"]
    threshold           = CONFIG["WEIGHT_DISCREPANCY_PCT"]

    log.info(f"TYPE 8 — Scanning weight discrepancy (threshold={threshold:.0%})...")

    for row in data["bag_app"]:
        bid    = str(row.get("bag_id", ""))
        app_w  = to_float(row.get("bag_weight"))
        prod_w = bag_prod_weight_map.get(bid)

        if app_w is not None and prod_w is not None:
            disc = abs(app_w - prod_w) / prod_w
            if disc > threshold:
                anomalies.append(make_anomaly(
                    "bag_application", "TYPE 8",
                    f"Weight discrepancy {disc:.1%}: bag_app={app_w:.2f} kg vs bag_prod={prod_w:.2f} kg",
                    "bag_weight", app_w,
                    f"Berat di produksi={prod_w:.2f} kg. Rekonsiliasi diperlukan.",
                    "FLAGGED → VALIDATION_QUEUE",
                    bid,
                ))
                log.warning(f"  bag_id={bid} discrepancy={disc:.1%} (app={app_w:.2f} prod={prod_w:.2f})")

    log.info(f"TYPE 8: {len(anomalies)} finding(s)")
    return anomalies


# ─────────────────────────────────────────────────────────
# TASK 11 — TYPE 9: BATCH SUM MISMATCH
# ─────────────────────────────────────────────────────────
@task(
    name="detect-type9-batch-sum-mismatch",
    description="TYPE 9: Deteksi jumlah berat bag ≠ biochar_amount_kg di production batch",
    retries=CONFIG["TASK_RETRIES"],
    retry_delay_seconds=CONFIG["TASK_RETRY_DELAY_SEC"],
    tags=["anomaly-detection", "cross-sheet"],
)
def detect_type9(data: dict, lookup: dict) -> list[dict]:
    """
    Sum semua bag weight per production_id, bandingkan dengan
    biochar_amount_kg yang dideklarasikan di biochar_production.

    Selisih > tolerance (0.01 kg) = anomali.

    Kemungkinan penyebab:
      - Ada bag yang belum diinput ke sistem
      - biochar_amount_kg di-input salah oleh operator
      - Ada bag duplikat yang menggembungkan sum
    """
    log        = get_run_logger()
    anomalies  = []
    batch_sums = lookup["batch_sums"]
    tolerance  = CONFIG["BATCH_SUM_TOLERANCE_KG"]

    log.info(f"TYPE 9 — Scanning batch sum mismatch (tolerance={tolerance} kg)...")

    for row in data["biochar_prod"]:
        pid      = str(row.get("activity_id", ""))
        declared = to_float(row.get("biochar_amount_kg"))
        bag_sum  = batch_sums.get(pid)

        if bag_sum is not None and declared is not None:
            diff = abs(bag_sum - declared)
            if diff > tolerance:
                anomalies.append(make_anomaly(
                    "bag_production", "TYPE 9",
                    f"Batch sum mismatch: sum_bags={bag_sum:.2f} kg vs declared={declared:.2f} kg (Δ={diff:.2f} kg)",
                    "biochar_amount_kg vs sum(bag weights)",
                    f"bags_sum={bag_sum:.2f}",
                    f"Declared={declared:.2f} kg. Rekonsiliasi bag weights atau biochar_amount_kg.",
                    "FLAGGED → VALIDATION_QUEUE",
                    pid,
                ))
                log.warning(f"  production_id={pid}: sum={bag_sum:.2f} declared={declared:.2f} Δ={diff:.2f}")

    log.info(f"TYPE 9: {len(anomalies)} finding(s)")
    return anomalies


# ─────────────────────────────────────────────────────────
# TASK 12 — TYPE 10: BAG IN MULTIPLE APPLICATION BATCHES
# ─────────────────────────────────────────────────────────
@task(
    name="detect-type10-bag-in-multiple-applications",
    description="TYPE 10: Deteksi bag_id yang dipakai di lebih dari satu application batch",
    retries=CONFIG["TASK_RETRIES"],
    retry_delay_seconds=CONFIG["TASK_RETRY_DELAY_SEC"],
    tags=["anomaly-detection", "cross-sheet"],
)
def detect_type10(data: dict, lookup: dict) -> list[dict]:
    """
    Key Rule dari brief: satu bag_id hanya boleh muncul di SATU application batch.
    Bag yang sama dipakai di 2+ batch = data integrity violation.

    Kemungkinan penyebab:
      - Operator scan bag yang sama dua kali di event berbeda
      - Copy-paste error saat input data
    """
    log         = get_run_logger()
    anomalies   = []
    bag_app_map = lookup["bag_app_map"]

    log.info("TYPE 10 — Scanning bag yang dipakai di multiple application batches...")

    for row in data["bag_app"]:
        bid     = str(row.get("bag_id", ""))
        app_ids = bag_app_map.get(bid, [])
        if len(app_ids) > 1:
            anomalies.append(make_anomaly(
                "bag_application", "TYPE 10",
                f"Bag dipakai di {len(app_ids)} application batches: {sorted(app_ids)}",
                "bag_id / application_id", bid,
                "Satu bag_id hanya boleh muncul di SATU application batch.",
                "FLAGGED → VALIDATION_QUEUE",
                bid,
            ))
            log.warning(f"  bag_id={bid} muncul di {len(app_ids)} batches: {sorted(app_ids)}")

    unique_bags = len({a["Record_ID"] for a in anomalies})
    log.info(f"TYPE 10: {len(anomalies)} finding(s) dari {unique_bags} unique bag_id")
    return anomalies
