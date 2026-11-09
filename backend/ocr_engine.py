"""OCR and Multimodal Vision Pipeline for Scanned / Image Invoices.

Supports:
1. Google AI Studio / Gemini API (Free tier: 15 RPM, 1,500 requests/day).
2. Local Tesseract / System OCR (if available).
3. ClearMatch Offline Vision Simulation for seamless interview demonstration.
"""

from __future__ import annotations

import base64
import json
import os
import re
from io import BytesIO
from pathlib import Path
from typing import Any

import requests
from pypdf import PdfReader
from utils.logger import logger


def get_ocr_api_key() -> tuple[str | None, str]:
    """Retrieve Gemini API key from environment, Streamlit secrets, session state, or .env file."""
    # 1. Environment variable
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key and env_key.strip():
        return env_key.strip(), "Environment Variable"

    # 2. Streamlit secrets or session_state
    try:
        import streamlit as st
        if "gemini_api_key" in st.session_state and st.session_state["gemini_api_key"].strip():
            return st.session_state["gemini_api_key"].strip(), "Session State (UI)"
        if "ocr_api_key_widget" in st.session_state and st.session_state["ocr_api_key_widget"].strip():
            return st.session_state["ocr_api_key_widget"].strip(), "Session State (UI)"
        if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
            sec_key = st.secrets["GEMINI_API_KEY"]
            if sec_key and sec_key.strip():
                return sec_key.strip(), "Streamlit Secrets"
    except Exception:
        pass

    # 3. .env file
    try:
        env_file = Path(__file__).resolve().parent.parent / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "GEMINI_API_KEY" in line:
                    if "=" in line:
                        k, v = line.split("=", 1)
                        if k.strip() == "GEMINI_API_KEY":
                            val = v.strip().strip('"').strip("'")
                            if val:
                                return val, ".env File"
    except Exception:
        pass

    # 4. .streamlit/secrets.toml file check directly
    try:
        secrets_file = Path(__file__).resolve().parent.parent / ".streamlit" / "secrets.toml"
        if secrets_file.exists():
            for line in secrets_file.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("GEMINI_API_KEY"):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        return val, ".streamlit/secrets.toml"
    except Exception:
        pass

    return None, "Not Configured"


def get_ocr_engine_status() -> dict[str, Any]:
    """Check availability of OCR engines (Gemini Vision API, Local Tesseract, Demo Engine)."""
    api_key, key_source = get_ocr_api_key()
    has_tesseract = False
    try:
        import pytesseract  # type: ignore
        has_tesseract = True
    except ImportError:
        pass

    if api_key:
        active = "Google Gemini Multimodal Vision API"
    elif has_tesseract:
        active = "Local Tesseract OCR"
    else:
        active = "No OCR Engine Configured (Manual In-Place Editing Active)"

    return {
        "gemini_api_available": bool(api_key),
        "api_key_source": key_source,
        "local_tesseract_available": has_tesseract,
        "active_engine": active,
    }


def extract_with_gemini_vision(image_or_pdf_bytes: bytes, filename: str) -> dict[str, Any] | None:
    """Extract structured invoice fields from an image/PDF using Google Gemini Vision API."""
    api_key, source = get_ocr_api_key()
    if not api_key:
        return None

    logger.info("Triggering Gemini Vision Multimodal OCR for %s (Key source: %s)", filename, source)
    b64_data = base64.b64encode(image_or_pdf_bytes).decode("utf-8")
    mime_type = "application/pdf" if filename.lower().endswith(".pdf") else "image/png"

    # For scanned PDFs, extract the underlying raster image so Gemini receives clean image/jpeg
    if filename.lower().endswith(".pdf"):
        try:
            reader = PdfReader(BytesIO(image_or_pdf_bytes))
            if reader.pages and reader.pages[0].images:
                raw_img = reader.pages[0].images[0].data
                b64_data = base64.b64encode(raw_img).decode("utf-8")
                mime_type = "image/jpeg"
                logger.info("Extracted embedded raster image (%d bytes, JPEG) from %s for Gemini Vision", len(raw_img), filename)
        except Exception as img_exc:
            logger.debug("PDF raster image extraction fallback: %s", img_exc)

    prompt = """You are an enterprise Accounts Payable OCR engine. Extract data from this scanned/photo invoice into clean JSON:
{
  "vendor_name": string or null,
  "invoice_number": string or null,
  "invoice_date": "YYYY-MM-DD" or null,
  "po_number": string or null,
  "currency": "USD" or "INR" or "EUR" or "GBP" or null,
  "subtotal": "0.00" (numeric string) or null,
  "tax_amount": "0.00" (numeric string) or null,
  "total": "0.00" (numeric string) or null,
  "line_items": [
    {
      "description": string,
      "quantity": "integer or decimal string",
      "unit_price": "0.00",
      "line_total": "0.00"
    }
  ]
}

CRITICAL ANTI-HALLUCINATION & INTEGRITY DIRECTIVES:
1. Do NOT hallucinate, infer, extrapolate, or guess any value.
2. If any field, word, or number is illegible, blurry, cut off, or not explicitly stated in the document, return null for that field. Never substitute plausible or close-looking numbers or names.
3. For line items: Only include line items that are clearly and legibly printed in the document table. If a table row's rate or quantity cannot be read with certainty, return null for that specific attribute.
4. Extract strictly the exact values shown without adding assumptions.

Return ONLY pure JSON without markdown code fences."""

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": b64_data,
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "response_mime_type": "application/json",
        },
    }

    candidate_urls = [
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-lite-latest:generateContent?key={api_key}",
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}",
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={api_key}",
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}",
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}",
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
    ]

    try:
        for url in candidate_urls:
            resp = requests.post(url, json=payload, timeout=25)
            if resp.status_code == 200:
                result_json = resp.json()
                text_resp = result_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                # Clean possible markdown fences
                if text_resp.startswith("```"):
                    text_resp = re.sub(r"^```(?:json)?\s*", "", text_resp)
                    text_resp = re.sub(r"\s*```$", "", text_resp)
                parsed = json.loads(text_resp)
                parsed["extraction"] = {
                    "method": "gemini_multimodal_vision_ocr",
                    "confidence": "high",
                    "warnings": [],
                    "source_file": filename,
                }
                logger.info("Gemini Vision OCR extraction successful for %s via %s", filename, url.split("models/")[1].split(":")[0])
                return parsed
            if resp.status_code == 404:
                continue
            logger.warning("Gemini Vision API returned status %d: %s", resp.status_code, resp.text)
            break
    except Exception as exc:
        logger.error("Gemini Vision OCR failed for %s: %s", filename, exc)

    return None


def run_ocr_pipeline(source_bytes: bytes, filename: str) -> dict[str, Any] | None:
    """Unified entry point to run OCR extraction on scanned PDFs or invoice images."""
    # 1. Try Live Gemini Vision API if key is present
    gemini_result = extract_with_gemini_vision(source_bytes, filename)
    if gemini_result and gemini_result.get("vendor_name"):
        return gemini_result

    # 2. Try Local Tesseract if available
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore

        reader = PdfReader(BytesIO(source_bytes))
        extracted_text = ""
        for page in reader.pages:
            for img in page.images:
                pil_img = Image.open(BytesIO(img.data))
                extracted_text += "\n" + pytesseract.image_to_string(pil_img)

        if extracted_text.strip():
            from backend.reader import parse_invoice_text
            res = parse_invoice_text(extracted_text)
            res["extraction"]["method"] = "tesseract_local_ocr"
            res["extraction"]["source_file"] = filename
            logger.info("Tesseract local OCR succeeded for %s", filename)
            return res
    except Exception as exc:
        logger.debug("Local Tesseract OCR skipped: %s", exc)

    return None
