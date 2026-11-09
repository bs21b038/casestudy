"""Reusable UI components and shell layout for ClearMatch AP Operations Workspace."""

from __future__ import annotations

from typing import Any
import streamlit as st
from utils.config import DEFAULT_CASE_REFERENCE, STATUS_INFO, STATUS_READY, STATUS_REVIEW

CURRENT_ANALYST = "Mohith"
CURRENT_ROLE = "AP Operations Analyst"


def render_top_bar(title: str, case_ref: str | None = None) -> None:
    """Render the fixed top bar matching reference design (Step Title + Info icon + Analyst Badge)."""
    case_badge_html = f'<div class="case-badge-pill">Case: {case_ref}</div>' if case_ref else ""
    st.html(
        f"""
        <div class="top-fixed-bar">
            <div class="top-bar-title">
                <span>{title}</span>
                <span class="info-icon" title="ClearMatch Automated AP Workflow Step">ⓘ</span>
            </div>
            <div style="display:flex; align-items:center; gap: 0.65rem;">
                {case_badge_html}
                <div class="top-user-pill">
                    <div class="avatar-circle">MO</div>
                    <div class="user-details">
                        <span class="user-name">{CURRENT_ANALYST}</span>
                        <span class="user-role">{CURRENT_ROLE}</span>
                    </div>
                </div>
            </div>
        </div>
        """
    )


@st.dialog("Enterprise Architecture & ERP Integration Blueprint", width="large")
def render_architecture_dialog() -> None:
    """Modal dialog displaying the comprehensive enterprise architecture and ERP integration blueprint."""
    st.html(
        """
        <div style="font-size:0.86rem; color:#475569; line-height:1.55; margin-bottom:1.1rem;">
            ClearMatch serves as the <strong>AP Verification & Operational Control Desk</strong> decoupled from proprietary ERP storage. In production, 
            reference records (Vendors, POs, Prior Billed History) and approval write-backs communicate with ERP systems through secure REST/OData APIs or event streams.
        </div>
        """
    )

    st.html(
        """
        <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:0.9rem; margin-bottom:1.2rem;">
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:0.9rem;">
                <div style="font-weight:700; color:#0f766e; font-size:0.88rem; margin-bottom:0.35rem;">1. Ingestion Layer</div>
                <div style="font-size:0.78rem; color:#64748b; line-height:1.45;">
                    • In-memory PDF Parser & Regex tokenization<br/>
                    • Document AI / Vision OCR fallback<br/>
                    • Zero temporary disk persistence (SOX-compliant)
                </div>
            </div>
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:0.9rem;">
                <div style="font-weight:700; color:#0f766e; font-size:0.88rem; margin-bottom:0.35rem;">2. Core Rule Engine</div>
                <div style="font-size:0.78rem; color:#64748b; line-height:1.45;">
                    • 10 Automated Financial & Fraud Checks<br/>
                    • Fixed-point Decimal precision arithmetic<br/>
                    • Cumulative PO ceiling & overage tolerance matching
                </div>
            </div>
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:0.9rem;">
                <div style="font-weight:700; color:#0f766e; font-size:0.88rem; margin-bottom:0.35rem;">3. ERP Integration & Audit</div>
                <div style="font-size:0.78rem; color:#64748b; line-height:1.45;">
                    • SAP S/4HANA OData & NetSuite SuiteTalk REST APIs<br/>
                    • Webhook triggers on PO approval event<br/>
                    • Immutable SQLite run store & 3-sheet Excel audit exports
                </div>
            </div>
        </div>
        """
    )

    st.markdown("#### Real-World Enterprise Data Mapping")
    mapping_data = [
        {"ClearMatch Model": "vendors.csv", "SAP S/4HANA Table": "LFA1 (Vendor Master)", "Oracle NetSuite Entity": "Vendor Record (`vendor`)", "Integration Endpoint": "GET /sap/opu/odata/sap/MD_SUPPLIER_SRV"},
        {"ClearMatch Model": "purchase_orders.csv", "SAP S/4HANA Table": "EKKO (PO Header)", "Oracle NetSuite Entity": "PurchaseOrder (`transaction`)", "Integration Endpoint": "GET /API_PURCHASEORDER_PROCESS_SRV/A_PurchaseOrder"},
        {"ClearMatch Model": "purchase_order_lines.csv", "SAP S/4HANA Table": "EKPO (PO Line Item)", "Oracle NetSuite Entity": "PurchaseOrder (`item` sublist)", "Integration Endpoint": "GET /A_PurchaseOrder('{id}')/to_PurchaseOrderItem"},
        {"ClearMatch Model": "processed_invoice_history.csv", "SAP S/4HANA Table": "RBKP / RSEG (Invoice Receipt)", "Oracle NetSuite Entity": "VendorBill (`transaction`)", "Integration Endpoint": "GET /services/rest/record/v1/vendorBill"},
        {"ClearMatch Model": "Approval Write-Back", "SAP S/4HANA Table": "MIRO (Incoming Invoice Posting)", "Oracle NetSuite Entity": "VendorBill (`POST /record/v1/vendorBill`)", "Integration Endpoint": "POST /API_INVOICING_PROCESS_SRV/A_SupplierInvoice"},
    ]
    st.dataframe(mapping_data, width="stretch", hide_index=True)


def render_sidebar_navigation(current_step: int, completed_steps: set[int], is_dashboard: bool = False) -> None:
    """Render the compact left sidebar navigation matching reference format.

    - Header: 'AP Operations' / 'Invoice Control Desk' with info modal button (ⓘ)
    - Step buttons with small square number or green tick checkmark
    - Same step names as right-hand page headers
    - No wordy 'DONE'/'ACTIVE' text tags
    - Compact: no scrolling needed
    - Text in step boxes alone is left-aligned
    - Clear separation between workflow steps and Audit Dashboard at the bottom
    - Clickable navigation between all steps and dashboard
    """
    steps = [
        (1, "Data Ingestion", ":material/looks_one:"),
        (2, "Run Analysis", ":material/looks_two:"),
        (3, "Review Decision", ":material/looks_3:"),
        (4, "Vendor Communication", ":material/looks_4:"),
    ]

    # Dynamic CSS to turn completed step box boundaries green (#22c55e)
    green_rules = []
    for step_num, _, _ in steps:
        is_active = (step_num == current_step) and not is_dashboard
        is_done = (step_num in completed_steps)
        if is_done and not is_active:
            # child 1 is horizontal header (Brand + Info), child 2 is divider; step N is child (N + 2)
            child_idx = step_num + 2
            green_rules.append(
                f"""
                section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:nth-child({child_idx}) button {{
                    border: 1.5px solid #22c55e !important;
                    background-color: #f0fdf4 !important;
                    color: #15803d !important;
                    font-weight: 700 !important;
                }}
                section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:nth-child({child_idx}) button:hover {{
                    border-color: #16a34a !important;
                    background-color: #dcfce7 !important;
                    color: #166534 !important;
                }}
                """
            )

    green_style_tag = f"<style>{''.join(green_rules)}</style>" if green_rules else ""

    # Header Row: Brand Titles on the left, subtle clickable ⓘ Info button on the right
    col_brand, col_info = st.columns([4.2, 0.8])
    with col_brand:
        st.html(
            f"""
            {green_style_tag}
            <div style="padding-top: 0.15rem;">
                <div class="sidebar-brand-title">AP Operations</div>
                <div class="sidebar-brand-subtitle">Invoice Control Desk</div>
            </div>
            """
        )
    with col_info:
        if st.button("", key="sidebar_arch_info", icon=":material/info:", help="Enterprise Architecture & ERP Integration Blueprint"):
            render_architecture_dialog()

    # Sleek Horizontal Divider
    st.html('<div class="sidebar-divider" style="margin-top: 0.15rem; margin-bottom: 0.65rem;"></div>')

    # 4 Workflow Step Buttons
    for step_num, label, num_icon in steps:
        is_active = (step_num == current_step) and not is_dashboard
        is_done = (step_num in completed_steps)

        # Icon: square with number if not done, green tick if done
        icon = ":material/check:" if is_done else num_icon
        btn_type = "primary" if is_active else "secondary"

        if st.button(
            label,
            key=f"sidebar_step_{step_num}",
            icon=icon,
            type=btn_type,
            use_container_width=True,
        ):
            st.session_state["active_step"] = step_num
            st.session_state["view_mode"] = "workflow"
            st.rerun()

    # Spacer providing visible separation between steps and bottom dashboard
    st.html('<div class="sidebar-spacer"></div>')

    # Divider & Dashboard Button (Anchored to bottom of sidebar)
    st.html(
        """
        <div class="sidebar-bottom-anchor">
            <div class="sidebar-divider" style="margin-top: 0.5rem; margin-bottom: 0.65rem;"></div>
        </div>
        """
    )

    dash_type = "primary" if is_dashboard else "secondary"
    if st.button(
        "Audit Dashboard",
        key="sidebar_dashboard",
        icon=":material/dashboard:",
        type=dash_type,
        use_container_width=True,
    ):
        st.session_state["view_mode"] = "history"
        st.rerun()


def status_badge_pill(status: str) -> str:
    """Return HTML markup for clean status badge pill without emojis."""
    if status in {STATUS_READY, "APPROVED"}:
        text = "APPROVED" if status == "APPROVED" else "READY FOR AP APPROVAL"
        return f'<span class="badge-pill badge-high">{text}</span>'
    elif status in {STATUS_INFO, "ON_HOLD"}:
        text = "ON HOLD" if status == "ON_HOLD" else "NEEDS INFORMATION"
        return f'<span class="badge-pill badge-medium">{text}</span>'
    elif status in {STATUS_REVIEW, "REJECTED"}:
        text = "REJECTED" if status == "REJECTED" else "NEEDS REVIEW"
        return f'<span class="badge-pill badge-danger">{text}</span>'
    return f'<span class="badge-pill" style="background:#f1f5f9; color:#475569;">{status}</span>'


def confidence_pill(confidence: str) -> str:
    """Render a compact confidence pill."""
    confidence_lower = str(confidence).lower()
    if confidence_lower == "high":
        return '<span class="badge-pill badge-high">Confidence: High</span>'
    elif confidence_lower == "medium":
        return '<span class="badge-pill badge-medium">Confidence: Medium</span>'
    return '<span class="badge-pill badge-danger">Confidence: Low / OCR Needed</span>'


def clear_invoice_selection() -> None:
    """Clear active invoice state on file changes."""
    for key in (
        "loaded_filename",
        "current_invoice_bytes",
        "current_invoice",
        "draft_invoice",
        "last_result",
        "last_run_id",
        "completed_steps",
        "case_reference",
    ):
        st.session_state.pop(key, None)
