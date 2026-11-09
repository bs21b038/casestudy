"""Custom enterprise CSS design system for ClearMatch AP Operations Workspace."""

import streamlit as st

CUSTOM_CSS = """
<style>
  :root {
    --bg-page: #f8fafc;
    --bg-surface: #ffffff;
    --border-color: #e2e8f0;
    --border-subtle: #cbd5e1;
    --text-primary: #0f172a;
    --text-secondary: #475569;
    --text-muted: #64748b;
    --brand-primary: #0f766e;
    --brand-primary-hover: #115e59;
    --brand-dark: #0f172a;
    --status-success: #15803d;
    --status-success-bg: #f0fdf4;
    --status-success-border: #bbf7d0;
    --status-warning: #b45309;
    --status-warning-bg: #fffbeb;
    --status-warning-border: #fde68a;
    --status-danger: #b91c1c;
    --status-danger-bg: #fef2f2;
    --status-danger-border: #fecaca;
  }

  /* Global Layout */
  .stApp {
    background-color: var(--bg-page);
    color: var(--text-primary);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  }

  /* Clean Streamlit Header - keeps collapse/expand arrow available */
  [data-testid="stHeader"] {
    background: transparent !important;
    height: 2.5rem !important;
    z-index: 99 !important;
  }

  [data-testid="stToolbar"] [data-testid="stHeaderActionElements"] {
    display: none !important;
  }

  .block-container {
    max-width: 1380px;
    padding-top: 0.5rem !important;
    padding-bottom: 1.5rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
  }

  /* Left Sidebar: Sleek, compact, perfectly aligned to top bar */
  section[data-testid="stSidebar"] {
    background-color: var(--bg-page) !important;
    border-right: 1px solid var(--border-color) !important;
    width: 260px !important;
    min-width: 240px !important;
  }

  /* Eliminate empty sidebar header spacing so content aligns with right top bar */
  [data-testid="stSidebarHeader"] {
    display: none !important;
    height: 0px !important;
    min-height: 0px !important;
    padding: 0px !important;
    margin: 0px !important;
  }

  [data-testid="stSidebarContent"] {
    background-color: var(--bg-page) !important;
    padding-top: 0.5rem !important;
    padding-left: 0.9rem !important;
    padding-right: 0.9rem !important;
    padding-bottom: 0.85rem !important;
    overflow-y: auto !important; /* Allow graceful scroll if viewport is tiny, no clipping */
    overflow-x: hidden !important;
    display: flex !important;
    flex-direction: column !important;
    height: 100vh !important;
    box-sizing: border-box !important;
  }

  /* Target only user content container and vertical block */
  [data-testid="stSidebarUserContent"],
  section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"],
  section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
    display: flex !important;
    flex-direction: column !important;
    height: 100% !important;
    flex-grow: 1 !important;
    flex: 1 1 auto !important;
    box-sizing: border-box !important;
  }

  /* Spacer between Step 4 and Bottom Section: visible separation */
  .sidebar-spacer {
    flex-grow: 1 !important;
    flex: 1 1 auto !important;
    min-height: clamp(50px, 20vh, 240px) !important;
  }

  [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:has(.sidebar-spacer) {
    flex-grow: 1 !important;
    flex: 1 1 auto !important;
  }

  /* Bottom anchor: pins divider and Audit Dashboard button to the very bottom */
  [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:has(.sidebar-bottom-anchor) {
    margin-top: auto !important;
    width: 100% !important;
  }

  .sidebar-brand-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: -0.01em;
    margin: 0;
    line-height: 1.2;
    padding-top: 0.15rem;
  }

  .sidebar-brand-subtitle {
    font-size: 0.78rem;
    font-weight: 500;
    color: #64748b;
    margin-top: 2px;
    margin-bottom: 0.65rem;
    line-height: 1.2;
  }

  .sidebar-divider {
    border: none;
    border-top: 1px solid var(--border-color);
    margin: 0.5rem 0 0.65rem 0;
  }

  /* Base Sidebar Buttons: Clean Card Format */
  [data-testid="stSidebar"] .stButton > button {
    display: flex !important;
    align-items: center !important;
    width: 100% !important;
    padding: 0.55rem 0.85rem !important;
    border-radius: 8px !important;
    border: 1px solid var(--border-color) !important;
    background-color: #ffffff !important;
    color: #334155 !important;
    font-size: 0.86rem !important;
    font-weight: 600 !important;
    margin-bottom: 0.4rem !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02) !important;
    transition: all 0.15s ease-in-out !important;
    gap: 0.65rem !important;
  }

  [data-testid="stSidebar"] .stButton > button:hover {
    border-color: #94a3b8 !important;
    background-color: #f1f5f9 !important;
    color: #0f172a !important;
  }

  /* Active Sidebar Step (Teal border, soft tint) */
  [data-testid="stSidebar"] .stButton > button[kind="primary"],
  [data-testid="stSidebar"] .stButton > button[data-testid="stBaseButton-primary"] {
    border: 1.8px solid #0f766e !important;
    background-color: #f0fdfa !important;
    color: #0f766e !important;
    box-shadow: 0 1px 3px rgba(15, 118, 110, 0.12) !important;
    font-weight: 700 !important;
  }

  [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
    border-color: #115e59 !important;
    background-color: #ccfbf1 !important;
    color: #115e59 !important;
  }

  /* Top-left Architecture Info Icon Button */
  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {
    align-items: center !important;
  }

  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] [data-testid="column"]:last-child {
    display: flex !important;
    justify-content: flex-end !important;
    align-items: flex-start !important;
  }

  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] .stButton {
    width: auto !important;
    margin-bottom: 0 !important;
  }

  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] .stButton > button {
    border: 1px solid var(--border-color) !important;
    background: #ffffff !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
    color: #475569 !important;
    padding: 0 !important;
    min-height: 28px !important;
    height: 28px !important;
    width: 28px !important;
    border-radius: 6px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    cursor: pointer !important;
    transition: all 0.15s ease-in-out !important;
    margin: 0.15rem 0 0 0 !important;
  }

  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] .stButton > button:hover {
    color: #0f766e !important;
    border-color: #0f766e !important;
    background-color: #f0fdfa !important;
    transform: scale(1.05) !important;
  }

  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] .stButton > button span[data-testid="stIconMaterial"],
  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] .stButton > button .material-symbols-rounded {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 1.15rem !important;
    line-height: 1 !important;
    color: #475569 !important;
    margin: 0 !important;
  }

  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] .stButton > button:hover span[data-testid="stIconMaterial"],
  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] .stButton > button:hover .material-symbols-rounded {
    color: #0f766e !important;
  }

  /* Sidebar Step Boxes ALONE: Left-aligned icon and text */
  [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:has(.stButton):not(:last-child) .stButton > button,
  [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:nth-child(3) .stButton > button,
  [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:nth-child(4) .stButton > button,
  [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:nth-child(5) .stButton > button,
  [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:nth-child(6) .stButton > button {
    justify-content: flex-start !important;
    text-align: left !important;
    padding-left: 0.85rem !important;
    padding-right: 0.85rem !important;
  }

  [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:has(.stButton):not(:last-child) .stButton > button div[data-testid="stMarkdownContainer"],
  [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:nth-child(3) .stButton > button div[data-testid="stMarkdownContainer"],
  [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:nth-child(4) .stButton > button div[data-testid="stMarkdownContainer"],
  [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:nth-child(5) .stButton > button div[data-testid="stMarkdownContainer"],
  [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:nth-child(6) .stButton > button div[data-testid="stMarkdownContainer"] {
    display: flex !important;
    justify-content: flex-start !important;
    text-align: left !important;
    flex-grow: 1 !important;
    width: 100% !important;
  }

  [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:has(.stButton):not(:last-child) .stButton > button p,
  [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:nth-child(3) .stButton > button p,
  [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:nth-child(4) .stButton > button p,
  [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:nth-child(5) .stButton > button p,
  [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:nth-child(6) .stButton > button p {
    text-align: left !important;
    width: 100% !important;
    margin: 0 !important;
  }

  /* Audit Dashboard Button at bottom: Centered alignment & compact margins */
  [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:last-child .stButton > button {
    justify-content: center !important;
    text-align: center !important;
    margin-bottom: 0 !important;
  }

  [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:last-child .stButton > button div[data-testid="stMarkdownContainer"] {
    display: flex !important;
    justify-content: center !important;
    text-align: center !important;
  }

  [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:last-child .stButton > button p {
    text-align: center !important;
    margin: 0 !important;
  }

  /* Fixed Top Bar on the Right */
  .top-fixed-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.7rem 1.25rem;
    background: #ffffff;
    border: 1px solid var(--border-color);
    border-radius: 9px;
    margin-bottom: 1rem;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
    position: sticky;
    top: 0;
    z-index: 90;
  }

  .top-bar-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0;
    display: flex;
    align-items: center;
    gap: 0.45rem;
    letter-spacing: -0.01em;
  }

  .info-icon {
    font-size: 0.95rem;
    color: #94a3b8;
    cursor: default;
  }

  .top-user-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.55rem;
    padding: 0.25rem 0.65rem;
    background: #f8fafc;
    border: 1px solid var(--border-color);
    border-radius: 8px;
  }

  .avatar-circle {
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background-color: #0f766e;
    color: #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.72rem;
    font-weight: 700;
  }

  .user-details {
    display: flex;
    flex-direction: column;
    text-align: left;
    line-height: 1.15;
  }

  .user-name {
    font-size: 0.8rem;
    font-weight: 700;
    color: #0f172a;
  }

  .user-role {
    font-size: 0.68rem;
    color: #64748b;
  }

  .case-badge-pill {
    padding: 0.3rem 0.65rem;
    background-color: #f1f5f9;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    font-size: 0.76rem;
    font-weight: 600;
    color: #334155;
    letter-spacing: 0.02em;
  }

  /* Main Enclosed Card Box (Matching photo's CASE DETAILS card) */
  .main-panel-card {
    background: #ffffff;
    border: 1px solid var(--border-color);
    border-radius: 10px;
    padding: 1.25rem 1.4rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
  }

  .card-section-title {
    font-size: 0.82rem;
    font-weight: 800;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 0.85rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  /* Compact Input Row Upload Header */
  .upload-header-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1.25rem;
    background: #ffffff;
    border: 1px solid var(--border-color);
    border-radius: 10px;
    margin-bottom: 1rem;
  }

  /* Soft Amber Notice Banner (Matching reference photo) */
  .notice-banner {
    background-color: #fffbeb;
    border: 1px solid #fde68a;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-top: 1rem;
    margin-bottom: 1.25rem;
    font-size: 0.82rem;
    color: #92400e;
    line-height: 1.4;
    display: flex;
    align-items: flex-start;
    gap: 0.6rem;
  }

  .notice-banner strong {
    color: #78350f;
  }

  /* Modern Pill Badges */
  .badge-pill {
    display: inline-flex;
    align-items: center;
    padding: 0.2rem 0.6rem;
    border-radius: 9999px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.02em;
  }

  .badge-high {
    background: #ecfdf5;
    color: #065f46;
    border: 1px solid #a7f3d0;
  }

  .badge-medium {
    background: #fffbeb;
    color: #92400e;
    border: 1px solid #fde68a;
  }

  .badge-danger {
    background: #fef2f2;
    color: #991b1b;
    border: 1px solid #fecaca;
  }

  .tag-auto-detected {
    background-color: #ecfdf5;
    color: #047857;
    border: 1px solid #a7f3d0;
    border-radius: 4px;
    font-size: 0.68rem;
    font-weight: 700;
    padding: 1px 6px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  .tag-required {
    background-color: #fef2f2;
    color: #b91c1c;
    border: 1px solid #fecaca;
    border-radius: 4px;
    font-size: 0.68rem;
    font-weight: 700;
    padding: 1px 6px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  /* Checks Grid Box (Page 2 - Non-wordy, colored borders, tooltip on hover) */
  .check-box {
    background: #ffffff;
    border-radius: 8px;
    padding: 0.75rem 0.9rem;
    border: 1.8px solid var(--border-color);
    margin-bottom: 0.65rem;
    transition: all 0.15s ease;
    cursor: default;
    position: relative;
    min-height: 82px;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
  }

  .check-box.check-pass {
    border-color: #22c55e;
    background-color: #fcfdfc;
  }

  .check-box.check-fail {
    border-color: #ef4444;
    background-color: #fef2f2;
  }

  .check-box.check-warning {
    border-color: #f59e0b;
    background-color: #fffbeb;
  }

  .check-box.check-skipped {
    border-color: #cbd5e1;
    border-style: dashed;
    background-color: #f8fafc;
  }

  .check-box-header {
    font-size: 0.86rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .check-box.check-skipped .check-box-header {
    color: #64748b;
  }

  .check-box-detail {
    font-size: 0.76rem;
    line-height: 1.35;
    margin-top: 0.35rem;
    font-weight: 500;
  }

  .check-box-detail.check-detail-pass {
    color: #166534;
  }

  .check-box-detail.check-detail-fail {
    color: #b91c1c;
    font-weight: 600;
  }

  .check-box-detail.check-detail-warning {
    color: #b45309;
    font-weight: 500;
  }

  .check-box-detail.check-detail-skipped {
    color: #94a3b8;
    font-style: italic;
  }

  /* Streamlit Button Tweaks */
  .stButton > button {
    border-radius: 7px;
    font-weight: 600;
    font-size: 0.88rem;
    padding: 0.45rem 1.1rem;
    transition: all 0.15s ease;
  }

  .stButton > button[kind="primary"] {
    background-color: var(--brand-primary);
    border: 1px solid var(--brand-primary);
    color: white;
  }

  .stButton > button[kind="primary"]:hover {
    background-color: var(--brand-primary-hover);
    border-color: var(--brand-primary-hover);
  }

  /* Streamlit Compact File Uploader in Header Row */
  div[data-testid="stFileUploader"] {
    background: transparent;
    border: none;
    padding: 0;
    margin: 0;
  }

  div[data-testid="stFileUploaderDropzone"] {
    padding: 0.4rem 0.75rem !important;
    border: 1px dashed var(--border-subtle) !important;
    border-radius: 7px !important;
    background-color: #f8fafc !important;
  }
</style>
"""


def apply_custom_styles() -> None:
    """Inject custom enterprise CSS styles."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

