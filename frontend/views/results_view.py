"""Stage 03: Review & Final Decision."""

from __future__ import annotations

from typing import Any
import streamlit as st

from backend.store import save_run, update_run
from frontend.components.ui_helpers import (
    render_top_bar,
    status_badge_pill,
)
from utils.config import (
    DEFAULT_CASE_REFERENCE,
    STATUS_INFO,
    STATUS_READY,
    STATUS_REVIEW,
)


def render_results(nav_callbacks: dict[str, Any]) -> None:
    """Render Stage 03: Decision & Payment Authorization."""
    case_ref = st.session_state.get("case_reference", DEFAULT_CASE_REFERENCE)
    completed_steps = st.session_state.get("completed_steps", set())

    render_top_bar("Review Decision", case_ref)

    result = st.session_state.get("last_result")
    if not result:
        st.warning("No completed review found. Return to Data Ingestion to begin.")
        if st.button("<- Return to Data Ingestion"):
            nav_callbacks["go_to_intake"]()
        return

    status = result.get("status", "UNKNOWN")
    invoice = result.get("invoice", {})
    amounts = result.get("amounts", {})
    active_mode = result.get("matching_mode") or st.session_state.get("matching_mode", "2way")
    mode_text = "3-way" if str(active_mode).startswith("3") else "2-way"

    # Settlement & Financial Calculations
    grn_lines = result.get("reconciled_grn_lines") or []
    has_shortage = any(float(r.get("invoiced_qty", 0)) > float(r.get("received_qty", 0)) for r in grn_lines)

    total_val = float(amounts.get("invoice_total") or invoice.get("total") or 0.0)
    subtotal_val = float(invoice.get("subtotal") or total_val)
    tax_val = float(invoice.get("tax_amount") or 0.0)
    tax_rate = (tax_val / subtotal_val) if subtotal_val > 0 else 0.0
    curr = invoice.get("currency", "USD")
    inv_num = invoice.get("invoice_number", "Draft")

    accepted_total = total_val
    withheld_val = 0.0
    if has_shortage:
        accepted_base = 0.0
        for r in grn_lines:
            inv_q = float(r.get("invoiced_qty", 0))
            rec_q = float(r.get("received_qty", 0))
            up_str = str(r.get("unit_price", "0")).replace("$", "").replace("₹", "").replace(",", "")
            try:
                up = float(up_str or 0.0)
            except ValueError:
                up = 0.0
            accepted_base += min(inv_q, rec_q) * up
        accepted_tax = accepted_base * tax_rate
        accepted_total = accepted_base + accepted_tax
        withheld_val = max(0.0, total_val - accepted_total)

    # Determine Net Payable to ERP & Card Titles
    if status == "APPROVED":
        card_title = "Authorized Settlement Summary"
        payable_amount = total_val
        payable_label = f"{curr} ${total_val:.2f}"
        payable_caption = "Authorized & Released to ERP"
        payable_color = "#16a34a"
        voucher_disp = result.get("voucher_number") or f"VCH-2026-{1040 + int(st.session_state.get('upload_count', 1)):04d}"
    elif status == STATUS_READY:
        card_title = "Proposed Settlement Summary"
        payable_amount = total_val
        payable_label = f"{curr} ${total_val:.2f}"
        payable_caption = "Proposed Payable (Pending Sign-off)"
        payable_color = "#059669"
        voucher_disp = "Pending Release"
    elif status in {"ON_HOLD", "REJECTED"}:
        card_title = "Settlement Summary (Payment Suspended)"
        payable_amount = 0.0
        payable_label = f"{curr} $0.00"
        payable_caption = "Disbursement Suspended (Hold/Void)"
        payable_color = "#dc2626"
        voucher_disp = "Suspended"
    elif has_shortage:
        card_title = "Discrepancy Settlement Summary (Shortage Hold)"
        payable_amount = accepted_total
        payable_label = f"{curr} ${accepted_total:.2f}"
        payable_caption = "Warehouse Accepted (Shortage Withheld)"
        payable_color = "#d97706"
        voucher_disp = "Hold"
    else:
        card_title = "Exception Settlement Review"
        payable_amount = 0.0
        payable_label = f"{curr} $0.00"
        payable_caption = "Pending AP Review"
        payable_color = "#64748b"
        voucher_disp = "Under Review"

    # PO Budget Allocation Computations
    po_num = invoice.get("po_number") or result.get("matched_po_number") or "N/A"
    try:
        po_total_val = float(amounts.get("po_total") or 0.0)
    except (ValueError, TypeError):
        po_total_val = 0.0
    try:
        prev_billed_val = float(amounts.get("previously_billed") or 0.0)
    except (ValueError, TypeError):
        prev_billed_val = 0.0
    try:
        cumul_billed_val = float(amounts.get("cumulative_billed") or (prev_billed_val + total_val))
    except (ValueError, TypeError):
        cumul_billed_val = prev_billed_val + total_val

    remaining_balance = max(0.0, po_total_val - cumul_billed_val)
    budget_pct = (cumul_billed_val / po_total_val * 100.0) if po_total_val > 0 else 100.0
    budget_badge_bg = "#dcfce7" if remaining_balance == 0 else "#e0f2fe"
    budget_badge_color = "#15803d" if remaining_balance == 0 else "#0369a1"

    # Decision Banner Card (Primary Header Box)
    if status == "APPROVED":
        border_color = "#22c55e"
        bg_color = "#f0fdf4"
        decision_title = "APPROVED: PAYMENT AUTHORIZATION CONFIRMED"
        decision_sub = f"Payment Voucher <strong>#{voucher_disp}</strong> generated for Invoice {inv_num} · Scheduled for ERP electronic settlement ({curr} ${payable_amount:.2f}) · Authorized by Mohith (AP Operations Analyst)."
    elif status == STATUS_READY:
        border_color = "#22c55e"
        bg_color = "#f0fdf4"
        decision_title = "RECOMMENDATION: READY FOR PAYMENT AUTHORIZATION"
        decision_sub = f"All automated controls, {mode_text} matching rules, and tolerance limits passed without exception. Awaiting AP analyst sign-off."
    elif status == "ON_HOLD":
        border_color = "#f59e0b"
        bg_color = "#fffbeb"
        decision_title = "STATUS: CASE PLACED ON HOLD"
        decision_sub = result.get("summary", "Payment processing suspended pending resolution.")
    elif status == "REJECTED":
        border_color = "#ef4444"
        bg_color = "#fef2f2"
        decision_title = "STATUS: INVOICE REJECTED / DISAPPROVED"
        decision_sub = result.get("summary", "Invoice rejected due to compliance/contractual exceptions.")
    elif status == STATUS_INFO:
        border_color = "#f59e0b"
        bg_color = "#fffbeb"
        decision_title = "RECOMMENDATION: MANDATORY INFORMATION REQUIRED"
        decision_sub = result.get("summary", "Required invoice details are missing or invalid.")
    else:
        border_color = "#ef4444"
        bg_color = "#fef2f2"
        decision_title = "RECOMMENDATION: EXCEPTION REVIEW REQUIRED"
        decision_sub = result.get("summary", "Discrepancy detected during rule validation. Requires analyst review.")

    st.html(
        f"""
        <div class="main-panel-card" style="border-left: 5px solid {border_color}; background-color: {bg_color};">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <div style="font-size:1.02rem; font-weight:800; color:#0f172a;">{decision_title}</div>
                    <div style="font-size:0.84rem; color:#475569; margin-top:3px;">{decision_sub}</div>
                </div>
                <div>{status_badge_pill(status)}</div>
            </div>
        </div>
        """
    )

    # Discrepancy Callout (Rendered ONLY when there is an actual short shipment / damaged goods variance)
    settlement_card_html = ""
    if has_shortage:
        settlement_card_html = f"""
        <div style="background-color:#fff1f2; border:1px solid #fecdd3; border-radius:8px; padding:0.85rem 1.1rem; margin-top:0.75rem;">
            <div style="font-weight:700; color:#be123c; font-size:0.9rem; display:flex; align-items:center; gap:6px;">
                <span>⚠️</span> <span>DISCREPANCY SETTLEMENT HOLD: Short Shipment / Dock Rejection</span>
            </div>
            <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:0.6rem; margin-top:0.5rem; font-size:0.82rem; background:#ffffff; padding:0.6rem; border-radius:6px; border:1px solid #ffe4e6;">
                <div><span style="color:#64748b;">Gross Billed Total:</span> <strong style="color:#0f172a;">{curr} ${total_val:.2f}</strong></div>
                <div><span style="color:#64748b;">Warehouse Accepted Value:</span> <strong style="color:#16a34a;">{curr} ${accepted_total:.2f}</strong></div>
                <div><span style="color:#64748b;">Withheld Shortage:</span> <strong style="color:#e11d48;">-{curr} ${withheld_val:.2f}</strong></div>
            </div>
            <div style="font-size:0.82rem; color:#475569; margin-top:0.5rem; line-height:1.45;">
                <strong>AP Settlement Directive:</strong> <u>DO NOT DISBURSE full {curr} ${total_val:.2f}</u>. Request vendor Credit Memo for <strong>-{curr} ${withheld_val:.2f}</strong> to offset damaged goods. Net payable of <strong>{curr} ${accepted_total:.2f}</strong> will be released upon credit memo reconciliation.
            </div>
        </div>
        """

    # Core Financial Metrics Grid inside Main Card
    st.html(
        f"""
        <div class="main-panel-card">
            <div class="card-section-title">{card_title}</div>
            <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; margin-top:0.6rem;">
                <div class="field-metric-box">
                    <div class="field-metric-label">Vendor Name</div>
                    <div class="field-metric-value">{invoice.get('vendor_name', 'N/A')}</div>
                </div>
                <div class="field-metric-box">
                    <div class="field-metric-label">Invoice Number</div>
                    <div class="field-metric-value">{invoice.get('invoice_number', 'N/A')}</div>
                </div>
                <div class="field-metric-box">
                    <div class="field-metric-label">Gross Billed Total</div>
                    <div class="field-metric-value">{curr} ${total_val:.2f}</div>
                    <div style="font-size:0.72rem; color:#64748b; margin-top:2px;">Vendor Invoiced Amount</div>
                </div>
                <div class="field-metric-box">
                    <div class="field-metric-label">Net Payable to ERP</div>
                    <div class="field-metric-value" style="color:{payable_color}; font-weight:800;">{payable_label}</div>
                    <div style="font-size:0.72rem; color:{payable_color}; margin-top:2px; font-weight:600;">{payable_caption}</div>
                </div>
            </div>
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:0.5rem 0.85rem; font-size:0.82rem; color:#475569; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-top:0.65rem;">
                <div>
                    <span style="font-weight:700; color:#0f172a;">PO Allocation ({po_num}):</span>
                    Prior Invoices: <strong>${prev_billed_val:,.2f}</strong> + Current Invoice: <strong>${total_val:,.2f}</strong> = Cumulative: <strong>${cumul_billed_val:,.2f}</strong> / <strong>${po_total_val:,.2f}</strong> PO Budget
                </div>
                <div>
                    <span style="background:{budget_badge_bg}; color:{budget_badge_color}; padding:2px 8px; border-radius:10px; font-weight:700; font-size:0.75rem;">
                        Remaining Budget: ${remaining_balance:,.2f} ({budget_pct:.0f}% Utilized)
                    </span>
                </div>
            </div>
            {settlement_card_html}
        </div>
        """
    )

    # Line-Level Audit Verification Table (2-Way or 3-Way Reconciled)
    grn_lines = result.get("reconciled_grn_lines")
    po_reconciled = result.get("reconciled_po_lines")
    matching_mode = result.get("matching_mode") or st.session_state.get("matching_mode", "2way")

    if matching_mode == "3way" and grn_lines:
        has_shortage = any(float(r.get("invoiced_qty", 0)) > float(r.get("received_qty", 0)) for r in grn_lines)
        exp_title = f"3-Way Receiving Verification (Warehouse vs. Billed — {len(grn_lines)} items)"
        with st.expander(exp_title, expanded=has_shortage or status != STATUS_READY):
            table_display = []
            for r in grn_lines:
                inv_q = float(r.get("invoiced_qty", 0))
                rec_q = float(r.get("received_qty", 0))
                if inv_q == rec_q:
                    m_status = "Exact Match"
                elif rec_q > inv_q:
                    m_status = f"Verified (Partial Bill: {inv_q:.0f} of {rec_q:.0f})"
                else:
                    diff = inv_q - rec_q
                    m_status = f"Short Shipment (-{diff:.0f} units)"

                table_display.append({
                    "Item Description": r.get("description", ""),
                    "Invoiced Qty": r.get("invoiced_qty", ""),
                    "PO Ordered Qty": r.get("po_qty", "N/A"),
                    "Warehouse Received Qty": r.get("received_qty", ""),
                    "Unit Price": r.get("unit_price", ""),
                    "GRN Reference": r.get("grn_number", ""),
                    "Receiving Audit Status": m_status,
                    "Dock Inspection Notes": r.get("dock_notes", "Verified"),
                })
            st.dataframe(table_display, width="stretch", hide_index=True)

    elif po_reconciled:
        has_po_variance = any(r.get("status") != "Exact Match" for r in po_reconciled)
        exp_title = f"2-Way Purchase Order Line Verification ({len(po_reconciled)} items)"
        with st.expander(exp_title, expanded=has_po_variance or status != STATUS_READY):
            table_display = [
                {
                    "Line #": r.get("line_number", ""),
                    "Item Description": r.get("description", ""),
                    "Invoiced Qty": r.get("invoiced_qty", ""),
                    "PO Ordered Qty": r.get("po_qty", ""),
                    "Invoiced Unit Price": r.get("unit_price", ""),
                    "PO Agreed Price": r.get("po_unit_price", ""),
                    "Line Total": r.get("line_total", ""),
                    "Price Variance": r.get("variance", "$0.00"),
                    "PO Match Status": r.get("status", ""),
                }
                for r in po_reconciled
            ]
            st.dataframe(table_display, width="stretch", hide_index=True)

    # Analyst Audit Memo & Findings Summary (Interactive & Editable)
    st.markdown("<div style='font-size:0.85rem; font-weight:700; text-transform:uppercase; color:#64748b; margin:1rem 0 0.4rem;'>Analyst Audit Memo & Review Notes</div>", unsafe_allow_html=True)
    memo_run_tracker = f"memo_tracker_{case_ref}_{invoice.get('invoice_number', 'draft')}"
    if st.session_state.get("active_memo_tracker") != memo_run_tracker:
        st.session_state["active_memo_tracker"] = memo_run_tracker
        st.session_state["analyst_notes"] = result.get("summary", "")

    initial_memo = st.session_state.get("analyst_notes") or result.get("summary", "")
    edited_memo = st.text_area(
        "Analyst Resolution Memo",
        value=initial_memo,
        height=75,
        help="Edit or customize audit memo notes. These notes are preserved in the compliance audit trail and synced to vendor communications.",
        label_visibility="collapsed",
        key="analyst_memo_input",
    )
    if edited_memo != st.session_state.get("analyst_notes"):
        st.session_state["analyst_notes"] = edited_memo

    # Human-in-the-Loop AP Sign-off Actions
    st.markdown("<div style='font-size:0.85rem; font-weight:700; text-transform:uppercase; color:#64748b; margin:0.8rem 0 0.4rem;'>Operational Actions</div>", unsafe_allow_html=True)

    all_passed = all(c.get("result") == "pass" for c in result.get("checks", []))

    if status in {STATUS_READY, "APPROVED"}:
        col_restart, col_hold, col_reject, col_approve = st.columns([1, 1, 1.1, 1.6])
        with col_restart:
            if st.button("Process New Invoice", width="stretch"):
                for k in ["loaded_filename", "draft_invoice", "last_result", "last_run_id", "case_reference", "analyst_notes", "analyst_action_message"]:
                    st.session_state.pop(k, None)
                st.session_state["completed_steps"] = set()
                nav_callbacks["go_to_intake"]()

        with col_hold:
            if st.button("Put on Hold", width="stretch"):
                updated = result.copy()
                updated["status"] = "ON_HOLD"
                updated["summary"] = f"HELD BY ANALYST: {edited_memo}"
                updated["net_payable"] = 0.0
                updated["reviewer"] = "Mohith · AP Operations Analyst"
                last_run_id = st.session_state.get("last_run_id")
                if last_run_id:
                    update_run(last_run_id, updated)
                else:
                    st.session_state["last_run_id"] = save_run(st.session_state.get("loaded_filename", "invoice.pdf"), updated)
                st.session_state["last_result"] = updated
                st.rerun()

        with col_reject:
            if st.button("Reject Invoice", width="stretch"):
                updated = result.copy()
                updated["status"] = "REJECTED"
                updated["summary"] = f"REJECTED BY ANALYST: {edited_memo}"
                updated["net_payable"] = 0.0
                updated["reviewer"] = "Mohith · AP Operations Analyst"
                last_run_id = st.session_state.get("last_run_id")
                if last_run_id:
                    update_run(last_run_id, updated)
                else:
                    st.session_state["last_run_id"] = save_run(st.session_state.get("loaded_filename", "invoice.pdf"), updated)
                st.session_state["last_result"] = updated
                st.session_state["vendor_comm_reason"] = f"REJECTION NOTICE: {edited_memo}"
                st.rerun()

        with col_approve:
            if status == "APPROVED":
                st.html(
                    """
                    <div style="background-color: #059669; color: #ffffff; padding: 0.52rem 0.9rem; border-radius: 8px; text-align: center; font-weight: 700; font-size: 0.88rem; box-shadow: 0 2px 4px rgba(5,150,105,0.25); display: flex; align-items: center; justify-content: center; gap: 6px; height: 38px;">
                        <span>✓</span> <span>Voucher Released to ERP</span>
                    </div>
                    """
                )
            else:
                if st.button("Authorize & Route to ERP", type="primary", width="stretch"):
                    updated = result.copy()
                    updated["status"] = "APPROVED"
                    updated["summary"] = f"APPROVED & RELEASED: {edited_memo}"
                    voucher_num = f"VCH-2026-{1040 + int(st.session_state.get('upload_count', 1)):04d}"
                    updated["voucher_number"] = voucher_num
                    updated["net_payable"] = payable_amount
                    updated["reviewer"] = "Mohith · AP Operations Analyst"
                    last_run_id = st.session_state.get("last_run_id")
                    if last_run_id:
                        update_run(last_run_id, updated)
                    else:
                        st.session_state["last_run_id"] = save_run(st.session_state.get("loaded_filename", "invoice.pdf"), updated)
                    st.session_state["last_result"] = updated
                    st.rerun()

    else:
        # Status is ON_HOLD, REJECTED, NEEDS_REVIEW, or NEEDS_INFORMATION
        col_restart, col_middle_1, col_middle_2, col_comm = st.columns([1, 1.1, 1.2, 1.5])
        with col_restart:
            if st.button("Process New Invoice", width="stretch"):
                for k in ["loaded_filename", "draft_invoice", "last_result", "last_run_id", "case_reference", "analyst_notes", "analyst_action_message"]:
                    st.session_state.pop(k, None)
                st.session_state["completed_steps"] = set()
                nav_callbacks["go_to_intake"]()

        with col_middle_1:
            if status == "ON_HOLD":
                if st.button("Release Hold", type="primary", width="stretch"):
                    updated = result.copy()
                    updated["status"] = STATUS_READY if all_passed else STATUS_REVIEW
                    updated["summary"] = f"Hold released by Mohith. Status restored."
                    updated["reviewer"] = "Mohith · AP Operations Analyst"
                    last_run_id = st.session_state.get("last_run_id")
                    if last_run_id:
                        update_run(last_run_id, updated)
                    else:
                        st.session_state["last_run_id"] = save_run(st.session_state.get("loaded_filename", "invoice.pdf"), updated)
                    st.session_state["last_result"] = updated
                    st.rerun()
            else:
                if st.button("Put on Hold", width="stretch"):
                    updated = result.copy()
                    updated["status"] = "ON_HOLD"
                    updated["summary"] = f"HELD BY ANALYST: {edited_memo}"
                    updated["net_payable"] = 0.0
                    updated["reviewer"] = "Mohith · AP Operations Analyst"
                    last_run_id = st.session_state.get("last_run_id")
                    if last_run_id:
                        update_run(last_run_id, updated)
                    else:
                        st.session_state["last_run_id"] = save_run(st.session_state.get("loaded_filename", "invoice.pdf"), updated)
                    st.session_state["last_result"] = updated
                    st.rerun()

        with col_middle_2:
            if status == "REJECTED":
                if st.button("Re-open / Undo Rejection", type="primary", width="stretch"):
                    updated = result.copy()
                    updated["status"] = STATUS_READY if all_passed else STATUS_REVIEW
                    updated["summary"] = f"Rejection cancelled by Mohith. Status restored."
                    updated["reviewer"] = "Mohith · AP Operations Analyst"
                    last_run_id = st.session_state.get("last_run_id")
                    if last_run_id:
                        update_run(last_run_id, updated)
                    else:
                        st.session_state["last_run_id"] = save_run(st.session_state.get("loaded_filename", "invoice.pdf"), updated)
                    st.session_state["last_result"] = updated
                    st.rerun()
            else:
                if st.button("Reject Invoice", width="stretch"):
                    updated = result.copy()
                    updated["status"] = "REJECTED"
                    updated["summary"] = f"REJECTED BY ANALYST: {edited_memo}"
                    updated["net_payable"] = 0.0
                    updated["reviewer"] = "Mohith · AP Operations Analyst"
                    last_run_id = st.session_state.get("last_run_id")
                    if last_run_id:
                        update_run(last_run_id, updated)
                    else:
                        st.session_state["last_run_id"] = save_run(st.session_state.get("loaded_filename", "invoice.pdf"), updated)
                    st.session_state["last_result"] = updated
                    st.session_state["vendor_comm_reason"] = f"REJECTION NOTICE: {edited_memo}"
                    st.rerun()

        with col_comm:
            if st.button("Vendor Communication ->", width="stretch"):
                st.session_state["vendor_comm_reason"] = edited_memo or result.get("summary", "")
                completed_steps.add(4)
                st.session_state["completed_steps"] = completed_steps
                nav_callbacks["go_to_vendor_comm"]()
