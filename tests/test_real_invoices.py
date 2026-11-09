"""Test parsing and 3-way matching of real-world GST invoices."""

import unittest
from backend.reader import read_invoice_pdf
from backend.checker import evaluate_invoice, load_csv, STATUS_READY, STATUS_INFO
from utils.config import INVOICES_DIR, REFERENCE_DIR

VENDORS = load_csv(REFERENCE_DIR / "vendors.csv", ["vendor_id", "legal_name", "status"])
POS = load_csv(REFERENCE_DIR / "purchase_orders.csv", ["po_number", "vendor_id", "currency", "status", "total"])
PO_LINES = load_csv(REFERENCE_DIR / "purchase_order_lines.csv", ["po_number", "description", "quantity", "unit_price"])
HISTORY = load_csv(REFERENCE_DIR / "processed_invoice_history.csv", ["vendor_id", "invoice_number", "po_number", "total"])
GRNS = load_csv(REFERENCE_DIR / "goods_receipts.csv", ["grn_number", "po_number", "vendor_id", "item_description", "quantity_received"])

PATH_664 = INVOICES_DIR / "E-664.pdf"
PATH_658 = INVOICES_DIR / "e-658.pdf"


class TestRealGSTInvoices(unittest.TestCase):
    def test_parse_real_invoice_664(self):
        inv = read_invoice_pdf(PATH_664)
        self.assertEqual(inv["vendor_name"], "SRI BALAJI ENTERPRISES")
        self.assertEqual(inv["invoice_number"], "664")
        self.assertEqual(inv["invoice_date"], "2026-11-04")
        self.assertEqual(inv["currency"], "INR")
        self.assertEqual(inv["total"], "45109.52")
        self.assertEqual(inv["subtotal"], "38228.40")
        self.assertEqual(inv["tax_amount"], "6881.12")
        self.assertGreaterEqual(len(inv["line_items"]), 1)
        self.assertIn("HDPE PIPE", inv["line_items"][0]["description"])
        self.assertEqual(inv["line_items"][0]["quantity"], "315")
        self.assertEqual(inv["line_items"][0]["unit_price"], "121.36")
        self.assertEqual(inv["line_items"][0]["line_total"], "38228.40")

    def test_parse_real_invoice_658(self):
        inv = read_invoice_pdf(PATH_658)
        self.assertEqual(inv["vendor_name"], "SRI BALAJI ENTERPRISES")
        self.assertEqual(inv["invoice_number"], "658")
        self.assertEqual(inv["invoice_date"], "2026-11-03")
        self.assertEqual(inv["currency"], "INR")
        self.assertEqual(inv["total"], "125009.20")
        self.assertEqual(inv["subtotal"], "105940.00")
        self.assertEqual(inv["tax_amount"], "19069.20")
        self.assertGreaterEqual(len(inv["line_items"]), 1)
        self.assertIn("3CX2.5 SQMM", inv["line_items"][0]["description"])
        self.assertEqual(inv["line_items"][0]["quantity"], "1000")
        self.assertEqual(inv["line_items"][0]["unit_price"], "105.94")
        self.assertEqual(inv["line_items"][0]["line_total"], "105940.00")

    def test_3way_matching_invoice_664(self):
        inv = read_invoice_pdf(PATH_664)
        # Without PO number, flags missing field:
        res_no_po = evaluate_invoice(inv, VENDORS, POS, PO_LINES, HISTORY, goods_receipts=GRNS, matching_mode="3way")
        self.assertEqual(res_no_po["status"], STATUS_INFO)

        # With PO-664 assigned:
        inv["po_number"] = "PO-664"
        res = evaluate_invoice(inv, VENDORS, POS, PO_LINES, HISTORY, goods_receipts=GRNS, matching_mode="3way")
        self.assertEqual(res["status"], STATUS_READY)
        self.assertEqual(len(res["checks"]), 12)
        for c in res["checks"]:
            self.assertEqual(c["result"], "pass", f"Check {c['check']} failed: {c['detail']}")

    def test_3way_matching_invoice_658(self):
        inv = read_invoice_pdf(PATH_658)
        inv["po_number"] = "PO-658"
        res = evaluate_invoice(inv, VENDORS, POS, PO_LINES, HISTORY, goods_receipts=GRNS, matching_mode="3way")
        self.assertEqual(res["status"], STATUS_READY)
        self.assertEqual(len(res["checks"]), 12)
        for c in res["checks"]:
            self.assertEqual(c["result"], "pass", f"Check {c['check']} failed: {c['detail']}")


if __name__ == "__main__":
    unittest.main()
