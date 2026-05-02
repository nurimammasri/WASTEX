# WasteX — Biochar Data Cleaning, Validation & Automation Pipeline

> **Data Analyst Technical Workflow** · Biochar Production & Application Tracking  
> Prepared by **Nur Imam Masri** · April 2026

---

## Table of Contents

1. [About WasteX](#1-about-wastex)
2. [About the Author](#2-about-the-author)
3. [Project Overview](#3-project-overview)
4. [Dataset Structure](#4-dataset-structure)
5. [Pipeline Architecture](#5-pipeline-architecture)
6. [10 Anomaly Types](#6-10-anomaly-types)
7. [Output Files](#7-output-files)
8. [Automation Options](#8-automation-options)
   - [Python Script (Standalone)](#81-python-script-standalone)
   - [n8n Workflow](#82-n8n-workflow)
   - [Python + Prefect](#83-python--prefect)
   - [Google Apps Script](#84-google-apps-script)
9. [Quick Start](#9-quick-start)
10. [Repository Structure](#10-repository-structure)
11. [Tech Stack](#11-tech-stack)

---

## 1. About WasteX

**WasteX** is a climate-tech and agritech company that provides end-to-end biochar solutions for agricultural and agro-industrial sectors. The company helps farmers, livestock businesses, mills, fertilizer producers, and other biomass-generating operations convert organic waste into **biochar** using small-scale carbonizer technology.

**Biochar** is a carbon-rich solid material produced through **pyrolysis** — a low-oxygen thermal process that converts biomass such as rice husks, corn cobs, wood waste, and agricultural residues into a stable form of carbon. Unlike conventional charcoal, biochar is primarily used to improve soil quality, enhance nutrient and water retention, and support long-term carbon storage.

WasteX's solution focuses on both operational and environmental value. By turning underutilized biomass waste into biochar, WasteX enables agricultural businesses to improve productivity, reduce emissions, and create additional value from waste streams. Its offering includes biochar production equipment, implementation support, operational guidance, and carbon credit-related services.

---

## 2. About the Author

| | |
|---|---|
| **Name** | Nur Imam Masri |
| **Role** | Data Analyst Candidate |
| **Email** | nurimammasri.01@gmail.com |
| **GitHub** | [github.com/nurimammasri](https://github.com/nurimammasri/WASTEX/tree/master) |

**Background**

Nur Imam Masri is a data professional with 4+ years of experience in Data Science, Data Analytics, Business Intelligence, and Machine Learning. He has a strong focus on end-to-end data workflows, including data cleaning, validation, analysis, visualization, reporting, and automation.

**Technical Skills**

| Category | Tools & Technologies |
|---|---|
| Data Processing | Python, Pandas, NumPy, R |
| Databases & Querying | SQL, BigQuery |
| Machine Learning | Scikit-learn, TensorFlow |
| BI & Visualization | Power BI, Tableau, Looker Studio, Excel |
| Automation | n8n, Prefect, Google Apps Script, API Integration |
| AI & GenAI | Prompt Engineering, AI-assisted Workflows |

His work focuses on building reliable, scalable, and business-oriented data solutions that improve data quality, operational visibility, and decision-making.

---

## 3. Project Overview

This project implements a complete **data cleaning and validation pipeline** for WasteX's biochar operational data. The pipeline reads four raw Excel/Google Sheets, detects 10 predefined anomaly types, auto-fixes safe formatting issues, and routes all business-critical anomalies to a human review queue.

**Core Design Principles:**

| Principle | Description |
|---|---|
| Auto-fix only low-risk issues | Comma decimal separators are automatically corrected because the intended value is unambiguous |
| Flag business-critical anomalies | Negative values, missing critical fields, duplicate IDs, orphan bags, weight discrepancies, and cross-sheet mismatches are routed to `VALIDATION_QUEUE` |
| Keep cleaned outputs reliable | Records with unresolved anomalies are excluded from cleaned output sheets until reviewed or corrected |

---

## 4. Dataset Structure

The WasteX dataset consists of four raw operational sheets that represent the full biochar workflow from production to field application. The dataset is structured around two main operational stages:

1. **Biochar Production** — when biomass is processed into biochar and packed into bags
2. **Biochar Application** — when produced biochar bags are applied to land or sold

### Sheet 1: `biochar_production` — Production Batch Level

One row per biochar production batch (carbonizer run).

| Field Group | Example Columns | Description |
|---|---|---|
| Batch identity | `activity_id`, `Timestamp`, `username` | Identifies when the batch was recorded and which operator submitted it |
| Production output | `biochar_amount_kg`, `number_of_bags` | Shows the total biochar produced and expected number of bags |
| Feedstock details | `feedstock_type`, `feedstock_amount`, `feedstock_humidity`, `feedstock_size` | Describes the biomass input used in the production process |
| Carbon metrics | `carbon_content_%`, `co2e_persistent`, `co2e_100`, `ch4`, `spc`, `margin_of_safety` | Captures carbon-related calculations and environmental impact indicators |
| Process details | `actual_start_time`, `actual_finish_time`, `temp_1`, `temp_2`, `temp_3` | Provides operational process data from the carbonizer run |

> The `activity_id` from this sheet is used as the production batch identifier and should match the `production_id` in bag-level production data.

### Sheet 2: `bag_production` — Production Bag Level

One row per individual biochar bag produced.

| Field Group | Example Columns | Description |
|---|---|---|
| Bag identity | `bag_id`, `production_id`, `Timestamp`, `username` | Identifies each individual bag and links it to its production batch |
| Bag measurement | `weight` | Records the weight of each produced bag |
| Carbon metrics | `co2e_persistent`, `co2e_100`, `ch4`, `spc`, `margin_of_safety`, `electricity_emission` | Provides carbon impact estimates at individual bag level |
| Production context | `feedstock_type` | Shows which feedstock type the bag originated from |

> This sheet is the **source of truth** for valid `bag_id` values. Any bag used later in the application process should already exist in this sheet.

### Sheet 3: `biochar_application` — Application Batch Level

One row per biochar application or sale event.

| Field Group | Example Columns | Description |
|---|---|---|
| Application identity | `activity_id`, `Timestamp`, `username` | Identifies each application or sale event |
| Application details | `application_type`, `application_date`, `number_of_bags`, `total_weight` | Describes what type of application occurred, when, and how much biochar was used |
| Location and purpose | `location`, `purpose` | Captures where and why the biochar was applied |
| Charging information | `charging_material`, `charging_amount` | Records additional material used when biochar is charged before application |
| Carbon metrics | `co2e_persistent_exc_transport`, `co2e_100_exc_transport`, `ch4`, `spc`, `margin_of_safety` | Measures carbon impact at application batch level |
| Emission adjustments | `biomass_transport_emission`, `biochar_transport_emission`, `emission_electricity`, `methane_compensation` | Captures transport and electricity-related emission components |

### Sheet 4: `bag_application` — Application Bag Level

One row per individual bag used in an application or sale event.

| Field Group | Example Columns | Description |
|---|---|---|
| Application linkage | `application_id`, `Timestamp`, `username` | Links each bag to a specific application batch |
| Bag traceability | `bag_id`, `production_id` | Connects the applied bag back to its original production record |
| Bag measurement | `bag_weight` | Records the weight of the bag at the time of application |
| Carbon metrics | `co2e_persistent_excl_transport`, `co2e_100_excl_transport`, `ch4`, `spc`, `margin_of_safety` | Provides carbon impact calculations at applied bag level |
| Emission components | `biomass_emission_transport`, `biochar_emission_transport`, `emission_electricity` | Captures transport and electricity-related emissions |
| Production context | `feedstock_type` | Shows the feedstock source of the applied bag |

### Dataset Relationships

The four sheets are connected through structured IDs:

| Relationship | Description |
|---|---|
| `biochar_production.activity_id` → `bag_production.production_id` | Links each produced bag to its production batch |
| `bag_production.bag_id` → `bag_application.bag_id` | Links each applied bag to its original production record |
| `biochar_application.activity_id` → `bag_application.application_id` | Links each applied bag to its application batch |

> **Key Business Rule:** One production bag (`bag_id`) can only be used in **ONE** application batch, and every bag recorded in `bag_application` must exist in `bag_production`.

---

## 5. Pipeline Architecture

The pipeline is a single-pass ETL + QA batch process with six stages:

```
load_data()
    ↓
detect_anomalies()
    ↓
build_cleaned_sheets()
    ↓
build_automation_log()
    ↓
analytical_insights()
    ↓
write_output()
```

![Data Cleaning Pipeline](Image/1.%20Data%20Cleaning.png)

### Pipeline Flow

```
RAW DATA (4 Excel Sheets)
        │
        ▼
  ① INGEST & LOAD
  Read all 4 sheets, normalize column names, standardize data types
        │
        ▼
  ② DETECT ANOMALIES
  Scan 10 anomaly types per sheet & cross-sheet
        │
        ▼
  ③ ROUTING DECISION
  ┌─────────────────────┐
  │ TYPE 1 (Auto-Fix)   │ → AUTO-FIXED → enters CLEANED sheets
  │ TYPE 2-10 (Flag)    │ → FLAGGED → enters VALIDATION_QUEUE
  └─────────────────────┘
        │
        ▼
  ④ BUILD OUTPUTS
  Create 4 CLEANED sheets + VALIDATION_QUEUE + AUTOMATION_LOG
        │
        ▼
  ⑤ WRITE OUTPUT
  Save to combined Excel workbook + separate cleaned files
        │
        ▼
  ⑥ REVIEW & ITERATE
  Human reviews VALIDATION_QUEUE → updates source data → re-run
```

---

## 6. 10 Anomaly Types

| # | Anomaly Type | Sheet(s) Checked | Field(s) | Action |
|---|---|---|---|---|
| 1 | Comma decimal separator (e.g. `"18,45"` → `18.45`) | `bag_production` | `weight` | **AUTO-FIXED** → CLEANED |
| 2 | Negative values in non-negative fields | `bag_production`, `biochar_production` | `weight`, `co2e_persistent`, `co2e_100`, `spc` | FLAGGED → VALIDATION_QUEUE |
| 3 | Missing critical fields | `bag_production`, `biochar_production` | `weight`, `carbon_content_%` | FLAGGED → VALIDATION_QUEUE |
| 4 | Duplicate `bag_id` | `bag_production` | `bag_id` | FLAGGED → VALIDATION_QUEUE (first kept) |
| 5 | Future timestamps or suspicious date gap >30 days | All 4 sheets | `Timestamp`, `application_date` | FLAGGED → VALIDATION_QUEUE |
| 6 | Invalid `application_type` | `biochar_application` | `application_type` | FLAGGED → VALIDATION_QUEUE |
| 7 | Orphan `bag_id` (applied but never produced) | `bag_application` vs `bag_production` | `bag_id` | FLAGGED → VALIDATION_QUEUE |
| 8 | Weight discrepancy >5% between application and production | `bag_application` vs `bag_production` | `bag_weight`, `weight` | FLAGGED → VALIDATION_QUEUE |
| 9 | Bag-weight sum ≠ declared `biochar_amount_kg` at batch level | `bag_production` vs `biochar_production` | `weight`, `biochar_amount_kg` | FLAGGED → VALIDATION_QUEUE |
| 10 | `bag_id` appears in multiple application batches | `bag_application` | `bag_id`, `application_id` | FLAGGED → VALIDATION_QUEUE |

### Valid `application_type` Values (TYPE 6)

```
Application-Pure Biochar
Application-Charged Biochar
Sale-Pure Biochar
Sale-Charged Biochar
```

### Validation Queue Columns

Each row in `VALIDATION_QUEUE` contains:

| Column | Filled By | Description |
|---|---|---|
| `Sheet` | Pipeline | Source sheet where the anomaly was found |
| `row_index` | Pipeline | Original row index from the raw dataset |
| `anomaly_type` | Pipeline | TYPE 1 to TYPE 10 |
| `description` | Pipeline | Human-readable explanation of the issue |
| `Field` | Pipeline | Field or relationship affected |
| `original_value` | Pipeline | Original problematic value |
| `suggested_fix` | Pipeline | Recommended review or correction |
| `action` | Pipeline | Auto-fixed or flagged status |
| `Record_ID` | Pipeline | Main identifier (e.g. `bag_id` or `activity_id`) |
| `Reviewed_By` | **Reviewer** | Name of the person who reviewed this record |
| `Resolution` | **Reviewer** | `approved` / `rejected` / `corrected` |
| `Resolved_At` | **Reviewer** | Timestamp of when the review was completed |

---

## 7. Output Files

The pipeline produces one combined Excel workbook containing 6 sheets:

| Sheet | Description |
|---|---|
| `CLEANED_prod_batch` | Anomaly-free production batch records |
| `CLEANED_bag_prod` | Anomaly-free bag production records (with TYPE 1 auto-fixed) |
| `CLEANED_app_batch` | Anomaly-free application batch records |
| `CLEANED_bag_app` | Anomaly-free bag application records |
| `VALIDATION_QUEUE` | All flagged rows with anomaly type, description, and review fields |
| `AUTOMATION_LOG` | Execution summary per sheet per run |

The pipeline also exports each cleaned sheet as a separate Excel file:

```
data/
├── WasteX_Cleaned_Output.xlsx     ← Combined workbook (all 6 sheets)
├── CLEANED_prod_batch.xlsx
├── CLEANED_bag_prod.xlsx
├── CLEANED_app_batch.xlsx
└── CLEANED_bag_app.xlsx
```

### Automation Log Columns

| Column | Description |
|---|---|
| `run_timestamp` | Timestamp of the pipeline run |
| `sheet_processed` | Name of the processed source sheet |
| `total_rows_input` | Number of raw input records |
| `anomalies_detected` | Number of anomalies found |
| `auto_fixed` | Number of auto-fixed records |
| `flagged_for_review` | Number of records requiring human review |
| `status` | Pipeline execution status (`SUCCESS`) |

---

## 8. Automation Options

This project provides **three separate automation implementations** for different infrastructure preferences. All implementations detect the same 10 anomaly types and produce the same outputs.

### 8.1 Python Script (Standalone)

The simplest implementation — a single Python script with no external dependencies beyond standard data libraries.

**Files:**
- `wastex_pipeline.py` — original pipeline
- `wastex_pipeline_v1_updated.py` — extended TYPE 5 detection (also flags gaps >30 days between `Timestamp` and `application_date`)

**Installation:**

```bash
pip install pandas numpy xlrd xlsxwriter openpyxl
```

**Path Configuration** — update these constants at the top of the script for local Windows use:

```python
INPUT_FILE  = 'data/WasteX_DA_Test_Dataset_final.xlsx'
OUTPUT_FILE = 'data/WasteX_Cleaned_Output.xlsx'
```

**Run:**

```bash
# Recommended (enhanced date validation):
python wastex_pipeline_v1_updated.py

# Original version:
python wastex_pipeline.py
```

---

### 8.2 n8n Workflow

A fully automated no-code/low-code workflow using **n8n** as the orchestration engine. Runs on a daily schedule (07:00 WIB), reads from Google Sheets, and sends email notifications on anomaly detection.

![n8n Automation Workflow](Image/2.%20Automation%20(N8N).png)

**Specs:**
- **Version:** v4d · **Nodes:** 37 · **Trigger:** Daily 07:00 WIB (Cron: `0 7 * * *`)
- **Data Source:** Google Sheets (Spreadsheet ID: `1QqSa7reb4i2Oz7pnbb6sAflJEtbsCwF4m19J7aDgsoE`)
- **Notification:** Email via Gmail to `nurimammasri.01@gmail.com`

**Workflow Architecture:**

```
⏰ Daily Trigger 07:00
        │
        ├── Read biochar_production  ─┐
        ├── Read bag_production       ├── (parallel reads)
        ├── Read biochar_application  │
        └── Read bag_application    ──┘
                │
        🔗 Collect All Sheets
                │
        🗺️ Build Lookup Maps
                │
        🔍 Detect All 10 Anomaly Types
                │
        🧹 Build Cleaned Data
                │
        📊 Flatten → 🗑️ Clear → ✅ Write (parallel — 4 CLEANED sheets)
                │
        ⏳ Wait All Writes Done (Merge node)
                │
        ⚠️ Split Anomalies → 📋 Append VALIDATION_QUEUE
                │
        📊 Build Log → 📝 Append AUTOMATION_LOG
                │
        ❓ Any new anomalies?
        ├── YES → 📧 Build Email → 📨 Send Email Notification
        └── NO  → ✅ Done
```

**Key features:**
- Parallel data reads (4 sheets simultaneously) — saves ~5–8 seconds per run
- State management via `_pp` (pipeline payload) field for fan-in/fan-out
- Deduplication: VALIDATION_QUEUE only appends new anomalies, not re-running duplicates
- Email preview includes 5 top anomalies and reviewer instructions

**Setup:** See [`Automation/N8N/README.md`](Automation/N8N/README.md) for full setup guide including Google OAuth2 configuration.

---

### 8.3 Python + Prefect

A production-grade Python pipeline using **Prefect** for orchestration, monitoring, retries, and observability. Reads from and writes to Google Sheets via Service Account.

![Python Prefect Automation (1)](Image/3.%20Automation%20(Python%201).png)
![Python Prefect Automation (2)](Image/3.%20Automation%20(Python%202).png)

**File Structure:**

```
Automation/Python - Prefert/
├── main.py          ← Entry point — defines Prefect Flow with 19 tasks
├── config.py        ← Centralized configuration (IDs, thresholds, emails)
├── helpers.py       ← Utility functions (to_float, to_date, is_empty, make_anomaly)
├── loader.py        ← Task 1 & 2: load data + build lookup maps
├── detection.py     ← Task 3–12: detect 10 anomaly types
├── cleaning.py      ← Task 13 & 14: merge anomalies + build cleaned dataset
├── writer.py        ← Task 15–17: write cleaned sheets, validation queue, automation log
├── notifier.py      ← Task 18 & 19: Prefect UI report + email notification
└── credentials.json ← Google Service Account key (NOT committed to Git)
```

**Installation:**

```bash
pip install -r Automation/Python\ -\ Prefert/requirements_prefect.txt
# prefect==3.6.28, gspread==6.1.2, google-auth==2.29.0
```

**Run manually:**

```bash
python Automation/Python\ -\ Prefert/main.py
```

**Deploy with daily schedule (07:00 WIB):**

```bash
prefect deploy main.py:wastex_pipeline \
    --name "WasteX Daily Pipeline" \
    --cron "0 7 * * *" \
    --pool "default-agent-pool"

# Start the worker in a separate terminal:
prefect worker start --pool "default-agent-pool"
```

**Key features:**
- 19 modular Prefect tasks with automatic retry (3x, 30s delay) and 5-minute timeout per task
- Prefect UI Artifact report (run summary, anomaly table, before vs after counts)
- VALIDATION_QUEUE deduplication — only new anomalies are appended per daily run
- Email notification sent only when new anomalies are found

**Configurable thresholds in `config.py`:**

```python
CONFIG = {
    "MAX_APP_DATE_GAP_DAYS"  : 30,   # TYPE 5: max gap between Timestamp and application_date
    "WEIGHT_DISCREPANCY_PCT" : 0.05, # TYPE 8: max weight difference = 5%
    "BATCH_SUM_TOLERANCE_KG" : 0.01, # TYPE 9: batch sum tolerance = 0.01 kg
    "VALID_APP_TYPES"        : [     # TYPE 6: allowed application_type values
        "Application-Pure Biochar",
        "Application-Charged Biochar",
        "Sale-Pure Biochar",
        "Sale-Charged Biochar",
    ],
}
```

**Setup:** See [`Automation/Python - Prefert/README.md`](Automation/Python%20-%20Prefert/README.md) for full setup guide including Google Service Account configuration.

---

### 8.4 Google Apps Script

A zero-infrastructure option that runs entirely inside Google Sheets using **Google Apps Script**. No server, no external tools — just the spreadsheet itself.

**Files:**
- `Automation/Google App Script/WasteX_Automation.gs` — complete pipeline script
- `Automation/Google App Script/README.md` — setup guide

**Setup (5 minutes):**

1. Open your WasteX Google Sheet
2. Click **Extensions → Apps Script**
3. Paste the contents of `WasteX_Automation.gs`
4. Update `NOTIFICATION_EMAIL` in the `CONFIG` object
5. Run `setupTrigger()` to activate the daily 07:00 trigger
6. Run `runPipeline()` manually to test

**Automation comparison:**

| Feature | Python Script | n8n | Python + Prefect | Google Apps Script |
|---|---|---|---|---|
| Infrastructure | Local only | n8n server | Prefect server | Google Sheets (built-in) |
| Scheduling | Manual | Cron (daily 07:00) | Cron (daily 07:00) | Google trigger (daily 07:00) |
| Data source | Excel file | Google Sheets | Google Sheets | Google Sheets |
| Monitoring | Terminal output | n8n execution log | Prefect UI + Artifacts | Apps Script execution log |
| Email alerts | No | Yes (Gmail OAuth2) | Yes (Gmail App Password) | Yes (Gmail built-in) |
| Retry on failure | No | No | Yes (3x, 30s delay) | No |
| Setup complexity | Low | Medium | Medium | Very Low |
| Best for | Local analysis | Production (no-code) | Production (Python) | Lightweight automation |

---

## 9. Quick Start

### Option A — Run Python Script Locally

```bash
# 1. Clone the repository
git clone https://github.com/nurimammasri/WASTEX.git
cd WASTEX

# 2. Install dependencies
pip install pandas numpy xlrd xlsxwriter openpyxl

# 3. Place input data
#    data/WasteX_DA_Test_Dataset_final.xlsx  (already included)

# 4. Run the pipeline
python wastex_pipeline_v1_updated.py

# 5. Check output
#    WasteX_Cleaned_Output.xlsx
```

### Option B — Run with Jupyter Notebook

Open the pipeline notebook on GitHub:  
[WasteX_Pipeline_Notebook.ipynb](https://github.com/nurimammasri/WASTEX/blob/master/WasteX_Pipeline_Notebook.ipynb)

### Option C — Import n8n Workflow

```
1. Open n8n → Workflows → Import from file
2. Upload Automation/N8N/WasteX_n8n_Workflow.json
3. Connect Google Sheets + Gmail credentials
4. Click Activate
```

### Option D — Deploy Google Apps Script

```
1. Open WasteX Google Sheet
2. Extensions → Apps Script → paste WasteX_Automation.gs
3. Run setupTrigger() → done
```

---

## 10. Repository Structure

```
WASTEX/
│
├── wastex_pipeline.py                    ← Standalone Python pipeline (original)
├── wastex_pipeline_v1_updated.py         ← Extended TYPE 5 detection
├── WasteX_Cleaned_Output.xlsx            ← Sample pipeline output
├── wastex_interactive_dashboard.html     ← Standalone Chart.js dashboard (mockup)
│
├── data/
│   └── WasteX_DA_Test_Dataset_final.xlsx ← Raw input dataset (4 sheets)
│
├── Automation/
│   ├── N8N/
│   │   ├── WasteX_n8n_Workflow.json      ← n8n workflow export (v4d, 37 nodes)
│   │   └── README.md
│   │
│   ├── Python - Prefert/
│   │   ├── main.py                       ← Prefect flow entry point
│   │   ├── config.py                     ← Centralized configuration
│   │   ├── helpers.py                    ← Utility functions
│   │   ├── loader.py                     ← Data loading tasks
│   │   ├── detection.py                  ← 10 anomaly detection tasks
│   │   ├── cleaning.py                   ← Data cleaning tasks
│   │   ├── writer.py                     ← Output writing tasks
│   │   ├── notifier.py                   ← Report and email tasks
│   │   ├── requirements_prefect.txt      ← Python dependencies
│   │   └── README.md
│   │
│   └── Google App Script/
│       ├── WasteX_Automation.gs          ← Apps Script pipeline
│       └── README.md
│
├── Image/
│   ├── 1. Data Cleaning.png
│   ├── 2. Automation (N8N).png
│   ├── 3. Automation (Python 1).png
│   └── 3. Automation (Python 2).png
│
├── WasteX Data Analyst Workflow — Biochar Data Cleaning, Validation, and Reporting.pdf
├── CLAUDE.md
└── README.md
```

---

## 11. Tech Stack

| Category | Technology |
|---|---|
| **Language** | Python 3.x, JavaScript |
| **Data Processing** | Pandas, NumPy |
| **Excel I/O** | openpyxl, xlrd, xlsxwriter |
| **Google Sheets API** | gspread, google-auth |
| **Pipeline Orchestration** | Prefect 3.x |
| **Workflow Automation** | n8n (v2.x) |
| **Serverless Automation** | Google Apps Script |
| **Visualization** | Chart.js (interactive dashboard) |
| **Scheduling** | Cron (`0 7 * * *`) |
| **Notification** | Gmail (OAuth2 / App Password) |
| **Version Control** | Git / GitHub |

---

## Links

| Resource | URL |
|---|---|
| GitHub Repository | [github.com/nurimammasri/WASTEX](https://github.com/nurimammasri/WASTEX/tree/master) |
| Pipeline Notebook | [WasteX_Pipeline_Notebook.ipynb](https://github.com/nurimammasri/WASTEX/blob/master/WasteX_Pipeline_Notebook.ipynb) |
| n8n Workflow | [Automation/N8N](https://github.com/nurimammasri/WASTEX/tree/master/Automation/N8N) |
| Technical Document | [PDF Workflow Document](WasteX%20Data%20Analyst%20Workflow%20%E2%80%94%20Biochar%20Data%20Cleaning%2C%20Validation%2C%20and%20Reporting.pdf) |

---

*WasteX Data Analyst Technical Workflow · Biochar Data Cleaning, Validation, and Reporting · April 2026*  
*Prepared by Nur Imam Masri · nurimammasri.01@gmail.com*
