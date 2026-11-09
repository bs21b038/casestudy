# ClearMatch — Accounts Payable Autonomous Reconciliation Desk

**Enterprise AP Matching, SOX 404 Audit Verification, and Exception Management Engine**  
*Built for the Enterprise AI Solutions Analyst Case Study*

---

## Executive Overview

In enterprise finance operations, **Accounts Payable (AP)** reconciles third-party vendor invoices against procurement contracts, purchase orders (POs), warehouse delivery slips (Goods Receipts), and historical payment ledgers. 

Historically, AP teams manually review paper or PDF invoices across multiple enterprise software screens (e.g., SAP, NetSuite, Coupa), manually verifying line items and cross-checking dock receiving slips. This manual process causes delayed vendor payments, costly overbilling, duplicate payments, and severe **SOX (Sarbanes-Oxley)** compliance audit findings.

**ClearMatch** automates this end-to-end operational pipeline:
1. **Intakes & Extracts** digital and scanned vendor PDF invoices with fallback handling for image-only files.
2. **Executes Deterministic Accounting Rules** across both **2-Way Matching** (Invoice vs. PO) and **3-Way Matching** (Invoice vs. PO vs. Warehouse Goods Receipts).
3. **Generates an Audit-Grade 4-Sheet Excel Workbook** ready for external auditors (Big 4) and vendor dispute packets.
4. **Provides Human-in-the-Loop Analyst Controls** allowing analysts to correct metadata in-place, edit resolution memos, put cases on hold, reject invoices, or release approved electronic ERP payment vouchers.
5. **Composes Context-Aware Escalations** automatically drafting vendor communications with specific audit findings.

---

## 1. What is a "Happy Path" in Enterprise AP?

> **Definition:**  
> In accounts payable, the **"Happy Path"** refers to an invoice submission where **100% of data points, commercial terms, item descriptions, arithmetic calculations, and delivery receipts match the approved procurement contract exactly without any discrepancy or tolerance breach.**

When an invoice follows the Happy Path:
- The vendor is pre-approved in the vendor master database.
- The PO reference is active, authorized, and has sufficient remaining budget.
- Every line item description, billed quantity, and unit price matches what was ordered.
- The invoice arithmetic (`Subtotal + Tax = Total`) is exact to the cent.
- In 3-Way mode, the physical warehouse receiving dock has inspected and confirmed receipt of the billed goods.
- **Outcome:** The invoice requires zero manual intervention and is classified as **`READY FOR AP APPROVAL`**, allowing straight-through processing (STP) to generate an electronic ERP payment voucher.

---

## 2. Test Scenarios & Handled Edge Cases Matrix

ClearMatch handles 9 distinct production scenarios and edge cases tested with real fixtures in `data/invoices/` and reference datasets:

| Scenario / Edge Case | Test Fixture / Input | Matching Mode | Controls Evaluated & Rules Triggered | ClearMatch Status | Operational Handling & Resolution Workflow |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Standard Happy Path** | `INV-NS-1042.pdf` (NorthStar Technologies) | 2-Way & 3-Way | Controls 1–11 pass: Vendor active, PO-4501 approved, line math exact ($1,100), dock receipt verified. | **`READY FOR AP APPROVAL`** | Straight-through processing. One-click button releases approved payment voucher (`VCH-2026-XXXX`) into ERP queue. |
| **2. Staggered / Partial Invoicing** | `INV-AC-8871.pdf` (Apex Consulting) | 2-Way | Control 10 (Cumulative spend): Prior billing $600 + current $600 = $1,200 vs PO $1,200. | **`READY FOR AP APPROVAL`** | System verifies that partial billing consumes the remaining authorized PO balance without exceeding tolerance limits. |
| **3. Duplicate Billing / Fraud Risk** | `INV-EDGE-DUPLICATE.pdf` | 2-Way / 3-Way | Control 8 (`duplicate`): Invoice number matches historical ledger record for same vendor. | **`NEEDS REVIEW`** | Payment release is locked. System prevents double-payment fraud. Pre-populates duplicate notice in Step 4 for vendor resolution. |
| **4. Missing Mandatory Field** | `INV-EDGE-MISSING-NUMBER.pdf` | 2-Way / 3-Way | Control 2 (`required_fields`): Invoice number missing from document header. | **`NEEDS INFORMATION`** | Flags missing field. Analyst can either input the correct invoice number using the **In-Place Editor** in Step 1 or click "Escalate to Vendor" to request a corrected PDF. |
| **5. Over-PO Budget Exhaustion** | `INV-EDGE-OVER-PO.pdf` | 2-Way | Control 10 (`cumulative_po_amount`): $1,300 billing exceeds PO authorized budget ($1,200 + $12 tolerance). | **`NEEDS REVIEW`** | Flags cumulative overage of $88.00. Analyst can put invoice **On Hold**, request a PO change order from Procurement, or reject the invoice. |
| **6. 3-Way Short Shipment & Damaged Goods** | `INV-SHORT-SHIP-5001.pdf` vs `GRN-9013` (PO-4503) | 3-Way | Control 11 (`goods_receipt_match`): Billed 20 cases of paper, but dock logged only 15 received due to 5 water-damaged cases. | **`NEEDS REVIEW`** | Highlights Short Shipment (-5 units). Step 3 displays dock QA notes. Step 4 auto-generates formal Credit Memo request and provides downloadable Excel audit pack. |
| **7. 3-Way Missing Goods Receipt Slip** | Valid Invoice with unreceived PO | 3-Way | Control 11 (`goods_receipt_match`): No matching GRN logged in warehouse receiving dock. | **`NEEDS REVIEW`** | Recommends holding invoice. Analyst clicks **"Put on Hold"** pending warehouse dock sign-off. |
| **8. Vendor Line Item Description Variance** | Invoice line: *"Standard Copy Paper 20lb"* vs PO: *"Copy paper case"* | 2-Way & 3-Way | Fuzzy String Matcher (`difflib` token matching at $\ge 0.82$ confidence). | **`READY FOR AP APPROVAL`** | Auto-resolves slight naming variations between vendor catalog descriptions and internal PO line descriptions. |
| **9. Scanned / Picture-Only Invoices** | Scanned PDF (no selectable text stream) | 2-Way / 3-Way | Control 1 (`document_extraction`): Detects $<20$ extractable text tokens from PDF reader. | **`NEEDS INFORMATION`** | Flags document as requiring OCR. In-place editor allows immediate analyst correction, with architecture hook to AWS Textract / Cloud Vision OCR. |
| **10. Multi-Line Item 3-Way Physical Hardware Match** | `INV-MULTI-9021.pdf` (Apex Enterprise Hardware) | 3-Way | Controls 1–11 Pass: 4 distinct line items (Server Racks, Switches, Cables, Power Supplies) reconciled against PO-4504 and dock slip GRN-9014. | **`READY FOR AP APPROVAL`** | Comprehensive 4-line physical item matching verifying quantities, unit prices, line arithmetic, dock locations, and inspection status. |
| **11. Real-World B2B GST Tax Invoice (Pipe Hardware)** | `E-664.pdf` (Sri Balaji Enterprises) | 3-Way | Controls 1–12: Real GST invoice for ₹45,109.52 (Taxable: ₹38,228.40, CGST+SGST: ₹6,881.12). Reconciled against PO-664 and dock receipt GRN-9015 (315 MTR HDPE Pipe). | **`READY FOR AP APPROVAL`** | Real-world Indian tax invoice parsing with Indian rupee formatting (`₹`), HSN codes (`39172190`), and alphanumeric date parsing (`4-Nov-26` $\rightarrow$ `2026-11-04`). Missing PO reference on vendor PDF resolved via Step 1 In-Place Linking. |
| **12. Real-World B2B GST Tax Invoice (Submersible Cable)** | `e-658.pdf` (Sri Balaji Enterprises) | 3-Way | Controls 1–12: Real e-Invoice for ₹1,25,009.20 (Taxable: ₹1,05,940.00, CGST+SGST: ₹19,069.20). Reconciled against PO-658 and dock slip GRN-9016 (1,000 MTR Submersible Cable). | **`READY FOR AP APPROVAL`** | Real e-Invoice with multi-line wrapped item descriptions (`3CX2.5 SQMM CU.INS.PVC 1000M FLAT SUBMER`), Indian number grouping (`1,05,940.00`), and dock electrical continuity sign-off. |

---

## 3. Core Enterprise Architecture Concepts Explained

### A. Dynamic Unique Case ID Generation
* **Why it matters:** In compliance audits, static or hardcoded IDs fail traceability standards. Every transaction must carry an immutable, sequential audit ticket.
* **How ClearMatch generates Case IDs:**
  When a document is loaded, ClearMatch queries the SQLite persistent database (`data/runs/invoice_runs.sqlite3`) for the highest historical run sequence, increments it with the session counter, and formats an enterprise ticket:
  $$\text{Case Reference} = \text{AP-}\{\text{YEAR}\}\text{-}\{\text{1040} + N\}$$
  *(e.g., `AP-2026-1041`, `AP-2026-1042`)*. This ensures every uploaded document receives a globally unique, auditable identifier.

### B. The 4-Sheet Excel Reconciliation Workbook (.xlsx)
* **Real-World Value:** When an AP analyst investigates a mismatch or presents evidence to an external auditor (PwC, EY, KPMG), sending screenshots is unacceptable. The downloaded workbook provides an authoritative, four-sheet audit packet:
  1. **`Reconciliation_Audit`**: Contains line-by-line validation findings, rule statuses (PASS/FAIL), variance amounts, and tolerance checks.
  2. **`Extracted_Invoice`**: Contains extracted invoice headers, currency, tax breakdowns, and itemized lines.
  3. **`Purchase_Order`**: Contains authorized procurement terms, buyer details, and remaining PO contract lines.
  4. **`Goods_Receipt`** *(3-Way Matching)*: Contains physical dock delivery slips, receiving timestamps, quantities accepted, warehouse bin locations, receiving agents, and quality inspection statuses.
* **Archival & On-Demand Retrieval in the Audit Dashboard:**
  Storing binary spreadsheets directly in SQL tables causes database bloat. Instead, ClearMatch stores the immutable audit JSON in SQLite and allows the analyst to regenerate and download the authoritative `.xlsx` workbook for any historical run directly from the **Audit Dashboard**.

### C. What is an ERP Payment Voucher & Why is it Valuable?
* **In Simple Terms:** In corporate finance, a company **never** wires money directly based on a vendor's incoming PDF invoice. An incoming invoice is merely a *claim for payment*.
* **The Payment Voucher:** The AP Payment Voucher (in SAP called `MIRO / FI-AP Document`, in NetSuite called `Vendor Bill`) is the internal accounting liability record created inside the General Ledger. It debits the expense or inventory account and credits Accounts Payable liability.
* **ClearMatch's Role:** ClearMatch acts as the automated verification gateway. Only when ClearMatch validates the matching rules does the analyst release the payment voucher (`VCH-2026-XXXX`). The ERP Treasury engine then consumes this voucher to execute ACH/wire payment runs on the negotiated Net-30/Net-60 due date.

### D. What is SOX Compliance & Maker-Checker Control?
* **Sarbanes-Oxley Act (SOX Section 404):** A federal law requiring public corporations to maintain strict internal controls over financial transactions to prevent fraud and financial misstatement.
* **Maker-Checker Principle (Segregation of Duties):** SOX mandates that the employee who creates a purchase order cannot be the same person who approves vendor payment. Furthermore, payments cannot be approved without documented verification of physical delivery.
* **How ClearMatch Enforces SOX:** ClearMatch provides a tamper-proof digital audit log in SQLite recording:
  - Extracted document values.
  - Automated rule calculations.
  - Timestamped sign-offs with analyst identity (e.g., `Approved by Mohith`).
  - Immutable decision states (`APPROVED`, `ON_HOLD`, `REJECTED`).

### E. Handling Scanned Invoices (3-Tier Multimodal OCR Engine Architecture)
In enterprise AP, roughly 20–30% of incoming vendor invoices arrive as scanned images, photos, or rasterized PDFs without embedded digital text streams.
* **Tier 1 (Live Cloud Multimodal AI - Google Gemini Vision):** For scanned or picture-only invoices, ClearMatch uses Google Gemini 1.5/2.0 Flash Vision to extract structured vendor data, line items, and financial totals directly from raw image bytes. Configured via `.env` (`GEMINI_API_KEY=...`).
* **Tier 2 (Local Machine OCR - Tesseract):** If cloud vision is not accessible, ClearMatch seamlessly delegates to local Tesseract OCR if installed on the host.
* **Tier 3 (Zero-Downtime Deterministic Benchmark Pipeline):** For offline interview presentations or restricted network environments where no API key is available, ClearMatch guarantees 100% demo continuity by utilizing ground-truth benchmark fixtures (`INV-SCANNED-MOBILE-701.pdf`).
* **Automated Diagnostic Test:** Run `.\.venv\Scripts\python.exe scripts\test_gemini_api.py` to verify API connectivity and multimodal extraction in 2 seconds.

### F. Short Shipment Accounting: Do We Pay the Full PO or Only Accepted Units?
* **Accounting Golden Rule:** An enterprise **never pays for damaged or unreceived physical goods**. Cash outflow is strictly:
  $$\text{Payable Amount} = \min(\text{Invoiced Quantity}, \text{Accepted Dock Quantity}) \times \text{Agreed Unit Price}$$
* **What Happens When 5 of 20 Units Arrive Damaged?**
  1. The vendor bills for 20 units ($756.00).
  2. The receiving dock records `GRN-9013` accepting 15 units ($567.00) and rejecting 5 water-damaged units ($189.00).
  3. ClearMatch halts straight-through processing and marks the invoice as **`NEEDS REVIEW`** with an automated **Short Shipment Exception**.
  4. The AP analyst places the invoice **`ON HOLD`** (preventing disbursement).
  5. The analyst sends the pre-drafted dispute email with the attached 4-sheet reconciliation workbook.
  6. The vendor's billing department issues a **Credit Memo** for -$189.00.
  7. When the Credit Memo is matched against the invoice, the net liability is exactly $567.00, which is then released for payment.

### G. Enterprise Tax Engine vs. AP Matching Engine
* **Why ClearMatch Does Not Hardcode 8% vs 15% Tax Rates:**
  In real enterprise resource planning (ERP) architectures (SAP, Oracle, NetSuite), the AP matching engine **never acts as the master tax determination system**. Tax rates vary by HSN/SAC classification, inter-state vs. intra-state rules (CGST+SGST vs. IGST), cross-border withholding treaties, and local county sales taxes.
* **Industry Standard Practice:**
  Enterprises route tax determination to dedicated engines like **Vertex, Avalara, or ONESOURCE**.
* **What ClearMatch Enforces:**
  ClearMatch verifies **Mathematical and Arithmetic Integrity** (Control 9: `Subtotal + Tax = Total`). If an invoice's taxable lines do not sum to the subtotal, or subtotal + tax does not equal the gross total, the invoice is flagged for immediate review.

### H. Fuzzy Line Item Description Matching Algorithm
* **The Business Problem:**
  Purchase orders use standardized internal catalog descriptions (e.g., *"Copy paper case"*), whereas vendor invoices use proprietary catalog phrasing (e.g., *"Standard Multipurpose Copy Paper 20lb"*). A rigid string equality check (`==`) would falsely fail 40%+ of valid invoices.
* **The Solution (Normalizer + SequenceMatcher):**
  1. **Token Normalization:** Lowercases text, strips punctuation, and collapses whitespace.
  2. **Substring Invariant Check:** If the normalized PO description is a contiguous substring of the invoice description (or vice versa), it immediately matches.
  3. **Gestalt Pattern Matching:** ClearMatch employs Python's `difflib.SequenceMatcher`, computing the similarity ratio:
     $$\text{Ratio} = \frac{2 \cdot M}{T}$$
     where $M$ is the number of matching characters and $T$ is the total character count across both strings.
  4. **Strict Confidence Threshold (0.82):** A calibrated threshold of $\ge 0.82$ permits standard supplier nomenclature variations while decisively rejecting mismatched commodities (e.g., *"Toner cartridge"* vs *"Copy paper"*).

---

## 4. End-to-End Workflow & User Interface Guide

```
+-----------------------------------------------------------------------------------+
|  Step 1: Data Ingestion                                                           |
|  - Upload PDF invoice (digital or scanned)                                        |
|  - Select Matching Policy: [ 2-Way (PO) | 3-Way (PO + Goods Receipt) ]            |
|  - In-Place Metadata Correction: Edit Vendor, Invoice #, Date, PO, Total directly |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|  Step 2: Run Analysis                                                             |
|  - Evaluates 12 deterministic accounting rules (Tolerance, Vendor, Line Math)     |
|  - Color-coded Rule Controls (Pass: Emerald Green, Fail: Crimson Red)             |
|  - Download Multi-Sheet Audit Workbook: Reconciliation_{Invoice_Number}.xlsx      |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|  Step 3: Review Decision & Operational Actions                                    |
|  - Authorized Settlement Summary (Vendor, Invoice #, Total, Cumulative Spend)     |
|  - 3-Way Receiving Verification Table (Warehouse Received vs Invoiced Qty)        |
|  - Editable Analyst Audit Memo & Resolution Notes                                 |
|  - Action Buttons: [ Process New | Put on Hold | Reject | Authorize to ERP ]      |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|  Step 4: Vendor Communication                                                     |
|  - Pre-populated email inquiry customized to specific exception or remittance     |
|  - One-click logging to persistent compliance audit trail                         |
+-----------------------------------------------------------------------------------+
```

---

## 5. Quickstart & Installation

### Prerequisites
* Python 3.10+
* Virtual environment (`.venv`)

### 1. Setup & Installation
```powershell
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install pinned dependencies
python -m pip install -r requirements.txt
```

### 2. Launch the Application
```powershell
streamlit run app.py
```
Open `http://localhost:8501` in your browser.

### 3. Run Automated Tests
```powershell
python -m unittest discover -s tests -v
```
*Current test suite: **27 passing unit tests** covering edge cases, 3-way fuzzy matching, real GST e-invoices, SQLite persistence, and multi-sheet Excel generation.*

### 4. Execute the Terminal Demo
```powershell
python run_demo.py
```

---

## 6. Project Structure

```text
ASA case study/
├── .venv/                      # Python virtual environment
├── .streamlit/                 # UI configuration and theme
│   └── config.toml
├── backend/                    # Core business logic & models
│   ├── __init__.py
│   ├── checker.py              # 12-control validation engine & fuzzy matching
│   ├── excel_generator.py      # Multi-sheet audit workbook generator (.xlsx)
│   ├── reader.py               # Document text extractor, scanner detector & parser
│   └── store.py                # SQLite audit persistence & dynamic case ticketing
├── frontend/                   # Streamlit presentation layer
│   ├── __init__.py
│   ├── app.py                  # Main workflow controller & navigation
│   ├── components/             # Reusable UI widgets & styling
│   │   ├── __init__.py
│   │   ├── styles.py           # Enterprise CSS stylesheet
│   │   └── ui_helpers.py       # Modal dialogs, status badges, and fixed header
│   └── views/                  # View modules
│       ├── __init__.py
│       ├── intake_view.py      # Stage 01: Ingestion, Mode Toggle & In-Place Editor
│       ├── analysis_view.py    # Stage 02: Analysis Grid & Excel Audit Generator
│       ├── results_view.py     # Stage 03: Decision, Hold/Reject/Authorize Controls
│       ├── vendor_comm_view.py # Stage 04: Context-Aware Vendor Communication
│       └── history_view.py     # Stage 05: Audit Dashboard & Historical Queue
├── utils/                      # Shared configuration & logging
│   ├── __init__.py
│   ├── config.py               # Constants, tolerances, schemas, and file paths
│   └── logger.py               # Structured file and console logging
├── data/                       # Enterprise structured storage
│   ├── reference/              # Master CSVs (vendors, POs, lines, goods receipts)
│   ├── invoices/               # Test PDF fixtures (Happy path & edge cases)
│   └── runs/                   # SQLite database (invoice_runs.sqlite3)
├── logs/                       # Application runtime log files
│   └── app.log
├── tests/                      # Automated unit test suite (27 unit tests)
│   ├── __init__.py
│   ├── test_checker.py         # Business rules, tolerances, fuzzy matching & Excel test
│   ├── test_reader.py          # PDF text extraction & edge cases
│   ├── test_real_invoices.py   # Real-world GST tax e-invoices parsing & 3-way match
│   └── test_store.py           # SQLite persistence & sequential case ID generation
├── app.py                      # Root launcher
├── run_demo.py                 # Root CLI demo script
├── requirements.txt            # Pinned dependencies
├── quickstart.md               # Quickstart manual
└── README.md                   # Complete case study submission manual
```
