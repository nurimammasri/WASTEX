"""
WasteX Pipeline — Tasks: Notifier
===================================
Task untuk:
  - create_run_report        : buat laporan HTML di Prefect UI (Artifacts)
  - send_email_notification  : kirim email kalau ada anomali baru
"""

import smtplib
from collections import Counter
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from prefect import task, get_run_logger
from prefect.artifacts import create_markdown_artifact

from config import CONFIG


# ─────────────────────────────────────────────────────────
# TASK 18 — CREATE PREFECT ARTIFACT (Laporan di UI)
# ─────────────────────────────────────────────────────────
@task(
    name="create-run-report",
    description="Buat laporan Markdown yang tampil di Prefect UI tab Artifacts setiap run",
    tags=["reporting"],
)
def create_run_report(
    all_anomalies : list[dict],
    cleaned       : dict,
    data          : dict,
    new_count     : int,
    start_time    : datetime,
    end_time      : datetime,
) -> None:
    """
    Buat Prefect Artifact berupa laporan Markdown.
    Laporan ini bisa dilihat langsung di Prefect UI → tab 'Artifacts'
    tanpa perlu buka Google Sheets atau log file.

    Isi laporan:
      - Summary run (waktu, durasi, total anomali)
      - Tabel anomali per tipe
      - Tabel cleaned sheets (before vs after)
      - Detail 10 anomali teratas yang butuh review
    """
    log          = get_run_logger()
    type_counts  = Counter(a["anomaly_type"] for a in all_anomalies)
    duration_sec = int((end_time - start_time).total_seconds())
    flagged      = [a for a in all_anomalies if "VALIDATION_QUEUE" in a["action"]]
    auto_fixed   = [a for a in all_anomalies if "AUTO-FIXED" in a["action"]]

    # Tabel anomali per tipe
    type_rows = "\n".join(
        f"| {t} | {c} | {'✅ Auto-fixed' if t == 'TYPE 1' else '⚠️ Needs review'} |"
        for t, c in sorted(type_counts.items())
    ) or "| — | Tidak ada anomali | — |"

    # Tabel cleaned sheets
    sheet_rows = "\n".join([
        f"| CLEANED_prod_batch | {len(cleaned.get('biochar_prod', []))} | {len(data.get('biochar_prod', []))} |",
        f"| CLEANED_bag_prod   | {len(cleaned.get('bag_prod', []))}    | {len(data.get('bag_prod', []))} |",
        f"| CLEANED_app_batch  | {len(cleaned.get('biochar_app', []))} | {len(data.get('biochar_app', []))} |",
        f"| CLEANED_bag_app    | {len(cleaned.get('bag_app', []))}     | {len(data.get('bag_app', []))} |",
    ])

    # Detail 10 anomali teratas yang butuh review
    detail_rows = ""
    for a in flagged[:10]:
        desc = a["description"]
        if len(desc) > 70:
            desc = desc[:67] + "..."
        detail_rows += f"| {a['anomaly_type']} | {a['Sheet']} | {a['Record_ID']} | {desc} |\n"
    if not detail_rows:
        detail_rows = "| — | Tidak ada anomali yang perlu review | — | — |\n"
    if len(flagged) > 10:
        detail_rows += f"| ... | dan {len(flagged) - 10} anomali lainnya | ... | ... |\n"

    markdown = f"""
# WasteX Pipeline Run Report

| | |
|---|---|
| **Run time** | {start_time.strftime('%Y-%m-%d %H:%M:%S')} |
| **Duration** | {duration_sec} seconds |
| **Total anomali ditemukan** | {len(all_anomalies)} |
| **Anomali baru di queue** | {new_count} |
| **Auto-fixed (TYPE 1)** | {len(auto_fixed)} record(s) |
| **Butuh review manusia** | {len(flagged)} record(s) |

---

## Anomaly Summary per Tipe

| Type | Count | Status |
|------|-------|--------|
{type_rows}

---

## Cleaned Sheets — Before vs After

| Sheet | Rows Cleaned | Rows Raw |
|-------|-------------|---------|
{sheet_rows}

---

## Top 10 Anomali yang Butuh Review

| Type | Sheet | Record ID | Description |
|------|-------|-----------|-------------|
{detail_rows}
> Lihat VALIDATION_QUEUE di Google Sheets untuk detail lengkap dan lakukan review.

---

*Report ini dibuat otomatis oleh WasteX Prefect Pipeline pada {start_time.strftime('%Y-%m-%d %H:%M:%S')}.*
    """.strip()

    create_markdown_artifact(
        key="wastex-pipeline-report",
        markdown=markdown,
        description=f"WasteX Pipeline Report — {start_time.strftime('%Y-%m-%d')} | {len(all_anomalies)} anomali",
    )
    log.info("✓ Prefect artifact report berhasil dibuat — cek tab Artifacts di Prefect UI")


# ─────────────────────────────────────────────────────────
# TASK 19 — SEND EMAIL NOTIFICATION
# ─────────────────────────────────────────────────────────
@task(
    name="send-email-notification",
    description="Kirim email notifikasi ke tim kalau ada anomali baru ditemukan",
    retries=1,          # Retry sekali saja untuk email — tidak kritis
    retry_delay_seconds=60,
    tags=["notification"],
)
def send_email_notification(
    all_anomalies : list[dict],
    new_count     : int,
    start_time    : datetime,
) -> None:
    """
    Kirim email ke NOTIFICATION_EMAIL dengan ringkasan anomali baru.

    Email berisi:
      - Jumlah anomali baru
      - Ringkasan per tipe anomali
      - Preview 5 anomali pertama
      - Instruksi untuk reviewer

    Note: Kegagalan kirim email TIDAK mematikan pipeline.
    Error di-log tapi tidak di-raise supaya pipeline tetap SUCCESS.
    """
    log = get_run_logger()

    if new_count == 0:
        log.info("Tidak ada anomali baru — email tidak dikirim")
        return

    flagged    = [a for a in all_anomalies if "VALIDATION_QUEUE" in a["action"]]
    auto_fixed = [a for a in all_anomalies if "AUTO-FIXED" in a["action"]]

    # Ringkasan per tipe
    type_counts   = Counter(a["anomaly_type"] for a in flagged)
    summary_lines = "\n".join(
        f"  • {t}: {c} finding(s)"
        for t, c in sorted(type_counts.items())
    )

    # Preview 5 anomali pertama
    preview = ""
    for a in flagged[:5]:
        preview += f"\n  [{a['anomaly_type']}] {a['Sheet']} | ID: {a['Record_ID']}"
        preview += f"\n  → {a['description']}\n"
    if len(flagged) > 5:
        preview += f"\n  ... dan {len(flagged) - 5} anomali lainnya di VALIDATION_QUEUE"

    subject = f"[WasteX Pipeline] {new_count} anomali baru ditemukan — {start_time.strftime('%d %b %Y')}"

    body = f"""
WasteX Data Pipeline — Laporan Otomatis
=========================================
Run time           : {start_time.strftime('%Y-%m-%d %H:%M:%S')}
Anomali baru       : {new_count}
Auto-fixed (TYPE 1): {len(auto_fixed)} record(s)
Butuh review       : {len(flagged)} record(s)

RINGKASAN ANOMALI PER TIPE:
{summary_lines}

PREVIEW ANOMALI:
{preview}

ACTION REQUIRED:
Buka VALIDATION_QUEUE di Google Sheet dan isi kolom berikut untuk setiap anomali:
  - Reviewed_By  : nama reviewer
  - Resolution   : approved / rejected / corrected
  - Resolved_At  : tanggal selesai review

---
Email ini dikirim otomatis oleh WasteX Prefect Pipeline.
Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """.strip()

    try:
        msg             = MIMEMultipart()
        msg["From"]     = CONFIG["EMAIL_SENDER"]
        msg["To"]       = CONFIG["NOTIFICATION_EMAIL"]
        msg["Subject"]  = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(CONFIG["EMAIL_SENDER"], CONFIG["EMAIL_PASSWORD"])
            server.sendmail(CONFIG["EMAIL_SENDER"], CONFIG["NOTIFICATION_EMAIL"], msg.as_string())

        log.info(f"✓ Email berhasil dikirim ke {CONFIG['NOTIFICATION_EMAIL']}")

    except Exception as e:
        # Email failure tidak boleh matikan pipeline
        log.error(f"Gagal kirim email (pipeline tetap lanjut): {str(e)}")
