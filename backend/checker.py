"""Rule-based invoice-to-PO checks for the Accounts Payable matching engine.

Evaluates an invoice against approved vendors, purchase orders, PO lines, and historical
processed invoices. Recommends review outcomes without executing or authorizing payments.
"""

from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

from utils.config import STATUS_INFO, STATUS_READY, STATUS_REVIEW
from utils.logger import logger

CENT = Decimal("0.01")


class InputDataError(ValueError):
    """Raised when reference CSV files are missing or missing required headers."""


def load_csv(path: str | Path, required_columns: Iterable[str]) -> list[dict[str, str]]:
    """Load a CSV file and verify that required column headers exist."""
    path = Path(path)
    if not path.is_file():
        raise InputDataError(f"Required data file not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        headers = set(reader.fieldnames or [])
        missing = sorted(set(required_columns) - headers)
        if missing:
            raise InputDataError(
                f"{path.name} is missing required columns: {', '.join(missing)}"
            )
        return [dict(row) for row in reader]


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _money(value: Any) -> Decimal | None:
    if value is None or _text(value) == "":
        return None
    try:
        amount = Decimal(_text(value).replace(",", "").replace("$", ""))
    except InvalidOperation:
        return None
    return amount if amount.is_finite() else None


def _normalized(value: Any) -> str:
    return " ".join(_text(value).casefold().split())


def _is_match(text_a: str, text_b: str, threshold: float = 0.82) -> bool:
    """Fuzzy/token matcher for line item descriptions to handle minor supplier variations."""
    norm_a = _normalized(text_a)
    norm_b = _normalized(text_b)
    if not norm_a or not norm_b:
        return False
    if norm_a == norm_b or norm_a in norm_b or norm_b in norm_a:
        return True
    return SequenceMatcher(None, norm_a, norm_b).ratio() >= threshold


def _check(checks: list[dict[str, str]], name: str, outcome: str, detail: str) -> None:
    checks.append({"check": name, "result": outcome, "detail": detail})


def _review_result(
    checks: list[dict[str, str]],
    invoice: dict[str, Any],
    summary: str,
    amounts: dict[str, Any] | None = None,
    reconciled_grn_lines: list[dict[str, Any]] | None = None,
    reconciled_po_lines: list[dict[str, Any]] | None = None,
    matched_vendor_id: str | None = None,
    matched_po_number: str | None = None,
    matching_mode: str = "2way",
) -> dict[str, Any]:
    return {
        "status": STATUS_REVIEW,
        "summary": summary,
        "checks": checks,
        "missing_fields": [],
        "invoice": invoice,
        "amounts": amounts or {},
        "reconciled_grn_lines": reconciled_grn_lines or [],
        "reconciled_po_lines": reconciled_po_lines or [],
        "matched_vendor_id": matched_vendor_id,
        "matched_po_number": matched_po_number,
        "matching_mode": matching_mode,
    }


def evaluate_invoice(
    invoice: dict[str, Any],
    vendors: list[dict[str, Any]],
    purchase_orders: list[dict[str, Any]],
    purchase_order_lines: list[dict[str, Any]],
    invoice_history: list[dict[str, Any]],
    goods_receipts: list[dict[str, Any]] | None = None,
    matching_mode: str = "2way",
) -> dict[str, Any]:
    """Evaluate an invoice against procurement reference records.

    Supports both 2-Way (Invoice-to-PO) and 3-Way (Invoice-to-PO-to-GRN) matching policies.
    Returns a decision dictionary containing status, summary, and itemized checks.
    """
    checks: list[dict[str, str]] = []

    # 1. Extraction Quality Check
    extraction = invoice.get("extraction")
    if isinstance(extraction, dict):
        raw_warnings = extraction.get("warnings") or []
        # Resolve warnings for fields that have now been supplied or corrected
        extraction_warnings = []
        for w in raw_warnings:
            if "Required fields were not extracted:" in w:
                missing_in_w = [f.strip() for f in w.split(":")[-1].split(",")]
                still_missing = [f for f in missing_in_w if not _text(invoice.get(f))]
                if still_missing:
                    extraction_warnings.append("Required fields were not extracted: " + ", ".join(still_missing))
            else:
                extraction_warnings.append(w)

        if extraction.get("confidence") in {"low", "none"}:
            _check(
                checks,
                "document_extraction",
                "fail",
                "Extraction confidence is too low for automated matching.",
            )
            return _review_result(
                checks,
                invoice,
                "Invoice text could not be read reliably; OCR or human review is required.",
            )
        method = extraction.get("method", "pdf_text")
        if "gemini" in method:
            msg = "Scanned document (image); fields extracted via Gemini Vision AI."
            if extraction_warnings:
                msg += f" ({'; '.join(extraction_warnings)})"
            _check(checks, "document_extraction", "pass", msg)
        elif "tesseract" in method:
            msg = "Scanned document (image); fields extracted via Local Tesseract OCR."
            if extraction_warnings:
                msg += f" ({'; '.join(extraction_warnings)})"
            _check(checks, "document_extraction", "pass", msg)
        elif extraction_warnings:
            _check(checks, "document_extraction", "warning", "; ".join(extraction_warnings))
        else:
            _check(checks, "document_extraction", "pass", "Invoice fields were extracted from the PDF text.")

    # 2. Required Invoice Fields
    missing_fields = [
        field
        for field in ("vendor_name", "invoice_number", "invoice_date", "currency", "total")
        if not _text(invoice.get(field))
    ]
    po_number = _text(invoice.get("po_number"))
    if not po_number:
        missing_fields.append("po_number")

    amount_fields = ("total", "subtotal", "tax_amount")
    parsed_amounts = {field: _money(invoice.get(field)) for field in amount_fields}
    for field in ("total", "subtotal", "tax_amount"):
        if invoice.get(field) not in (None, "") and parsed_amounts[field] is None:
            missing_fields.append(f"valid {field}")

    # Check for unreadable / null values in line items (Anti-Hallucination Guardrail)
    line_items = invoice.get("line_items") or []
    for idx, line in enumerate(line_items, start=1):
        for attr in ("description", "quantity", "unit_price", "line_total"):
            v = line.get(attr)
            if v is None or str(v).strip() == "" or str(v).strip().lower() == "none":
                missing_fields.append(f"line_{idx}_{attr} (unreadable)")

    if missing_fields:
        unique_missing = list(dict.fromkeys(missing_fields))
        _check(checks, "required_fields", "fail", "Missing or invalid: " + ", ".join(unique_missing))
        logger.info("Evaluation result: %s (missing fields: %s)", STATUS_INFO, unique_missing)
        return {
            "status": STATUS_INFO,
            "summary": "Required invoice information is missing or invalid; request clarification.",
            "checks": checks,
            "missing_fields": unique_missing,
            "invoice": invoice,
        }
    _check(checks, "required_fields", "pass", "Required invoice fields are present and numeric amounts are valid.")

    # 3. Invoice Date Format (YYYY-MM-DD)
    invoice_date = _text(invoice.get("invoice_date"))
    try:
        date.fromisoformat(invoice_date)
    except ValueError:
        _check(checks, "invoice_date", "fail", "Date must be normalized to YYYY-MM-DD for this prototype.")
        return {
            "status": STATUS_INFO,
            "summary": "Invoice date could not be interpreted; correct or review the date.",
            "checks": checks,
            "missing_fields": ["valid invoice_date (YYYY-MM-DD)"],
            "invoice": invoice,
        }
    _check(checks, "invoice_date", "pass", f"Invoice date {invoice_date} is valid.")

    # 4. Approved Vendor Master Lookup
    vendor_name = _normalized(invoice.get("vendor_name"))
    vendor = next(
        (row for row in vendors if _normalized(row.get("legal_name")) == vendor_name),
        None,
    )
    if vendor is None:
        _check(checks, "vendor", "fail", "Vendor name was not found in the vendor master.")
        return _review_result(checks, invoice, "Vendor is unknown; confirm the vendor before proceeding.")

    vendor_id = _text(vendor.get("vendor_id"))
    if _text(vendor.get("status")).casefold() != "approved":
        _check(checks, "vendor", "fail", f"Vendor {vendor_id} is not marked approved.")
        return _review_result(checks, invoice, "Vendor is not approved; procurement review is required.")
    _check(checks, "vendor", "pass", f"{vendor.get('legal_name')} ({vendor_id}) is an approved vendor.")

    # 5. PO Existence, Approval, and Ownership
    po = next((row for row in purchase_orders if _text(row.get("po_number")) == po_number), None)
    if po is None:
        _check(checks, "purchase_order", "fail", f"PO {po_number} was not found.")
        return _review_result(checks, invoice, "No matching purchase order was found.")
    if _text(po.get("status")).casefold() != "approved":
        _check(checks, "purchase_order", "fail", f"PO {po_number} is not approved.")
        return _review_result(checks, invoice, "Purchase order is not approved.")
    if _text(po.get("vendor_id")) != vendor_id:
        _check(checks, "purchase_order", "fail", "PO vendor does not match the invoice vendor.")
        return _review_result(checks, invoice, "Invoice vendor and PO vendor do not match.")
    if _text(po.get("currency")).upper() != _text(invoice.get("currency")).upper():
        _check(checks, "currency", "fail", "Invoice currency does not match the PO currency.")
        return _review_result(checks, invoice, "Currency mismatch; confirm the invoice and PO.")
    _check(checks, "purchase_order", "pass", f"PO {po_number} is approved and belongs to the approved vendor.")
    _check(checks, "currency", "pass", f"Both invoice and PO use {_text(po.get('currency')).upper()}.")

    # 6. Duplicate Detection
    is_three_way = str(matching_mode).lower().startswith("3")
    invoice_number = _text(invoice.get("invoice_number")).casefold()
    duplicate = next(
        (
            row
            for row in invoice_history
            if _text(row.get("vendor_id")) == vendor_id
            and _text(row.get("invoice_number")).casefold() == invoice_number
        ),
        None,
    )
    if duplicate:
        _check(
            checks,
            "duplicate",
            "fail",
            f"Invoice number {_text(invoice.get('invoice_number'))} for this vendor already appears in history.",
        )
        # Mark subsequent checks as skipped so the full scorecard is visible in grey
        _check(checks, "invoice_arithmetic", "skipped", "Skipped: Blocked by duplicate invoice exception.")
        _check(checks, "line_items", "skipped", "Skipped: Blocked by duplicate invoice exception.")
        _check(checks, "cumulative_po_amount", "skipped", "Skipped: Blocked by duplicate invoice exception.")
        _check(checks, "po_arithmetic", "skipped", "Skipped: Blocked by duplicate invoice exception.")
        if is_three_way:
            _check(checks, "goods_receipt_match", "skipped", "Skipped: Blocked by duplicate invoice exception.")
        return _review_result(checks, invoice, "Possible duplicate invoice; do not mark ready until checked.")
    _check(checks, "duplicate", "pass", "No matching vendor and invoice number found in processed history.")

    # 7. Invoice Header Arithmetic (Subtotal + Tax = Total)
    subtotal = parsed_amounts["subtotal"]
    tax_amount = parsed_amounts["tax_amount"]
    total = parsed_amounts["total"]
    if subtotal is not None and tax_amount is not None:
        if abs((subtotal + tax_amount) - total) > CENT:
            _check(checks, "invoice_arithmetic", "fail", f"Invoice subtotal (${subtotal:.2f}) + tax (${tax_amount:.2f}) does not equal stated total (${total:.2f}).")
        else:
            _check(checks, "invoice_arithmetic", "pass", f"Subtotal (${subtotal:.2f}) + tax (${tax_amount:.2f}) = stated total (${total:.2f}) verified.")
    else:
        _check(checks, "invoice_arithmetic", "warning", "Subtotal or tax was not provided; only the stated total can be checked.")

    # 8. Itemized Line Items Reconciliation
    line_items = invoice.get("line_items") or []
    po_lines = [row for row in purchase_order_lines if _text(row.get("po_number")) == po_number]
    reconciled_po_lines: list[dict[str, Any]] = []

    if not line_items:
        _check(checks, "line_items", "warning", "No itemized invoice lines supplied; only header totals can be checked.")
    elif not po_lines:
        _check(checks, "line_items", "fail", "Invoice is itemized but no PO line details are available to compare.")
    else:
        line_error: str | None = None
        invoice_line_sum = Decimal("0")
        for index, line in enumerate(line_items, start=1):
            description = line.get("description", "")
            matched_po_line = next(
                (row for row in po_lines if _is_match(row.get("description", ""), description)),
                None,
            )
            quantity = _money(line.get("quantity"))
            unit_price = _money(line.get("unit_price"))
            line_total = _money(line.get("line_total"))
            po_quantity = _money(matched_po_line.get("quantity")) if matched_po_line else None
            po_unit_price = _money(matched_po_line.get("unit_price")) if matched_po_line else None

            # Build line reconciliation record for 2-Way verification
            price_var = abs(unit_price - po_unit_price) if (unit_price is not None and po_unit_price is not None) else Decimal("0")
            line_stat = "Exact Match" if (matched_po_line and unit_price == po_unit_price and quantity is not None and po_quantity is not None and quantity <= po_quantity) else "Variance Flagged"
            reconciled_po_lines.append({
                "line_number": index,
                "description": description,
                "invoiced_qty": f"{quantity:.0f}" if quantity is not None and quantity == int(quantity) else f"{quantity}",
                "po_qty": f"{po_quantity:.0f}" if po_quantity is not None and po_quantity == int(po_quantity) else ("N/A" if po_quantity is None else f"{po_quantity}"),
                "unit_price": f"${unit_price:.2f}" if unit_price is not None else "",
                "po_unit_price": f"${po_unit_price:.2f}" if po_unit_price is not None else "N/A",
                "line_total": f"${line_total:.2f}" if line_total is not None else "",
                "variance": f"${price_var:.2f}",
                "status": line_stat,
            })

            if matched_po_line is None:
                line_error = f"Invoice line {index} did not match a PO line by description."
                break
            if None in (quantity, unit_price, line_total, po_quantity, po_unit_price):
                null_cols = [col for col, val in [("quantity", quantity), ("unit_price", unit_price), ("line_total", line_total)] if val is None]
                if null_cols:
                    line_error = f"Invoice line {index} has unreadable optical values ({', '.join(null_cols)}). AI anti-hallucination guardrail flagged for human completion."
                else:
                    line_error = f"Invoice or PO line {index} has a missing or invalid quantity/price."
                break
            assert quantity is not None and unit_price is not None and line_total is not None
            assert po_quantity is not None and po_unit_price is not None
            if quantity <= 0 or quantity > po_quantity:
                line_error = f"Invoice line {index} quantity must be positive and cannot exceed its PO line quantity."
                break
            if unit_price != po_unit_price:
                line_error = f"Invoice line {index} unit price differs from the PO unit price."
                break
            if abs(quantity * unit_price - line_total) > CENT:
                line_error = f"Invoice line {index} quantity × unit price does not equal its line total."
                break
            invoice_line_sum += line_total

        if line_error:
            _check(checks, "line_items", "fail", line_error)
        elif subtotal is not None and abs(invoice_line_sum - subtotal) > CENT:
            _check(checks, "line_items", "fail", "Sum of invoice line totals does not equal the invoice subtotal.")
        else:
            _check(checks, "line_items", "pass", f"Invoice descriptions, quantities, unit prices, and line totals match PO lines.")

    # 9. Cumulative PO Amount and Tolerance Threshold
    po_total = _money(po.get("total"))
    po_tolerance_amount = _money(po.get("tolerance_amount")) or Decimal("0")
    tolerance_percent = _money(po.get("tolerance_percent")) or Decimal("0")
    if po_total is None:
        _check(checks, "po_total", "fail", "PO total is missing or invalid in the PO data.")
        po_total = Decimal("0")

    allowed_overage = max(po_tolerance_amount, po_total * tolerance_percent / Decimal("100"))
    previously_billed = sum(
        (
            _money(row.get("total")) or Decimal("0")
            for row in invoice_history
            if _text(row.get("po_number")) == po_number
        ),
        Decimal("0"),
    )
    cumulative_total = previously_billed + total
    amounts_dict = {
        "invoice_total": f"{total:.2f}",
        "previously_billed": f"{previously_billed:.2f}",
        "cumulative_billed": f"{cumulative_total:.2f}",
        "po_total": f"{po_total:.2f}",
        "allowed_overage": f"{allowed_overage:.2f}",
    }

    if cumulative_total > po_total + allowed_overage:
        _check(
            checks,
            "cumulative_po_amount",
            "fail",
            f"Previously billed {previously_billed:.2f} + this invoice {total:.2f} = {cumulative_total:.2f}, "
            f"above PO total {po_total:.2f} plus tolerance {allowed_overage:.2f}.",
        )
    else:
        _check(
            checks,
            "cumulative_po_amount",
            "pass",
            f"Cumulative billed amount is {cumulative_total:.2f} of PO {po_total:.2f}; "
            f"configured overage tolerance is {allowed_overage:.2f}.",
        )

    # 10. PO Header Arithmetic Check
    po_subtotal = _money(po.get("subtotal"))
    po_tax = _money(po.get("tax_amount"))
    if po_subtotal is not None and po_tax is not None and abs((po_subtotal + po_tax) - po_total) > CENT:
        _check(checks, "po_arithmetic", "warning", "PO subtotal plus tax differs from PO total; check the reference PO data.")
    else:
        _check(checks, "po_arithmetic", "pass", "PO header amounts are internally consistent.")

    # 11. 3-Way Matching: Warehouse Goods Receipt Note (GRN) Verification
    reconciled_grn_lines: list[dict[str, Any]] = []
    if is_three_way:
        grn_records = [
            row
            for row in (goods_receipts or [])
            if _text(row.get("po_number")) == po_number
        ]
        if not grn_records:
            _check(
                checks,
                "goods_receipt_match",
                "fail",
                f"No Goods Receipt (GRN) on record for PO {po_number}. Delivery confirmation required before payment.",
            )
        else:
            grn_numbers = sorted({_text(r.get("grn_number")) for r in grn_records if _text(r.get("grn_number"))})
            grn_ref = ", ".join(grn_numbers) or "GRN"

            # Verify quantities received per itemized line
            if line_items:
                short_shipment_error: str | None = None
                for index, line in enumerate(line_items, start=1):
                    line_desc = line.get("description", "")
                    inv_qty = _money(line.get("quantity")) or Decimal("0")

                    matching_grns = [
                        r for r in grn_records if _is_match(r.get("item_description", ""), line_desc)
                    ]
                    if not matching_grns:
                        short_shipment_error = f"Invoice line {index} ('{line_desc}') has no matching delivery entry on {grn_ref}."
                        break

                    total_received = sum(
                        (_money(r.get("quantity_received")) or Decimal("0") for r in matching_grns),
                        Decimal("0"),
                    )
                    dock_reasons = [r.get("status_reason") for r in matching_grns if r.get("status_reason")]
                    reason_note = "; ".join(dock_reasons) if dock_reasons else ("Verified" if total_received >= inv_qty else "Quantity shortage at dock")
                    dock_status = matching_grns[0].get("status", "verified") if matching_grns else "missing"

                    matched_po_line = next(
                        (row for row in po_lines if _is_match(row.get("description", ""), line_desc)),
                        None,
                    )
                    po_q_str = str(matched_po_line.get("quantity", "N/A")) if matched_po_line else "N/A"
                    u_p_val = _money(line.get("unit_price"))
                    u_p_str = f"${u_p_val:.2f}" if u_p_val is not None else "N/A"

                    reconciled_grn_lines.append({
                        "description": line_desc,
                        "invoiced_qty": f"{inv_qty:.0f}" if inv_qty == int(inv_qty) else f"{inv_qty}",
                        "po_qty": po_q_str,
                        "received_qty": f"{total_received:.0f}" if total_received == int(total_received) else f"{total_received}",
                        "unit_price": u_p_str,
                        "grn_number": grn_ref,
                        "dock_status": dock_status,
                        "dock_notes": reason_note,
                    })

                    if inv_qty > total_received:
                        note_str = f" [{reason_note}]" if reason_note and reason_note != "Quantity shortage at dock" else ""
                        short_shipment_error = (
                            f"Short shipment on line {index}: Billed {inv_qty:.0f} units of '{line_desc}', "
                            f"but warehouse only received {total_received:.0f} units ({grn_ref}){note_str}."
                        )
                        break

                if short_shipment_error:
                    _check(checks, "goods_receipt_match", "fail", short_shipment_error)
                else:
                    _check(
                        checks,
                        "goods_receipt_match",
                        "pass",
                        f"Warehouse delivery confirmed on {grn_ref}; received quantities reconcile with invoiced quantities.",
                    )
            else:
                _check(
                    checks,
                    "goods_receipt_match",
                    "pass",
                    f"Warehouse delivery confirmed on {grn_ref}.",
                )

    failed_checks = [c for c in checks if c.get("result") in {"fail", "warning"}]
    if failed_checks:
        first_error = failed_checks[0].get("detail", "Exception detected during rule validation.")
        if len(failed_checks) > 1:
            summary_msg = f"{len(failed_checks)} exceptions detected: {first_error}"
        else:
            summary_msg = first_error

        logger.info("Evaluation result: %s (%s exceptions flagged)", STATUS_REVIEW, len(failed_checks))
        return _review_result(
            checks,
            invoice,
            summary_msg,
            amounts=amounts_dict,
            reconciled_po_lines=reconciled_po_lines,
            reconciled_grn_lines=reconciled_grn_lines,
            matched_vendor_id=vendor_id,
            matched_po_number=po_number,
            matching_mode=matching_mode,
        )

    logger.info("Evaluation result: %s for invoice %s", STATUS_READY, invoice.get("invoice_number"))
    return {
        "status": STATUS_READY,
        "summary": "Automated checks passed. This is a recommendation for human AP approval, not a payment authorization.",
        "checks": checks,
        "missing_fields": [],
        "invoice": invoice,
        "matched_vendor_id": vendor_id,
        "matched_po_number": po_number,
        "matching_mode": matching_mode,
        "reconciled_grn_lines": reconciled_grn_lines,
        "reconciled_po_lines": reconciled_po_lines,
        "amounts": amounts_dict,
    }

