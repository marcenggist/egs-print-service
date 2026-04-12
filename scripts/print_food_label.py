#!/usr/bin/env python3
"""
Print Food Label to CAB SQUIX via EGS Print Service
====================================================

This script demonstrates how to print food safety labels
from CalcMenu/Velocity to the CAB SQUIX printer.

Usage:
    # First, start EGS Print Service:
    python -m egs_print_service

    # Then run this script:
    python scripts/print_food_label.py

Requirements:
    pip install requests Pillow
"""

import sys
import os

# Configure UTF-8 encoding for Windows compatibility
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta


def print_food_label_zpl():
    """Print a food label using ZPL commands (text-based, fast)."""
    from egs_print_service.client import EGSPrintClient

    # Connect to EGS Print Service
    client = EGSPrintClient(
        host="localhost",
        port=5100,
        api_key=os.environ.get('EGS_PRINT_SERVICE_KEY', 'egs-print-2026')
    )

    # Find CAB printer
    printers = client.list_printers()
    cab_printer = None
    for p in printers:
        if p.get('brand') == 'cab' or 'cab' in p.get('name', '').lower():
            cab_printer = p
            break

    if not cab_printer:
        print("[ERROR] CAB printer not found. Add it first with:")
        print("   bash scripts/add_cab_printer.sh")
        return False

    printer_id = cab_printer['id']
    print(f"[OK] Found CAB printer: {cab_printer['name']} ({printer_id})")

    # Food label data
    dish_name = "Grilled Atlantic Salmon"
    description = "with Lemon Butter & Asparagus"
    allergens = ["Fish", "Dairy", "Sulfites"]
    prep_date = datetime.now()
    use_by = prep_date + timedelta(hours=36)
    chef = "Chef Marco"
    station = "Hot Kitchen"

    # Build ZPL label
    # Label size: 100mm x 50mm at 300 DPI = ~1181 x 591 dots
    allergen_text = ", ".join(allergens)

    # ZPL code - no comments inside (CAB doesn't support ; comments)
    zpl = f"""^XA
^CI28
^LH0,0
^LL591
^PW1181
^CF0,60
^FO30,30^FD{dish_name}^FS
^CF0,35
^FO30,100^FD{description}^FS
^FO30,150^GB1121,2,2^FS
^CF0,30
^FO30,170^FDAllergens:^FS
^CF0,35
^FO200,165^FR^GB800,45,45,B^FS
^FO210,170^FR^FD {allergen_text} ^FS
^FO30,230^GB1121,2,2^FS
^CF0,28
^FO30,250^FDPrep Date:^FS
^FO250,250^FD{prep_date.strftime('%d %b %Y %H:%M')}^FS
^FO30,290^FDUse By:^FS
^CF0,35
^FO250,285^FD{use_by.strftime('%d %b %Y %H:%M')}^FS
^CF0,25
^FO30,340^FDPrepared by: {chef}^FS
^FO30,375^FDStation: {station}^FS
^FO30,410^GB1121,2,2^FS
^CF0,30
^FO30,430^FDFairmont Le Montreux Palace^FS
^CF0,22
^FO30,470^FDVelocity by CalcMenu^FS
^FO950,400^BQN,2,4^FDQA,{dish_name[:20]}^FS
^XZ
"""

    print(f"\n[INFO] Printing food label for: {dish_name}")
    print(f"   Allergens: {allergen_text}")
    print(f"   Use By: {use_by.strftime('%d %b %Y %H:%M')}")

    # Send to printer
    result = client.print_raw(printer_id, zpl, document_name=f"Food Label - {dish_name}")

    if result.get('success'):
        print(f"\n[OK] Label sent to printer!")
        print(f"  Job ID: {result.get('job', {}).get('id')}")
        return True
    else:
        print(f"\n[ERROR] Print failed: {result.get('error')}")
        return False


def print_food_label_image():
    """Print a food label as an image (more flexible formatting)."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow not installed. Run: pip install Pillow")
        return False

    from egs_print_service.client import EGSPrintClient
    from io import BytesIO
    import base64

    # Connect to EGS Print Service
    client = EGSPrintClient(
        host="localhost",
        port=5100,
        api_key=os.environ.get('EGS_PRINT_SERVICE_KEY', 'egs-print-2026')
    )

    # Find CAB printer
    printers = client.list_printers()
    cab_printer = None
    for p in printers:
        if p.get('brand') == 'cab' or 'cab' in p.get('name', '').lower():
            cab_printer = p
            break

    if not cab_printer:
        print("[ERROR] CAB printer not found.")
        return False

    printer_id = cab_printer['id']
    print(f"[OK] Found CAB printer: {cab_printer['name']}")

    # Create label image (300 DPI, 100mm x 50mm)
    # 100mm at 300dpi = 1181 pixels, 50mm = 591 pixels
    width, height = 1181, 591
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)

    # Load fonts
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
        font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    except:
        font_title = font_large = font_medium = font_small = ImageFont.load_default()

    # Food label data
    dish_name = "Beef Bourguignon"
    description = "Slow-braised beef in red wine"
    allergens = ["Celery", "Sulfites", "Gluten"]
    prep_date = datetime.now()
    use_by = prep_date + timedelta(hours=48)

    # Draw label
    y = 20

    # Title
    draw.text((30, y), dish_name, font=font_title, fill='black')
    y += 55

    # Description
    draw.text((30, y), description, font=font_large, fill='gray')
    y += 45

    # Line
    draw.line([(30, y), (width-30, y)], fill='black', width=2)
    y += 15

    # Allergens with red background
    allergen_text = "Allergens: " + ", ".join(allergens)
    draw.rectangle([(25, y-5), (width-25, y+35)], fill='#ffebee')
    draw.text((30, y), allergen_text, font=font_medium, fill='#c62828')
    y += 50

    # Line
    draw.line([(30, y), (width-30, y)], fill='black', width=2)
    y += 15

    # Dates
    draw.text((30, y), f"Prep Date: {prep_date.strftime('%d %b %Y %H:%M')}", font=font_medium, fill='black')
    y += 35
    draw.text((30, y), f"Use By: {use_by.strftime('%d %b %Y %H:%M')}", font=font_large, fill='#d32f2f')
    y += 45

    # Chef info
    draw.text((30, y), "Prepared by: Chef Jean-Pierre", font=font_small, fill='gray')
    y += 30
    draw.text((30, y), "Station: Garde Manger", font=font_small, fill='gray')
    y += 40

    # Line
    draw.line([(30, y), (width-30, y)], fill='black', width=2)
    y += 10

    # Footer
    draw.text((30, y), "Fairmont Le Montreux Palace", font=font_medium, fill='black')
    draw.text((30, y+30), "Velocity by CalcMenu", font=font_small, fill='gray')

    # Save to buffer
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    print(f"\n[INFO] Printing food label image for: {dish_name}")

    # Send to printer
    result = client.print_image(
        printer_id,
        image_base64,
        document_name=f"Food Label - {dish_name}"
    )

    if result.get('success'):
        print(f"\n[OK] Label sent to printer!")
        return True
    else:
        print(f"\n[ERROR] Print failed: {result.get('error')}")
        return False


def main():
    print("""
============================================================
       CalcMenu Food Label Printing
       CAB SQUIX 6.3/300P via EGS Print Service
============================================================
""")

    print("Select print method:")
    print("  1. ZPL (text commands, fast)")
    print("  2. Image (graphical, flexible)")
    print("  3. Exit")

    choice = input("\nChoice (1-3): ").strip()

    if choice == "1":
        print_food_label_zpl()
    elif choice == "2":
        print_food_label_image()
    else:
        print("Goodbye!")


if __name__ == "__main__":
    main()
