"""Unit tests for the backend AP invoice checker."""

import unittest
from backend.checker import evaluate_invoice, load_csv
from backend.reader import read_invoice_pdf
from utils.config import (
    INVOICES_DIR,
    REFERENCE_DIR,
    STATUS_INFO,
    STATUS_READY,
    STATUS_REVIEW,
)

VENDORS = load_csv(REFERENCE_DIR / "vendors.csv", ["vendor_id", "legal_name", "status"])
POS = load_csv(REFERENCE_DIR / "purchase_orders.csv", ["po_number", "vendor_id", "currency", "status", "total"])
PO_LINES = load_csv(REFERENCE_DIR / "purchase_order_lines.csv", ["po_number", "description", "quantity", "unit_price"])
HISTORY = load_csv(REFERENCE_DIR / "processed_invoice_history.csv", ["vendor_id", "invoice_number", "po_number", "total"])


class TestInvoiceChecker(unittest.TestCase):
    def setUp(self) -> None:
        self.invoice = {
            "vendor_name": "Northstar Office Supplies Ltd",
            "invoice_number": "NS-1042",
            "invoice_date": "2026-10-28",
            "po_number": "PO-4501",
            "currency": "USD",
            "subtotal": "1100.00",
            "tax_amount": "88.00",
            "total": "1188.00",
            "line_items": [
                {"description": "Copy paper case", "quantity": "20", "unit_price": "35.00", "line_total": "700.00"},
                {"description": "Toner cartridge", "quantity": "5", "unit_price": "80.00", "line_total": "400.00"},
            ],
        }

    def evaluate(self, invoice=None):
        return evaluate_invoice(invoice or self.invoice, VENDORS, POS, PO_LINES, HISTORY)

    def test_happy_path_is_ready_for_approval(self):
        result = self.evaluate()
        self.assertEqual(result["status"], STATUS_READY)

    def test_missing_invoice_number_needs_information(self):
        invoice = {**self.invoice, "invoice_number": ""}
        result = self.evaluate(invoice)
        self.assertEqual(result["status"], STATUS_INFO)
        self.assertIn("invoice_number", result["missing_fields"])

    def test_duplicate_invoice_needs_review(self):
        invoice = {
            **self.invoice,
            "vendor_name": "Acme Cloud Services Inc",
            "invoice_number": "AC-8870",
            "po_number": "PO-4502",
            "subtotal": "600.00",
            "tax_amount": "0.00",
            "total": "600.00",
            "line_items": [],
        }
        self.assertEqual(self.evaluate(invoice)["status"], STATUS_REVIEW)

    def test_split_invoice_within_po_is_ready(self):
        invoice = {
            **self.invoice,
            "vendor_name": "Acme Cloud Services Inc",
            "invoice_number": "AC-8871",
            "po_number": "PO-4502",
            "subtotal": "600.00",
            "tax_amount": "0.00",
            "total": "600.00",
            "line_items": [
                {"description": "Cloud service onboarding hours", "quantity": "6", "unit_price": "100.00", "line_total": "600.00"}
            ],
        }
        result = self.evaluate(invoice)
        self.assertEqual(result["status"], STATUS_READY)
        self.assertEqual(result["amounts"]["cumulative_billed"], "1200.00")

    def test_total_arithmetic_mismatch_needs_review(self):
        invoice = {**self.invoice, "total": "1200.00"}
        self.assertEqual(self.evaluate(invoice)["status"], STATUS_REVIEW)

    def test_unmatched_line_description_needs_review(self):
        invoice = {
            **self.invoice,
            "line_items": [{"description": "Unknown Item", "quantity": "1", "unit_price": "5", "line_total": "5"}],
            "subtotal": "5",
            "tax_amount": "0",
            "total": "5",
        }
        self.assertEqual(self.evaluate(invoice)["status"], STATUS_REVIEW)

    def test_duplicate_pdf_edge_case(self):
        invoice = read_invoice_pdf(INVOICES_DIR / "INV-EDGE-DUPLICATE.pdf")
        result = self.evaluate(invoice)
        self.assertEqual(result["status"], STATUS_REVIEW)
        self.assertTrue(any(c["check"] == "duplicate" and c["result"] == "fail" for c in result["checks"]))

    def test_missing_number_pdf_edge_case(self):
        invoice = read_invoice_pdf(INVOICES_DIR / "INV-EDGE-MISSING-NUMBER.pdf")
        result = self.evaluate(invoice)
        self.assertEqual(result["status"], STATUS_INFO)
        self.assertIn("invoice_number", result["missing_fields"])

    def test_over_po_pdf_edge_case(self):
        invoice = read_invoice_pdf(INVOICES_DIR / "INV-EDGE-OVER-PO.pdf")
        result = self.evaluate(invoice)
        self.assertEqual(result["status"], STATUS_REVIEW)
        cumulative_check = next(c for c in result["checks"] if c["check"] == "cumulative_po_amount")
        self.assertEqual(cumulative_check["result"], "fail")

    def test_excel_reconciliation_generation(self):
        import io
        import openpyxl
        from backend.excel_generator import generate_reconciliation_workbook
        result = self.evaluate()
        # 2-way workbook (3 sheets)
        wb_bytes = generate_reconciliation_workbook(self.invoice, POS[0], PO_LINES, result)
        self.assertGreater(len(wb_bytes), 2000)
        wb = openpyxl.load_workbook(io.BytesIO(wb_bytes))
        self.assertEqual(wb.sheetnames, ["Reconciliation_Audit", "Extracted_Invoice", "Purchase_Order"])
        ws = wb["Reconciliation_Audit"]
        cell_vals = [cell.value for row in ws.iter_rows(max_row=8) for cell in row if cell.value]
        self.assertIn("Gross Billed Total", cell_vals)
        self.assertIn("Net Payable to ERP", cell_vals)
        self.assertIn("ERP Voucher #", cell_vals)
        self.assertIn("AP Reviewer", cell_vals)
        self.assertIn("Matching Mode", cell_vals)

        # 3-way workbook with Goods Receipts (4 sheets)
        grns = [{"receipt_id": "GRN-901", "po_number": "PO-4501", "item_description": "Copy paper case", "received_quantity": "20"}]
        result_3way = result.copy()
        result_3way["matching_mode"] = "3way"
        wb_3way_bytes = generate_reconciliation_workbook(self.invoice, POS[0], PO_LINES, result_3way, goods_receipts=grns)
        wb_3way = openpyxl.load_workbook(io.BytesIO(wb_3way_bytes))
        self.assertEqual(wb_3way.sheetnames, ["Reconciliation_Audit", "Extracted_Invoice", "Purchase_Order", "Goods_Receipt"])

    def test_three_way_matching_happy_path(self):
        grns = [
            {"grn_number": "GRN-901", "po_number": "PO-4501", "vendor_id": "V-1001", "item_description": "Copy paper case", "quantity_received": "20"},
            {"grn_number": "GRN-901", "po_number": "PO-4501", "vendor_id": "V-1001", "item_description": "Toner cartridge", "quantity_received": "5"},
        ]
        result = evaluate_invoice(self.invoice, VENDORS, POS, PO_LINES, HISTORY, goods_receipts=grns, matching_mode="3way")
        self.assertEqual(result["status"], STATUS_READY)
        grn_check = next(c for c in result["checks"] if c["check"] == "goods_receipt_match")
        self.assertEqual(grn_check["result"], "pass")

    def test_three_way_matching_short_shipment(self):
        # Warehouse only received 15 cases of copy paper, but invoice bills for 20
        grns = [
            {"grn_number": "GRN-901", "po_number": "PO-4501", "vendor_id": "V-1001", "item_description": "Copy paper case", "quantity_received": "15"},
            {"grn_number": "GRN-901", "po_number": "PO-4501", "vendor_id": "V-1001", "item_description": "Toner cartridge", "quantity_received": "5"},
        ]
        result = evaluate_invoice(self.invoice, VENDORS, POS, PO_LINES, HISTORY, goods_receipts=grns, matching_mode="3way")
        self.assertEqual(result["status"], STATUS_REVIEW)
        grn_check = next(c for c in result["checks"] if c["check"] == "goods_receipt_match")
        self.assertEqual(grn_check["result"], "fail")
        self.assertIn("Short shipment", grn_check["detail"])

    def test_three_way_matching_missing_grn(self):
        result = evaluate_invoice(self.invoice, VENDORS, POS, PO_LINES, HISTORY, goods_receipts=[], matching_mode="3way")
        self.assertEqual(result["status"], STATUS_REVIEW)
        grn_check = next(c for c in result["checks"] if c["check"] == "goods_receipt_match")
        self.assertEqual(grn_check["result"], "fail")
        self.assertIn("No Goods Receipt", grn_check["detail"])

    def test_fuzzy_line_item_description_matching(self):
        # Invoice has minor variation: 'Copy paper cases (white)' instead of 'Copy paper case'
        invoice = {
            **self.invoice,
            "line_items": [
                {"description": "Copy paper case (white)", "quantity": "20", "unit_price": "35.00", "line_total": "700.00"},
                {"description": "Toner cartridge replacement", "quantity": "5", "unit_price": "80.00", "line_total": "400.00"},
            ],
        }
        result = self.evaluate(invoice)
        self.assertEqual(result["status"], STATUS_READY)

    def test_short_shipment_pdf_fixture(self):
        from backend.reader import read_invoice_pdf
        from utils.config import INVOICES_DIR
        inv = read_invoice_pdf(INVOICES_DIR / "INV-SHORT-SHIP-5001.pdf")
        grns = [{"grn_number": "GRN-9013", "po_number": "PO-4503", "vendor_id": "V-1001", "item_description": "Copy paper case", "quantity_received": "15", "status_reason": "water-damaged"}]
        pos = [{"po_number": "PO-4503", "vendor_id": "V-1001", "currency": "USD", "status": "approved", "total": "756.00", "subtotal": "700.00", "tax_amount": "56.00", "tolerance_amount": "5.00", "tolerance_percent": "1.00"}]
        lines = [{"po_number": "PO-4503", "description": "Copy paper case", "quantity": "20", "unit_price": "35.00", "line_total": "700.00"}]
        result = evaluate_invoice(inv, VENDORS, pos, lines, HISTORY, goods_receipts=grns, matching_mode="3way")
        self.assertEqual(result["status"], STATUS_REVIEW)
        chk = next(c for c in result["checks"] if c["check"] == "goods_receipt_match")
        self.assertEqual(chk["result"], "fail")
        self.assertIn("Short shipment", chk["detail"])

    def test_multi_line_hardware_pdf_fixture(self):
        from backend.reader import read_invoice_pdf
        from utils.config import INVOICES_DIR
        inv = read_invoice_pdf(INVOICES_DIR / "INV-MULTI-9021.pdf")
        self.assertEqual(len(inv["line_items"]), 4)


if __name__ == "__main__":
    unittest.main()

