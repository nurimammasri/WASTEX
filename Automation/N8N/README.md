# WasteX Biochar Data Pipeline — n8n Workflow Documentation

> **Version:** v4d · **Nodes:** 37 · **Trigger:** Daily 07:00 WIB
> **Spreadsheet:** `1QqSa7reb4i2Oz7pnbb6sAflJEtbsCwF4m19J7aDgsoE`
> **Notifikasi:** `nurimammasri.01@gmail.com`

---

## Daftar Isi

1. [Gambaran Umum](#1-gambaran-umum)
2. [Arsitektur Workflow](#2-arsitektur-workflow)
3. [Semua Node — Penjelasan Lengkap](#3-semua-node--penjelasan-lengkap)
4. [Alur Data End-to-End](#4-alur-data-end-to-end)
5. [10 Tipe Anomali yang Dideteksi](#5-10-tipe-anomali-yang-dideteksi)
6. [Output Sheets](#6-output-sheets)
7. [Setup & Cara Import](#7-setup--cara-import)
8. [Troubleshooting](#8-troubleshooting)
9. [Pertanyaan Umum (FAQ)](#9-pertanyaan-umum-faq)

---

## 1. Gambaran Umum

Pipeline ini berjalan **otomatis setiap hari jam 07:00** dan melakukan:

| # | Langkah | Keterangan |
|---|---------|------------|
| 1 | **Baca data** | Ambil 4 sheet sumber dari Google Sheets secara paralel |
| 2 | **Deteksi anomali** | Scan 10 tipe anomali per brief WasteX |
| 3 | **Auto-fix** | TYPE 1 (comma decimal) diperbaiki otomatis |
| 4 | **Tulis CLEANED sheets** | 4 sheet output dengan data bersih |
| 5 | **VALIDATION_QUEUE** | Anomali TYPE 2–10 dikirim ke antrian review |
| 6 | **AUTOMATION_LOG** | 1 baris log per sheet per run |
| 7 | **Email notifikasi** | Kirim email ke tim jika ada anomali baru |

### Dataset

```
biochar_production    → 7 rows   (1 row = 1 batch carbonizer run)
bag_production        → 78 rows  (1 row = 1 bag yang diproduksi)
biochar_application   → 5 rows   (1 row = 1 event aplikasi)
bag_application       → 42 rows  (1 row = 1 bag yang diaplikasikan)
```

### Key Rule dari Brief

> ⚠️ **Satu Production Bag ID hanya boleh digunakan di SATU application batch.**
> `bag_id` di `bag_application` harus selalu ada di `bag_production`.

---

## 2. Arsitektur Workflow

### Diagram Alur

```
⏰ Daily Trigger 07:00
        │
        ├──────────────────────────────────┐
        │                                  │ (paralel)
   📥 Read biochar_production         📥 Read bag_production
   📥 Read biochar_application        📥 Read bag_application
        │                                  │
        └──────────┬───────────────────────┘
                   │
          🔗 Collect All Sheets
          (gabungkan 4 sheet via referensi langsung)
                   │
          🗺️ Build Lookup Maps
          (siapkan dict untuk cross-sheet validation)
                   │
          🔍 Detect All 10 Anomaly Types
          (deteksi TYPE 1 s/d TYPE 10)
                   │
          🧹 Build Cleaned Data
          (filter baris flagged TYPE 2-10)
                   │
          📝 Prepare Write Data
          (flatten array jadi individual items)
                   │
        ┌──────────┼──────────────────────┐
        │ (paralel - 4 jalur sekaligus)   │
   📊 Flatten prod → 🗑️ Clear → ✅ Write CLEANED_prod_batch
   📊 Flatten bag  → 🗑️ Clear → ✅ Write CLEANED_bag_prod
   📊 Flatten app  → 🗑️ Clear → ✅ Write CLEANED_app_batch
   📊 Flatten bapp → 🗑️ Clear → ✅ Write CLEANED_bag_app
        │                                 │
        └──────────┬──────────────────────┘
                   │
         ⏳ Wait All Writes Done
         (Merge node — tunggu semua 4 Write selesai)
                   │
         🔄 Restore Pipeline Data
         (ambil kembali payload dari Detect node)
                   │
         ⚠️ Split Anomalies for Queue
         (pisahkan anomali TYPE 2-10 jadi individual items)
                   │
         🧼 Clean Before Queue Write
         (hapus field internal _pp)
                   │
         📋 Append VALIDATION_QUEUE
         (tulis anomali ke Google Sheets)
                   │
         🔄 Restore After Queue
         (ambil payload dari Split node)
                   │
         📊 Build AUTOMATION_LOG Rows
         (buat 4 baris log, 1 per sheet)
                   │
         🧼 Clean Before Log Write
         (hapus field internal _pp)
                   │
         📝 Append AUTOMATION_LOG
         (tulis log ke Google Sheets)
                   │
         🔔 Check Notify
         (cek apakah ada anomali baru)
                   │
         ❓ Ada Anomali Baru?
          │                    │
         YES                   NO
          │                    │
   📧 Build Email        ✅ Done
   📨 Send Email              (selesai tanpa email)
   ✅ Done
```

### Kenapa Paralel untuk Read dan Write?

Membaca dan menulis 4 sheet secara **paralel** (bukan sequential) menghemat waktu eksekusi signifikan:
- Sequential: ~8–12 detik (jalan satu per satu)
- Paralel: ~3–5 detik (semua jalan bersamaan)

n8n menjalankan paralel dengan **fan-out** dari satu node ke banyak node sekaligus.

---

## 3. Semua Node — Penjelasan Lengkap

### Node 1 — ⏰ Daily Trigger 07:00

**Tipe:** `Schedule Trigger`
**Fungsi:** Entry point workflow. Aktif setiap hari jam 07:00 WIB.

```
Cron expression: 0 7 * * *
```

Format cron lain yang bisa digunakan:
| Expression | Arti |
|-----------|------|
| `0 7 * * *` | Setiap hari jam 07:00 |
| `0 7 * * 1-5` | Senin–Jumat jam 07:00 |
| `0 */6 * * *` | Setiap 6 jam |
| `0 7,19 * * *` | Dua kali sehari |

---

### Node 2–5 — 📥 Read [Sheet Name]

**Tipe:** `Google Sheets` · Operation: `Read Sheet`

Keempat node ini berjalan **paralel** secara bersamaan setelah trigger aktif:

| Node | Sheet Sumber | Rows Ekspektasi |
|------|-------------|-----------------|
| Read biochar_production | `biochar_production` | 7 rows |
| Read bag_production | `bag_production` | 78 rows |
| Read biochar_application | `biochar_application` | 5 rows |
| Read bag_application | `bag_application` | 42 rows |

**Konfigurasi:**
```
Document ID : 1QqSa7reb4i2Oz7pnbb6sAflJEtbsCwF4m19J7aDgsoE
Mode        : Read Sheet
Header Row  : Row 1
```

> **Catatan:** Jika muncul error `"Quota exceeded"`, tunggu 1–2 menit dan coba lagi.
> Google Sheets API limit: 60 read requests/menit per user.

---

### Node 6 — 🔗 Collect All Sheets

**Tipe:** `Code` (JavaScript)
**Fungsi:** Menggabungkan output dari 4 Read nodes menjadi satu objek tunggal.

```javascript
const addIdx = arr => arr.map((r,i) => ({...r, _row_index: i+2}));

return [{ json: {
  biochar_prod : addIdx($('📥 Read biochar_production').all().map(i=>i.json)),
  bag_prod     : addIdx($('📥 Read bag_production').all().map(i=>i.json)),
  biochar_app  : addIdx($('📥 Read biochar_application').all().map(i=>i.json)),
  bag_app      : addIdx($('📥 Read bag_application').all().map(i=>i.json)),
  loaded_at    : new Date().toISOString(),
}}];
```

**Kenapa pakai `$(nodeName)` bukan `$input`?**
Karena 4 Read nodes berjalan paralel dan hasilnya tidak bisa digabung langsung via `$input`. Dengan referensi `$(nodeName)`, kita bisa akses output dari node mana saja yang sudah selesai.

**`_row_index`** ditambahkan ke setiap row sebagai referensi nomor baris asli di Google Sheet (mulai dari 2, karena row 1 = header).

---

### Node 7 — 🗺️ Build Lookup Maps

**Tipe:** `Code` (JavaScript)
**Fungsi:** Membangun 5 lookup dictionary dari data yang sudah di-load, digunakan oleh deteksi cross-sheet (TYPE 7, 8, 9, 10).

| Lookup | Isi | Dipakai untuk |
|--------|-----|---------------|
| `bag_prod_weight_map` | `{ bag_id → weight }` | TYPE 8: cek weight discrepancy |
| `bag_prod_id_set` | `[bag_id, ...]` | TYPE 7: cek orphan bag |
| `bag_id_count` | `{ bag_id → jumlah_muncul }` | TYPE 4: cek duplikat |
| `bag_app_map` | `{ bag_id → [application_id] }` | TYPE 10: cek multi-application |
| `batch_sums` | `{ production_id → sum_weight }` | TYPE 9: cek batch sum |

---

### Node 8 — 🔍 Detect All 10 Anomaly Types

**Tipe:** `Code` (JavaScript) — node terpanjang (~150 baris)
**Fungsi:** Mendeteksi semua 10 tipe anomali sesuai brief WasteX.

Output yang dihasilkan:
```javascript
{
  ...data,              // semua data asli
  fixed_bag_prod,       // bag_production setelah TYPE 1 di-fix
  anomalies,            // array semua anomali yang ditemukan
  type_counts,          // { 'TYPE 1': 1, 'TYPE 2': 1, ... }
  total_anomalies,      // total jumlah findings
  new_flags,            // jumlah yang perlu review manusia
  auto_fixed,           // jumlah yang auto-fixed
  run_timestamp,        // waktu eksekusi
}
```

Setiap anomali punya struktur:
```javascript
{
  Sheet          : 'bag_production',
  anomaly_type   : 'TYPE 1',
  description    : 'Comma decimal: "18,15" → 18.15',
  Field          : 'weight',
  original_value : '18,15',
  suggested_fix  : '18.15',
  action         : 'AUTO-FIXED → CLEANED',
  Record_ID      : '241101-Y0014-M0030-5',
  detected_at    : '2026-05-01 07:00:15',
  Reviewed_By    : '',
  Resolution     : '',
  Resolved_At    : '',
}
```

---

### Node 9 — 🧹 Build Cleaned Data

**Tipe:** `Code` (JavaScript)
**Fungsi:** Memfilter baris bermasalah dari dataset dan menghasilkan 4 cleaned arrays.

**Logika routing:**
```
TYPE 1 → auto-fixed → TETAP masuk CLEANED
TYPE 2–10 → di-flag → DIBUANG dari CLEANED, masuk VALIDATION_QUEUE
TYPE 4 → keep first occurrence per bag_id (dedup otomatis)
```

Output:
```javascript
{
  ...payload,
  cleaned: {
    biochar_prod : [...],  // rows yang lolos
    bag_prod     : [...],
    biochar_app  : [...],
    bag_app      : [...],
  }
}
```

---

### Node 10 — 📝 Prepare Write Data

**Tipe:** `Code` (JavaScript)
**Fungsi:** Menyiapkan data untuk ditulis ke Google Sheets. Menambahkan kolom `_cleaning_note: 'auto-cleaned'` ke setiap row.

---

### Node 11–14 — 📊 Flatten [Sheet Name]

**Tipe:** `Code` (JavaScript)
**Fungsi:** Mengubah array of objects menjadi **individual items** (1 item = 1 row).

> **Kenapa perlu Flatten?**
> Node Google Sheets `autoMapInputData` hanya bisa mapping jika input sudah berupa flat individual items. Tanpa Flatten, seluruh array ditulis sebagai JSON string di satu sel.

**Contoh Flatten untuk CLEANED_prod_batch:**
```javascript
const p = $('🧹 Build Cleaned Data').first().json;
const rows = p.cleaned.biochar_prod || [];
return rows.map(r => {
  const { _row_index, ...clean } = r;
  return { json: { ...clean, _cleaning_note: 'auto-cleaned' } };
});
```

---

### Node 15–18 — 🗑️ Clear [Sheet Name]

**Tipe:** `Google Sheets` · Operation: `Clear`
**Fungsi:** Menghapus isi CLEANED sheet lama (baris 2 ke bawah) sebelum ditulis ulang.

```
startIndex: 1  (baris ke-2, karena baris 1 = header yang tidak boleh dihapus)
```

> Tanpa Clear dulu, data baru akan di-append ke data lama sehingga ada duplikat.

---

### Node 19–22 — ✅ Write CLEANED [Sheet Name]

**Tipe:** `Google Sheets` · Operation: `Append or Update`
**Fungsi:** Menulis data bersih ke 4 CLEANED sheets.

```
Mapping Mode: Map Automatically (autoMapInputData)
```

Keempat node Clear dan Write ini berjalan **paralel** (fan-out dari Prepare Write Data).

---

### Node 23 — ⏳ Wait All Writes Done

**Tipe:** `Merge` (n8n built-in)
**Fungsi:** Menunggu **semua 4 Write nodes selesai** sebelum pipeline lanjut ke tahap berikutnya.

```
Mode: Append
Input 0 ← Write CLEANED_prod_batch
Input 1 ← Write CLEANED_bag_prod
Input 2 ← Write CLEANED_app_batch
Input 3 ← Write CLEANED_bag_app
```

> Ini adalah **kunci arsitektur paralel** di n8n. Tanpa Merge node, pipeline akan lanjut bahkan sebelum semua Write selesai, menyebabkan data tidak lengkap.

---

### Node 24 — 🔄 Restore Pipeline Data

**Tipe:** `Code` (JavaScript)
**Fungsi:** Setelah Merge node, data pipeline perlu "dipulihkan" karena Merge output hanya berisi data dari Write nodes (bukan full pipeline payload).

```javascript
const detect  = $('🔍 Detect All 10 Anomaly Types').first().json;
const cleaned = $('🧹 Build Cleaned Data').first().json.cleaned;
return [{ json: { ...detect, cleaned } }];
```

---

### Node 25 — ⚠️ Split Anomalies for Queue

**Tipe:** `Code` (JavaScript)
**Fungsi:** Memisahkan anomali TYPE 2–10 menjadi **individual items** untuk di-append satu per satu ke VALIDATION_QUEUE.

```javascript
const toQ = p.anomalies.filter(a => !a.action.includes('AUTO-FIXED'));

if (toQ.length === 0) {
  return [{ json: { ...p, _skip: true, queued_count: 0 } }];
}

// Return setiap anomali sebagai item terpisah
// Hanya 12 kolom yang perlu masuk ke sheet
return toQ.map((a, i) => ({
  json: {
    Sheet, anomaly_type, description, Field,
    original_value, suggested_fix, action, Record_ID,
    detected_at, Reviewed_By: '', Resolution: '', Resolved_At: '',
    _pp: i === 0 ? JSON.stringify(payload) : '',  // simpan state di item pertama
  }
}));
```

> `_pp` (pipeline payload) disimpan di item pertama untuk digunakan oleh `Restore After Queue`. Field ini dihapus sebelum ditulis ke sheet oleh node Clean.

---

### Node 26 — 🧼 Clean Before Queue Write

**Tipe:** `Code` (JavaScript)
**Fungsi:** Menghapus field internal `_pp` sebelum data ditulis ke Google Sheets.

```javascript
const { _pp, ...cleanRow } = $input.item.json;
return [{ json: cleanRow }];
```

> **Kenapa perlu?** Field `_pp` berisi seluruh pipeline payload (bisa 50.000+ karakter) — jika ikut ke-write ke Google Sheets, akan muncul error `"Your input contains more than the maximum of 50000 characters in a single cell"`.

---

### Node 27 — 📋 Append VALIDATION_QUEUE

**Tipe:** `Google Sheets` · Operation: `Append Row`
**Fungsi:** Menulis setiap anomali sebagai baris baru ke sheet `VALIDATION_QUEUE`.

```
Mapping Mode: Map Automatically
```

Kolom yang ditulis:
| Kolom | Isi |
|-------|-----|
| Sheet | Nama sheet sumber anomali |
| anomaly_type | TYPE 1 s/d TYPE 10 |
| description | Penjelasan detail anomali |
| Field | Nama kolom yang bermasalah |
| original_value | Nilai asli sebelum fix |
| suggested_fix | Saran perbaikan |
| action | AUTO-FIXED atau FLAGGED |
| Record_ID | bag_id atau activity_id |
| detected_at | Timestamp deteksi |
| Reviewed_By | *(kosong — diisi reviewer)* |
| Resolution | *(kosong — diisi reviewer)* |
| Resolved_At | *(kosong — diisi reviewer)* |

---

### Node 28 — 🔄 Restore After Queue

**Tipe:** `Code` (JavaScript)
**Fungsi:** Memulihkan pipeline payload dari Split node setelah semua anomali selesai di-append.

```javascript
const splitItems = $('⚠️ Split Anomalies for Queue').all();
const withPayload = splitItems.find(i => i.json._pp);
if (!withPayload) {
  return [{ json: $input.first().json }];
}
return [{ json: JSON.parse(withPayload.json._pp) }];
```

---

### Node 29 — 📊 Build AUTOMATION_LOG Rows

**Tipe:** `Code` (JavaScript)
**Fungsi:** Membuat 4 baris log (1 per sheet sumber) dengan kolom persis sesuai struktur `AUTOMATION_LOG` di Google Sheet.

Kolom yang dihasilkan:
| Kolom | Keterangan |
|-------|-----------|
| `Run_Timestamp` | Waktu pipeline jalan |
| `Sheet_Processed` | Nama sheet sumber |
| `Records_In` | Jumlah baris input |
| `Records_Clean` | Jumlah baris di CLEANED sheet |
| `Records_Flagged` | Jumlah baris di-flag TYPE 2–10 |
| `Errors_Comma_Decimal` | Count TYPE 1 |
| `Errors_Negative` | Count TYPE 2 |
| `Errors_Missing_Critical` | Count TYPE 3 |
| `Errors_Duplicate_Bag` | Count TYPE 4 |
| `Errors_Orphan_Bag` | Count TYPE 7 |
| `Errors_Weight_Discrepancy` | Count TYPE 8 |
| `Errors_Future_Date` | Count TYPE 5 |
| `Errors_Invalid_Category` | Count TYPE 6 |
| `Action_Taken` | Ringkasan tindakan |
| `Notes` | TYPE 9 dan TYPE 10 (tidak ada kolom khusus) |

---

### Node 30 — 🧼 Clean Before Log Write

**Tipe:** `Code` (JavaScript)
**Fungsi:** Sama seperti Clean Before Queue Write — menghapus `_pp` sebelum ditulis ke sheet.

---

### Node 31 — 📝 Append AUTOMATION_LOG

**Tipe:** `Google Sheets` · Operation: `Append Row`
**Fungsi:** Menulis 4 baris log ke sheet `AUTOMATION_LOG`.

---

### Node 32 — 🔔 Check Notify

**Tipe:** `Code` (JavaScript)
**Fungsi:** Mengecek apakah ada anomali baru yang perlu dinotifikasi.

```javascript
return [{ json: { ...payload, should_notify: (payload.new_flags || 0) > 0 } }];
```

---

### Node 33 — ❓ Ada Anomali Baru?

**Tipe:** `IF` (n8n built-in)
**Fungsi:** Percabangan kondisional.

```
Jika should_notify === true → kirim email
Jika should_notify === false → selesai tanpa email
```

---

### Node 34 — 📧 Build Email Content

**Tipe:** `Code` (JavaScript)
**Fungsi:** Menyusun subject dan body email notifikasi.

Email berisi:
- Waktu run dan jumlah anomali baru
- Ringkasan per tipe anomali
- Preview 5 anomali pertama
- Instruksi untuk reviewer (isi Reviewed_By, Resolution, Resolved_At)

---

### Node 35 — 📨 Send Email Notification

**Tipe:** `Gmail`
**Fungsi:** Mengirim email notifikasi ke `nurimammasri.01@gmail.com`.

```
sendTo   : nurimammasri.01@gmail.com
subject  : [WasteX Pipeline] {N} anomali baru — {tanggal}
emailType: text (plain text)
```

> **Catatan:** Butuh Gmail OAuth2 credential yang sudah terautentikasi.

---

### Node 36–37 — ✅ Done

Dua endpoint terminal:
- **✅ Done — Tidak Ada Anomali:** Pipeline selesai, tidak ada yang perlu dikirim
- **✅ Done — Email Terkirim:** Pipeline selesai, email notifikasi sudah terkirim

---

## 4. Alur Data End-to-End

### Fase 1: Input (Baca Data)

```
Google Sheets API
    ↓
4 sheet dibaca paralel
    ↓
Collect All Sheets: 4 arrays → 1 object
{
  biochar_prod: [ {row1}, {row2}, ... ],
  bag_prod    : [ {row1}, {row2}, ... ],
  biochar_app : [ {row1}, {row2}, ... ],
  bag_app     : [ {row1}, {row2}, ... ],
}
```

### Fase 2: Processing (Deteksi & Cleaning)

```
Build Lookup Maps
    ↓ (siapkan 5 lookup dict)

Detect All 10 Anomaly Types
    ↓
{
  anomalies    : [ {anomaly1}, {anomaly2}, ... ],
  fixed_bag_prod: [ rows dengan weight sudah di-fix ],
  type_counts  : { 'TYPE 1': 1, 'TYPE 9': 7, ... },
  total_anomalies: 25,
  new_flags    : 24,
  auto_fixed   : 1,
}

Build Cleaned Data
    ↓
{
  cleaned: {
    biochar_prod: [ rows tanpa TYPE 3, 5 ],
    bag_prod    : [ rows tanpa TYPE 2, 3, 4, 5 — weight sudah fixed ],
    biochar_app : [ rows tanpa TYPE 5, 6 ],
    bag_app     : [ rows tanpa TYPE 7, 8, 10 ],
  }
}
```

### Fase 3: Output (Tulis ke Sheets)

```
Flatten → Clear → Write (paralel untuk 4 sheets)
    ↓
Merge: tunggu semua 4 Write selesai
    ↓
Split anomalies → Clean → Append VALIDATION_QUEUE (24 rows)
    ↓
Build Log → Clean → Append AUTOMATION_LOG (4 rows)
    ↓
Cek anomali → Kirim email (jika ada)
```

---

## 5. 10 Tipe Anomali yang Dideteksi

### TYPE 1 — Comma Decimal Separator ✅ AUTO-FIXED

**Sheet:** `bag_production`
**Field:** `weight`
**Contoh:** `"18,15"` → `18.15`

```javascript
if (w.includes(',')) {
  const fixed = parseFloat(w.replace(',', '.'));
  fixedBagProd[i].weight = fixed;
}
```

Anomali ini **langsung diperbaiki** di data — row tetap masuk ke CLEANED sheet.

---

### TYPE 2 — Negative Values ⚠️ FLAG

**Sheet:** `bag_production`, `biochar_production`
**Fields:** `weight`, `co2e_persistent`, `co2e_100`, `spc`

Field-field ini secara fisik tidak mungkin bernilai negatif. Nilai negatif = error input operator.

---

### TYPE 3 — Missing Critical Fields ⚠️ FLAG

**Sheet:** `bag_production`, `biochar_production`
**Fields:** `weight`, `carbon_content_%`

Kedua field ini wajib diisi karena kritikal untuk perhitungan CO₂e dan carbon sequestration credit.

---

### TYPE 4 — Duplicate bag_id ⚠️ FLAG

**Sheet:** `bag_production`
**Field:** `bag_id`

Setiap `bag_id` harus unik. Kemungkinan penyebab:
- Operator scan bag yang sama dua kali
- Bag ditimbang ulang dengan berat berbeda

**Auto-dedup:** Pipeline secara otomatis keep first occurrence dan flag duplikatnya.

---

### TYPE 5 — Future Timestamps / Suspicious Date ⚠️ FLAG

**Sheet:** Semua 4 sheets
**Fields:** `Timestamp`, `application_date`

Dua sub-pengecekan:
1. **`Timestamp > today`** → tidak mungkin ada data dari masa depan
2. **`application_date` > 30 hari setelah `Timestamp`** → suspicious: operator tidak mungkin input data sekarang untuk kejadian yang baru terjadi 30+ hari kemudian

---

### TYPE 6 — Invalid application_type ⚠️ FLAG

**Sheet:** `biochar_application`
**Field:** `application_type`

Nilai yang valid:
```
- Application-Pure Biochar
- Application-Charged Biochar
- Sale-Pure Biochar
- Sale-Charged Biochar
```

Nilai lain (misal: `Application-Enriched Biochar`) = TYPE 6 anomali.

---

### TYPE 7 — Orphan bag_id ⚠️ FLAG

**Sheet:** `bag_application` (cross-sheet vs `bag_production`)

**Key Rule dari Brief:** Setiap `bag_id` di `bag_application` harus ada di `bag_production`. Kalau tidak ada = orphan bag = tidak punya production record.

```javascript
const bpids = new Set(lookup.bag_prod_id_set);
if (bid && !bpids.has(bid)) → TYPE 7
```

---

### TYPE 8 — Weight Discrepancy >5% ⚠️ FLAG

**Sheet:** `bag_application` vs `bag_production` (cross-sheet)

Membandingkan `bag_weight` di `bag_application` dengan `weight` di `bag_production`.
Selisih > 5% = anomali.

```javascript
const disc = Math.abs(appW - prodW) / prodW;
if (disc > 0.05) → TYPE 8
```

---

### TYPE 9 — Batch Sum Mismatch ⚠️ FLAG

**Sheet:** `bag_production` vs `biochar_production` (cross-sheet)

Sum semua bag weights per `production_id`, bandingkan dengan `biochar_amount_kg` yang dideklarasikan di `biochar_production`. Selisih > 0.01 kg = anomali.

```javascript
const batchSum = sum of bag weights for this production_id
const declared = biochar_amount_kg
if (Math.abs(batchSum - declared) > 0.01) → TYPE 9
```

---

### TYPE 10 — Bag in Multiple Application Batches ⚠️ FLAG

**Sheet:** `bag_application` (cross-row)

**Key Rule dari Brief:** Satu `bag_id` hanya boleh muncul di **SATU** application batch. Bag yang sama di 2+ batch = data integrity violation.

```javascript
const bagAppMap = { bag_id: [application_id1, application_id2, ...] }
if (appIds.length > 1) → TYPE 10
```

---

## 6. Output Sheets

### CLEANED Sheets (4 sheets)

Data yang sudah bersih, siap digunakan untuk reporting dan analysis.

| Sheet | Rows Input | Rows Cleaned |
|-------|-----------|--------------|
| CLEANED_prod_batch | 7 | 5–6 |
| CLEANED_bag_prod | 78 | ~60–70 |
| CLEANED_app_batch | 5 | 3–4 |
| CLEANED_bag_app | 42 | ~30–35 |

Setiap row punya kolom tambahan `_cleaning_note: 'auto-cleaned'`.

### VALIDATION_QUEUE

Antrian review untuk anomali TYPE 2–10. Tim perlu mengisi:

| Kolom | Isi | Contoh |
|-------|-----|--------|
| `Reviewed_By` | Nama reviewer | `nia@wastex.io` |
| `Resolution` | Keputusan | `approved` / `rejected` / `corrected` |
| `Resolved_At` | Tanggal selesai | `2024-11-15` |

### AUTOMATION_LOG

Satu baris per sheet per run. Total 4 baris setiap kali pipeline berjalan.

---

## 7. Setup & Cara Import

### Prerequisites

- n8n versi 2.x (self-hosted atau cloud)
- Akun Google dengan akses ke Google Sheet WasteX
- Google Cloud Project dengan Google Sheets API dan Google Drive API aktif
- Gmail account untuk kirim notifikasi

### Step 1 — Setup Google OAuth2

1. Buka [Google Cloud Console](https://console.cloud.google.com/)
2. Buat atau pilih project
3. **APIs & Services → Library** → Enable:
   - Google Sheets API
   - Google Drive API
4. **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
5. Application type: **Web application**
6. **Authorized JavaScript origins:**
   ```
   https://[url-n8n-kamu]
   ```
7. **Authorized redirect URIs:**
   ```
   https://[url-n8n-kamu]/rest/oauth2-credential/callback
   ```
8. Download credentials → catat **Client ID** dan **Client Secret**

### Step 2 — Setup OAuth Consent Screen

1. **APIs & Services → OAuth consent screen**
2. User type: **External**
3. Isi App name, email, dll
4. **Scopes:** tambahkan Google Sheets dan Google Drive scopes
5. **Test users:** tambahkan email Google kamu
6. Save

### Step 3 — Import Workflow ke n8n

1. Buka n8n → menu kiri → **Workflows**
2. Klik **⋯ → Import from file**
3. Upload `WasteX_n8n_v4d.json`
4. Workflow muncul dengan semua 37 node

### Step 4 — Connect Google Sheets Credential

Untuk setiap node Google Sheets (14 node):
1. Klik node
2. Panel kanan → **Credential** → **+ Create new credential**
3. Isi Client ID dan Client Secret
4. Klik **Sign in with Google**
5. Login dengan akun Google kamu
6. Save

> Setelah credential pertama berhasil dibuat, node lain tinggal **pilih credential yang sama** — tidak perlu Sign in lagi.

### Step 5 — Connect Gmail Credential

1. Klik node **📨 Send Email Notification**
2. **Credential → + Create new → Gmail OAuth2**
3. Isi Client ID dan Client Secret yang sama
4. Klik **Sign in with Google**
5. Pilih akun Gmail untuk kirim email
6. Save

### Step 6 — Test

```
Klik Execute workflow → semua node harus hijau ✅
```

Cek di Google Sheet:
- Tab `CLEANED_prod_batch` → ada data bersih
- Tab `VALIDATION_QUEUE` → ada anomali yang di-flag
- Tab `AUTOMATION_LOG` → ada 4 baris log baru

### Step 7 — Aktifkan Trigger

Klik tombol **Activate** di pojok kanan atas → workflow akan jalan otomatis setiap hari jam 07:00.

---

## 8. Troubleshooting

### Error: "Quota exceeded — too many requests"

```
Penyebab : Terlalu banyak eksekusi dalam waktu singkat selama testing
Solusi   : Tunggu 1–2 menit, lalu Execute workflow lagi
Limit    : Google Sheets API 60 read requests/menit per user
```

### Error: "Unable to sign without access token"

```
Penyebab : Node Google Sheets belum terhubung ke credential
Solusi   : Klik node → pilih credential Google Sheets di dropdown
```

### Error: "Access blocked: has not completed Google verification"

```
Penyebab : Email tidak terdaftar sebagai test user di OAuth consent screen
Solusi   : Google Cloud → APIs & Services → OAuth consent screen
           → Test users → Add email kamu → Save
```

### Error: "More than 50000 characters in a single cell"

```
Penyebab : Field internal _pp (pipeline payload) ikut ke-write ke sheet
Solusi   : Pastikan node 🧼 Clean Before Queue Write dan 🧼 Clean Before Log Write
           ada di workflow dan sudah terhubung dengan benar
```

### Error: "At least one value has to be added under Values to Send"

```
Penyebab : Node Append pakai defineBelow tapi tidak ada field yang di-map
Solusi   : Ubah Mapping Column Mode ke "Map Automatically"
```

### Error: "Node X hasn't been executed"

```
Penyebab : Node Code mencoba akses $(nodeName) tapi node itu belum jalan
Solusi   : Pastikan semua Read nodes sudah terconnect credential
           dan sudah jalan sebelum Collect All Sheets dipanggil
```

### Hanya 1 jalur paralel yang jalan

```
Penyebab : n8n tidak otomatis menunggu semua jalur paralel sebelum lanjut
Solusi   : Pastikan semua 4 Write nodes terconnect ke ⏳ Wait All Writes Done
           dengan index berbeda (0, 1, 2, 3)
```

### Data CLEANED sheet muncul sebagai JSON string di satu kolom

```
Penyebab : Data belum di-flatten sebelum ditulis ke sheet
Solusi   : Pastikan 📊 Flatten nodes ada di antara Prepare Write Data
           dan Clear nodes
```

---

## 9. Pertanyaan Umum (FAQ)

**Q: Apakah pipeline akan duplikat data kalau dijalankan dua kali?**

A: Untuk CLEANED sheets — tidak, karena sheet di-clear dulu sebelum ditulis ulang. Untuk VALIDATION_QUEUE dan AUTOMATION_LOG — ya, akan ada duplikat karena menggunakan Append. Solusi: tambahkan dedup check sebelum Append berdasarkan `detected_at + Record_ID + anomaly_type`.

---

**Q: Kenapa ada banyak node "Restore" dan "Collect"?**

A: Ini konsekuensi dari arsitektur paralel di n8n. Ketika banyak jalur paralel bergabung (fan-in), data dari jalur sebelumnya tidak otomatis tersedia — perlu di-"restore" dari node upstream via referensi `$(nodeName)`.

---

**Q: Bagaimana cara update threshold anomali (misal ubah dari 5% ke 10%)?**

A: Edit node `🔍 Detect All 10 Anomaly Types`:
```javascript
const WEIGHT_PCT = 0.10;  // ubah dari 0.05 ke 0.10
```

---

**Q: Bagaimana cara tambah jenis feedstock baru ke validasi TYPE 6?**

A: Edit node `🔍 Detect All 10 Anomaly Types`:
```javascript
const VALID = [
  'Application-Pure Biochar',
  'Application-Charged Biochar',
  'Sale-Pure Biochar',
  'Sale-Charged Biochar',
  'Application-Enriched Biochar',  // ← tambah di sini
];
```

---

**Q: Apakah pipeline bisa dijalankan untuk sheet Google yang berbeda?**

A: Ya. Ubah `SPREADSHEET_ID` di semua node Google Sheets. Cara paling mudah: cari-ganti `1QqSa7reb4i2Oz7pnbb6sAflJEtbsCwF4m19J7aDgsoE` dengan ID baru di file JSON sebelum di-import.

---

**Q: Kenapa email tidak terkirim meskipun ada anomali?**

A: Cek:
1. Gmail credential sudah terautentikasi
2. `should_notify` di node Check Notify bernilai `true`
3. Lihat execution log node `📨 Send Email Notification` untuk error detail

---

**Q: Apakah bisa menambah penerima email lebih dari satu?**

A: Ya. Edit node `📧 Build Email`:
```javascript
to: 'email1@wastex.io, email2@wastex.io',
```

---

*Dokumen ini dibuat untuk WasteX Data Analyst Skills Test · Versi pipeline: v4d · 37 nodes · 10 anomaly types*
