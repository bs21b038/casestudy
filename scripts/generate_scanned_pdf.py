"""Generate a realistic image-only / mobile-scanned invoice PDF."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def generate_scanned_invoice():
    # Canvas
    img = Image.new("RGB", (800, 1050), color=(248, 248, 246))
    draw = ImageDraw.Draw(img)

    # Header
    draw.text((60, 60), "ACME CLOUD SERVICES INC", fill=(30, 30, 30))
    draw.text((60, 85), "100 Innovation Way, Suite 400, Austin, TX", fill=(80, 80, 80))
    draw.text((60, 105), "Tax ID: US-TAX-1002", fill=(80, 80, 80))

    draw.text((530, 60), "INVOICE (MOBILE SCAN)", fill=(120, 30, 30))
    draw.text((530, 85), "Invoice #: SCAN-701", fill=(30, 30, 30))
    draw.text((530, 105), "Invoice Date: 2026-10-15", fill=(30, 30, 30))
    draw.text((530, 125), "PO Reference: PO-4502", fill=(30, 30, 30))

    draw.line([(50, 160), (750, 160)], fill=(180, 180, 180), width=2)
    draw.text((60, 180), "Description", fill=(60, 60, 60))
    draw.text((450, 180), "Qty", fill=(60, 60, 60))
    draw.text((530, 180), "Rate", fill=(60, 60, 60))
    draw.text((640, 180), "Amount", fill=(60, 60, 60))
    draw.line([(50, 205), (750, 205)], fill=(200, 200, 200), width=1)

    # Line item with explicit dollar amounts
    draw.text((60, 230), "Cloud service onboarding hours", fill=(40, 40, 40))
    draw.text((455, 230), "6", fill=(40, 40, 40))
    draw.text((530, 230), "$100.00", fill=(40, 40, 40))
    draw.text((640, 230), "$600.00", fill=(40, 40, 40))

    draw.line([(50, 300), (750, 300)], fill=(200, 200, 200), width=1)
    draw.text((500, 320), "Subtotal:", fill=(60, 60, 60))
    draw.text((640, 320), "$600.00", fill=(30, 30, 30))
    draw.text((500, 345), "Tax (0%):", fill=(60, 60, 60))
    draw.text((640, 345), "$0.00", fill=(30, 30, 30))
    draw.text((500, 375), "Total Due:", fill=(20, 20, 20))
    draw.text((640, 375), "$600.00 USD", fill=(20, 20, 20))

    # Add subtle rotation to simulate mobile camera shot
    skewed = img.rotate(0.5, expand=False, fillcolor=(242, 242, 240))

    # Save to brain first
    brain_path = Path(r"C:\Users\User\.gemini\antigravity\brain\ee2ce58f-301a-4b40-b65a-eaf13ccded6e\INV-SCANNED-MOBILE-701.pdf")
    skewed.save(brain_path, "PDF", resolution=100.0)
    print("Generated clean PDF at:", brain_path)

if __name__ == "__main__":
    generate_scanned_invoice()

