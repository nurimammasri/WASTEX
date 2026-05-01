"""
WasteX Pipeline — Helper Functions
====================================
Fungsi-fungsi kecil yang dipakai bersama oleh semua task.
Dipisah ke sini supaya tidak ada duplikasi kode di task files.
"""

from datetime import datetime, date


def to_float(val) -> float | None:
    """
    Konversi nilai ke float.
    Handles: string dengan koma ('18,15'), None, kosong.
    Return None kalau tidak bisa dikonversi.
    """
    try:
        return float(str(val).replace(",", ".").strip())
    except (ValueError, TypeError):
        return None


def to_date(val) -> date | None:
    """
    Konversi nilai ke date object.
    Handles: datetime, date, string format 'YYYY-MM-DD'.
    Return None kalau tidak bisa dikonversi.
    """
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    try:
        return datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def is_empty(val) -> bool:
    """
    Cek apakah nilai kosong/null.
    Handles: None, string kosong, 'nan', 'None', 'NaN'.
    """
    return val is None or str(val).strip().lower() in ("", "nan", "none", "nat")


def make_anomaly(
    sheet      : str,
    atype      : str,
    desc       : str,
    field      : str,
    orig_val,
    fix        : str,
    action     : str,
    record_id  : str,
) -> dict:
    """
    Buat dict anomali dengan struktur yang konsisten.
    Dipakai oleh semua detect_type* tasks untuk menghasilkan
    format yang seragam sebelum ditulis ke VALIDATION_QUEUE.

    Struktur output:
        Sheet           : nama sheet sumber anomali
        anomaly_type    : TYPE 1 s/d TYPE 10
        description     : penjelasan detail anomali
        Field           : nama kolom yang bermasalah
        original_value  : nilai asli sebelum fix
        suggested_fix   : saran perbaikan
        action          : AUTO-FIXED atau FLAGGED
        Record_ID       : bag_id / activity_id
        detected_at     : timestamp deteksi
        Reviewed_By     : (kosong, diisi reviewer)
        Resolution      : (kosong, diisi reviewer)
        Resolved_At     : (kosong, diisi reviewer)
    """
    return {
        "Sheet"         : sheet,
        "anomaly_type"  : atype,
        "description"   : desc,
        "Field"         : field,
        "original_value": str(orig_val),
        "suggested_fix" : str(fix),
        "action"        : action,
        "Record_ID"     : str(record_id),
        "detected_at"   : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Reviewed_By"   : "",
        "Resolution"    : "",
        "Resolved_At"   : "",
    }
