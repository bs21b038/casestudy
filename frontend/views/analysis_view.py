"""Stage 02: Automated Matching & Reconciliation."""

from __future__ import annotations

import streamlit as st

from backend.checker import evaluate_invoice, load_csv
from backend.excel_generator import generate_reconciliation_workbook
from backend.store import save_run
from frontend.components.ui_helpers import (
    render_top_bar,
    status_badge_pill,
)
from utils.config import (
    CSV_REQUIREMENTS,
    DEFAULT_CASE_REFERENCE,
    REFERENCE_DIR,
    STATUS_READY,
)


@st.cache_data(show_spinner=False)
def get_reference_data():
    return {
        filename: load_csv(REFERENCE_DIR / filename, required_columns)
        for filename, required_columns in CSV_REQUIREMENTS.items()
    }


def render_analysis(nav_callbacks: dict[str, Any]) -> None:
    """Render Stage 02: Live Execution and Decision Trail Grid."""
    case_ref = st.session_state.get("case_reference", DEFAULT_CASE_REFERENCE)
    completed_steps = st.session_state.get("completed_steps", set())

    render_top_bar("Run Analysis", case_ref)

    draft = st.session_state.get("draft_invoice")
    if not draft:
        st.warning("No active invoice loaded. Return to Data Ingestion to upload an invoice.")
        if st.button("<- Return to Data Ingestion"):
            nav_callbacks["go_to_intake"]()
        return

    # Check if analysis has already run for this draft
    result = st.session_state.get("last_result")
    if not result:
        # Run evaluation automatically
        support = get_reference_data()
        matching_mode = st.session_state.get("matching_mode", "2way")

        progress_bar = st.progress(0, text="Executing matching engine...")
        progress_bar.progress(30, text="Validating vendor credentials & PO authorization...")
        progress_bar.progress(65, text="Reconciling itemized lines & warehouse receiving logs..." if matching_mode == "3way" else "Reconciling itemized lines & historical spend...")

        result = evaluate_invoice(
            draft,
            support["vendors.csv"],
            support["purchase_orders.csv"],
            support["purchase_order_lines.csv"],
            support["processed_invoice_history.csv"],
            goods_receipts=support.get("goods_receipts.csv", []),
            matching_mode=matching_mode,
        )
        result["case_reference"] = case_ref
        result["reviewer"] = "Mohith · AP Operations Analyst"

        loaded_filename = st.session_state.get("loaded_filename", "uploaded_invoice.pdf")
        run_id = save_run(loaded_filename, result)

        progress_bar.progress(100, text="Matching complete.")
        st.session_state["last_result"] = result
        st.session_state["last_run_id"] = run_id
        completed_steps.add(2)
        st.session_state["completed_steps"] = completed_steps

    status = result.get("status", "UNKNOWN")

    # 1. Main Enclosed Card: Reconciliation Summary
    st.html(
        f"""
        <div class="main-panel-card" style="display:flex; justify-content:space-between; align-items:center; padding:1rem 1.4rem;">
            <div>
                <div style="font-size:0.75rem; text-transform:uppercase; color:#64748b; font-weight:700; letter-spacing:0.04em;">Matching Engine Summary</div>
                <div style="font-size:1.05rem; font-weight:700; color:#0f172a; margin-top:3px;">{result.get('summary', '')}</div>
            </div>
            <div>{status_badge_pill(status)}</div>
        </div>
        """
    )

    # 2. 3-Column Interactive Checks Grid (Full-spectrum policy controls with inline reasoning)
    raw_checks = result.get("checks", [])
    checks_map = {c.get("check"): c for c in raw_checks if isinstance(c, dict)}
    mode_is_3way = str(result.get("matching_mode", "")).startswith("3") or str(st.session_state.get("matching_mode", "")).startswith("3")
    mode_label = "3-Way Match" if mode_is_3way else "2-Way Match"

    rule_display_names = {
        "document_extraction": "Document Extraction Quality",
        "required_fields": "Mandatory Header Fields",
        "invoice_date": "Invoice Date & Format",
        "vendor": "Approved Vendor Master",
        "purchase_order": "PO Validity & Authorization",
        "currency": "Currency Alignment",
        "duplicate": "Duplicate Invoice Detection",
        "invoice_arithmetic": "Arithmetic Verification",
        "line_items": "Line Item Specifications",
        "po_total": "PO Authorized Amount",
        "cumulative_po_amount": "Cumulative Spend vs PO",
        "po_arithmetic": "PO Structural Integrity",
        "goods_receipt_match": "Warehouse Goods Receipt",
    }

    # Standard control suite sequence
    ordered_rules = [
        "document_extraction",
        "required_fields",
        "invoice_date",
        "vendor",
        "purchase_order",
        "currency",
        "duplicate",
        "invoice_arithmetic",
        "line_items",
        "cumulative_po_amount",
        "po_arithmetic",
    ]
    if mode_is_3way:
        ordered_rules.append("goods_receipt_match")

    # Build full display list preserving all controls (active or skipped)
    display_checks = []
    seen_keys = set()
    for r_key in ordered_rules:
        seen_keys.add(r_key)
        chk = checks_map.get(r_key)
        if not chk and r_key == "cumulative_po_amount":
            chk = checks_map.get("po_total")
        if chk:
            display_checks.append(chk)
        else:
            display_checks.append({
                "check": r_key,
                "result": "skipped",
                "detail": "Skipped: Blocked by upstream exception.",
            })

    # Include any custom/extra checks not in the standard suite
    for c in raw_checks:
        k = c.get("check")
        if k not in seen_keys and k != "po_total":
            display_checks.append(c)

    st.html(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
            <div style="font-size:0.8rem; font-weight:800; text-transform:uppercase; color:#64748b; letter-spacing:0.05em;">{mode_label} Rule Controls</div>
            <div style="font-size:0.74rem; color:#94a3b8;">All policy controls evaluated · Status &amp; verification details shown inline</div>
        </div>
        """
    )

    cols = st.columns(3)
    for idx, check in enumerate(display_checks):
        col = cols[idx % 3]
        chk_name = check.get("check", "")
        chk_result = check.get("result", "")
        chk_detail = check.get("detail", "")
        title = rule_display_names.get(chk_name, chk_name.replace("_", " ").title())

        if chk_result == "pass":
            css_class = "check-pass"
            status_icon = "✓"
            status_icon_color = "#16a34a"
            detail_class = "check-detail-pass"
        elif chk_result == "fail":
            css_class = "check-fail"
            status_icon = "✕"
            status_icon_color = "#dc2626"
            detail_class = "check-detail-fail"
        elif chk_result == "warning":
            css_class = "check-warning"
            status_icon = "⚠️"
            status_icon_color = "#d97706"
            detail_class = "check-detail-warning"
        else:
            css_class = "check-skipped"
            status_icon = "—"
            status_icon_color = "#94a3b8"
            detail_class = "check-detail-skipped"

        # Verification reasoning is now displayed inline on all checks
        detail_html = f'<div class="check-box-detail {detail_class}">{chk_detail}</div>' if chk_detail else ""

        with col:
            st.html(
                f"""
                <div class="check-box {css_class}">
                    <div class="check-box-header">
                        <span>{title}</span>
                        <span style="font-size:0.88rem; color:{status_icon_color}; font-weight:800; line-height:1;">{status_icon}</span>
                    </div>
                    {detail_html}
                </div>
                """
            )

    # 3. Excel Reconciliation & Actions
    support = get_reference_data()
    po_num = draft.get("po_number")
    matched_po = next((row for row in support["purchase_orders.csv"] if row.get("po_number") == po_num), None)
    matched_po_lines = [row for row in support["purchase_order_lines.csv"] if row.get("po_number") == po_num]
    matched_grns = [row for row in support.get("goods_receipts.csv", []) if row.get("po_number") == po_num]
    active_mode = result.get("matching_mode") or st.session_state.get("matching_mode", "2way")

    excel_bytes = generate_reconciliation_workbook(
        invoice=draft,
        po=matched_po,
        po_lines=matched_po_lines,
        evaluation_result=result,
        goods_receipts=matched_grns if active_mode == "3way" else None,
    )

    st.markdown("<div style='height:0.75rem;'></div>", unsafe_allow_html=True)
    col_back, col_excel, col_esc, col_next = st.columns([1, 1.4, 1.3, 1.3])

    with col_back:
        if st.button("<- Data Ingestion", use_container_width=True):
            nav_callbacks["go_to_intake"]()

    with col_excel:
        st.download_button(
            label="Download Reconciliation (.xlsx)",
            data=excel_bytes,
            file_name=f"Reconciliation_{draft.get('invoice_number', 'Draft')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with col_esc:
        if status != STATUS_READY:
            if st.button("Escalate to Vendor ->", use_container_width=True):
                failed_checks = [c.get("detail") for c in checks if c.get("result") in {"fail", "warning"}]
                st.session_state["vendor_comm_reason"] = "; ".join(failed_checks) or result.get("summary", "")
                nav_callbacks["go_to_vendor_comm"]()

    with col_next:
        if st.button("Review Decision ->", type="primary", use_container_width=True):
            completed_steps.add(3)
            st.session_state["completed_steps"] = completed_steps
            nav_callbacks["go_to_results"]()
