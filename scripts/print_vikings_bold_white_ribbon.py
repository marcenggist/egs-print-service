"""
Print Vikings BOLD Labels for White Ribbon on Black PVC
=======================================================
Run this on the print PC where Evolis is connected.
"""

import requests
import base64
import os
import time

PRINT_SERVICE_URL = 'http://localhost:5100'
PRINTER_ID = 'A04FCB32'
API_KEY = os.environ.get('EGS_PRINT_SERVICE_KEY', 'egs-print-2026')
LABELS_FOLDER = 'vikings-project/labels/png_white_ribbon_bold'


def print_label(filepath, label_name):
    """Print a single label."""
    with open(filepath, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode()

    response = requests.post(
        f'{PRINT_SERVICE_URL}/api/printers/{PRINTER_ID}/print',
        json={
            'api_key': API_KEY,
            'image_base64': image_data,
            'orientation': 'landscape',
            'document_name': label_name
        },
        timeout=60
    )
    return response.json()


def main():
    print("=" * 60)
    print("  Print Vikings BOLD Labels (White Ribbon)")
    print("=" * 60)
    print()
    print("  Card type: BLACK PVC")
    print("  Ribbon: WHITE monochrome")
    print("  Images: BOLD fonts (110pt/55pt)")
    print()

    # Get all labels
    files = sorted([f for f in os.listdir(LABELS_FOLDER) if f.endswith('.png')])
    print(f"  Found {len(files)} labels to print")
    print()

    # Print test card first
    print("[1] Printing TEST card (salmon-sashimi)...")
    test_file = os.path.join(LABELS_FOLDER, files[0])
    result = print_label(test_file, 'Test - Bold Viking')

    if result.get('success'):
        print(f"    OK - Sent to printer")
    else:
        print(f"    ERROR: {result.get('error')}")
        return

    print()
    print("=" * 60)
    print("  CHECK THE PRINTED CARD!")
    print("=" * 60)
    print()
    print("  Is the text bold and readable?")
    print("  Are the icons visible?")
    print("  Type 'yes' to print remaining 7 cards.")
    print()

    answer = input("  Continue? (yes/no): ").strip().lower()

    if answer != 'yes':
        print("  Aborted.")
        return

    # Print remaining
    print()
    print("[2] Printing remaining labels...")

    for i, filename in enumerate(files[1:], 2):
        filepath = os.path.join(LABELS_FOLDER, filename)
        result = print_label(filepath, f'Viking Bold {i}')

        if result.get('success'):
            print(f"    [{i}/{len(files)}] OK - {filename}")
        else:
            print(f"    [{i}/{len(files)}] ERROR - {filename}: {result.get('error')}")

        time.sleep(0.5)

    print()
    print("=" * 60)
    print("  DONE - All 8 labels sent to printer")
    print("=" * 60)


if __name__ == '__main__':
    main()
