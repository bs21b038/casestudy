"""Stage 01: Data Ingestion & Extraction."""

from __future__ import annotations

import os
from pathlib import Path
import streamlit as st
from backend.reader import InvoiceReadError, read_invoice_pdf
from backend.store import get_next_case_reference
from frontend.components.ui_helpers import (
    confidence_pill,
    render_top_bar,
)
from utils.config import BASE_DIR, DEFAULT_CASE_REFERENCE, MAX_PDF_BYTES


def render_intake(nav_callbacks: dict[str, Any]) -> None:
    """Render Stage 01: Data Ingestion & In-place Case Details."""
    completed_steps = st.session_state.get("completed_steps", set())
    invoice = st.session_state.get("draft_invoice")
    case_ref = st.session_state.get("case_reference") if invoice else None

    # Top fixed bar matching sidebar title - only shows Case ID if invoice is loaded
    render_top_bar("Data Ingestion", case_ref)

    # 1. Compact Header Row with Upload Button on the right and Matching Mode selector
    col_upload_text, col_upload_btn = st.columns([1.5, 1.5])
    with col_upload_text:
        st.html(
            """
            <div style="padding-top: 0.2rem; margin-bottom: 0.35rem;">
                <div style="font-size: 1.05rem; font-weight: 700; color: #0f172a;">Upload Vendor Invoice</div>
                <div style="font-size: 0.82rem; color: #64748b; margin-top: 2px;">Upload a text or digital PDF invoice to extract details and verify matching.</div>
            </div>
            """
        )
        current_mode = st.session_state.get("matching_mode", "2way")
        selected_mode = st.segmented_control(
            "Matching Mode",
            options=["2-Way (PO)", "3-Way (PO + Goods Receipt)"],
            default="2-Way (PO)" if current_mode == "2way" else "3-Way (PO + Goods Receipt)",
            label_visibility="collapsed",
            key="matching_policy_seg",
        )
        new_mode = "3way" if selected_mode and "3-Way" in selected_mode else "2way"
        if new_mode != current_mode:
            st.session_state["matching_mode"] = new_mode
            st.session_state["last_result"] = None
            st.rerun()

    with col_upload_btn:
        uploaded = st.file_uploader(
            "Upload invoice PDF",
            type=["pdf"],
            key="invoice_upload",
            label_visibility="collapsed",
        )

    # Quick One-Click Load & Download Sample Test Invoices
    sample_options = [
        ("INV-NS-1042.pdf", "Happy Path", "100% 2-Way Match", "2way"),
        ("INV-EDGE-DUPLICATE.pdf", "Duplicate Invoice", "Fraud Prevention Hold", "2way"),
        ("INV-SHORT-SHIP-5001.pdf", "3-Way Short Ship", "Warehouse Damage Hold", "3way"),
        ("INV-EDGE-MISSING-NUMBER.pdf", "Missing Header Info", "Needs Clarification", "2way"),
        ("INV-SCANNED-MOBILE-701.pdf", "Mobile Image OCR", "Gemini Vision Multimodal", "2way"),
    ]

    samples_dir = BASE_DIR / "sample_test_invoices"
    if not samples_dir.exists():
        samples_dir = BASE_DIR / "data" / "invoices"

    with st.expander("Sample Test Invoices", expanded=not bool(invoice)):
        st.markdown(
            "<div style='font-size:0.78rem; color:#64748b; margin-bottom:0.6rem;'>"
            "Select a test scenario to load directly into the review desk, or download the PDF:"
            "</div>",
            unsafe_allow_html=True,
        )
        sample_cols = st.columns(len(sample_options))
        for col, (fname, title, desc, rec_mode) in zip(sample_cols, sample_options):
            fpath = samples_dir / fname
            with col:
                st.markdown(
                    f"""
                    <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:0.45rem 0.5rem; margin-bottom:0.35rem; text-align:center;">
                        <div style="font-size:0.73rem; font-weight:700; color:#0f172a; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="{fname}">{fname}</div>
                        <div style="font-size:0.68rem; font-weight:600; color:#0f766e; margin-top:2px;">{title}</div>
                        <div style="font-size:0.65rem; color:#64748b; min-height:28px; line-height:1.25; margin-top:2px;">{desc}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                btn_load = st.button("Load", key=f"quick_load_{fname}", help=f"Load {fname} directly", use_container_width=True)
                if btn_load and fpath.exists():
                    b = fpath.read_bytes()
                    parsed = read_invoice_pdf(b, source_name=fname)
                    st.session_state["matching_mode"] = rec_mode
                    st.session_state["loaded_filename"] = fname
                    st.session_state["current_invoice"] = parsed
                    st.session_state["draft_invoice"] = parsed.copy()
                    st.session_state["current_invoice_bytes"] = b
                    upload_count = st.session_state.get("upload_count", 0)
                    st.session_state["upload_count"] = upload_count + 1
                    st.session_state["case_reference"] = get_next_case_reference(session_offset=upload_count)
                    st.session_state["last_result"] = None
                    for k in ["analyst_notes", "active_memo_tracker", "analyst_action_message", "analyst_memo_input"]:
                        st.session_state.pop(k, None)

                    st.session_state["meta_vendor_name"] = parsed.get("vendor_name") or ""
                    st.session_state["meta_invoice_number"] = parsed.get("invoice_number") or ""
                    st.session_state["meta_invoice_date"] = parsed.get("invoice_date") or ""
                    st.session_state["meta_po_number"] = parsed.get("po_number") or ""
                    st.session_state["meta_total_amount"] = str(parsed.get("total") or "")
                    st.session_state["meta_currency"] = parsed.get("currency") or "USD"

                    completed_steps = st.session_state.get("completed_steps", set())
                    completed_steps.add(1)
                    st.session_state["completed_steps"] = completed_steps
                    st.rerun()

                if fpath.exists():
                    st.download_button(
                        label="Download",
                        data=fpath.read_bytes(),
                        file_name=fname,
                        mime="application/pdf",
                        key=f"dl_btn_{fname}",
                        help=f"Download {fname} to test manual upload",
                        use_container_width=True,
                    )

    invoice_bytes: bytes | None = None
    invoice_name = ""

    if uploaded is not None:
        invoice_bytes = uploaded.getvalue()
        invoice_name = uploaded.name
        if len(invoice_bytes) > MAX_PDF_BYTES:
            st.error("Uploaded file exceeds 10 MB limit.")
            invoice_bytes = None

    if invoice_bytes is not None and invoice_name:
        if st.session_state.get("loaded_filename") != invoice_name:
            try:
                parsed = read_invoice_pdf(invoice_bytes, source_name=invoice_name)
                st.session_state["loaded_filename"] = invoice_name
                st.session_state["current_invoice"] = parsed
                st.session_state["draft_invoice"] = parsed.copy()
                st.session_state["current_invoice_bytes"] = invoice_bytes
                upload_count = st.session_state.get("upload_count", 0)
                st.session_state["upload_count"] = upload_count + 1
                st.session_state["case_reference"] = get_next_case_reference(session_offset=upload_count)
                st.session_state["last_result"] = None  # Invalidate stale analysis cache
                for k in ["analyst_notes", "active_memo_tracker", "analyst_action_message", "analyst_memo_input"]:
                    st.session_state.pop(k, None)

                # Explicitly sync input widget session keys for in-place editing
                st.session_state["meta_vendor_name"] = parsed.get("vendor_name") or ""
                st.session_state["meta_invoice_number"] = parsed.get("invoice_number") or ""
                st.session_state["meta_invoice_date"] = parsed.get("invoice_date") or ""
                st.session_state["meta_po_number"] = parsed.get("po_number") or ""
                st.session_state["meta_total_amount"] = str(parsed.get("total") or "")
                st.session_state["meta_currency"] = parsed.get("currency") or "USD"

                completed_steps.add(1)
                st.session_state["completed_steps"] = completed_steps
                st.rerun()
            except InvoiceReadError as exc:
                st.error(f"Error parsing PDF document: {exc}")
                return

    invoice = st.session_state.get("draft_invoice")
    if not invoice:
        st.html(
            """
            <div class="main-panel-card" style="text-align:center; padding: 2.5rem 1rem; color: #64748b;">
                <div style="font-size: 0.92rem; font-weight: 600; color: #334155;">No Invoice Loaded</div>
                <div style="font-size: 0.8rem; margin-top: 0.35rem;">Upload a vendor invoice PDF above to populate case details and start the matching engine.</div>
            </div>
            """
        )
        return

    extraction = invoice.get("extraction", {})
    confidence = extraction.get("confidence", "high")

    # 2. Main Enclosed Card: CASE DETAILS
    with st.container(border=True):
        st.html(
            f"""
            <div class="card-section-title" style="margin-bottom: 0.85rem;">
                <span>CASE DETAILS</span>
                <span>{confidence_pill(confidence)}</span>
            </div>
            """
        )

        # In-place Editable Fields (Values immediately update draft_invoice for analysis)
        method = extraction.get("method", "pdf_text")
        if "gemini" in method:
            st.info("📷 **Scanned Document Detected:** Document was an image without digital text; extracted via Gemini Vision AI.")
        elif "tesseract" in method:
            st.info("📷 **Scanned Document Detected:** Extracted via local Tesseract OCR.")
        elif extraction.get("confidence") == "none":
            st.warning("⚠️ **Scanned Document Detected:** No digital text found in file. Please verify or input values manually below.")

        c1, c2, c3 = st.columns(3)
        with c1:
            v_val = st.text_input(
                "Vendor Name",
                value=st.session_state.get("meta_vendor_name", invoice.get("vendor_name") or ""),
                key="meta_vendor_name",
            )
            if v_val.strip() != (invoice.get("vendor_name") or ""):
                invoice["vendor_name"] = v_val.strip() or None
                st.session_state["draft_invoice"] = invoice
                st.session_state["last_result"] = None

        with c2:
            inv_val = st.text_input(
                "Invoice Number",
                value=st.session_state.get("meta_invoice_number", invoice.get("invoice_number") or ""),
                key="meta_invoice_number",
            )
            if inv_val.strip() != (invoice.get("invoice_number") or ""):
                invoice["invoice_number"] = inv_val.strip() or None
                st.session_state["draft_invoice"] = invoice
                st.session_state["last_result"] = None

        with c3:
            d_val = st.text_input(
                "Invoice Date (YYYY-MM-DD)",
                value=st.session_state.get("meta_invoice_date", invoice.get("invoice_date") or ""),
                key="meta_invoice_date",
            )
            if d_val.strip() != (invoice.get("invoice_date") or ""):
                invoice["invoice_date"] = d_val.strip() or None
                st.session_state["draft_invoice"] = invoice
                st.session_state["last_result"] = None

        c4, c5, c6 = st.columns(3)
        with c4:
            po_val = st.text_input(
                "PO Reference Number",
                value=st.session_state.get("meta_po_number", invoice.get("po_number") or ""),
                key="meta_po_number",
            )
            if po_val.strip() != (invoice.get("po_number") or ""):
                invoice["po_number"] = po_val.strip() or None
                st.session_state["draft_invoice"] = invoice
                st.session_state["last_result"] = None

        with c5:
            tot_val = st.text_input(
                "Invoice Total Amount",
                value=st.session_state.get("meta_total_amount", str(invoice.get("total") or "")),
                key="meta_total_amount",
            )
            if tot_val.strip() != str(invoice.get("total") or ""):
                invoice["total"] = tot_val.strip() or None
                st.session_state["draft_invoice"] = invoice
                st.session_state["last_result"] = None

        with c6:
            curr_val = st.text_input(
                "Currency",
                value=st.session_state.get("meta_currency", invoice.get("currency") or "USD"),
                key="meta_currency",
            )
            if curr_val.strip() != (invoice.get("currency") or "USD"):
                invoice["currency"] = curr_val.strip() or "USD"
                st.session_state["draft_invoice"] = invoice
                st.session_state["last_result"] = None

    line_items = invoice.get("line_items") or []
    incomplete_lines = []
    for idx, itm in enumerate(line_items, start=1):
        null_attrs = [k for k in ("description", "quantity", "unit_price", "line_total") if itm.get(k) is None or str(itm.get(k)).strip() == "" or str(itm.get(k)).strip().lower() == "none"]
        if null_attrs:
            incomplete_lines.append(f"Line {idx} ({', '.join(null_attrs)})")

    if line_items:
        with st.expander(f"Extracted Line Items ({len(line_items)} items)", expanded=bool(incomplete_lines)):
            if incomplete_lines:
                st.warning(
                    f"⚠️ **Optical Recognition Incomplete:** Vision AI could not infer legible values for **{', '.join(incomplete_lines)}**. "
                    f"Due to ClearMatch's Anti-Hallucination Policy, unreadable values were set to null rather than guessed. "
                    f"Please complete the missing details directly in the table below or escalate to the vendor."
                )
            edited_lines = st.data_editor(line_items, width="stretch", hide_index=True, key="intake_line_items_editor")
            if edited_lines != line_items:
                invoice["line_items"] = edited_lines
                st.session_state["draft_invoice"] = invoice
                st.session_state["last_result"] = None

    # Check for missing mandatory fields
    missing_fields = []
    if not invoice.get("vendor_name"):
        missing_fields.append("Vendor Name")
    if not invoice.get("invoice_number"):
        missing_fields.append("Invoice Number")
    if not invoice.get("invoice_date"):
        missing_fields.append("Invoice Date")
    if not invoice.get("po_number"):
        missing_fields.append("PO Reference")
    if incomplete_lines:
        missing_fields.extend(incomplete_lines)

    # Amber Notice Banner (Matching reference photo)
    if missing_fields:
        missing_str = ", ".join(missing_fields)
        active_mode_str = "3-way" if str(current_mode).startswith("3") else "2-way"
        st.html(
            f"""
            <div class="notice-banner">
                <span style="font-size:1.1rem; line-height:1;">⚠️</span>
                <div>
                    <strong>Missing Mandatory Reference</strong> — Automated {active_mode_str} matching requires {missing_str}.
                    Supply the missing information in the fields above, or escalate to the vendor for document reissue.
                </div>
            </div>
            """
        )

        col_esc, col_space, col_run = st.columns([1.2, 1.8, 1])
        with col_esc:
            if st.button("Escalate to Vendor ->", use_container_width=True):
                st.session_state["vendor_comm_reason"] = f"Missing mandatory field(s): {missing_str}"
                nav_callbacks["go_to_vendor_comm"]()
        with col_run:
            if st.button("Run Analysis ->", type="primary", use_container_width=True):
                st.session_state["last_result"] = None
                completed_steps.add(1)
                st.session_state["completed_steps"] = completed_steps
                nav_callbacks["go_to_analysis"]()
    else:
        # Clean bottom row with right-aligned Run Analysis button
        st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)
        col_space, col_run = st.columns([2.8, 1])
        with col_run:
            if st.button("Run Analysis ->", type="primary", use_container_width=True):
                st.session_state["last_result"] = None
                completed_steps.add(1)
                st.session_state["completed_steps"] = completed_steps
                nav_callbacks["go_to_analysis"]()
