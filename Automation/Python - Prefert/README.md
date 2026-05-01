# WasteX Automated Data Pipeline — Dokumentasi Lengkap

> **Terakhir diperbarui:** Mei 2026  
> **Author:** Data Analyst — WasteX

---

# 🌿 Overview Proyek

**WasteX** adalah sistem pelacakan produksi biochar dari berbagai bahan baku pertanian
(sekam padi, tongkol jagung, limbah kayu, batang singkong) hingga tahap aplikasi dan penjualan.

Pipeline ini adalah sistem **otomasi pembersihan data harian** yang:

1. Membaca 4 sheet data mentah dari Google Sheets
2. Mendeteksi 10 tipe anomali secara otomatis
3. Menulis data bersih ke sheet CLEANED\_\*
4. Mencatat semua anomali ke VALIDATION\_QUEUE
5. Menulis log eksekusi ke AUTOMATION\_LOG
6. Mengirim notifikasi email jika ada anomali baru

---

# 📁 Struktur File

```
Python - Prefert/
│
├── main.py                  ← Entry point utama, mendefinisikan Prefect Flow
├── config.py                ← Semua pengaturan terpusat (ID sheet, email, threshold)
├── helpers.py               ← Fungsi utilitas kecil (konversi tipe data, buat dict anomali)
├── loader.py                ← Task 1 & 2: Load data dari Google Sheets + build lookup
├── detection.py             ← Task 3–12: Deteksi 10 tipe anomali
├── cleaning.py              ← Task 13 & 14: Gabungkan anomali + build cleaned dataset
├── writer.py                ← Task 15–17: Tulis output ke Google Sheets
├── notifier.py              ← Task 18 & 19: Laporan Prefect UI + email notifikasi
├── credentials.json         ← Kunci Service Account Google (JANGAN di-share/upload ke Git!)
├── requirements_prefect.txt ← Daftar library yang dibutuhkan
└── check_headers.py         ← Script diagnostik (cek struktur sheet Google Sheets)
```

---

# ⚙️ Cara Setup (Pertama Kali)

## 1. Install Library

Buka terminal di folder ini, lalu jalankan:

```bash
pip install -r requirements_prefect.txt
```

Library yang diinstall:

| Library | Fungsi |
|---|---|
| `prefect==3.6.28` | Orkestrasi pipeline (monitoring, retry, logging) |
| `gspread==6.1.2` | Koneksi dan baca/tulis Google Sheets via Python |
| `google-auth==2.29.0` | Autentikasi ke Google Cloud menggunakan Service Account |

## 2. Siapkan Google Credentials

File `credentials.json` adalah **kunci akses** ke Google Sheets. Cara mendapatkannya:

1. Buka [Google Cloud Console](https://console.cloud.google.com/)
2. Buat Project baru (gunakan akun Gmail **pribadi**, bukan akun organisasi)
3. Aktifkan **Google Sheets API** dan **Google Drive API**
4. Buat **Service Account** → masuk ke tab **Keys** → **Add Key → JSON**
5. Rename file yang ter-download menjadi `credentials.json`
6. Letakkan di folder ini (`Python - Prefert/`)

> ⚠️ **PENTING:** Jangan pernah upload `credentials.json` ke GitHub atau share ke orang lain.
> File ini setara dengan password akses ke Google Sheets Anda.

## 3. Share Google Sheets ke Bot

Cari `client_email` di dalam `credentials.json`, lalu share Google Sheet Anda
ke alamat email tersebut dengan akses **Editor**.

Contoh email bot:
```
googlesheets-exercise@nama-project.iam.gserviceaccount.com
```

## 4. Update config.py

Buka `config.py` dan isi `SPREADSHEET_ID`:

```python
"SPREADSHEET_ID" : "ISI_ID_DARI_URL_GOOGLE_SHEETS_ANDA",
```

ID ada di URL Google Sheets:
```
https://docs.google.com/spreadsheets/d/[SPREADSHEET_ID]/edit
```

---

# ▶️ Cara Menjalankan Pipeline

## Jalankan Sekali (Manual)

```bash
python main.py
```

Pipeline akan berjalan dari awal sampai selesai. Output log muncul di terminal.

## Deploy ke Prefect Cloud (Jadwal Otomatis)

```bash
# Deploy dengan jadwal harian jam 07:00
prefect deploy main.py:wastex_pipeline \
    --name "WasteX Daily Pipeline" \
    --cron "0 7 * * *" \
    --pool "default-agent-pool"

# Jalankan worker di terminal terpisah
prefect worker start --pool "default-agent-pool"
```

---

# 🗂️ Penjelasan File per File

---

## `config.py` — Pusat Konfigurasi

File ini adalah **satu-satunya tempat** untuk mengubah pengaturan pipeline.
Tidak perlu menyentuh file lain jika hanya ingin mengubah konfigurasi.

```python
CONFIG = {
    # Google Sheets — sumber dan tujuan data
    "SPREADSHEET_ID"   : "1gBjAm5dDuc...",   # ID dari URL Google Sheets
    "CREDENTIALS_FILE" : "credentials.json",  # path ke file kunci

    # Nama sheet sumber (INPUT — tidak diubah pipeline)
    "SHEET_BIOCHAR_PROD" : "biochar_production",
    "SHEET_BAG_PROD"     : "bag_production",
    "SHEET_BIOCHAR_APP"  : "biochar_application",
    "SHEET_BAG_APP"      : "bag_application",

    # Nama sheet output (OUTPUT — ditulis pipeline)
    "SHEET_CLEANED_PROD"   : "CLEANED_prod_batch",
    "SHEET_CLEANED_BAG"    : "CLEANED_bag_prod",
    "SHEET_CLEANED_APP"    : "CLEANED_app_batch",
    "SHEET_CLEANED_BAGAPP" : "CLEANED_bag_app",
    "SHEET_QUEUE"          : "VALIDATION_QUEUE",
    "SHEET_LOG"            : "AUTOMATION_LOG",

    # Pengaturan email notifikasi
    "NOTIFICATION_EMAIL" : "tim@wastex.io",   # penerima email
    "EMAIL_SENDER"       : "bot@gmail.com",   # pengirim email
    "EMAIL_PASSWORD"     : "app_password",    # App Password Gmail (bukan password utama!)

    # Pengaturan Prefect Task
    "TASK_RETRIES"         : 3,   # coba ulang 3x jika task gagal
    "TASK_RETRY_DELAY_SEC" : 30,  # tunggu 30 detik sebelum retry
    "TASK_TIMEOUT_SEC"     : 300, # batas waktu per task = 5 menit

    # Threshold untuk deteksi anomali
    "MAX_APP_DATE_GAP_DAYS"  : 30,   # TYPE 5: maks gap antara Timestamp dan application_date
    "WEIGHT_DISCREPANCY_PCT" : 0.05, # TYPE 8: maks selisih berat = 5%
    "BATCH_SUM_TOLERANCE_KG" : 0.01, # TYPE 9: toleransi selisih batch sum = 0.01 kg

    # Nilai valid untuk application_type (TYPE 6)
    "VALID_APP_TYPES" : [
        "Application-Pure Biochar",
        "Application-Charged Biochar",
        "Sale-Pure Biochar",
        "Sale-Charged Biochar",
    ],
}
```

---

## `helpers.py` — Fungsi Utilitas

Berisi 4 fungsi kecil yang dipakai bersama oleh hampir semua file task.

### `to_float(val)`

Konversi nilai apapun ke `float`. Menangani kasus khusus:
- String dengan koma desimal: `"18,15"` → `18.15`
- Nilai `None` → return `None`
- String kosong → return `None`

```python
to_float("18,15")  # → 18.15
to_float(None)     # → None
to_float("abc")    # → None
```

### `to_date(val)`

Konversi ke `date` object. Menangani `datetime`, `date`, dan string `"YYYY-MM-DD"`.

```python
to_date("2024-11-01")              # → date(2024, 11, 1)
to_date(datetime(2024, 11, 1, 9))  # → date(2024, 11, 1)
```

### `is_empty(val)`

Cek apakah nilai kosong/null. Menangani `None`, `""`, `"nan"`, `"None"`, `"NaT"`.

```python
is_empty(None)   # → True
is_empty("")     # → True
is_empty("nan")  # → True
is_empty(18.5)   # → False
```

### `make_anomaly(...)`

Buat dictionary anomali dengan format yang seragam.
Semua task deteksi memanggil fungsi ini agar output-nya konsisten.

```python
make_anomaly(
    sheet     = "bag_production",
    atype     = "TYPE 2",
    desc      = "Negative value in weight: -5.0",
    field     = "weight",
    orig_val  = -5.0,
    fix       = "Requires human review",
    action    = "FLAGGED → VALIDATION_QUEUE",
    record_id = "241101-Y0014-M0030-1",
)
# → dict dengan 12 key: Sheet, anomaly_type, description, Field,
#   original_value, suggested_fix, action, Record_ID,
#   detected_at, Reviewed_By, Resolution, Resolved_At
```

---

## `loader.py` — Task 1 & 2: Load Data

### Task 1 — `load_data()`

Membaca 4 sheet dari Google Sheets dan mengembalikannya sebagai dictionary.

```
Google Sheets
    ├── biochar_production  →  data["biochar_prod"]  (list of dict)
    ├── bag_production      →  data["bag_prod"]
    ├── biochar_application →  data["biochar_app"]
    └── bag_application     →  data["bag_app"]
```

Setiap baris data punya key tambahan `_row_index` (nomor baris di sheet) yang
digunakan nanti untuk mengidentifikasi baris mana yang harus dikeluarkan dari CLEANED.

### Task 2 — `build_lookup_maps(data)`

Membangun **lookup dictionary** agar deteksi cross-sheet menjadi efisien
(tidak perlu loop nested yang lambat).

| Lookup | Isi | Dipakai oleh |
|---|---|---|
| `bag_prod_weight_map` | `{bag_id → weight}` | TYPE 8 |
| `bag_prod_id_set` | `[bag_id, ...]` list unik | TYPE 7 |
| `bag_id_count` | `{bag_id → jumlah kemunculan}` | TYPE 4 |
| `bag_app_map` | `{bag_id → [application_id]}` | TYPE 10 |
| `batch_sums` | `{production_id → sum_weight}` | TYPE 9 |

---

## `detection.py` — Task 3–12: Deteksi 10 Anomali

### TYPE 1 — Comma Decimal Separator ✅ Auto-Fix

**Sheet:** `bag_production.weight`

**Masalah:** Operator menginput berat dengan koma sebagai desimal, contoh `"18,15"` seharusnya `18.15`.

**Aksi:** **AUTO-FIX** — nilai langsung diperbaiki. Record tetap masuk CLEANED.

```python
if "," in str(row["weight"]):
    fixed_w = float(str(row["weight"]).replace(",", "."))
```

---

### TYPE 2 — Negative Values ❌ Flagged

**Sheet:** `bag_production`, `biochar_production`

**Masalah:** Field yang tidak mungkin negatif secara fisik ternyata bernilai negatif.

Field yang dicek:
- `bag_production`: `weight`, `co2e_persistent`, `co2e_100`, `spc`
- `biochar_production`: `co2e_persistent`, `co2e_100`, `spc`

**Aksi:** FLAGGED ke VALIDATION_QUEUE, dikeluarkan dari CLEANED.

---

### TYPE 3 — Missing Critical Fields ❌ Flagged

**Sheet:** `bag_production`, `biochar_production`

**Masalah:** Field wajib tidak diisi.

Field yang dicek:
- `bag_production.weight` — tidak boleh kosong (berat = data inti)
- `biochar_production.carbon_content_%` — tidak boleh kosong (kritis untuk CO2e)

**Aksi:** FLAGGED ke VALIDATION_QUEUE.

---

### TYPE 4 — Duplicate bag_id ❌ Flagged

**Sheet:** `bag_production`

**Masalah:** `bag_id` yang sama muncul lebih dari sekali.
Kemungkinan: double scan oleh operator, atau bag ditimbang dua kali.

**Aksi:** Occurrence pertama tetap masuk CLEANED, sisanya FLAGGED.

```python
# Menggunakan lookup bag_id_count yang sudah dibangun di Task 2
if bag_id_count.get(bid, 0) > 1:
    # FLAGGED
```

---

### TYPE 5 — Future Timestamps ❌ Flagged

**Sheet:** Semua 4 sheet

**Masalah (2 kasus):**

1. `Timestamp > hari ini` → data masa depan tidak mungkin ada
2. `application_date` lebih dari 30 hari setelah `Timestamp` → mencurigakan

```python
# Kasus 1: Timestamp masa depan
if ts > today:
    # FLAGGED

# Kasus 2: Gap application_date vs Timestamp
gap_days = (ad - ts).days
if gap_days > CONFIG["MAX_APP_DATE_GAP_DAYS"]:  # default: 30 hari
    # FLAGGED
```

---

### TYPE 6 — Invalid application_type ❌ Flagged

**Sheet:** `biochar_application`

**Masalah:** Nilai `application_type` tidak termasuk dalam 4 nilai yang valid:
- `Application-Pure Biochar`
- `Application-Charged Biochar`
- `Sale-Pure Biochar`
- `Sale-Charged Biochar`

---

### TYPE 7 — Orphan bag_id ❌ Flagged

**Sheet:** `bag_application` vs `bag_production` (cross-sheet)

**Masalah:** Ada `bag_id` di `bag_application` yang tidak punya record di `bag_production`.
Artinya ada catatan aplikasi yang bag-nya tidak pernah diproduksi (atau salah ketik ID).

```python
if bid not in bag_prod_id_set:
    # FLAGGED — orphan bag
```

---

### TYPE 8 — Weight Discrepancy >5% ❌ Flagged

**Sheet:** `bag_application` vs `bag_production` (cross-sheet)

**Masalah:** Berat bag saat aplikasi (`bag_weight`) berbeda >5% dari berat saat produksi (`weight`).

```python
disc = abs(app_w - prod_w) / prod_w
if disc > 0.05:  # 5%
    # FLAGGED
```

---

### TYPE 9 — Batch Sum Mismatch ❌ Flagged

**Sheet:** `bag_production` vs `biochar_production` (cross-sheet)

**Masalah:** Total berat semua bag dalam satu batch ≠ `biochar_amount_kg` yang dideklarasikan.

```python
diff = abs(bag_sum - declared)
if diff > 0.01:  # toleransi 0.01 kg
    # FLAGGED
```

---

### TYPE 10 — Bag in Multiple Application Batches ❌ Flagged

**Sheet:** `bag_application` (cross-row)

**Masalah:** Satu `bag_id` muncul di lebih dari satu application batch.
Satu bag fisik tidak mungkin diaplikasikan di dua tempat berbeda.

```python
app_ids = bag_app_map.get(bid, [])
if len(app_ids) > 1:
    # FLAGGED
```

---

## `cleaning.py` — Task 13 & 14

### Task 13 — `merge_anomalies()`

Menggabungkan output dari 10 task deteksi menjadi satu flat list.

```
[t1_anomalies] + [t2] + [t3] + ... + [t10]  →  all_anomalies (list tunggal)
```

### Task 14 — `build_cleaned()`

Mem-filter baris yang bermasalah dari data mentah.

**Aturan routing:**

| Tipe | Masuk CLEANED? | Masuk VALIDATION_QUEUE? |
|---|---|---|
| TYPE 1 (auto-fix) | ✅ Ya (sudah diperbaiki) | ✅ Ya (dicatat) |
| TYPE 2–10 | ❌ Tidak | ✅ Ya |

**Cara kerja:**
1. Kumpulkan `_row_index` dari semua baris yang di-flag TYPE 2–10
2. Filter: hanya baris yang `_row_index` TIDAK ada di flagged set yang masuk CLEANED
3. Untuk TYPE 4: hanya occurrence pertama per `bag_id` yang dipertahankan

---

## `writer.py` — Task 15–17

### Task 15 — `write_cleaned_sheets()`

Menulis 4 CLEANED sheets ke Google Sheets.

**Format output sheet:**
```
Baris 1  : Teks deskripsi (tidak diubah, sudah ada di sheet)
Baris 2  : Header kolom (nama-nama field)
Baris 3+ : Data bersih
```

### Task 16 — `write_validation_queue()`

Menulis anomali ke VALIDATION_QUEUE dengan **deduplication**.
Sebelum menulis, pipeline cek apakah kombinasi `Sheet + anomaly_type + Record_ID`
sudah ada. Jika sudah → **tidak ditulis ulang** (tidak spam di setiap run harian).

| Kolom | Diisi oleh | Keterangan |
|---|---|---|
| Sheet | Pipeline | Sheet sumber anomali |
| anomaly_type | Pipeline | TYPE 1 s/d TYPE 10 |
| description | Pipeline | Penjelasan detail anomali |
| Field | Pipeline | Nama kolom bermasalah |
| original_value | Pipeline | Nilai asli |
| suggested_fix | Pipeline | Saran perbaikan |
| action | Pipeline | AUTO-FIXED atau FLAGGED |
| Record_ID | Pipeline | bag_id / activity_id |
| detected_at | Pipeline | Waktu deteksi |
| Reviewed_By | **Reviewer** | Nama reviewer (diisi manual) |
| Resolution | **Reviewer** | approved / rejected / corrected |
| Resolved_At | **Reviewer** | Tanggal selesai review |

### Task 17 — `write_automation_log()`

Menulis 1 baris log per sheet ke AUTOMATION_LOG setiap pipeline dijalankan.

Kolom: `Run_Timestamp`, `Sheet_Processed`, `Records_In`, `Records_Clean`,
`Records_Flagged`, `Errors_Comma_Decimal`, `Errors_Negative`,
`Errors_Missing_Critical`, `Errors_Duplicate_Bag`, `Errors_Orphan_Bag`,
`Errors_Weight_Discrepancy`, `Errors_Future_Date`, `Errors_Invalid_Category`,
`Action_Taken`, `Notes`

---

## `notifier.py` — Task 18 & 19

### Task 18 — `create_run_report()`

Membuat **Prefect Artifact** berupa laporan Markdown yang bisa dilihat
di Prefect UI → tab **Artifacts** tanpa perlu buka Google Sheets.

Isi laporan: summary run, tabel anomali per tipe, before vs after cleaned sheets,
preview 10 anomali teratas.

### Task 19 — `send_email_notification()`

Mengirim email ke tim jika ada **anomali baru** yang belum ada di queue sebelumnya.

> 💡 Jika tidak ada anomali baru → email tidak dikirim.
> Jika email gagal → error dicatat tapi pipeline tetap SUCCESS.

Untuk mengaktifkan email, isi di `config.py`:
```python
"EMAIL_SENDER"   : "email_anda@gmail.com",
"EMAIL_PASSWORD" : "app_password_gmail",  # bukan password utama!
```

Cara buat App Password Gmail: **Google Account → Security → App Passwords**

---

## `main.py` — Flow Utama (Entry Point)

File ini mendefinisikan urutan 19 task menggunakan decorator `@flow` dari Prefect.

```python
@flow(name="wastex-daily-pipeline")
def wastex_pipeline():
    # Task 1-2: Load data & build lookup
    data   = load_data()
    lookup = build_lookup_maps(data)

    # Task 3: TYPE 1 → return tuple (anomalies, fixed_bag_prod)
    t1_result    = detect_type1(data)
    t1_anomalies = t1_result[0]
    fixed_bag    = t1_result[1]

    # Task 4-12: Deteksi TYPE 2–10
    t2  = detect_type2(data, fixed_bag)
    t3  = detect_type3(data, fixed_bag)
    t4  = detect_type4(data, lookup)
    t5  = detect_type5(data)
    t6  = detect_type6(data)
    t7  = detect_type7(data, lookup)
    t8  = detect_type8(data, lookup)
    t9  = detect_type9(data, lookup)
    t10 = detect_type10(data, lookup)

    # Task 13-14: Merge & build cleaned
    all_anomalies = merge_anomalies(t1_anomalies, t2, t3, t4, t5, t6, t7, t8, t9, t10)
    cleaned       = build_cleaned(data, fixed_bag, all_anomalies)

    # Task 15-17: Tulis output ke Google Sheets
    write_cleaned_sheets(cleaned)
    new_count = write_validation_queue(all_anomalies)
    write_automation_log(start_time, end_time, data, cleaned, all_anomalies, ...)

    # Task 18-19: Laporan & email
    create_run_report(all_anomalies, cleaned, data, new_count, ...)
    send_email_notification(all_anomalies, new_count, start_time)
```

**Kenapa task dijalankan berurutan, bukan paralel?**

- Task 3 (TYPE 1) harus selesai dulu → `fixed_bag_prod` dipakai TYPE 2 & 3
- Task 13–19 bergantung pada hasil semua task sebelumnya
- Prefect tetap memberikan monitoring & retry per task meski berurutan

---

# 🔄 Alur Data Lengkap

```
Google Sheets (4 sheet input)
         │
         ▼
    [Task 1] load_data()
         │
         ▼
    [Task 2] build_lookup_maps()
         │
    ┌────┴──────────────────────────────┐
    │                                   │
    ▼                                   ▼
[Task 3] detect_type1()           lookup dict
  → fixed_bag_prod                     │
  → t1_anomalies               [Task 4-12]
         │                    detect_type2-10()
         └──────────┬──────────────────┘
                    ▼
           [Task 13] merge_anomalies()
                    │
                    ▼
           [Task 14] build_cleaned()
                    │
          ┌─────────┼───────────┐
          ▼         ▼           ▼
   [Task 15]  [Task 16]   [Task 17]
  CLEANED_*  VALIDATION   AUTOMATION
   sheets     _QUEUE        _LOG
          │
          ▼
   [Task 18] Prefect UI Report
   [Task 19] Email Notification
```

---

# ❓ Troubleshooting

| Error | Penyebab | Solusi |
|---|---|---|
| `PermissionError` | Google Sheet belum di-share ke bot | Share sheet ke email dari `credentials.json` sebagai Editor |
| `FileNotFoundError: credentials.json` | File kunci tidak ada | Letakkan `credentials.json` di folder ini |
| `ModuleNotFoundError` | Library belum diinstall | Jalankan `pip install -r requirements_prefect.txt` |
| `GSpreadException: header not unique` | Kolom header duplikat di sheet | Sudah di-handle otomatis oleh writer |
| `APIError 403` | Service Account tidak punya akses | Share Google Sheet ke email bot sebagai Editor |
| Email tidak terkirim | App Password salah / Gmail ketat | Buat ulang App Password di Google Account → Security |

---

# 📋 Ringkasan 10 Tipe Anomali

| # | Nama | Sheet | Auto-Fix? |
|---|---|---|---|
| 1 | Comma decimal di weight | bag_production | ✅ Ya |
| 2 | Nilai negatif | bag_production, biochar_production | ❌ Flagged |
| 3 | Field wajib kosong | bag_production, biochar_production | ❌ Flagged |
| 4 | Duplicate bag_id | bag_production | ❌ Flagged |
| 5 | Future timestamp / suspicious date | Semua sheet | ❌ Flagged |
| 6 | application_type tidak valid | biochar_application | ❌ Flagged |
| 7 | Orphan bag_id | bag_application (cross-sheet) | ❌ Flagged |
| 8 | Selisih berat >5% | bag_application (cross-sheet) | ❌ Flagged |
| 9 | Total bag ≠ biochar_amount_kg | bag_production (cross-sheet) | ❌ Flagged |
| 10 | Bag di multiple application batch | bag_application (cross-row) | ❌ Flagged |

---

*Dokumentasi ini dibuat berdasarkan source code pipeline WasteX Prefect.*
