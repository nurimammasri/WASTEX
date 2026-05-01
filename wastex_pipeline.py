"""
WasteX Data Analyst Skills Test — Cleaning Pipeline
Detects 10 anomaly types, routes records, populates output sheets.
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, date
import warnings
warnings.filterwarnings('ignore')

# Fix for Windows console unicode errors
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

os.makedirs('data', exist_ok=True)

INPUT_FILE = os.path.join('data', 'WasteX_DA_Test_Dataset_final.xlsx')
OUTPUT_FILE = os.path.join('data', 'WasteX_Cleaned_Output.xlsx')

TODAY = date.today()

VALID_APPLICATION_TYPES = [
    'Application-Pure Biochar',
    'Application-Charged Biochar',
    'Sale-Pure Biochar',
    'Sale-Charged Biochar',
]

# ──────────────────────────────────────────────────────
# 1. LOAD RAW DATA
# ──────────────────────────────────────────────────────
def load_data():
    xls = pd.ExcelFile(INPUT_FILE)
    bp = pd.read_excel(xls, 'biochar_production')
    bprod = pd.read_excel(xls, 'bag_production')
    ba = pd.read_excel(xls, 'biochar_application')
    bapp = pd.read_excel(xls, 'bag_application')
    return bp, bprod, ba, bapp

# ──────────────────────────────────────────────────────
# 2. ANOMALY DETECTION
# ──────────────────────────────────────────────────────
def detect_anomalies(bp, bprod, ba, bapp):
    queue = []   # rows for VALIDATION_QUEUE
    fixes = {}   # auto-fixable records by sheet

    # ── TYPE 1: Comma decimal separator (bag_production.weight) ──
    t1_rows = []
    bprod_clean = bprod.copy()
    for i, row in bprod.iterrows():
        w = str(row['weight'])
        if ',' in w:
            fixed_w = float(w.replace(',', '.'))
            queue.append({
                'Sheet': 'bag_production',
                'row_index': i,
                'anomaly_type': 'TYPE 1',
                'description': 'Comma decimal separator',
                'Field': 'weight',
                'original_value': w,
                'suggested_fix': fixed_w,
                'action': 'AUTO-FIXED → CLEANED',
                'Record_ID': row.get('bag_id', ''),
            })
            bprod_clean.at[i, 'weight'] = fixed_w
        t1_rows.append(i)
    fixes['bag_production'] = bprod_clean

    # ── TYPE 2: Negative values in non-negative fields ──
    neg_fields_bprod = ['weight', 'co2e_persistent', 'co2e_100', 'spc']
    bprod_clean2 = fixes.get('bag_production', bprod).copy()
    for i, row in bprod_clean2.iterrows():
        for f in neg_fields_bprod:
            try:
                val = float(row[f])
                if val < 0:
                    queue.append({
                        'Sheet': 'bag_production',
                        'row_index': i,
                        'anomaly_type': 'TYPE 2',
                        'description': 'Negative value in non-negative field',
                        'Field': f,
                        'original_value': val,
                        'suggested_fix': 'Requires human review',
                        'action': 'FLAGGED → VALIDATION_QUEUE',
                        'Record_ID': row.get('bag_id', ''),
                    })
            except (ValueError, TypeError):
                pass

    # Check bag_production co2e fields
    neg_fields_bp = ['co2e_persistent', 'co2e_100', 'spc']
    for i, row in bp.iterrows():
        for f in neg_fields_bp:
            try:
                val = float(row[f])
                if val < 0:
                    queue.append({
                        'Sheet': 'biochar_production',
                        'row_index': i,
                        'anomaly_type': 'TYPE 2',
                        'description': 'Negative value in non-negative field',
                        'Field': f,
                        'original_value': val,
                        'suggested_fix': 'Requires human review',
                        'action': 'FLAGGED → VALIDATION_QUEUE',
                        'Record_ID': row.get('activity_id', ''),
                    })
            except (ValueError, TypeError):
                pass

    # ── TYPE 3: Missing critical values (weight, carbon_content_%) ──
    for i, row in bprod_clean2.iterrows():
        w = row.get('weight')
        if pd.isna(w) or str(w).strip() == '':
            queue.append({
                'Sheet': 'bag_production',
                'row_index': i,
                'anomaly_type': 'TYPE 3',
                'description': 'Missing critical value: weight',
                'Field': 'weight',
                'original_value': w,
                'suggested_fix': 'Requires human review',
                'action': 'FLAGGED → VALIDATION_QUEUE',
                'Record_ID': row.get('bag_id', ''),
            })

    for i, row in bp.iterrows():
        cc = row.get('carbon_content_%')
        if pd.isna(cc) or str(cc).strip() == '':
            queue.append({
                'Sheet': 'biochar_production',
                'row_index': i,
                'anomaly_type': 'TYPE 3',
                'description': 'Missing critical value: carbon_content_%',
                'Field': 'carbon_content_%',
                'original_value': cc,
                'suggested_fix': 'Requires human review',
                'action': 'FLAGGED → VALIDATION_QUEUE',
                'Record_ID': row.get('activity_id', ''),
            })

    # ── TYPE 4: Duplicate bag_id in bag_production ──
    dup_mask = bprod.duplicated(subset=['bag_id'], keep=False)
    dup_ids = bprod[dup_mask]['bag_id'].unique()
    for bid in dup_ids:
        dup_rows = bprod[bprod['bag_id'] == bid]
        for i, row in dup_rows.iterrows():
            queue.append({
                'Sheet': 'bag_production',
                'row_index': i,
                'anomaly_type': 'TYPE 4',
                'description': f'Duplicate bag_id with weight={row["weight"]}',
                'Field': 'bag_id',
                'original_value': bid,
                'suggested_fix': 'Keep first occurrence; flag duplicates for review',
                'action': 'FLAGGED → VALIDATION_QUEUE',
                'Record_ID': bid,
            })

    # ── TYPE 5: Future timestamp / application_date ──
    # biochar_production Timestamp
    for i, row in bp.iterrows():
        ts = row.get('Timestamp')
        if pd.notna(ts):
            ts_date = pd.to_datetime(ts).date()
            if ts_date > TODAY:
                queue.append({
                    'Sheet': 'biochar_production',
                    'row_index': i,
                    'anomaly_type': 'TYPE 5',
                    'description': f'Future timestamp: {ts}',
                    'Field': 'Timestamp',
                    'original_value': str(ts),
                    'suggested_fix': 'Requires human review',
                    'action': 'FLAGGED → VALIDATION_QUEUE',
                    'Record_ID': row.get('activity_id', ''),
                })
    # bag_production Timestamp
    for i, row in bprod.iterrows():
        ts = row.get('Timestamp')
        if pd.notna(ts):
            ts_date = pd.to_datetime(ts).date()
            if ts_date > TODAY:
                queue.append({
                    'Sheet': 'bag_production',
                    'row_index': i,
                    'anomaly_type': 'TYPE 5',
                    'description': f'Future timestamp: {ts}',
                    'Field': 'Timestamp',
                    'original_value': str(ts),
                    'suggested_fix': 'Requires human review',
                    'action': 'FLAGGED → VALIDATION_QUEUE',
                    'Record_ID': row.get('bag_id', ''),
                })
    # biochar_application: application_date dan Timestamp
    for i, row in ba.iterrows():
        ad = row.get('application_date')
        ts = row.get('Timestamp')

        # Cek application_date > today (future date)
        if pd.notna(ad):
            ad_date = pd.to_datetime(ad).date()
            if ad_date > TODAY:
                queue.append({
                    'Sheet': 'biochar_application',
                    'row_index': i,
                    'anomaly_type': 'TYPE 5',
                    'description': f'Future application_date: {ad}',
                    'Field': 'application_date',
                    'original_value': str(ad),
                    'suggested_fix': 'Requires human review',
                    'action': 'FLAGGED → VALIDATION_QUEUE',
                    'Record_ID': row.get('activity_id', ''),
                })

        # Cek Timestamp > today (future timestamp)
        if pd.notna(ts):
            ts_date = pd.to_datetime(ts).date()
            if ts_date > TODAY:
                queue.append({
                    'Sheet': 'biochar_application',
                    'row_index': i,
                    'anomaly_type': 'TYPE 5',
                    'description': f'Future Timestamp: {ts}',
                    'Field': 'Timestamp',
                    'original_value': str(ts),
                    'suggested_fix': 'Requires human review',
                    'action': 'FLAGGED → VALIDATION_QUEUE',
                    'Record_ID': row.get('activity_id', ''),
                })

        # Catatan tambahan: application_date jauh lebih lambat dari Timestamp
        # (bukan TYPE 5 secara definitif, tapi suspicious — perlu dikonfirmasi)
        # Threshold: application_date lebih dari 30 hari setelah Timestamp
        if pd.notna(ad) and pd.notna(ts):
            ad_date = pd.to_datetime(ad).date()
            ts_date = pd.to_datetime(ts).date()
            gap_days = (ad_date - ts_date).days
            if gap_days > 30:
                queue.append({
                    'Sheet': 'biochar_application',
                    'row_index': i,
                    'anomaly_type': 'TYPE 5',
                    'description': (
                        f'Suspicious application_date: {ad} is {gap_days} days '
                        f'after Timestamp {ts}. Kemungkinan salah input — '
                        f'operator tidak mungkin input data di {ts} '
                        f'untuk kejadian yang baru akan terjadi {gap_days} hari kemudian.'
                    ),
                    'Field': 'application_date',
                    'original_value': str(ad),
                    'suggested_fix': (
                        f'Konfirmasi ke operator: apakah application_date {ad} benar? '
                        f'Kemungkinan harusnya {ts_date} atau sekitar tanggal Timestamp.'
                    ),
                    'action': 'FLAGGED → VALIDATION_QUEUE',
                    'Record_ID': row.get('activity_id', ''),
                })

    # ── TYPE 6: Invalid application_type ──
    for i, row in ba.iterrows():
        at = row.get('application_type', '')
        if at not in VALID_APPLICATION_TYPES:
            queue.append({
                'Sheet': 'biochar_application',
                'row_index': i,
                'anomaly_type': 'TYPE 6',
                'description': f'Invalid application_type: "{at}"',
                'Field': 'application_type',
                'original_value': at,
                'suggested_fix': f'Must be one of: {VALID_APPLICATION_TYPES}',
                'action': 'FLAGGED → VALIDATION_QUEUE',
                'Record_ID': row.get('activity_id', ''),
            })

    # ── TYPE 7: Orphan bag_id in bag_application ──
    prod_bag_ids = set(bprod['bag_id'].dropna())
    for i, row in bapp.iterrows():
        bid = row.get('bag_id', '')
        if bid not in prod_bag_ids:
            queue.append({
                'Sheet': 'bag_application',
                'row_index': i,
                'anomaly_type': 'TYPE 7',
                'description': f'Orphan bag_id not in bag_production: {bid}',
                'Field': 'bag_id',
                'original_value': bid,
                'suggested_fix': 'Requires human review — no matching production record',
                'action': 'FLAGGED → VALIDATION_QUEUE',
                'Record_ID': bid,
            })

    # ── TYPE 8: Weight discrepancy >5% between bag_application and bag_production ──
    # Build prod weight lookup (after TYPE 1 fix)
    bprod_wlookup = fixes.get('bag_production', bprod).copy()
    bprod_wlookup['weight_num'] = pd.to_numeric(bprod_wlookup['weight'], errors='coerce')
    prod_weight_map = bprod_wlookup.set_index('bag_id')['weight_num'].to_dict()

    for i, row in bapp.iterrows():
        bid = row.get('bag_id', '')
        app_w = row.get('bag_weight')
        prod_w = prod_weight_map.get(bid)
        if prod_w and pd.notna(app_w) and pd.notna(prod_w):
            try:
                app_w_f = float(app_w)
                discrepancy = abs(app_w_f - prod_w) / prod_w
                if discrepancy > 0.05:
                    queue.append({
                        'Sheet': 'bag_application (cross-sheet)',
                        'row_index': i,
                        'anomaly_type': 'TYPE 8',
                        'description': f'Weight discrepancy {discrepancy:.1%}: app={app_w_f:.2f} vs prod={prod_w:.2f}',
                        'Field': 'bag_weight',
                        'original_value': app_w_f,
                        'suggested_fix': f'Production weight={prod_w:.2f}. Requires review.',
                        'action': 'FLAGGED → VALIDATION_QUEUE',
                        'Record_ID': bid,
                    })
            except (ValueError, TypeError):
                pass

    # ── TYPE 9: Batch sum mismatch ──
    bprod_wlookup2 = fixes.get('bag_production', bprod).copy()
    bprod_wlookup2['weight_num'] = pd.to_numeric(bprod_wlookup2['weight'], errors='coerce')
    for prod_id, group in bprod_wlookup2.groupby('production_id'):
        bag_sum = group['weight_num'].sum()
        bp_row = bp[bp['activity_id'] == prod_id]
        if not bp_row.empty:
            declared = float(bp_row.iloc[0]['biochar_amount_kg'])
            diff = abs(bag_sum - declared)
            if diff > 0.01 and not pd.isna(bag_sum) and not pd.isna(declared):
                queue.append({
                    'Sheet': 'bag_production (cross-sheet)',
                    'row_index': bp_row.index[0],
                    'anomaly_type': 'TYPE 9',
                    'description': f'Batch sum mismatch: bags_sum={bag_sum:.2f} vs biochar_amount={declared:.2f} (Δ={diff:.2f})',
                    'Field': 'biochar_amount_kg / bag weights',
                    'original_value': f'bags_sum={bag_sum:.2f}',
                    'suggested_fix': f'Declared={declared:.2f}. Requires reconciliation.',
                    'action': 'FLAGGED → VALIDATION_QUEUE',
                    'Record_ID': prod_id,
                })

    # ── TYPE 10: Bag used in multiple application batches ──
    bag_app_counts = bapp.groupby('bag_id')['application_id'].nunique()
    multi_app_bags = bag_app_counts[bag_app_counts > 1].index.tolist()
    for bid in multi_app_bags:
        rows = bapp[bapp['bag_id'] == bid]
        app_ids = rows['application_id'].unique().tolist()
        for i, row in rows.iterrows():
            queue.append({
                'Sheet': 'bag_application (cross-sheet)',
                'row_index': i,
                'anomaly_type': 'TYPE 10',
                'description': f'Bag used in multiple batches: {app_ids}',
                'Field': 'bag_id / application_id',
                'original_value': bid,
                'suggested_fix': 'Bag must appear in only one application batch.',
                'action': 'FLAGGED → VALIDATION_QUEUE',
                'Record_ID': bid,
            })

    return pd.DataFrame(queue), fixes

# ──────────────────────────────────────────────────────
# 3. ROUTING LOGIC
# ──────────────────────────────────────────────────────
def build_cleaned_sheets(bp, bprod, ba, bapp, queue_df, fixes):
    """
    CLEANED sheets = auto-fixed records (TYPE 1 fixed, others excluded if flagged).
    Records flagged for TYPES 2,3,4,5,6,7,8,9,10 go only to VALIDATION_QUEUE.
    """
    # Identify flagged indices per sheet
    def flagged_indices(sheet_name):
        if queue_df.empty:
            return set()
        mask = (queue_df['Sheet'].str.startswith(sheet_name)) & \
               (~queue_df['anomaly_type'].isin(['TYPE 1']))
        return set(queue_df[mask]['row_index'].tolist())

    # bag_production cleaned: apply TYPE 1 fix, remove flagged rows
    bprod_fixed = fixes.get('bag_production', bprod).copy()
    bprod_fixed['weight'] = pd.to_numeric(bprod_fixed['weight'].astype(str).str.replace(',', '.'), errors='coerce')
    flagged_bprod = flagged_indices('bag_production')
    # De-duplicate: keep first occurrence
    first_seen = {}
    dup_later = []
    for i, row in bprod_fixed.iterrows():
        bid = row['bag_id']
        if bid not in first_seen:
            first_seen[bid] = i
        else:
            dup_later.append(i)
    flagged_bprod = flagged_bprod.union(set(dup_later))

    cleaned_bag_prod = bprod_fixed[~bprod_fixed.index.isin(flagged_bprod)].copy()
    cleaned_bag_prod['_cleaning_note'] = 'auto-cleaned'

    # biochar_production cleaned: remove flagged rows
    flagged_bp = flagged_indices('biochar_production')
    cleaned_prod_batch = bp[~bp.index.isin(flagged_bp)].copy()
    cleaned_prod_batch['_cleaning_note'] = 'auto-cleaned'

    # biochar_application cleaned: remove flagged
    flagged_ba = flagged_indices('biochar_application')
    cleaned_app_batch = ba[~ba.index.isin(flagged_ba)].copy()
    cleaned_app_batch['_cleaning_note'] = 'auto-cleaned'

    # bag_application cleaned: remove flagged (TYPE 7,8,10)
    flagged_bapp = flagged_indices('bag_application')
    cleaned_bag_app = bapp[~bapp.index.isin(flagged_bapp)].copy()
    cleaned_bag_app['_cleaning_note'] = 'auto-cleaned'

    return cleaned_prod_batch, cleaned_bag_prod, cleaned_app_batch, cleaned_bag_app

# ──────────────────────────────────────────────────────
# 4. AUTOMATION LOG
# ──────────────────────────────────────────────────────
def build_automation_log(bp, bprod, ba, bapp, queue_df):
    run_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    rows = []
    for sheet_name, df in [
        ('biochar_production', bp),
        ('bag_production', bprod),
        ('biochar_application', ba),
        ('bag_application', bapp),
    ]:
        anomalies_found = len(queue_df[queue_df['Sheet'].str.startswith(sheet_name)])
        rows.append({
            'run_timestamp': run_ts,
            'sheet_processed': sheet_name,
            'total_rows_input': len(df),
            'anomalies_detected': anomalies_found,
            'auto_fixed': len(queue_df[(queue_df['Sheet'].str.startswith(sheet_name)) & (queue_df['anomaly_type'] == 'TYPE 1')]),
            'flagged_for_review': anomalies_found,
            'status': 'SUCCESS',
        })
    return pd.DataFrame(rows)

# ──────────────────────────────────────────────────────
# 5. WRITE OUTPUT
# ──────────────────────────────────────────────────────
def write_output(cleaned_prod_batch, cleaned_bag_prod, cleaned_app_batch,
                 cleaned_bag_app, queue_df, log_df):
    # Tambah kolom review kosong ke VALIDATION_QUEUE sebelum ditulis
    queue_out = queue_df.copy()
    queue_out['Reviewed_By']  = ''
    queue_out['Resolution']   = ''
    queue_out['Resolved_At']  = ''

    with pd.ExcelWriter(OUTPUT_FILE, engine='xlsxwriter') as writer:
        cleaned_prod_batch.to_excel(writer, sheet_name='CLEANED_prod_batch', index=False)
        cleaned_bag_prod.to_excel(writer, sheet_name='CLEANED_bag_prod', index=False)
        cleaned_app_batch.to_excel(writer, sheet_name='CLEANED_app_batch', index=False)
        cleaned_bag_app.to_excel(writer, sheet_name='CLEANED_bag_app', index=False)
        queue_out.to_excel(writer, sheet_name='VALIDATION_QUEUE', index=False)
        log_df.to_excel(writer, sheet_name='AUTOMATION_LOG', index=False)
    print(f"Combined output written to {OUTPUT_FILE}")

    # Simpan 4 sheet terpisah
    p1 = os.path.join('data', 'CLEANED_prod_batch.xlsx')
    p2 = os.path.join('data', 'CLEANED_bag_prod.xlsx')
    p3 = os.path.join('data', 'CLEANED_app_batch.xlsx')
    p4 = os.path.join('data', 'CLEANED_bag_app.xlsx')
    
    cleaned_prod_batch.to_excel(p1, index=False)
    cleaned_bag_prod.to_excel(p2, index=False)
    cleaned_app_batch.to_excel(p3, index=False)
    cleaned_bag_app.to_excel(p4, index=False)
    
    print("4 separate cleaned files written to data/ folder")

# ──────────────────────────────────────────────────────
# 6. ANALYTICAL SUMMARY
# ──────────────────────────────────────────────────────
def analytical_insights(bp, bprod, ba, bapp):
    print("\n" + "="*60)
    print("ANALYTICAL INSIGHTS")
    print("="*60)

    # Q1: Conversion efficiency (feedstock → biochar per batch)
    bp2 = bp.copy()
    bp2['conversion_rate_%'] = (bp2['biochar_amount_kg'] / bp2['feedstock_amount'] * 100).round(2)
    print("\n[Q1] Biochar Conversion Efficiency by Feedstock")
    eff = bp2.groupby('feedstock_type').agg(
        avg_conversion_pct=('conversion_rate_%','mean'),
        total_biochar_kg=('biochar_amount_kg','sum'),
        batches=('activity_id','count')
    ).reset_index()
    print(eff.to_string(index=False))

    # Q2: Carbon sequestration by batch
    print("\n[Q2] Carbon Sequestration (co2e_persistent) per batch")
    seq = bp[['activity_id','feedstock_type','biochar_amount_kg','co2e_persistent','carbon_content_%']].copy()
    print(seq.to_string(index=False))

    # Q3: Application patterns
    print("\n[Q3] Application Type Distribution")
    app_pat = ba.groupby('application_type').agg(
        batches=('activity_id','count'),
        total_weight_kg=('total_weight','sum'),
        total_bags=('number_of_bags','sum'),
    ).reset_index()
    print(app_pat.to_string(index=False))

    return eff, seq, app_pat

# ──────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────
if __name__ == '__main__':
    print("Loading data...")
    bp, bprod, ba, bapp = load_data()

    print("Detecting anomalies...")
    queue_df, fixes = detect_anomalies(bp, bprod, ba, bapp)

    print(f"\n{'='*50}")
    print(f"Total anomalies detected: {len(queue_df)}")
    print(queue_df[['anomaly_type','Sheet','Record_ID','description']].to_string(index=False))

    print("\nBuilding cleaned sheets...")
    c_prod, c_bag_prod, c_app, c_bag_app = build_cleaned_sheets(bp, bprod, ba, bapp, queue_df, fixes)

    log_df = build_automation_log(bp, bprod, ba, bapp, queue_df)

    print("\nWriting output...")
    write_output(c_prod, c_bag_prod, c_app, c_bag_app, queue_df, log_df)

    eff, seq, app_pat = analytical_insights(bp, bprod, ba, bapp)
