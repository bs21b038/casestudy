"""Diagnostic test for Google Gemini Vision API with automatic model discovery."""

import base64
import json
import os
import re
import sys
from pathlib import Path
import requests

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.ocr_engine import get_ocr_api_key, extract_with_gemini_vision


def load_api_key_from_env_file() -> tuple[str | None, str]:
    if len(sys.argv) > 1 and len(sys.argv[1].strip()) > 10:
        return sys.argv[1].strip(), "Command Line Argument"
    return get_ocr_api_key()


def test_gemini():
    print("=" * 65)
    print("      ClearMatch -- Google Gemini Vision API Test Diagnostic")
    print("=" * 65)

    api_key, source = load_api_key_from_env_file()

    if not api_key:
        print("\n[!] STATUS: NO API KEY DETECTED")
        print("\nHow to set your API Key:")
        print("  1. Open the file '.env' in your project root:")
        print(f"     Path: {ROOT_DIR / '.env'}")
        print("  2. Add your key:")
        print("     GEMINI_API_KEY=YourActualKeyHere")
        print("  3. Save the file and re-run this script:")
        print("     .\\.venv\\Scripts\\python.exe scripts\\test_gemini_api.py\n")
        sys.exit(1)

    masked_key = api_key[:7] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
    print(f"\n[+] API Key Found: {masked_key} (Source: {source})")
    print("[*] Contacting Google ModelService to list available models for this key...")

    # Step 1: Query Google ModelService to see what models this key can access
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    discovered_models = []

    try:
        resp = requests.get(list_url, timeout=15)
        print(f"[*] ModelService Response Status: HTTP {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            models = data.get("models", [])
            print(f"[+] Successfully authenticated! Google returned {len(models)} accessible model(s):")
            for m in models:
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])
                if "generateContent" in methods:
                    discovered_models.append(name)
                    print(f"    - {name} (supports generateContent)")
        else:
            print(f"[-] Google API returned non-200 status:")
            print(f"    Status: {resp.status_code}")
            print(f"    Body:   {resp.text}")
    except Exception as exc:
        print(f"[-] Network connection error: {exc}")

    # Fallback to standard model names if ListModels returned none
    if not discovered_models:
        candidate_names = [
            "gemini-1.5-flash",
            "gemini-1.5-flash-latest",
            "gemini-1.5-flash-001",
            "gemini-1.5-flash-002",
            "gemini-1.5-flash-8b",
            "gemini-2.0-flash",
            "gemini-2.0-flash-exp",
            "gemini-1.5-pro",
            "gemini-1.5-pro-latest",
            "gemini-pro",
        ]
    else:
        # Prioritize flash models
        flash_models = [m for m in discovered_models if "flash" in m.lower()]
        other_models = [m for m in discovered_models if "flash" not in m.lower()]
        candidate_names = flash_models + other_models

    print(f"\n[*] Testing 'generateContent' with candidate models...")
    working_model = None
    ping_payload = {
        "contents": [{"parts": [{"text": "Reply with exactly: 'GEMINI_ONLINE'"}]}]
    }

    for model_name in candidate_names:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        try:
            r = requests.post(url, json=ping_payload, timeout=12)
            if r.status_code == 200:
                body = r.json()
                reply = body.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                print(f"  [PASS] Model '{model_name}': HTTP 200 OK (Response: '{reply}')")
                working_model = model_name
                break
            else:
                err_detail = r.text[:140].replace("\n", " ")
                print(f"  [FAIL] Model '{model_name}': HTTP {r.status_code} -> {err_detail}")
        except Exception as exc:
            print(f"  [ERROR] Model '{model_name}': {exc}")

    if not working_model:
        print("\n" + "=" * 65)
        print("[-] DIAGNOSTIC CONCLUSION:")
        print("    None of the generateContent endpoints succeeded.")
        print("    Please review the HTTP error responses printed above.")
        print("=" * 65)
        sys.exit(1)

    print(f"\n[+] Active Model Confirmed: {working_model}")
    print("[*] Testing Multimodal PDF Extraction on 'INV-SCANNED-MOBILE-701.pdf'...")

    sample_pdf = ROOT_DIR / "data" / "invoices" / "INV-SCANNED-MOBILE-701.pdf"
    if not sample_pdf.exists():
        print(f"[!] Warning: Sample PDF not found at {sample_pdf}")
        sys.exit(0)

    pdf_bytes = sample_pdf.read_bytes()
    
    # Try with extract_with_gemini_vision
    extracted = extract_with_gemini_vision(pdf_bytes, filename=sample_pdf.name)

    if extracted and extracted.get("vendor_name"):
        print("\n" + "=" * 65)
        print(" [SUCCESS] LIVE GEMINI MULTIMODAL EXTRACTION VERIFIED!")
        print("=" * 65)
        print(f"  Vendor Name:    {extracted.get('vendor_name')}")
        print(f"  Invoice Number: {extracted.get('invoice_number')}")
        print(f"  Invoice Date:   {extracted.get('invoice_date')}")
        print(f"  PO Reference:   {extracted.get('po_number')}")
        print(f"  Total Amount:   {extracted.get('currency')} {extracted.get('total')}")
        print(f"  Line Items ({len(extracted.get('line_items', []))} item(s)):")
        for idx, item in enumerate(extracted.get("line_items", []), 1):
            print(f"    {idx}. {item.get('description')} | Qty: {item.get('quantity')} | Rate: {item.get('unit_price')} | Total: {item.get('line_total')}")
        print("\n[+] The Google Gemini Vision API is live and fully working for ClearMatch!")
    else:
        print("\n[-] Extraction did not return structured fields.")
        print("    If Google returned HTTP 429, you reached the 15 req/min free-tier rate limit.")
        print("    Wait 30-45 seconds for the Google quota bucket to reset and re-run.")


if __name__ == "__main__":
    test_gemini()
