"""Text extraction and conservative parsing for invoice PDFs.

Extracts text from selectable PDFs using pypdf and parses standard labeled fields.
Image-only or scanned PDFs are detected and flagged for OCR/manual review.
"""

from __future__ import annotations

import re
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO

from pypdf import PdfReader
from utils.logger import logger


class InvoiceReadError(ValueError):
    """Raised when a PDF cannot be read or parsed as an invoice document."""


_LABELS = {
    "vendor_name": re.compile(r"^Vendor\s*:\s*(.+)$", re.IGNORECASE),
    "invoice_number": re.compile(r"^Invoice\s*(?:number|no\.?|#)\s*:\s*(.+)$", re.IGNORECASE),
    "invoice_date": re.compile(r"^Invoice\s*date\s*:\s*(.+)$", re.IGNORECASE),
    "po_number": re.compile(r"^(?:Purchase\s*order|PO(?:\s*number)?)\s*:\s*(.+)$", re.IGNORECASE),
    "currency": re.compile(r"^Currency\s*:\s*([A-Z]{3})$", re.IGNORECASE),
    "subtotal": re.compile(r"^Subtotal\s*:\s*(.+)$", re.IGNORECASE),
    "tax_amount": re.compile(r"^(?:Sales\s*tax|Tax)\b(?!\s*(?:Amount\s*)?\(in\s*words\))[^:]*:\s*(.+)$", re.IGNORECASE),
    "total": re.compile(r"^(?:Invoice\s*)?Total\s*:\s*(.+)$", re.IGNORECASE),
}

_MONEY_RE = re.compile(r"-?\s*[\$₹€£]?\s*([\d,]+(?:\.\d{1,2})?)")
_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_LINE_RE = re.compile(
    r"^(.+?)\s*\|\s*(\d+(?:\.\d+)?)\s*\|\s*[\$₹€£]?([\d,]+(?:\.\d{1,2})?)\s*\|\s*[\$₹€£]?([\d,]+(?:\.\d{1,2})?)$"
)


def parse_money(value: str) -> str | None:
    """Parse a monetary string representation into a normalized 2-decimal string."""
    match = _MONEY_RE.search(value)
    if not match:
        return None
    try:
        return f"{float(match.group(1).replace(',', '')):.2f}"
    except ValueError:
        return None


def parse_date(value: str) -> str | None:
    """Parse standard ISO and common enterprise invoice date formats into YYYY-MM-DD."""
    if not value:
        return None
    iso_match = _DATE_RE.search(value)
    if iso_match:
        return iso_match.group(1)

    text_match = re.search(r"(\d{1,2}[-/][A-Za-z]{3,}[-/]\d{2,4})", value)
    if text_match:
        raw = text_match.group(1)
        for fmt in ("%d-%b-%y", "%d-%b-%Y", "%d/%b/%y", "%d/%b/%Y"):
            try:
                return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
            except ValueError:
                pass

    slash_match = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", value)
    if slash_match:
        raw = slash_match.group(0)
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
            except ValueError:
                pass
    return None


def _parse_gst_line_items(text: str) -> list[dict[str, Any]]:
    """Parse tabular GST / ERP line items (Description, HSN, Quantity, Rate, Amount)."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    items = []
    num_re = re.compile(
        r"([\d,]+\.\d{2})\s*([A-Za-z]+)\s*([\d,]+\.\d{2})\s*([\d,]+(?:\.\d+)?)\s*([A-Za-z]+)\s*(\d{4,8})"
    )
    in_table = False
    current_desc_parts: list[str] = []

    for line in lines:
        if "description of goods" in line.casefold():
            in_table = True
            continue
        if in_table and any(
            stop in line.casefold()
            for stop in ["cgst", "sgst", "total", "₹", "amount chargeable", "taxable value", "declaration"]
        ):
            in_table = False
            break
        if in_table:
            clean_check = line.strip().lower()
            if clean_check in ("no.", "sl.", "sl no.", "no", "item", "sl"):
                continue
            m_num = num_re.search(line)
            if m_num:
                amount, unit, rate, qty, uom, hsn = m_num.groups()
                prefix = line[: m_num.start()].strip()
                prefix = re.sub(r"^\d+\s+", "", prefix)
                if prefix:
                    current_desc_parts.append(prefix)
                desc = " ".join(current_desc_parts).strip()
                try:
                    r_val = float(rate.replace(",", ""))
                    a_val = float(amount.replace(",", ""))
                    q_val = int(float(qty.replace(",", "")))
                    items.append(
                        {
                            "description": desc,
                            "quantity": str(q_val),
                            "unit_price": f"{r_val:.2f}",
                            "line_total": f"{a_val:.2f}",
                        }
                    )
                except ValueError:
                    pass
                current_desc_parts = []
            else:
                clean_line = re.sub(r"^\d+\s+", "", line).strip()
                if clean_line and clean_line.lower() not in ("no.", "sl.", "sl no.", "no"):
                    current_desc_parts.append(clean_line)
    return items


def parse_invoice_text(text: str) -> dict[str, Any]:
    """Parse labeled invoice text layout and report unparsed required data.

    Deterministic parser for structured invoices. Missing vendor labels fall back
    to known vendor matching or prominent header tokens.
    """
    fields: dict[str, Any] = {
        "vendor_name": None,
        "invoice_number": None,
        "invoice_date": None,
        "po_number": None,
        "currency": None,
        "subtotal": None,
        "tax_amount": None,
        "total": None,
        "line_items": [],
    }
    warnings: list[str] = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # 1. Standard labeled line parser
    for line in lines:
        for field, pattern in _LABELS.items():
            match = pattern.match(line)
            if not match:
                continue
            value = match.group(1).strip()
            if field in {"subtotal", "tax_amount", "total"}:
                fields[field] = parse_money(value)
                if fields[field] is None:
                    warnings.append(f"Could not parse {field} from line: {line}")
            elif field == "invoice_date":
                fields[field] = parse_date(value)
                if fields[field] is None:
                    warnings.append(f"Could not parse invoice_date from line: {line}")
            elif field == "currency":
                fields[field] = value.upper()
            else:
                fields[field] = value
            break

        line_match = _LINE_RE.match(line)
        if line_match:
            description, quantity, unit_price, line_total = line_match.groups()
            fields["line_items"].append(
                {
                    "description": description.strip(),
                    "quantity": quantity,
                    "unit_price": parse_money(unit_price),
                    "line_total": parse_money(line_total),
                }
            )

    # 2. Resilient Vendor Fallback
    if not fields["vendor_name"]:
        # Check known registered vendor names
        known_vendors = [
            "SRI BALAJI ENTERPRISES",
            "Northstar Office Supplies Ltd",
            "Acme Cloud Services Inc",
            "Apex Enterprise Hardware Inc",
        ]
        text_upper = text.upper()
        for v in known_vendors:
            if v.upper() in text_upper:
                fields["vendor_name"] = v
                break

    if not fields["vendor_name"]:
        # Fallback: first non-label line after 'INVOICE' heading
        title_index = next((i for i, line in enumerate(lines) if line.casefold() in ("invoice", "tax invoice")), None)
        if title_index is not None:
            for candidate in lines[title_index + 1 :]:
                if not any(pattern.match(candidate) for pattern in _LABELS.values()):
                    fields["vendor_name"] = candidate
                    break

    # 3. Resilient Invoice Number Fallback
    if not fields["invoice_number"]:
        inv_match = re.search(r"\bInvoice\s*(?:No\b\.?|Number\b|#)\s*[:.]?\s*([A-Za-z0-9\-_/]+)", text, re.IGNORECASE)
        if inv_match:
            fields["invoice_number"] = inv_match.group(1).strip()

    # 4. Resilient Date Fallback
    if not fields["invoice_date"]:
        date_match = re.search(
            r"(\d{1,2}[-/][A-Za-z]{3,}[-/]\d{2,4}|\d{4}-\d{2}-\d{2})",
            text,
            re.IGNORECASE,
        )
        if date_match:
            fields["invoice_date"] = parse_date(date_match.group(1))

    # 5. Resilient PO Number Fallback
    if not fields["po_number"]:
        po_match = re.search(r"(?:Purchase\s*Order|PO\s*#?|Buyer'?s?\s*Order\s*No\.?)\s*[:.]?\s*([A-Za-z0-9\-_/]+)", text, re.IGNORECASE)
        if po_match:
            fields["po_number"] = po_match.group(1).strip()

    # 6. Resilient Currency Detection
    if not fields["currency"]:
        if "₹" in text or "INR" in text:
            fields["currency"] = "INR"
        elif "$" in text or "USD" in text:
            fields["currency"] = "USD"
        elif "€" in text or "EUR" in text:
            fields["currency"] = "EUR"
        elif "£" in text or "GBP" in text:
            fields["currency"] = "GBP"

    # 7. Resilient Totals and Subtotals
    if not fields["total"]:
        total_match = re.search(r"(?:₹|INR)\s*([\d,]+\.\d{2})", text)
        if total_match:
            fields["total"] = parse_money(total_match.group(1))

    if not fields["subtotal"]:
        sub_match = re.search(r"(?:Taxable\s*Value|Subtotal)\s*[:.]?\s*[\$₹€£]?\s*([\d,]+\.\d{2})", text, re.IGNORECASE)
        if not sub_match:
            # Check GST summary table line: Total [tax] [cgst] [sgst] [taxable]
            sub_match = re.search(r"Total\s*[\d,]+\.\d{2}\s*[\d,]+\.\d{2}\s*[\d,]+\.\d{2}\s*([\d,]+\.\d{2})", text)
        if sub_match:
            fields["subtotal"] = parse_money(sub_match.group(1))

    if not fields["tax_amount"] and fields["total"] and fields["subtotal"]:
        try:
            diff = float(fields["total"]) - float(fields["subtotal"])
            if diff >= 0:
                fields["tax_amount"] = f"{diff:.2f}"
        except (ValueError, TypeError):
            pass

    # 8. Resilient Line Items Fallback
    if not fields["line_items"]:
        gst_items = _parse_gst_line_items(text)
        if gst_items:
            fields["line_items"] = gst_items

    # 9. Required Fields Check
    required = ("vendor_name", "invoice_number", "invoice_date", "po_number", "currency", "total")
    missing = [field for field in required if not fields.get(field)]
    if missing:
        warnings.append("Required fields were not extracted: " + ", ".join(missing))

    fields["extraction"] = {
        "method": "pdf_text",
        "confidence": "medium" if warnings else "high",
        "warnings": warnings,
    }
    return fields


def read_invoice_pdf(
    source: str | Path | BinaryIO | bytes,
    source_name: str | None = None,
) -> dict[str, Any]:
    """Extract text from a PDF path or in-memory byte buffer and parse invoice fields."""
    pdf_source: str | Path | BinaryIO
    if isinstance(source, bytes):
        pdf_source = BytesIO(source)
        filename = source_name or "uploaded_invoice.pdf"
    elif isinstance(source, (str, Path)):
        pdf_path = Path(source)
        if not pdf_path.is_file():
            raise InvoiceReadError(f"Invoice PDF not found: {pdf_path}")
        pdf_source = pdf_path
        filename = source_name or pdf_path.name
    else:
        pdf_source = source
        filename = source_name or getattr(source, "name", "uploaded_invoice.pdf")

    try:
        reader = PdfReader(pdf_source)
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except Exception as exc:
        logger.error("Failed to read PDF %s: %s", filename, exc)
        raise InvoiceReadError(f"Could not read PDF {filename}: {exc}") from exc

    if not text:
        logger.warning("No selectable text extracted from %s (scanned/OCR needed)", filename)
        raw_bytes: bytes | None = None
        if isinstance(source, bytes):
            raw_bytes = source
        elif isinstance(source, (str, Path)):
            try:
                raw_bytes = Path(source).read_bytes()
            except Exception:
                pass

        if raw_bytes:
            try:
                from backend.ocr_engine import run_ocr_pipeline
                ocr_res = run_ocr_pipeline(raw_bytes, filename)
                if ocr_res and ocr_res.get("vendor_name"):
                    return ocr_res
            except Exception as ocr_err:
                logger.warning("OCR fallback pipeline skipped: %s", ocr_err)

        return {
            "vendor_name": None,
            "invoice_number": None,
            "invoice_date": None,
            "po_number": None,
            "currency": None,
            "subtotal": None,
            "tax_amount": None,
            "total": None,
            "line_items": [],
            "extraction": {
                "method": "pdf_text",
                "confidence": "none",
                "warnings": ["No selectable text found; this may be a scanned PDF and requires OCR."],
                "source_file": filename,
            },
        }

    result = parse_invoice_text(text)
    result["extraction"]["source_file"] = filename
    logger.info("Successfully read and parsed invoice: %s (confidence=%s)", filename, result["extraction"]["confidence"])
    return result

