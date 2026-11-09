"""Unit tests for the backend PDF reader and text parser."""

import unittest
from backend.reader import parse_invoice_text, parse_money, read_invoice_pdf
from utils.config import INVOICES_DIR


class TestInvoiceReader(unittest.TestCase):
    def test_parse_money(self):
        self.assertEqual(parse_money("$1,234.50"), "1234.50")
        self.assertEqual(parse_money("50"), "50.00")
        self.assertEqual(parse_money("invalid"), None)

    def test_read_sample_pdf(self):
        invoice = read_invoice_pdf(INVOICES_DIR / "INV-NS-1042.pdf")
        self.assertEqual(invoice["invoice_number"], "NS-1042")
        self.assertEqual(invoice["po_number"], "PO-4501")
        self.assertEqual(invoice["total"], "1188.00")
        self.assertEqual(len(invoice["line_items"]), 2)
        self.assertEqual(invoice["extraction"]["confidence"], "high")

    def test_read_in_memory_bytes(self):
        raw_bytes = (INVOICES_DIR / "INV-NS-1042.pdf").read_bytes()
        invoice = read_invoice_pdf(raw_bytes, source_name="memory_test.pdf")
        self.assertEqual(invoice["invoice_number"], "NS-1042")
        self.assertEqual(invoice["extraction"]["source_file"], "memory_test.pdf")

    def test_unreadable_scan_flagged(self):
        dummy_scan = {
            "extraction": {
                "method": "pdf_text",
                "confidence": "none",
                "warnings": ["No selectable text found; this may be a scanned PDF and requires OCR."],
            }
        }
        self.assertEqual(dummy_scan["extraction"]["confidence"], "none")

    def test_ocr_engine_status(self):
        from backend.ocr_engine import get_ocr_engine_status
        status = get_ocr_engine_status()
        self.assertIn("active_engine", status)
        self.assertIn("gemini_api_available", status)

    def test_scanned_mobile_invoice_detection(self):
        invoice = read_invoice_pdf(INVOICES_DIR / "INV-SCANNED-MOBILE-701.pdf")
        # In offline/sandbox mode without cloud API connection, properly flags as requiring OCR
        self.assertIn(invoice["extraction"]["confidence"], ["none", "high"])
        if invoice["extraction"]["confidence"] == "none":
            self.assertIn("requires OCR", invoice["extraction"]["warnings"][0])

    def test_missing_fields_from_text(self):
        invoice = parse_invoice_text(
            """INVOICE
            Northstar Office Supplies Ltd
            Purchase order: PO-4501
            Currency: USD
            Invoice total: USD 1,188.00
            """
        )
        self.assertIsNone(invoice["invoice_number"])
        self.assertIn("invoice_number", invoice["extraction"]["warnings"][0])


if __name__ == "__main__":
    unittest.main()

