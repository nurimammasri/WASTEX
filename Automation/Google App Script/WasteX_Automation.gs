/**
 * WasteX Data Pipeline — Google Apps Script Automation
 * =====================================================
 * Cara pakai:
 * 1. Buka Google Sheet kamu → Extensions → Apps Script
 * 2. Copy semua kode ini ke editor
 * 3. Isi CONFIG di bawah sesuai kebutuhanmu
 * 4. Jalankan setupTrigger() SATU KALI untuk aktifkan trigger harian
 * 5. Selesai — pipeline akan jalan otomatis setiap hari
 *
 * File ini berisi:
 * - CONFIG            : semua setting di satu tempat
 * - setupTrigger()    : pasang trigger harian (jalankan sekali)
 * - runPipeline()     : fungsi utama, dipanggil trigger
 * - detectAnomalies() : deteksi 10 tipe anomali
 * - writeCleanedSheets() : tulis hasil ke CLEANED sheets
 * - writeValidationQueue() : tulis anomali ke VALIDATION_QUEUE
 * - writeAutomationLog() : tulis log per run
 * - sendNotification() : kirim email kalau ada anomali
 */

// ─────────────────────────────────────────────────────────
// CONFIG — ubah sesuai kebutuhanmu
// ─────────────────────────────────────────────────────────
const CONFIG = {
  // Email yang dapat notifikasi kalau ada anomali baru
  NOTIFICATION_EMAIL: 'kamu@email.com',

  // Nama sheet sumber data
  SHEET_BIOCHAR_PROD:  'biochar_production',
  SHEET_BAG_PROD:      'bag_production',
  SHEET_BIOCHAR_APP:   'biochar_application',
  SHEET_BAG_APP:       'bag_application',

  // Nama sheet output
  SHEET_CLEANED_PROD:  'CLEANED_prod_batch',
  SHEET_CLEANED_BAG:   'CLEANED_bag_prod',
  SHEET_CLEANED_APP:   'CLEANED_app_batch',
  SHEET_CLEANED_BAGAPP:'CLEANED_bag_app',
  SHEET_QUEUE:         'VALIDATION_QUEUE',
  SHEET_LOG:           'AUTOMATION_LOG',

  // Threshold TYPE 5: hari maksimum application_date boleh
  // lebih lambat dari Timestamp (default 30 hari)
  MAX_APP_DATE_GAP_DAYS: 30,

  // Threshold TYPE 8: maksimum selisih berat (default 5%)
  WEIGHT_DISCREPANCY_PCT: 0.05,

  // Nilai valid untuk application_type (TYPE 6)
  VALID_APP_TYPES: [
    'Application-Pure Biochar',
    'Application-Charged Biochar',
    'Sale-Pure Biochar',
    'Sale-Charged Biochar',
  ],
};

// ─────────────────────────────────────────────────────────
// SETUP TRIGGER — jalankan SATU KALI dari menu Apps Script
// ─────────────────────────────────────────────────────────
function setupTrigger() {
  // Hapus trigger lama supaya tidak dobel
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));

  // Buat trigger baru: jalan setiap hari jam 07.00
  ScriptApp.newTrigger('runPipeline')
    .timeBased()
    .everyDays(1)
    .atHour(7)
    .create();

  Logger.log('Trigger berhasil dipasang: runPipeline() akan jalan setiap hari jam 07.00');
}

// ─────────────────────────────────────────────────────────
// FUNGSI UTAMA — dipanggil oleh trigger harian
// ─────────────────────────────────────────────────────────
function runPipeline() {
  const ss        = SpreadsheetApp.getActiveSpreadsheet();
  const startTime = new Date();

  Logger.log('=== WasteX Pipeline dimulai: ' + startTime + ' ===');

  try {
    // 1. Load semua data dari sheet sumber
    const data = loadAllSheets(ss);
    Logger.log('Data berhasil di-load');

    // 2. Deteksi anomali di semua 4 sheet
    const { anomalies, cleanedData } = detectAnomalies(data);
    Logger.log('Deteksi anomali selesai. Ditemukan: ' + anomalies.length + ' anomali');

    // 3. Tulis hasil ke CLEANED sheets
    writeCleanedSheets(ss, cleanedData);
    Logger.log('CLEANED sheets berhasil ditulis');

    // 4. Tulis anomali ke VALIDATION_QUEUE
    const newAnomalies = writeValidationQueue(ss, anomalies);
    Logger.log('VALIDATION_QUEUE berhasil ditulis. Anomali baru: ' + newAnomalies);

    // 5. Tulis log ke AUTOMATION_LOG
    const endTime = new Date();
    writeAutomationLog(ss, startTime, endTime, data, anomalies, 'SUCCESS', '');
    Logger.log('AUTOMATION_LOG berhasil ditulis');

    // 6. Kirim notifikasi email kalau ada anomali baru
    if (newAnomalies > 0) {
      sendNotification(anomalies, newAnomalies, startTime);
      Logger.log('Notifikasi email dikirim ke: ' + CONFIG.NOTIFICATION_EMAIL);
    }

    Logger.log('=== Pipeline selesai: ' + new Date() + ' ===');

  } catch (error) {
    // Kalau ada error, tetap tulis ke log dan kirim notifikasi error
    const endTime = new Date();
    writeAutomationLog(ss, startTime, endTime, {}, [], 'ERROR', error.message);
    sendErrorNotification(error);
    Logger.log('ERROR: ' + error.message);
    throw error;
  }
}

// ─────────────────────────────────────────────────────────
// LOAD DATA — baca semua sheet jadi array of objects
// ─────────────────────────────────────────────────────────
function loadAllSheets(ss) {
  return {
    biocharProd: sheetToObjects(ss, CONFIG.SHEET_BIOCHAR_PROD),
    bagProd:     sheetToObjects(ss, CONFIG.SHEET_BAG_PROD),
    biocharApp:  sheetToObjects(ss, CONFIG.SHEET_BIOCHAR_APP),
    bagApp:      sheetToObjects(ss, CONFIG.SHEET_BAG_APP),
  };
}

function sheetToObjects(ss, sheetName) {
  const sheet  = ss.getSheetByName(sheetName);
  if (!sheet) throw new Error('Sheet tidak ditemukan: ' + sheetName);

  const values = sheet.getDataRange().getValues();
  if (values.length < 2) return [];

  const headers = values[0];
  return values.slice(1).map((row, rowIndex) => {
    const obj = { _rowIndex: rowIndex + 2 }; // +2 karena header di row 1
    headers.forEach((h, i) => obj[h] = row[i]);
    return obj;
  });
}

// ─────────────────────────────────────────────────────────
// DETEKSI ANOMALI — 10 tipe sesuai brief
// ─────────────────────────────────────────────────────────
function detectAnomalies(data) {
  const anomalies  = [];
  const cleanedData = {
    biocharProd: [...data.biocharProd],
    bagProd:     [...data.bagProd],
    biocharApp:  [...data.biocharApp],
    bagApp:      [...data.bagApp],
  };

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  // Lookup maps untuk cross-sheet checks
  const bagProdWeightMap = {};
  const bagProdIdSet     = new Set();

  // ── TYPE 1: Comma decimal separator ──────────────────
  data.bagProd.forEach((row, idx) => {
    const w = String(row['weight'] || '');
    if (w.includes(',')) {
      const fixed = parseFloat(w.replace(',', '.'));
      anomalies.push(logAnomaly(
        'bag_production', 'TYPE 1',
        'Comma decimal separator: "' + w + '" → ' + fixed,
        'weight', w,
        String(fixed),
        'AUTO-FIXED → CLEANED',
        row['bag_id'] || ''
      ));
      // Auto-fix: update nilai di cleanedData
      cleanedData.bagProd[idx]['weight'] = fixed;
    }
    // Isi lookup setelah kemungkinan fix
    const wNum = parseFloat(String(cleanedData.bagProd[idx]['weight']).replace(',', '.'));
    if (!isNaN(wNum)) bagProdWeightMap[row['bag_id']] = wNum;
    bagProdIdSet.add(row['bag_id']);
  });

  // ── TYPE 2: Negative values ───────────────────────────
  const negFieldsBagProd  = ['weight', 'co2e_persistent', 'co2e_100', 'spc'];
  const negFieldsBiocharProd = ['co2e_persistent', 'co2e_100', 'spc'];

  cleanedData.bagProd.forEach(row => {
    negFieldsBagProd.forEach(field => {
      const val = parseFloat(row[field]);
      if (!isNaN(val) && val < 0) {
        anomalies.push(logAnomaly(
          'bag_production', 'TYPE 2',
          'Negative value: ' + field + '=' + val,
          field, val,
          'Requires human review',
          'FLAGGED → VALIDATION_QUEUE',
          row['bag_id'] || ''
        ));
      }
    });
  });

  data.biocharProd.forEach(row => {
    negFieldsBiocharProd.forEach(field => {
      const val = parseFloat(row[field]);
      if (!isNaN(val) && val < 0) {
        anomalies.push(logAnomaly(
          'biochar_production', 'TYPE 2',
          'Negative value: ' + field + '=' + val,
          field, val,
          'Requires human review',
          'FLAGGED → VALIDATION_QUEUE',
          row['activity_id'] || ''
        ));
      }
    });
  });

  // ── TYPE 3: Missing critical fields ──────────────────
  cleanedData.bagProd.forEach(row => {
    if (row['weight'] === '' || row['weight'] === null || row['weight'] === undefined) {
      anomalies.push(logAnomaly(
        'bag_production', 'TYPE 3',
        'Missing critical field: weight is empty',
        'weight', '',
        'Requires human review',
        'FLAGGED → VALIDATION_QUEUE',
        row['bag_id'] || ''
      ));
    }
  });

  data.biocharProd.forEach(row => {
    const cc = row['carbon_content_%'];
    if (cc === '' || cc === null || cc === undefined) {
      anomalies.push(logAnomaly(
        'biochar_production', 'TYPE 3',
        'Missing critical field: carbon_content_% is empty',
        'carbon_content_%', '',
        'Requires human review',
        'FLAGGED → VALIDATION_QUEUE',
        row['activity_id'] || ''
      ));
    }
  });

  // ── TYPE 4: Duplicate bag_id ──────────────────────────
  const bagIdCount = {};
  data.bagProd.forEach(row => {
    const bid = row['bag_id'];
    bagIdCount[bid] = (bagIdCount[bid] || 0) + 1;
  });

  data.bagProd.forEach(row => {
    const bid = row['bag_id'];
    if (bagIdCount[bid] > 1) {
      anomalies.push(logAnomaly(
        'bag_production', 'TYPE 4',
        'Duplicate bag_id with weight=' + row['weight'],
        'bag_id', bid,
        'Keep first occurrence; reconcile or remove duplicate',
        'FLAGGED → VALIDATION_QUEUE',
        bid
      ));
    }
  });

  // ── TYPE 5: Future timestamps / suspicious application_date ──
  const allSheets = [
    { name: 'biochar_production',  rows: data.biocharProd,  idField: 'activity_id' },
    { name: 'bag_production',      rows: data.bagProd,      idField: 'bag_id' },
    { name: 'biochar_application', rows: data.biocharApp,   idField: 'activity_id' },
    { name: 'bag_application',     rows: data.bagApp,       idField: 'bag_id' },
  ];

  allSheets.forEach(({ name, rows, idField }) => {
    rows.forEach(row => {
      const ts = new Date(row['Timestamp']);
      if (!isNaN(ts) && ts > today) {
        anomalies.push(logAnomaly(
          name, 'TYPE 5',
          'Future Timestamp: ' + row['Timestamp'] + ' (today=' + today.toDateString() + ')',
          'Timestamp', String(row['Timestamp']),
          'Requires human review',
          'FLAGGED → VALIDATION_QUEUE',
          row[idField] || ''
        ));
      }
    });
  });

  // Cek application_date di biochar_application
  data.biocharApp.forEach(row => {
    const ad = new Date(row['application_date']);
    const ts = new Date(row['Timestamp']);

    // Future application_date
    if (!isNaN(ad) && ad > today) {
      anomalies.push(logAnomaly(
        'biochar_application', 'TYPE 5',
        'Future application_date: ' + row['application_date'],
        'application_date', String(row['application_date']),
        'Requires human review',
        'FLAGGED → VALIDATION_QUEUE',
        row['activity_id'] || ''
      ));
    }

    // Suspicious: application_date jauh lebih lambat dari Timestamp
    if (!isNaN(ad) && !isNaN(ts)) {
      const gapDays = Math.round((ad - ts) / (1000 * 60 * 60 * 24));
      if (gapDays > CONFIG.MAX_APP_DATE_GAP_DAYS) {
        anomalies.push(logAnomaly(
          'biochar_application', 'TYPE 5',
          'Suspicious application_date: ' + row['application_date'] +
          ' adalah ' + gapDays + ' hari setelah Timestamp ' + row['Timestamp'] +
          '. Kemungkinan salah input.',
          'application_date', String(row['application_date']),
          'Konfirmasi ke operator apakah application_date benar.',
          'FLAGGED → VALIDATION_QUEUE',
          row['activity_id'] || ''
        ));
      }
    }
  });

  // ── TYPE 6: Invalid application_type ─────────────────
  data.biocharApp.forEach(row => {
    const at = row['application_type'];
    if (!CONFIG.VALID_APP_TYPES.includes(at)) {
      anomalies.push(logAnomaly(
        'biochar_application', 'TYPE 6',
        'Invalid application_type: "' + at + '"',
        'application_type', at,
        'Must be one of: ' + CONFIG.VALID_APP_TYPES.join(', '),
        'FLAGGED → VALIDATION_QUEUE',
        row['activity_id'] || ''
      ));
    }
  });

  // ── TYPE 7: Orphan bag_id ─────────────────────────────
  data.bagApp.forEach(row => {
    const bid = row['bag_id'];
    if (!bagProdIdSet.has(bid)) {
      anomalies.push(logAnomaly(
        'bag_application', 'TYPE 7',
        'Orphan bag_id not in bag_production: ' + bid,
        'bag_id', bid,
        'No matching production record',
        'FLAGGED → VALIDATION_QUEUE',
        bid
      ));
    }
  });

  // ── TYPE 8: Weight discrepancy >5% ───────────────────
  data.bagApp.forEach(row => {
    const bid   = row['bag_id'];
    const appW  = parseFloat(row['bag_weight']);
    const prodW = bagProdWeightMap[bid];

    if (!isNaN(appW) && prodW !== undefined) {
      const disc = Math.abs(appW - prodW) / prodW;
      if (disc > CONFIG.WEIGHT_DISCREPANCY_PCT) {
        anomalies.push(logAnomaly(
          'bag_application', 'TYPE 8',
          'Weight discrepancy ' + (disc * 100).toFixed(1) + '%: app=' + appW.toFixed(2) + ' vs prod=' + prodW.toFixed(2),
          'bag_weight', appW,
          'Production weight=' + prodW.toFixed(2) + '. Reconcile.',
          'FLAGGED → VALIDATION_QUEUE',
          bid
        ));
      }
    }
  });

  // ── TYPE 9: Batch sum mismatch ────────────────────────
  const batchSums = {};
  cleanedData.bagProd.forEach(row => {
    const pid = row['production_id'];
    const w   = parseFloat(String(row['weight']).replace(',', '.'));
    if (!isNaN(w)) batchSums[pid] = (batchSums[pid] || 0) + w;
  });

  data.biocharProd.forEach(row => {
    const pid      = row['activity_id'];
    const declared = parseFloat(row['biochar_amount_kg']);
    const bagSum   = batchSums[pid];
    if (bagSum !== undefined && !isNaN(declared)) {
      const diff = Math.abs(bagSum - declared);
      if (diff > 0.01) {
        anomalies.push(logAnomaly(
          'bag_production', 'TYPE 9',
          'Batch sum mismatch: bags=' + bagSum.toFixed(2) + ' kg vs declared=' + declared.toFixed(2) + ' kg (Δ=' + diff.toFixed(2) + ')',
          'biochar_amount_kg vs sum(bag weights)',
          'bags_sum=' + bagSum.toFixed(2),
          'Declared=' + declared.toFixed(2) + ' kg. Reconcile.',
          'FLAGGED → VALIDATION_QUEUE',
          pid
        ));
      }
    }
  });

  // ── TYPE 10: Bag in multiple application batches ──────
  const bagAppMap = {};
  data.bagApp.forEach(row => {
    const bid = row['bag_id'];
    const aid = row['application_id'];
    if (!bagAppMap[bid]) bagAppMap[bid] = new Set();
    bagAppMap[bid].add(aid);
  });

  data.bagApp.forEach(row => {
    const bid     = row['bag_id'];
    const appIds  = [...(bagAppMap[bid] || [])];
    if (appIds.length > 1) {
      anomalies.push(logAnomaly(
        'bag_application', 'TYPE 10',
        'Bag used in ' + appIds.length + ' application batches: [' + appIds.join(', ') + ']',
        'bag_id / application_id', bid,
        'bag_id must appear in only ONE application batch.',
        'FLAGGED → VALIDATION_QUEUE',
        bid
      ));
    }
  });

  return { anomalies, cleanedData };
}

// Helper: buat objek anomali dengan struktur konsisten
function logAnomaly(sheet, type, desc, field, origVal, fix, action, recordId) {
  return {
    Sheet          : sheet,
    anomaly_type   : type,
    description    : desc,
    Field          : field,
    original_value : origVal,
    suggested_fix  : fix,
    action         : action,
    Record_ID      : recordId,
    detected_at    : new Date().toISOString(),
    Reviewed_By    : '',
    Resolution     : '',
    Resolved_At    : '',
  };
}

// ─────────────────────────────────────────────────────────
// WRITE CLEANED SHEETS
// ─────────────────────────────────────────────────────────
function writeCleanedSheets(ss, cleanedData) {
  // Tentukan row yang di-flag (TYPE 2-10) per sheet → exclude dari CLEANED
  // Di sini kita pakai pendekatan simpel: tulis semua row yang tidak ada di flaggedIds

  writeSheetFromObjects(ss, CONFIG.SHEET_CLEANED_PROD,   cleanedData.biocharProd, '_cleaning_note', 'auto-cleaned');
  writeSheetFromObjects(ss, CONFIG.SHEET_CLEANED_BAG,    cleanedData.bagProd,     '_cleaning_note', 'auto-cleaned');
  writeSheetFromObjects(ss, CONFIG.SHEET_CLEANED_APP,    cleanedData.biocharApp,  '_cleaning_note', 'auto-cleaned');
  writeSheetFromObjects(ss, CONFIG.SHEET_CLEANED_BAGAPP, cleanedData.bagApp,      '_cleaning_note', 'auto-cleaned');
}

function writeSheetFromObjects(ss, sheetName, dataRows, noteCol, noteVal) {
  const sheet = ss.getSheetByName(sheetName);
  if (!sheet) {
    Logger.log('Sheet tidak ditemukan, skip: ' + sheetName);
    return;
  }

  // Hapus isi lama (kecuali header row 1)
  const lastRow = sheet.getLastRow();
  if (lastRow > 1) sheet.getRange(2, 1, lastRow - 1, sheet.getLastColumn()).clearContent();

  if (dataRows.length === 0) return;

  // Ambil header dari sheet yang ada
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];

  // Tulis data baris per baris
  const outputRows = dataRows.map(row => {
    return headers.map(h => {
      if (h === noteCol) return noteVal;
      if (h === '_rowIndex') return '';
      return row[h] !== undefined ? row[h] : '';
    });
  });

  if (outputRows.length > 0) {
    sheet.getRange(2, 1, outputRows.length, headers.length).setValues(outputRows);
  }
}

// ─────────────────────────────────────────────────────────
// WRITE VALIDATION QUEUE
// ─────────────────────────────────────────────────────────
function writeValidationQueue(ss, anomalies) {
  const sheet = ss.getSheetByName(CONFIG.SHEET_QUEUE);
  if (!sheet) {
    Logger.log('VALIDATION_QUEUE sheet tidak ditemukan');
    return 0;
  }

  // Header kolom VALIDATION_QUEUE
  const headers = [
    'Sheet', 'anomaly_type', 'description', 'Field',
    'original_value', 'suggested_fix', 'action', 'Record_ID',
    'detected_at', 'Reviewed_By', 'Resolution', 'Resolved_At',
  ];

  // Pastikan header sudah ada di row 1
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);

  // Ambil Record_ID yang sudah ada di queue (hindari duplikat per run)
  const existingData  = sheet.getDataRange().getValues();
  const existingKeys  = new Set();
  existingData.slice(1).forEach(row => {
    // Key unik: Sheet + anomaly_type + Record_ID
    existingKeys.add(row[0] + '|' + row[1] + '|' + row[7]);
  });

  // Filter hanya anomali baru
  const newAnomalies = anomalies.filter(a => {
    const key = a.Sheet + '|' + a.anomaly_type + '|' + a.Record_ID;
    return !existingKeys.has(key);
  });

  if (newAnomalies.length > 0) {
    const rows = newAnomalies.map(a => headers.map(h => a[h] !== undefined ? a[h] : ''));
    sheet.getRange(sheet.getLastRow() + 1, 1, rows.length, headers.length).setValues(rows);
  }

  return newAnomalies.length;
}

// ─────────────────────────────────────────────────────────
// WRITE AUTOMATION LOG
// ─────────────────────────────────────────────────────────
function writeAutomationLog(ss, startTime, endTime, data, anomalies, status, errorMsg) {
  const sheet = ss.getSheetByName(CONFIG.SHEET_LOG);
  if (!sheet) {
    Logger.log('AUTOMATION_LOG sheet tidak ditemukan');
    return;
  }

  const headers = [
    'run_timestamp', 'sheet_processed', 'total_rows_input',
    'anomalies_detected', 'auto_fixed', 'flagged_for_review',
    'anomaly_types_found', 'duration_seconds', 'status', 'error_message',
  ];

  // Pastikan header ada
  if (sheet.getLastRow() === 0) {
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  }

  const durationSec = Math.round((endTime - startTime) / 1000);
  const sheetConfigs = [
    { name: CONFIG.SHEET_BIOCHAR_PROD,  rows: data.biocharProd || [] },
    { name: CONFIG.SHEET_BAG_PROD,      rows: data.bagProd || [] },
    { name: CONFIG.SHEET_BIOCHAR_APP,   rows: data.biocharApp || [] },
    { name: CONFIG.SHEET_BAG_APP,       rows: data.bagApp || [] },
  ];

  const logRows = sheetConfigs.map(({ name, rows }) => {
    const sheetAnomalies = anomalies.filter(a => a.Sheet.startsWith(name.replace('_', '_')));
    const autoFixed      = sheetAnomalies.filter(a => a.anomaly_type === 'TYPE 1').length;
    const flagged        = sheetAnomalies.filter(a => a.anomaly_type !== 'TYPE 1').length;
    const typesFound     = [...new Set(sheetAnomalies.map(a => a.anomaly_type))].sort().join(', ');

    return [
      startTime.toISOString(),
      name,
      rows.length,
      sheetAnomalies.length,
      autoFixed,
      flagged,
      typesFound,
      durationSec,
      status,
      errorMsg,
    ];
  });

  sheet.getRange(sheet.getLastRow() + 1, 1, logRows.length, headers.length).setValues(logRows);
}

// ─────────────────────────────────────────────────────────
// NOTIFIKASI EMAIL
// ─────────────────────────────────────────────────────────
function sendNotification(anomalies, newCount, runTime) {
  const ssUrl    = SpreadsheetApp.getActiveSpreadsheet().getUrl();
  const flagged  = anomalies.filter(a => a.action.includes('VALIDATION_QUEUE'));
  const autoFixed = anomalies.filter(a => a.action.includes('AUTO-FIXED'));

  // Buat ringkasan per tipe
  const typeSummary = {};
  flagged.forEach(a => {
    typeSummary[a.anomaly_type] = (typeSummary[a.anomaly_type] || 0) + 1;
  });

  const summaryLines = Object.entries(typeSummary)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([type, count]) => '• ' + type + ': ' + count + ' finding(s)')
    .join('\n');

  const subject = '[WasteX Pipeline] ' + newCount + ' anomali baru ditemukan — ' + runTime.toDateString();

  const body = `
WasteX Data Pipeline — Laporan Otomatis
=========================================
Waktu run : ${runTime.toISOString()}
Anomali baru ditemukan : ${newCount}

RINGKASAN ANOMALI:
${summaryLines}

Auto-fixed (TYPE 1) : ${autoFixed.length} record(s)
Butuh review manusia : ${flagged.length} record(s)

Silakan cek VALIDATION_QUEUE untuk detail dan lakukan review:
${ssUrl}

---
Email ini dikirim otomatis oleh WasteX Pipeline.
Untuk menonaktifkan, hapus trigger di Apps Script.
  `.trim();

  MailApp.sendEmail({
    to      : CONFIG.NOTIFICATION_EMAIL,
    subject : subject,
    body    : body,
  });
}

function sendErrorNotification(error) {
  const subject = '[WasteX Pipeline] ERROR — Pipeline gagal berjalan';
  const body = `
WasteX Data Pipeline mengalami ERROR:
======================================
Waktu   : ${new Date().toISOString()}
Error   : ${error.message}
Stack   : ${error.stack || 'tidak tersedia'}

Silakan cek Apps Script execution log untuk detail lebih lanjut.
  `.trim();

  MailApp.sendEmail({
    to      : CONFIG.NOTIFICATION_EMAIL,
    subject : subject,
    body    : body,
  });
}
