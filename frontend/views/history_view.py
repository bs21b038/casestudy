"""Audit Queue & Historical Runs View."""

from __future__ import annotations

import streamlit as st
from backend.excel_generator import generate_reconciliation_workbook
from backend.store import list_runs
from frontend.components.ui_helpers import render_top_bar, status_badge_pill
from frontend.views.analysis_view import get_reference_data
from utils.config import DEFAULT_CASE_REFERENCE, STATUS_INFO, STATUS_READY, STATUS_REVIEW


def render_history_view(nav_callbacks) -> None:
    """Render the historical audit queue."""
    # Audit Dashboard is a global workspace view, so no single active case ID is displayed
    render_top_bar("Audit Dashboard", None)

    col_btn, _ = st.columns([1.5, 4])
    with col_btn:
        if st.button("<- Return to Workflow", type="primary", use_container_width=True):
            st.session_state["view_mode"] = "workflow"
            st.rerun()

    try:
        runs = list_runs(limit=50)
    except Exception as exc:
        st.error(f"Failed to query run store: {exc}")
        return

    if not runs:
        st.info("No prior processing runs found in audit history.")
        return

    # Metrics Row
    m_approved = sum(1 for r in runs if r["status"] in {STATUS_READY, "APPROVED"})
    m_review = sum(1 for r in runs if r["status"] in {STATUS_REVIEW, "ON_HOLD", "REJECTED"})
    m_info = sum(1 for r in runs if r["status"] == STATUS_INFO)

    cols = st.columns(4)
    cols[0].metric("Total Runs", len(runs))
    cols[1].metric("Approved", m_approved)
    cols[2].metric("Exceptions", m_review)
    cols[3].metric("Info Required", m_info)

    st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

    table_data = []
    for r in runs:
        res = r.get("result", {})
        inv = res.get("invoice", {})
        ext = inv.get("extraction", {})
        m = ext.get("method", "pdf_text")
        if "gemini" in m:
            src_label = "Gemini Vision AI (Scan)"
        elif "tesseract" in m:
            src_label = "Tesseract OCR (Scan)"
        else:
            src_label = "Digital PDF (Text)"

        curr = inv.get("currency", "USD")
        try:
            billed_tot = float(res.get("amounts", {}).get("invoice_total") or inv.get("total") or 0.0)
        except (ValueError, TypeError):
            billed_tot = 0.0

        # Calculate Net Payable to ERP
        if res.get("net_payable") is not None:
            try:
                payable_val = float(res.get("net_payable"))
            except (ValueError, TypeError):
                payable_val = 0.0
        elif r["status"] in {"ON_HOLD", "REJECTED"}:
            payable_val = 0.0
        else:
            grn_lines = res.get("reconciled_grn_lines") or []
            has_shortage = any(float(g.get("invoiced_qty", 0)) > float(g.get("received_qty", 0)) for g in grn_lines)
            if has_shortage:
                subtotal_val = float(inv.get("subtotal") or billed_tot)
                tax_val = float(inv.get("tax_amount") or 0.0)
                tax_rate = (tax_val / subtotal_val) if subtotal_val > 0 else 0.0
                acc_base = 0.0
                for g in grn_lines:
                    iq = float(g.get("invoiced_qty", 0))
                    rq = float(g.get("received_qty", 0))
                    up_str = str(g.get("unit_price", 0)).replace("$", "").replace("₹", "").replace(",", "")
                    try:
                        up = float(up_str or 0.0)
                    except ValueError:
                        up = 0.0
                    acc_base += min(iq, rq) * up
                payable_val = acc_base + (acc_base * tax_rate)
            else:
                payable_val = billed_tot

        if r["status"] in {"ON_HOLD", "REJECTED"}:
            payable_str = f"{curr} $0.00 (Suspended)"
        else:
            payable_str = f"{curr} ${payable_val:,.2f}"

        # ERP Voucher Reference
        v_num = res.get("voucher_number")
        if not v_num:
            if r["status"] == "APPROVED":
                v_num = f"VCH-2026-{1040 + r['run_id']:04d}"
            elif r["status"] == STATUS_READY:
                v_num = "Pending Release"
            elif r["status"] == "ON_HOLD":
                v_num = "Suspended (Hold)"
            elif r["status"] == "REJECTED":
                v_num = "Rejected (Void)"
            else:
                v_num = "Pending Review"

        reviewer_name = res.get("reviewer") or "Mohith · AP Operations Analyst"

        # Determine Matching Mode
        mode_val = res.get("matching_mode") or "2way"
        mode_label = "3-Way (PO+GRN)" if str(mode_val).startswith("3") or res.get("reconciled_grn_lines") else "2-Way (PO)"

        table_data.append({
            "Case ID": res.get("case_reference") or DEFAULT_CASE_REFERENCE,
            "Voucher #": v_num,
            "Matching Mode": mode_label,
            "Run ID": f"#{r['run_id']}",
            "Timestamp (UTC)": r["created_at"].replace("T", " "),
            "Invoice Document": r["filename"],
            "Source": src_label,
            "Vendor": inv.get("vendor_name", "N/A"),
            "Billed Amount": f"{curr} ${billed_tot:,.2f}",
            "Net Payable to ERP": payable_str,
            "Status": r["status"].replace("_", " "),
            "Reviewer": reviewer_name,
            "Summary": r["summary"],
        })

    st.dataframe(table_data, width="stretch", hide_index=True)

    st.markdown("<div style='height:0.8rem;'></div>", unsafe_allow_html=True)
    with st.expander("Historical Audit Workbook Retrieval (.xlsx)", expanded=True):
        st.caption("External audit compliance archive: Regenerate and download authoritative reconciliation workbooks for any historical run.")
        run_options = {
            f"Run #{r['run_id']} - {r['filename']} ({r.get('result', {}).get('case_reference') or 'Case'})": r
            for r in runs
        }
        selected_run_label = st.selectbox("Select Transaction Record", options=list(run_options.keys()))
        if selected_run_label:
            sel_run = run_options[selected_run_label]
            sel_res = sel_run.get("result", {})
            sel_inv = sel_res.get("invoice", {})

            c_info, c_dl = st.columns([2.5, 1.5])
            with c_info:
                ext_meth = sel_inv.get("extraction", {}).get("method", "pdf_text")
                src_disp = "Gemini Vision AI (Scan)" if "gemini" in ext_meth else ("Tesseract OCR (Scan)" if "tesseract" in ext_meth else "Digital PDF (Text)")
                st.markdown(
                    f"**Case:** `{sel_res.get('case_reference', 'N/A')}` &nbsp;|&nbsp; "
                    f"**Source:** `{src_disp}` &nbsp;|&nbsp; "
                    f"**Vendor:** `{sel_inv.get('vendor_name', 'N/A')}` &nbsp;|&nbsp; "
                    f"**Status:** `{sel_run.get('status', 'N/A')}`"
                )
                st.caption(f"Audit Memo: {sel_run.get('summary', 'No memo logged')}")

            with c_dl:
                support = get_reference_data()
                po_num = sel_inv.get("po_number")
                matched_po = next((row for row in support["purchase_orders.csv"] if row.get("po_number") == po_num), None)
                matched_po_lines = [row for row in support["purchase_order_lines.csv"] if row.get("po_number") == po_num]
                matched_grns = [row for row in support.get("goods_receipts.csv", []) if row.get("po_number") == po_num]
                active_mode = sel_res.get("matching_mode") or "2way"

                hist_excel = generate_reconciliation_workbook(
                    invoice=sel_inv,
                    po=matched_po,
                    po_lines=matched_po_lines,
                    evaluation_result=sel_res,
                    goods_receipts=matched_grns if active_mode == "3way" else None,
                )

                run_identifier = sel_inv.get("invoice_number") or f"Run_{sel_run['run_id']}"
                st.download_button(
                    label="Download Workbook (.xlsx)",
                    data=hist_excel,
                    file_name=f"Reconciliation_{run_identifier}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_hist_{sel_run['run_id']}",
                    use_container_width=True,
                )

