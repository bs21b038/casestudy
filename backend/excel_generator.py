"""Generate multi-sheet Excel reconciliation audit workbooks for AP reviews."""

from __future__ import annotations

import io
from typing import Any
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from utils.config import STATUS_READY


def generate_reconciliation_workbook(
    invoice: dict[str, Any],
    po: dict[str, Any] | None,
    po_lines: list[dict[str, Any]],
    evaluation_result: dict[str, Any],
    goods_receipts: list[dict[str, Any]] | None = None,
) -> bytes:
    """Generate an audit-ready multi-sheet Excel workbook.

    Sheets:
    1. Reconciliation Audit: Side-by-side line comparison and check status
    2. Extracted Invoice: Header and line items extracted from the document
    3. Purchase Order: Reference PO header and line items
    4. Goods Receipt (Optional/3-Way): Warehouse receiving logs and inspection status
    """
    wb = openpyxl.Workbook()

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="102A43", end_color="102A43", fill_type="solid")
    pass_fill = PatternFill(start_color="D1E7DD", end_color="D1E7DD", fill_type="solid")
    fail_fill = PatternFill(start_color="F8D7DA", end_color="F8D7DA", fill_type="solid")
    thin_border = Border(
        left=Side(style="thin", color="D1D5DB"),
        right=Side(style="thin", color="D1D5DB"),
        top=Side(style="thin", color="D1D5DB"),
        bottom=Side(style="thin", color="D1D5DB"),
    )

    # ----------------------------------------------------
    # Sheet 1: Reconciliation Audit
    # ----------------------------------------------------
    ws_recon = wb.active
    ws_recon.title = "Reconciliation_Audit"

    ws_recon.append(["ClearMatch AP Operations -- Automated Reconciliation Audit"])
    ws_recon["A1"].font = Font(name="Calibri", size=14, bold=True, color="102A43")
    ws_recon.append([])

    curr_code = invoice.get("currency", "USD")
    total_val = invoice.get("total", "0.00")
    net_pay = evaluation_result.get("net_payable")
    if net_pay is None:
        if evaluation_result.get("status") in {"ON_HOLD", "REJECTED"}:
            net_pay_str = f"{curr_code} 0.00 (Suspended)"
        else:
            net_pay_str = f"{curr_code} {total_val}"
    else:
        try:
            net_pay_str = f"{curr_code} {float(net_pay):.2f}"
        except (ValueError, TypeError):
            net_pay_str = f"{curr_code} {net_pay}"

    voucher_str = evaluation_result.get("voucher_number") or ("Pending Release" if evaluation_result.get("status") in {STATUS_READY, "APPROVED"} else "Suspended")
    reviewer_str = evaluation_result.get("reviewer", "Mohith · AP Operations Analyst")
    mode_raw = evaluation_result.get("matching_mode", "2way")
    mode_label = "3-Way (PO + Goods Receipt)" if str(mode_raw).startswith("3") else "2-Way (Purchase Order)"

    ws_recon.append(["Invoice Number", invoice.get("invoice_number", "N/A"), "Status", evaluation_result.get("status", "UNKNOWN")])
    ws_recon.append(["Vendor Name", invoice.get("vendor_name", "N/A"), "Matched PO", evaluation_result.get("matched_po_number", "N/A")])
    ws_recon.append(["Gross Billed Total", f"{curr_code} {total_val}", "Net Payable to ERP", net_pay_str])
    ws_recon.append(["Matching Mode", mode_label, "ERP Voucher #", voucher_str])
    ws_recon.append(["AP Reviewer", reviewer_str, "", ""])
    ws_recon.append([])

    recon_headers = [
        "Check / Rule Name",
        "Result",
        "Audit Finding & Discrepancy Details",
    ]
    ws_recon.append(recon_headers)
    hdr_row = ws_recon.max_row
    for col_num in range(1, len(recon_headers) + 1):
        cell = ws_recon.cell(row=hdr_row, column=col_num)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center" if col_num == 2 else "left")

    for check in evaluation_result.get("checks", []):
        row_cells = [
            check.get("check", "").replace("_", " ").title(),
            check.get("result", "").upper(),
            check.get("detail", ""),
        ]
        ws_recon.append(row_cells)
        r = ws_recon.max_row
        status_cell = ws_recon.cell(row=r, column=2)
        status_cell.alignment = Alignment(horizontal="center")
        if check.get("result") == "pass":
            status_cell.fill = pass_fill
        elif check.get("result") == "fail":
            status_cell.fill = fail_fill

        for col_idx in range(1, 4):
            ws_recon.cell(row=r, column=col_idx).border = thin_border

    # ----------------------------------------------------
    # Sheet 2: Invoice Details
    # ----------------------------------------------------
    ws_inv = wb.create_sheet(title="Extracted_Invoice")
    ws_inv.append(["Extracted Invoice Header Fields"])
    ws_inv["A1"].font = Font(name="Calibri", size=13, bold=True, color="102A43")
    ws_inv.append([])

    extraction = invoice.get("extraction", {})
    method_name = extraction.get("method", "pdf_text")
    if "gemini" in method_name:
        method_label = "Gemini Vision AI (Scanned Image)"
    elif "tesseract" in method_name:
        method_label = "Local Tesseract OCR (Scanned Image)"
    else:
        method_label = "Digital PDF Text Stream (Direct)"

    for key, label in [
        ("vendor_name", "Vendor Name"),
        ("invoice_number", "Invoice Number"),
        ("invoice_date", "Invoice Date"),
        ("po_number", "PO Number"),
        ("currency", "Currency"),
        ("subtotal", "Subtotal"),
        ("tax_amount", "Tax Amount"),
        ("total", "Invoice Total"),
    ]:
        ws_inv.append([label, str(invoice.get(key) or "")])

    ws_inv.append(["Extraction Source", method_label])

    ws_inv.append([])
    ws_inv.append(["Itemized Line Items"])
    ws_inv.cell(row=ws_inv.max_row, column=1).font = Font(name="Calibri", size=12, bold=True, color="102A43")

    line_headers = ["Description", "Quantity", "Unit Price", "Line Total"]
    ws_inv.append(line_headers)
    lhdr_row = ws_inv.max_row
    for col_num in range(1, len(line_headers) + 1):
        cell = ws_inv.cell(row=lhdr_row, column=col_num)
        cell.font = header_font
        cell.fill = header_fill

    for item in invoice.get("line_items", []):
        ws_inv.append([
            item.get("description", ""),
            item.get("quantity", ""),
            item.get("unit_price", ""),
            item.get("line_total", ""),
        ])

    # ----------------------------------------------------
    # Sheet 3: Purchase Order Details
    # ----------------------------------------------------
    ws_po = wb.create_sheet(title="Purchase_Order")
    ws_po.append(["Purchase Order Reference Records"])
    ws_po["A1"].font = Font(name="Calibri", size=13, bold=True, color="102A43")
    ws_po.append([])

    if po:
        for key, label in [
            ("po_number", "PO Number"),
            ("vendor_id", "Vendor ID"),
            ("po_date", "PO Date"),
            ("currency", "Currency"),
            ("status", "PO Status"),
            ("total", "Authorized Total"),
            ("tolerance_amount", "Tolerance Amount ($)"),
            ("tolerance_percent", "Tolerance Percentage (%)"),
        ]:
            ws_po.append([label, str(po.get(key) or "")])
    else:
        ws_po.append(["No matching PO found in procurement records."])

    ws_po.append([])
    ws_po.append(["PO Authorized Line Items"])
    ws_po.cell(row=ws_po.max_row, column=1).font = Font(name="Calibri", size=12, bold=True, color="102A43")

    po_line_headers = ["Line #", "Description", "Quantity", "Unit", "Unit Price", "Line Total"]
    ws_po.append(po_line_headers)
    plhdr_row = ws_po.max_row
    for col_num in range(1, len(po_line_headers) + 1):
        cell = ws_po.cell(row=plhdr_row, column=col_num)
        cell.font = header_font
        cell.fill = header_fill

    for line in po_lines:
        ws_po.append([
            line.get("line_number", ""),
            line.get("description", ""),
            line.get("quantity", ""),
            line.get("unit", ""),
            line.get("unit_price", ""),
            line.get("line_total", ""),
        ])

    # ----------------------------------------------------
    # Sheet 4: Goods Receipt Notes (3-Way Verification)
    # ----------------------------------------------------
    sheets = [ws_recon, ws_inv, ws_po]
    if goods_receipts is not None or evaluation_result.get("matching_mode") == "3way":
        ws_grn = wb.create_sheet(title="Goods_Receipt")
        ws_grn.append(["Warehouse Goods Receipt Notes (GRN / Delivery Slips)"])
        ws_grn["A1"].font = Font(name="Calibri", size=13, bold=True, color="102A43")
        ws_grn.append([])

        grn_headers = [
            "Receipt ID",
            "PO Number",
            "Receipt Date",
            "Item Description",
            "Received Qty",
            "Warehouse Location",
            "Received By",
            "Inspection Status",
            "Dock QA & Inspection Notes",
        ]
        ws_grn.append(grn_headers)
        ghdr_row = ws_grn.max_row
        for col_num in range(1, len(grn_headers) + 1):
            cell = ws_grn.cell(row=ghdr_row, column=col_num)
            cell.font = header_font
            cell.fill = header_fill

        if goods_receipts:
            for rec in goods_receipts:
                ws_grn.append([
                    rec.get("grn_number") or rec.get("receipt_id") or "",
                    rec.get("po_number", ""),
                    rec.get("receipt_date", ""),
                    rec.get("item_description", ""),
                    rec.get("quantity_received") or rec.get("received_quantity") or "",
                    rec.get("warehouse_location") or ("Main Dock A" if "Dock" in rec.get("received_by", "") else "Central Storage"),
                    rec.get("received_by", ""),
                    (rec.get("status") or rec.get("inspection_status") or "verified").capitalize(),
                    rec.get("status_reason") or "Inspection passed without remarks",
                ])
        else:
            ws_grn.append(["No physical goods receipt records logged for this PO reference."])

        sheets.append(ws_grn)

    # Auto-adjust column widths across all sheets
    for ws in sheets:
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()

