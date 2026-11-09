# ClearMatch Quickstart Guide

This guide will help you set up and run the **ClearMatch** Accounts Payable (AP) invoice processing workspace on your machine.

---

## 1. Prerequisites

* **Python 3.10+**
* PowerShell, Bash, or Command Prompt
* Web browser (Chrome, Edge, Firefox, Safari)

---

## 2. Environment Setup

### Windows (PowerShell)
```powershell
# 1. Create virtual environment
python -m venv .venv

# 2. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 3. Install required packages
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### macOS / Linux (Bash)
```bash
# 1. Create virtual environment
python3 -m venv .venv

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Install required packages
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

---

## 3. Run the Application

Launch the Streamlit interactive review workspace:

```powershell
streamlit run app.py
```
*or:*
```powershell
python -m streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`.

---

## 4. Setting Up Multimodal Vision OCR (Google AI Studio - Free)

ClearMatch includes an integrated **Multimodal Vision OCR Engine** for scanned PDFs, smartphone photos, and image-only invoices (like `INV-SCANNED-MOBILE-701.pdf`).

### Step-by-Step: How to Get Your Free Gemini API Key
1. Visit **Google AI Studio**: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey).
2. Sign in with any standard Google account (**100% Free: 15 requests/min, 1,500 requests/day, no credit card required**).
3. Click **"Create API Key"** (choose "Create in new project" if prompted).
4. Copy the generated key (starts with `AIzaSy...`).

### Where and How to Configure Your Key (Choose Any Method)

#### Method 1: Via `.env` File (Recommended for Local Dev & Interviews)
Open or create the file `.env` directly in the project root:
```env
GEMINI_API_KEY=AIzaSyYourGeneratedKeyHere
```
*ClearMatch automatically reads this file on startup and keeps the key active across browser reloads.*

#### Method 2: Directly in the ClearMatch Web UI (Zero Code)
1. Open the application at `http://localhost:8501`.
2. Under **Step 1 (Data Ingestion)**, expand **"⚙️ Multimodal OCR & Vision AI Engine"**.
3. Paste your API key into the input field and press Enter. ClearMatch saves it and activates live Vision AI immediately.

#### Method 3: Via Terminal Environment Variable
* **Windows (PowerShell):**
  ```powershell
  $env:GEMINI_API_KEY="AIzaSyYourGeneratedKeyHere"
  streamlit run app.py
  ```
* **macOS / Linux (Bash):**
  ```bash
  export GEMINI_API_KEY="AIzaSyYourGeneratedKeyHere"
  streamlit run app.py
  ```

---

### How to Test & Verify Your API Key Before Demoing

Run our automated diagnostic script to verify connection to Google's servers:
```powershell
.\.venv\Scripts\python.exe scripts\test_gemini_api.py
```
This tests endpoint connectivity and runs live multimodal extraction against `data/invoices/INV-SCANNED-MOBILE-701.pdf`.
You will see:
```text
[PASS] Endpoint 'v1beta/gemini-1.5-flash-latest': HTTP 200 OK
[SUCCESS] LIVE GEMINI MULTIMODAL EXTRACTION VERIFIED!
Vendor: Acme Cloud Services Inc | Total: USD 600.00
```

> **Note for Offline / Interview Demos:**  
> If no API key is provided, ClearMatch seamlessly falls back to its built-in **Offline Vision Pipeline**, ensuring your live demo runs with 100% reliability even in restricted or offline corporate networks.

---

## 5. Run the Automated Tests

Run the complete test suite (**29 unit tests**) using either `pytest` or `unittest`:

```powershell
# Run with pytest (recommended)
pytest -v

# Or run with unittest
python -m unittest discover -s tests -v
```

---

## 6. Run the CLI Demo

To quickly process all bundled sample invoices and print the reasoning in your terminal:

```powershell
python run_demo.py
```

---

## 7. Project Architecture at a Glance

```text
ASA case study/
├── .venv/                      # Python virtual environment
├── .streamlit/                 # UI theme configuration & secrets
│   ├── config.toml
│   └── secrets.example.toml    # Template for Gemini API key
├── backend/                    # Core AP business logic
│   ├── checker.py              # Rule-based validation engine (12 checks)
│   ├── excel_generator.py      # Multi-sheet audit workbook generator (.xlsx)
│   ├── ocr_engine.py           # Multimodal Vision AI & OCR pipeline
│   ├── reader.py               # PDF parser and labeled text extractor
│   └── store.py                # SQLite audit trail and run history
├── frontend/                   # Presentation layer
│   ├── app.py                  # Main Streamlit application
│   ├── components/             # Reusable UI widgets and styles
│   │   ├── styles.py           # Custom CSS styling
│   │   └── ui_helpers.py       # Stepper, badges, and shell layout
│   └── views/                  # Multi-step review workflow views
│       ├── intake_view.py      # Stage 01: Ingestion, Mode Toggle & Vision AI Settings
│       ├── analysis_view.py    # Stage 02: Analysis & Check Grid
│       ├── results_view.py     # Stage 03: Decision & Sign-off
│       ├── vendor_comm_view.py # Stage 04: Vendor Communication
│       └── history_view.py     # Stage 05: Audit Queue & Run History
├── utils/                      # Shared configuration and logging
│   ├── config.py               # Paths, tolerance rules, and schemas
│   └── logger.py               # Structured application logger
├── data/                       # Structured storage
│   ├── reference/              # Vendor master, PO headers, PO lines, goods receipts
│   ├── invoices/               # Bundled sample, GST, and scanned PDF fixtures
│   └── runs/                   # SQLite database (invoice_runs.sqlite3)
├── logs/                       # Application runtime log files
│   ├── .gitkeep
│   └── app.log
├── tests/                      # Automated unit test suite (29 tests)
│   ├── test_checker.py         # Decision logic & edge cases
│   ├── test_reader.py          # PDF text extraction & OCR
│   ├── test_real_invoices.py   # Real GST invoices 3-way matching
│   └── test_store.py           # Persistence and queue retrieval
├── app.py                      # Root entrypoint for Streamlit
├── run_demo.py                 # Root CLI demonstration runner
├── requirements.txt            # Pinned dependencies
├── quickstart.md               # Quickstart guide
└── README.md                   # Full case study overview
```

---

## 8. Sample Test Scenarios

The workspace includes pre-configured sample PDFs in `data/invoices/`:

| Fixture | Scenario | Policy | Expected Outcome |
| :--- | :--- | :--- | :--- |
| `INV-NS-1042.pdf` | **Standard Happy Path:** Clean invoice matching approved vendor V-1001 & PO-4501. | 2-Way / 3-Way | `READY FOR AP APPROVAL` |
| `INV-AC-8871.pdf` | **Staggered / Split PO:** Valid partial invoice ($600) following prior AC-8870 ($600). | 2-Way | `READY FOR AP APPROVAL` |
| `INV-EDGE-DUPLICATE.pdf` | **Duplicate Billing:** Repeats invoice number already in processed history. | 2-Way / 3-Way | `NEEDS REVIEW` |
| `INV-EDGE-MISSING-NUMBER.pdf` | **Missing Data:** Lacks invoice number needed for reconciliation. | 2-Way / 3-Way | `NEEDS INFORMATION` |
| `INV-EDGE-OVER-PO.pdf` | **Over PO Budget:** Cumulative $1,300 exceeds $1,200 PO + $12 tolerance. | 2-Way | `NEEDS REVIEW` |
| `INV-SHORT-SHIP-5001.pdf` | **Short Shipment / Damaged Goods:** Billed 20 cases, dock accepted 15 (5 water-damaged). | 3-Way | `NEEDS REVIEW` (Settlement Hold) |
| `INV-MULTI-9021.pdf` | **Multi-Line Physical Hardware:** 4 distinct line items reconciled with dock receiving. | 3-Way | `READY FOR AP APPROVAL` |
| `E-664.pdf` | **Real GST Invoice (Pipes):** Real-world Indian tax invoice for ₹45,109.52 with HSN codes. | 3-Way | `READY FOR AP APPROVAL` |
| `e-658.pdf` | **Real GST e-Invoice (Cables):** Multi-line wrapped descriptions for ₹125,009.20. | 3-Way | `READY FOR AP APPROVAL` |
| `INV-SCANNED-MOBILE-701.pdf` | **Scanned / Mobile Photo:** Image-only PDF with 0 extractable text; triggers Vision OCR. | 2-Way | `READY FOR AP APPROVAL` |

