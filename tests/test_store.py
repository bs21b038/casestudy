"""Unit tests for the SQLite run store."""

import tempfile
import unittest
from pathlib import Path

from backend.store import get_next_case_reference, list_runs, save_run, update_run


class TestRunStore(unittest.TestCase):
    def test_save_and_list_runs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_db = Path(temp_dir) / "test_runs.sqlite3"
            test_result = {
                "status": "NEEDS_REVIEW",
                "summary": "Check mismatch test",
                "checks": [{"check": "total", "result": "fail", "detail": "Discrepancy"}],
            }
            run_id = save_run("invoice_test.pdf", test_result, db_path=temp_db)
            runs = list_runs(db_path=temp_db)

            self.assertEqual(run_id, 1)
            self.assertEqual(len(runs), 1)
            self.assertEqual(runs[0]["filename"], "invoice_test.pdf")
            self.assertEqual(runs[0]["status"], "NEEDS_REVIEW")
            self.assertEqual(runs[0]["result"], test_result)

    def test_update_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_db = Path(temp_dir) / "test_runs.sqlite3"
            test_result = {
                "status": "READY_FOR_AP_APPROVAL",
                "summary": "Ready for sign-off",
            }
            run_id = save_run("invoice_test.pdf", test_result, db_path=temp_db)
            
            # Transition to APPROVED with voucher and reviewer
            updated_result = {
                "status": "APPROVED",
                "summary": "APPROVED & RELEASED: All checks verified",
                "voucher_number": "VCH-2026-1041",
                "reviewer": "Mohith · AP Operations Analyst",
                "net_payable": 600.0,
            }
            update_run(run_id, updated_result, db_path=temp_db)
            
            runs = list_runs(db_path=temp_db)
            self.assertEqual(len(runs), 1)  # No duplicates created
            self.assertEqual(runs[0]["status"], "APPROVED")
            self.assertEqual(runs[0]["result"]["voucher_number"], "VCH-2026-1041")
            self.assertEqual(runs[0]["result"]["net_payable"], 600.0)

    def test_get_next_case_reference(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_db = Path(temp_dir) / "test_runs.sqlite3"
            ref1 = get_next_case_reference(db_path=temp_db, session_offset=0)
            self.assertTrue(ref1.startswith("AP-2026-1041"))

            save_run("inv.pdf", {"status": "READY"}, db_path=temp_db)
            ref2 = get_next_case_reference(db_path=temp_db, session_offset=0)
            self.assertTrue(ref2.startswith("AP-2026-1042"))


if __name__ == "__main__":
    unittest.main()

