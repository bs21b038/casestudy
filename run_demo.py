"""Command-line demonstration of AP invoice analysis across sample fixtures."""

from __future__ import annotations

import sys
from backend.checker import evaluate_invoice, load_csv
from backend.reader import read_invoice_pdf
from utils.config import INVOICES_DIR, REFERENCE_DIR

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def run_demo() -> None:
    """Run all sample invoices through the AP checking pipeline and print reasoned results."""
    vendors = load_csv(REFERENCE_DIR / "vendors.csv", ["vendor_id", "legal_name", "status"])
    purchase_orders = load_csv(
        REFERENCE_DIR / "purchase_orders.csv",
        ["po_number", "vendor_id", "currency", "status", "total", "tolerance_amount", "tolerance_percent"],
    )
    purchase_order_lines = load_csv(
        REFERENCE_DIR / "purchase_order_lines.csv",
        ["po_number", "description", "quantity", "unit_price", "line_total"],
    )
    history = load_csv(
        REFERENCE_DIR / "processed_invoice_history.csv",
        ["vendor_id", "invoice_number", "po_number", "total"],
    )

    invoice_paths = sorted(INVOICES_DIR.glob("INV-*.pdf"))
    if not invoice_paths:
        raise SystemExit(f"No sample invoices found in {INVOICES_DIR}")

    print("======================================================================")
    print("ClearMatch AP Invoice Analysis -- Automated CLI Demo")
    print("======================================================================\n")

    for invoice_path in invoice_paths:
        invoice = read_invoice_pdf(invoice_path)
        result = evaluate_invoice(invoice, vendors, purchase_orders, purchase_order_lines, history)
        status = result.get("status")
        print(f"[FILE] {invoice_path.name}")
        print(f"   Extraction : {invoice['extraction']['method']} (Confidence: {invoice['extraction']['confidence']})")
        print(f"   Status     : {status}")
        print(f"   Summary    : {result.get('summary')}")
        if result.get("amounts"):
            amt = result["amounts"]
            print(f"   Billed     : ${amt['cumulative_billed']} / PO Authorized: ${amt['po_total']} (Tolerance: ${amt['allowed_overage']})")
        print("-" * 70)


if __name__ == "__main__":
    run_demo()
