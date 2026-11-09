"""Application configuration and centralized directory paths."""

from __future__ import annotations

from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
REFERENCE_DIR = DATA_DIR / "reference"
INVOICES_DIR = DATA_DIR / "invoices"
RUNS_DIR = DATA_DIR / "runs"
LOGS_DIR = BASE_DIR / "logs"

# Database & Logging paths
RUNS_DB_PATH = RUNS_DIR / "invoice_runs.sqlite3"
LOG_FILE_PATH = LOGS_DIR / "app.log"

# Upload & File Limits
MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MB limit

# Team & Operations Defaults
TEAM_MEMBERS = [
    "Mohith · AP Analyst",
    "Aarav · AP Reviewer",
    "Priya · Procurement",
]
DEFAULT_CASE_REFERENCE = "AP-2026-1042"

# CSV Data Validation Schemas
CSV_REQUIREMENTS = {
    "vendors.csv": ["vendor_id", "legal_name", "status"],
    "purchase_orders.csv": [
        "po_number",
        "vendor_id",
        "currency",
        "status",
        "total",
        "tolerance_amount",
        "tolerance_percent",
    ],
    "purchase_order_lines.csv": [
        "po_number",
        "description",
        "quantity",
        "unit_price",
        "line_total",
    ],
    "processed_invoice_history.csv": [
        "vendor_id",
        "invoice_number",
        "po_number",
        "total",
    ],
    "goods_receipts.csv": [
        "grn_number",
        "po_number",
        "vendor_id",
        "item_description",
        "quantity_received",
    ],
}

# Status Definitions
STATUS_READY = "READY_FOR_AP_APPROVAL"
STATUS_REVIEW = "NEEDS_REVIEW"
STATUS_INFO = "NEEDS_INFORMATION"

