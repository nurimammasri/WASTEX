# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WasteX is a Python data cleaning and validation pipeline for a biochar production tracking system. It detects and auto-fixes anomalies in Excel-based records covering biochar production, bag-level production, application, and sales. The output is a cleaned Excel workbook plus a validation queue for human review.

Domain: environmental sustainability — tracking biochar from feedstocks (rice husk, corn cob/leaves, wood waste, cassava stems) through production and application/sale.

## Running the Pipeline

```bash
# Recommended (enhanced date validation):
python wastex_pipeline_v1_updated.py

# Original version:
python wastex_pipeline.py
```

**Dependencies** (no package manager; install manually):
```bash
pip install pandas numpy xlrd xlsxwriter openpyxl
```

**Path configuration** — both scripts hardcode Linux container paths:
```python
INPUT_FILE  = '/mnt/user-data/uploads/WasteX_DA_Test_Dataset_final.xlsx'
OUTPUT_FILE = '/mnt/user-data/outputs/WasteX_Cleaned_Output.xlsx'
```
When running locally on Windows, update these constants at the top of the script to point to the actual `.xlsx` files in this directory.

## Architecture

The pipeline is a single-file ETL + QA pattern with six stages:

```
load_data() → detect_anomalies() → build_cleaned_sheets()
           → build_automation_log() → analytical_insights() → write_output()
```

**Input (4 Excel sheets):**
- `biochar_production` — batch-level metadata
- `bag_production` — individual bag records (weight, carbon metrics)
- `biochar_application` — application batch metadata
- `bag_application` — bag-level application/sale records

**Output (6 Excel sheets):**
- `CLEANED_prod_batch`, `CLEANED_bag_prod`, `CLEANED_app_batch`, `CLEANED_bag_app` — anomaly-free rows
- `VALIDATION_QUEUE` — all flagged rows with anomaly type and description
- `AUTOMATION_LOG` — execution summary (timestamps, counts per anomaly type)

## The 10 Anomaly Types

| # | Description | Action |
|---|-------------|--------|
| 1 | Comma decimal separator in weights (e.g. `1,5`) | Auto-fixed → `1.5` |
| 2 | Negative values in non-negative fields | Flagged |
| 3 | Missing weight or `carbon_content_%` | Flagged |
| 4 | Duplicate `bag_id` in `bag_production` | Flagged |
| 5 | Future timestamps, future `application_date`, or gap >30 days between timestamp and application_date | Flagged |
| 6 | Invalid `application_type` (must be one of 4 valid strings) | Flagged |
| 7 | Orphan `bag_id`: in `bag_application` but not `bag_production` | Flagged |
| 8 | Weight discrepancy >5% between application and production records | Flagged |
| 9 | Bag-weight sum doesn't match declared `biochar_amount_kg` at batch level | Flagged |
| 10 | `bag_id` appears in multiple application batches | Flagged |

## Version Differences

`wastex_pipeline_v1_updated.py` extends TYPE 5 detection to also flag gaps >30 days between `Timestamp` and `application_date` in `biochar_application`. It is otherwise functionally equivalent to `wastex_pipeline.py`.

## Interactive Dashboard

`wastex_interactive_dashboard.html` is a standalone Chart.js visualization (no server needed — open in browser). It contains hardcoded sample data and is not wired to the pipeline output; it serves as a reporting mockup.
