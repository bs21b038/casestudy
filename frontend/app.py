"""ClearMatch Accounts Payable Operations Workspace -- Production UI."""

from __future__ import annotations

import os
from pathlib import Path
import streamlit as st

# Auto-load .env into environment if present
_env_p = Path(__file__).resolve().parent.parent / ".env"
if _env_p.exists():
    for _line in _env_p.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            if _k.strip() and _v.strip():
                os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

from frontend.components.styles import apply_custom_styles
from frontend.components.ui_helpers import render_sidebar_navigation
from frontend.views.analysis_view import render_analysis
from frontend.views.history_view import render_history_view
from frontend.views.intake_view import render_intake
from frontend.views.results_view import render_results
from frontend.views.vendor_comm_view import render_vendor_communication


def run() -> None:
    """Main application execution pipeline."""
    st.set_page_config(
        page_title="AP Operations -- ClearMatch Desk",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_custom_styles()

    # Session State Initialization
    if "active_step" not in st.session_state:
        st.session_state["active_step"] = 1
    if "completed_steps" not in st.session_state:
        st.session_state["completed_steps"] = set()
    if "view_mode" not in st.session_state:
        st.session_state["view_mode"] = "workflow"

    # Navigation helpers (passed to views for inline buttons like "Run Analysis ->")
    def go_to_intake():
        st.session_state["active_step"] = 1
        st.session_state["view_mode"] = "workflow"
        st.rerun()

    def go_to_analysis():
        st.session_state["active_step"] = 2
        st.session_state["view_mode"] = "workflow"
        st.rerun()

    def go_to_results():
        st.session_state["active_step"] = 3
        st.session_state["view_mode"] = "workflow"
        st.rerun()

    def go_to_vendor_comm():
        st.session_state["active_step"] = 4
        st.session_state["view_mode"] = "workflow"
        st.rerun()

    nav_callbacks = {
        "go_to_intake": go_to_intake,
        "go_to_analysis": go_to_analysis,
        "go_to_results": go_to_results,
        "go_to_vendor_comm": go_to_vendor_comm,
    }

    # ── Centralized sidebar (rendered once for all views) ──
    active_step = st.session_state.get("active_step", 1)
    completed_steps = st.session_state.get("completed_steps", set())
    is_dashboard = st.session_state.get("view_mode") == "history"

    with st.sidebar:
        render_sidebar_navigation(
            current_step=active_step,
            completed_steps=completed_steps,
            is_dashboard=is_dashboard,
        )

    # ── Route to active view ──
    if is_dashboard:
        render_history_view(nav_callbacks)
        return

    if active_step == 1:
        render_intake(nav_callbacks)
    elif active_step == 2:
        render_analysis(nav_callbacks)
    elif active_step == 3:
        render_results(nav_callbacks)
    elif active_step == 4:
        render_vendor_communication(nav_callbacks)


if __name__ == "__main__":
    run()
