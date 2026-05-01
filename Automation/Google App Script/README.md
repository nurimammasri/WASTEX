# WasteX Pipeline Automation — Setup Guide

## Overview

Pipeline ini berjalan otomatis setiap hari menggunakan **Google Apps Script**,
membaca data dari Google Sheet, mendeteksi 10 tipe anomali, menulis hasil ke
CLEANED sheets + VALIDATION_QUEUE, dan mengirim notifikasi email.

---

## Cara Setup (5 menit)

### Step 1 — Buka Apps Script
1. Buka Google Sheet WasteX kamu
2. Klik menu **Extensions → Apps Script**
3. Editor Apps Script akan terbuka

### Step 2 — Copy Script
1. Hapus semua kode default yang ada (function myFunction...)
2. Copy seluruh isi file `WasteX_Automation.gs`
3. Paste ke editor Apps Script
4. Klik **Save** (ikon floppy disk atau Ctrl+S)

### Step 3 — Isi CONFIG
Di bagian paling atas script, ubah nilai CONFIG sesuai kebutuhanmu:

```javascript
const CONFIG = {
  NOTIFICATION_EMAIL: 'emailkamu@gmail.com',  // ← WAJIB diubah
  // ... sisanya bisa dibiarkan default
};
```

### Step 4 — Aktifkan Trigger
1. Di editor Apps Script, pilih fungsi **setupTrigger** dari dropdown
2. Klik tombol **Run** (▶)
3. Izinkan akses saat diminta (Google akan minta permission)
4. Trigger harian jam 07.00 sudah aktif ✅

### Step 5 — Test Manual
1. Pilih fungsi **runPipeline** dari dropdown
2. Klik **Run**
3. Cek tab **Execution Log** untuk memastikan berjalan tanpa error
4. Cek sheet VALIDATION_QUEUE dan AUTOMATION_LOG di Google Sheet

---

## Alur Kerja Pipeline

```
Setiap hari jam 07.00
        ↓
  runPipeline() dipanggil
        ↓
  Load 4 sheet sumber data
        ↓
  Deteksi 10 tipe anomali
        ↓
  ┌─────────────────────────┐
  │   TYPE 1 (auto-fix)     │ → CLEANED sheets
  │   TYPE 2-10 (flag)      │ → VALIDATION_QUEUE
  └─────────────────────────┘
        ↓
  Tulis AUTOMATION_LOG
        ↓
  Ada anomali baru?
  ├── Ya  → Kirim email notifikasi
  └── Tidak → Selesai (tetap log)
```

---

## Notifikasi Email

Email otomatis dikirim ke `NOTIFICATION_EMAIL` setiap kali ada anomali baru.
Format email:
- Ringkasan anomali per tipe
- Jumlah auto-fixed vs butuh review
- Link langsung ke Google Sheet

---

## VALIDATION_QUEUE — Kolom untuk Review

Setelah menerima notifikasi, tim perlu mengisi kolom berikut di VALIDATION_QUEUE:

| Kolom | Isi |
|-------|-----|
| `Reviewed_By` | Nama reviewer |
| `Resolution` | `approved` / `rejected` / `corrected` |
| `Resolved_At` | Tanggal review selesai |

---

## Kustomisasi

### Ubah jadwal trigger
Di fungsi `setupTrigger()`, ubah `.atHour(7)` ke jam yang diinginkan:
```javascript
.atHour(7)   // jam 07.00
.atHour(9)   // jam 09.00
```

### Tambah penerima email
```javascript
MailApp.sendEmail({
  to: 'email1@gmail.com, email2@gmail.com',  // pisah dengan koma
  ...
});
```

### Ubah threshold TYPE 8 (weight discrepancy)
```javascript
WEIGHT_DISCREPANCY_PCT: 0.05,  // 5% default → ubah ke 0.10 untuk 10%
```

### Ubah threshold TYPE 5 (gap application_date)
```javascript
MAX_APP_DATE_GAP_DAYS: 30,  // 30 hari default
```

---

## Troubleshooting

**Pipeline tidak jalan otomatis**
→ Cek apakah trigger sudah terpasang: Apps Script → Triggers (ikon jam)

**Error "Sheet tidak ditemukan"**
→ Pastikan nama sheet di CONFIG sama persis dengan nama sheet di Google Sheet

**Email tidak terkirim**
→ Pastikan Apps Script sudah diberi permission akses Gmail saat pertama run

**Mau jalankan manual**
→ Pilih `runPipeline` di dropdown → klik Run

---

## File Structure

```
wastex_automation/
├── WasteX_Automation.gs   ← Script utama (copy ke Apps Script)
└── README.md              ← Panduan ini
```
