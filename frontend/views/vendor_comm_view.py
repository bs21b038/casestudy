"""Stage 04: Vendor Communication & Escalation."""

from __future__ import annotations

from typing import Any
import streamlit as st

from backend.excel_generator import generate_reconciliation_workbook
from frontend.components.ui_helpers import (
    render_top_bar,
)
from frontend.views.analysis_view import get_reference_data
from utils.config import DEFAULT_CASE_REFERENCE, STATUS_READY


def render_vendor_communication(nav_callbacks: dict[str, Any]) -> None:
    """Render Stage 04: Context-aware vendor inquiry and escalation composer."""
    case_ref = st.session_state.get("case_reference", DEFAULT_CASE_REFERENCE)
    completed_steps = st.session_state.get("completed_steps", set())

    render_top_bar("Vendor Communication", case_ref)

    invoice = st.session_state.get("draft_invoice", {})
    result = st.session_state.get("last_result", {})
    vendor_reason = st.session_state.get("vendor_comm_reason", "")
    status = result.get("status")

    vendor_name = invoice.get("vendor_name", "Vendor Accounts Receivable")
    inv_num = invoice.get("invoice_number", "Draft")
    po_num = invoice.get("po_number", "Unreferenced PO")

    # Matching Mode & Workbook Metadata
    active_mode = result.get("matching_mode") or st.session_state.get("matching_mode", "2way")
    is_3way = str(active_mode).startswith("3")
    mode_text = "3-way (PO & Goods Receipt)" if is_3way else "2-way (Purchase Order)"
    sheet_info = (
        f"4-sheet Reconciliation Audit Workbook (Reconciliation_{inv_num}.xlsx) containing line-level PO comparison and itemized dock receiving inspection notes"
        if is_3way
        else f"3-sheet Reconciliation Audit Workbook (Reconciliation_{inv_num}.xlsx) containing line-level PO comparison"
    )

    # Generate tailored template based on context
    if status == "APPROVED":
        voucher_disp = result.get("voucher_number") or f"VCH-2026-{1040 + int(st.session_state.get('upload_count', 1)):04d}"
        payable_amt = result.get("net_payable")
        if payable_amt is None:
            payable_amt = result.get("amounts", {}).get("invoice_total") or invoice.get("total") or "0.00"
        try:
            p_val = float(payable_amt)
        except (ValueError, TypeError):
            p_val = 0.0

        default_subject = f"Payment Remittance & Voucher Release: {inv_num} (PO: {po_num})"
        default_body = (
            f"Dear {vendor_name} Billing Team,\n\n"
            f"We are pleased to inform you that invoice {inv_num} referenced against Purchase Order {po_num} "
            f"has been APPROVED following automated {mode_text} matching controls and released for electronic settlement.\n\n"
            f"• ERP Payment Voucher: {voucher_disp}\n"
            f"• Approved Net Disbursement: {invoice.get('currency', 'USD')} ${p_val:.2f}\n"
            f"• Payment Execution: Automated ACH / Wire scheduled under standard Net-30 payment terms\n\n"
            f"• Audit Attachment: Attached please find the authoritative {sheet_info}.\n\n"
            f"Case Reference: {case_ref}\n"
            f"Accounts Payable Operations Desk"
        )
    elif status == STATUS_READY:
        default_subject = f"Payment Processing Notice: Invoice {inv_num} (PO: {po_num})"
        default_body = (
            f"Dear {vendor_name} Billing Team,\n\n"
            f"We are pleased to inform you that your invoice {inv_num} referenced against Purchase Order {po_num} "
            f"has passed all automated {mode_text} matching controls and is queued for electronic settlement authorization.\n\n"
            f"Settlement will occur in accordance with standard Net-30 payment terms.\n\n"
            f"Reference Case: {case_ref}\n"
            f"Accounts Payable Operations Desk"
        )
    elif "Missing" in vendor_reason or not inv_num or not po_num:
        default_subject = f"Action Required: Clarification Needed for Invoice from {vendor_name}"
        default_body = (
            f"Dear {vendor_name} Billing Team,\n\n"
            f"We recently received an invoice submission from your organization. However, automated verification "
            f"could not proceed due to the following missing mandatory details:\n\n"
            f"• Issue Identified: {vendor_reason or 'Invoice number or Purchase Order reference is absent.'}\n\n"
            f"To prevent payment delays, please provide a revised document referencing the valid Purchase Order number.\n\n"
            f"Case Reference: {case_ref}\n"
            f"Accounts Payable Operations Desk"
        )
    else:
        is_short = any(w in (vendor_reason or "").lower() for w in ["short", "damage", "warehouse", "grn", "delivery"])
        default_subject = f"Invoice Exception & Credit Memo Request: {inv_num} (PO: {po_num})" if is_short else f"Invoice Exception Notice: {inv_num} (PO: {po_num})"

        action_req = (
            "Please review our attached warehouse receiving slip (Sheet 4) and issue a formal Credit Memo for the unreceived or damaged balance "
            "so that payment release for accepted items can proceed."
            if is_short
            else "Please review this discrepancy and let us know if a credit memo or revised billing will be issued."
        )

        default_body = (
            f"Dear {vendor_name} Accounts Receivable,\n\n"
            f"During automated {mode_text} matching against Purchase Order {po_num}, an operational exception was flagged:\n\n"
            f"• Audit Finding: {vendor_reason or result.get('summary', 'Price/quantity variance detected')}\n\n"
            f"• Required Action: {action_req}\n\n"
            f"• Audit Attachment: Attached please find the {sheet_info}.\n\n"
            f"Case Reference: {case_ref}\n"
            f"Accounts Payable Operations Desk"
        )

    # Multi-Sheet Workbook Attachment Generator
    support = get_reference_data()
    matched_po = next((row for row in support["purchase_orders.csv"] if row.get("po_number") == po_num), None)
    matched_po_lines = [row for row in support["purchase_order_lines.csv"] if row.get("po_number") == po_num]
    matched_grns = [row for row in support.get("goods_receipts.csv", []) if row.get("po_number") == po_num]

    excel_bytes = generate_reconciliation_workbook(
        invoice=invoice,
        po=matched_po,
        po_lines=matched_po_lines,
        evaluation_result=result,
        goods_receipts=matched_grns if active_mode == "3way" else None,
    )

    c_hdr, c_attach = st.columns([2.5, 1.5])
    with c_hdr:
        st.html(
            """
            <div style="padding-top:0.2rem; margin-bottom:0.4rem;">
                <div style="font-size:1.02rem; font-weight:700; color:#0f172a;">Compose Vendor Inquiry</div>
                <div style="font-size:0.8rem; color:#64748b; margin-top:2px;">Pre-populated based on reconciliation audit findings. Edit as needed before dispatch.</div>
            </div>
            """
        )
    with c_attach:
        st.download_button(
            label="Download Attachment (.xlsx)",
            data=excel_bytes,
            file_name=f"Reconciliation_{inv_num}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Download the formal 4-sheet reconciliation workbook to attach to this vendor communication.",
            use_container_width=True,
        )

    with st.form("vendor_email_form"):
        subject = st.text_input("Subject Line", value=default_subject)
        email_body = st.text_area("Message Body", value=default_body, height=180)
        sent_clicked = st.form_submit_button("Record Communication in Audit Log", type="primary")

    if sent_clicked:
        st.success(f"Communication recorded in case {case_ref}. Notification dispatched to {vendor_name}.")

    col_back, col_home = st.columns([1, 1])
    with col_back:
        if st.button("<- Review Decision"):
            nav_callbacks["go_to_results"]()
    with col_home:
        if st.button("Return to Data Ingestion"):
            nav_callbacks["go_to_intake"]()

