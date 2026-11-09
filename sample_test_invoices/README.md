# Sample Test Invoices for ClearMatch AP Operations

This folder contains pre-configured sample invoice PDFs designed to demonstrate the end-to-end capabilities of ClearMatch, including clean digital extraction, policy control verification, and complex operational edge cases.

---

### Test Scenarios Overview

| File Name | Test Category | Matching Mode | Expected Status | Key Behavior Demonstrated |
| :--- | :--- | :--- | :--- | :--- |
| **`INV-NS-1042.pdf`** | **Happy Path** (Clean Digital Invoice) | 2-Way (PO) | `READY_FOR_AP_APPROVAL` | 100% match against approved PO-4503; all 11 policy controls pass; ready for payment voucher authorization ($756.00). |
| **`INV-EDGE-DUPLICATE.pdf`** | **Edge Case 1** (Duplicate Billing Detection) | 2-Way (PO) | `NEEDS_REVIEW` | Engine detects that invoice number `AC-8870` for this vendor was previously processed; halts downstream execution to prevent accidental double disbursement. |
| **`INV-SHORT-SHIP-5001.pdf`** | **Edge Case 2** (3-Way Short Shipment / Damage) | 3-Way (PO + GRN) | `NEEDS_REVIEW` | Vendor billed for 10 units ($750.00), but warehouse Goods Receipt (GRN) received only 7 units (3 damaged). System withholds $225.00, sets Net Payable to $525.00, and drafts a vendor Credit Memo request. |
| **`INV-EDGE-MISSING-NUMBER.pdf`** | **Edge Case 3** (Missing Mandatory Data) | 2-Way (PO) | `NEEDS_INFORMATION` | Document is missing a mandatory invoice number; flags missing field and drafts vendor clarification email. |
| **`INV-SCANNED-MOBILE-701.pdf`** | **Edge Case 4** (Scanned / Mobile Image OCR) | 2-Way (PO) | `READY_FOR_AP_APPROVAL` | Non-selectable raster image/photo; triggers Google Gemini Multimodal Vision AI with anti-hallucination guardrails to accurately extract fields and line items. |

---

### How to Test Live

1. Open the live application URL: [https://clearmatch-ap.streamlit.app](https://clearmatch-ap.streamlit.app)
2. In **Stage 01: Data Ingestion**, select **2-Way (PO)** or **3-Way (PO + Goods Receipt)** matching mode.
3. Click **Browse files** and upload one of the sample PDF files above.
4. Verify the auto-extracted metadata and line items.
5. Click **Run Analysis** to inspect the real-time policy control scorecard and audit findings.
6. Click **Review Decision** to inspect Net Payable amounts, budget utilization, and release the official ERP Payment Voucher.
7. Click **Vendor Communication** to see context-aware vendor inquiry emails and download the authoritative multi-sheet Excel Reconciliation Workbook (`.xlsx`).
