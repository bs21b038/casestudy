"""Simple Hello test for Google Gemini API."""

import os
import sys
from pathlib import Path
import requests

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.ocr_engine import get_ocr_api_key

def main():
    print("=" * 60)
    print("      Testing Google Gemini API - 'Hello' Verification")
    print("=" * 60)

    api_key, source = get_ocr_api_key()
    if not api_key:
        print("\n[!] No GEMINI_API_KEY found in .env file!")
        sys.exit(1)

    masked_key = api_key[:7] + "..." + api_key[-4:]
    print(f"\n[+] API Key Loaded: {masked_key} (Source: {source})")
    
    # We test the model that succeeded on your account: gemini-flash-lite-latest
    target_models = ["gemini-flash-lite-latest", "gemini-flash-latest"]
    
    for model_name in target_models:
        print(f"\n[*] Sending 'Hello' to model: '{model_name}'...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": "Hello! Please reply with a friendly one-sentence greeting and confirm you are connected and working."}
                    ]
                }
            ]
        }
        
        try:
            resp = requests.post(url, json=payload, timeout=20)
            print(f"[*] Response Status Code: HTTP {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                reply_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                print("\n" + "-" * 60)
                print(f"[SUCCESS] MODEL '{model_name}' REPLIED:")
                print(f"\"{reply_text}\"")
                print("-" * 60)
                print("\n[+] Your Gemini API key is 100% working and ready!")
                return
            else:
                print(f"[-] Status {resp.status_code}: {resp.text[:200]}")
        except Exception as exc:
            print(f"[-] Error connecting to {model_name}: {exc}")

if __name__ == "__main__":
    main()

