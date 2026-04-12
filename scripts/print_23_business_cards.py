"""
Print 23 Business Cards (300 DPI) to Evolis Printer
====================================================

Run this script on the print PC where the Evolis is connected.
Prints cards 01-23 from business_cards_36_300dpi/ folder.

First prints 1 test card, waits for confirmation, then prints remaining 22.
"""

import requests
import base64
import time
import os

# Configuration - adjust if needed
PRINT_SERVICE_URL = 'http://localhost:5100'  # Local print service
PRINTER_ID = 'A04FCB32'
API_KEY = os.environ.get('EGS_PRINT_SERVICE_KEY', 'egs-print-2026')
CARDS_FOLDER = 'business_cards_36_300dpi'

def print_card(card_num):
    """Print a single card."""
    filename = f'{CARDS_FOLDER}/card_{card_num:02d}.png'

    if not os.path.exists(filename):
        return {'success': False, 'error': f'File not found: {filename}'}

    with open(filename, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode()

    response = requests.post(
        f'{PRINT_SERVICE_URL}/api/printers/{PRINTER_ID}/print',
        json={
            'api_key': API_KEY,
            'image_base64': image_data,
            'orientation': 'landscape',
            'document_name': f'Business Card {card_num:02d}'
        },
        timeout=60
    )
    return response.json()


def main():
    print("=" * 60)
    print("  Print 23 Business Cards")
    print("=" * 60)
    print()

    # Check service
    print("[1] Checking print service...")
    try:
        r = requests.get(f'{PRINT_SERVICE_URL}/health', timeout=5)
        status = r.json()
        print(f"    Service: {status.get('status', 'unknown')}")
        print(f"    Printers: {status.get('printers_registered', 0)}")
    except Exception as e:
        print(f"    ERROR: Cannot reach print service at {PRINT_SERVICE_URL}")
        print(f"    {e}")
        print()
        print("    Make sure EGS Print Service is running!")
        return

    # Print test card first
    print()
    print("[2] Printing TEST card (card_01)...")
    result = print_card(1)

    if result.get('success'):
        print(f"    OK - Sent to printer")
        print(f"    Size: {result.get('size')}, DPI: {result.get('dpi')}")
    else:
        print(f"    ERROR: {result.get('error')}")
        print()
        print("    Fix the error before continuing!")
        return

    # Wait for user confirmation
    print()
    print("=" * 60)
    print("  CHECK THE PRINTED CARD!")
    print("=" * 60)
    print()
    print("  If the card printed correctly (fills the whole card,")
    print("  not 2-on-1, readable quality), type 'yes' to continue.")
    print()

    answer = input("  Continue with remaining 22 cards? (yes/no): ").strip().lower()

    if answer != 'yes':
        print()
        print("  Aborted. No more cards printed.")
        return

    # Print remaining 22 cards (02-23)
    print()
    print("[3] Printing cards 02-23...")
    print()

    success_count = 0
    fail_count = 0

    for i in range(2, 24):
        result = print_card(i)

        if result.get('success'):
            print(f"    [{i:02d}/23] OK")
            success_count += 1
        else:
            print(f"    [{i:02d}/23] ERROR: {result.get('error')}")
            fail_count += 1

        # Small delay between prints
        time.sleep(0.5)

    print()
    print("=" * 60)
    print(f"  DONE: {success_count + 1} success, {fail_count} failed")
    print("=" * 60)


if __name__ == '__main__':
    main()
