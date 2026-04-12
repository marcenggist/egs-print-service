"""
Print Business Card FRONT at 600 DPI
=====================================

Simple, clean design with CalcMenu branding.
CR-80 format at 600 DPI: 2032x1296 pixels
"""

from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import os
import sys
import requests
import base64
from io import BytesIO

# Configuration
PRINT_SERVICE_URL = 'http://192.168.1.39:5100'
PRINTER_ID = 'A04FCB32'
API_KEY = os.environ.get('EGS_PRINT_SERVICE_KEY', 'egs-print-2026')

# Card dimensions at 600 DPI
DPI = 600
CARD_WIDTH = 2032
CARD_HEIGHT = 1296

# Colors
BLACK = '#000000'
FOREST_GREEN = '#2C5F2D'
SANDY_BROWN = '#F4A460'
WHITE = '#FFFFFF'


def generate_card_front():
    """Generate business card front at 600 DPI."""

    print(f"[INFO] Generating card FRONT at {DPI} DPI ({CARD_WIDTH}x{CARD_HEIGHT} pixels)")

    # Create white card
    card = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), 'white')
    draw = ImageDraw.Draw(card)

    # Font paths: project fonts first (cross-platform), Windows fallback
    def find_font(candidates):
        for path in candidates:
            if os.path.exists(path):
                return path
        return candidates[0]

    arial_bold = find_font([
        "fonts/sans-serif/Lato-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ])
    arial_regular = find_font([
        "fonts/sans-serif/Lato-Regular.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ])

    if not os.path.exists(arial_bold):
        print("[ERROR] No suitable bold font found!")
        return None

    font_tagline = ImageFont.truetype(arial_regular, 60)
    font_url = ImageFont.truetype(arial_bold, 50)

    # === TOP ACCENT BAR (same as back for consistency) ===
    bar_height = 28
    green_width = int(CARD_WIDTH * 0.6)
    draw.rectangle([(0, 0), (green_width, bar_height)], fill=FOREST_GREEN)
    draw.rectangle([(green_width, 0), (CARD_WIDTH, bar_height)], fill=SANDY_BROWN)

    # === BOTTOM ACCENT BAR ===
    draw.rectangle([(0, CARD_HEIGHT - bar_height), (green_width, CARD_HEIGHT)], fill=FOREST_GREEN)
    draw.rectangle([(green_width, CARD_HEIGHT - bar_height), (CARD_WIDTH, CARD_HEIGHT)], fill=SANDY_BROWN)

    # === LOAD AND CENTER CALCMENU LOGO ===
    logo_path = "business_card_files/calcmenu_clean.png"
    if os.path.exists(logo_path):
        logo = Image.open(logo_path).convert('RGBA')

        # Enhance logo
        r, g, b, a = logo.split()
        rgb_img = Image.merge('RGB', (r, g, b))
        enhancer = ImageEnhance.Contrast(rgb_img)
        rgb_img = enhancer.enhance(1.4)
        enhancer = ImageEnhance.Sharpness(rgb_img)
        rgb_img = enhancer.enhance(1.5)
        r, g, b = rgb_img.split()
        logo = Image.merge('RGBA', (r, g, b, a))

        # Scale logo to be prominent (about 50% of card width)
        target_width = int(CARD_WIDTH * 0.5)
        ratio = target_width / logo.width
        new_height = int(logo.height * ratio)
        logo = logo.resize((target_width, new_height), Image.LANCZOS)

        # Center logo vertically and horizontally
        logo_x = (CARD_WIDTH - target_width) // 2
        logo_y = (CARD_HEIGHT - new_height) // 2 - 80  # Slightly above center

        card.paste(logo, (logo_x, logo_y), logo)
        print(f"  [OK] Loaded CalcMenu logo ({target_width}x{new_height})")

    # === TAGLINE ===
    tagline = "Kitchen Intelligence Platform"
    tag_bbox = draw.textbbox((0, 0), tagline, font=font_tagline)
    tag_width = tag_bbox[2] - tag_bbox[0]
    tag_x = (CARD_WIDTH - tag_width) // 2
    tag_y = CARD_HEIGHT // 2 + 150
    draw.text((tag_x, tag_y), tagline, font=font_tagline, fill=BLACK)

    # === WEBSITE URL ===
    url = "calcmenu.com"
    url_bbox = draw.textbbox((0, 0), url, font=font_url)
    url_width = url_bbox[2] - url_bbox[0]
    url_x = (CARD_WIDTH - url_width) // 2
    url_y = tag_y + 100
    draw.text((url_x, url_y), url, font=font_url, fill=FOREST_GREEN)

    print(f"[OK] Card FRONT generated: {CARD_WIDTH}x{CARD_HEIGHT} @ {DPI} DPI")

    return card


def print_card(card_image):
    """Send card to print service."""

    print(f"\n[INFO] Sending to print service at {PRINT_SERVICE_URL}")

    buffer = BytesIO()
    card_image.save(buffer, format='PNG', dpi=(DPI, DPI))
    image_bytes = buffer.getvalue()

    print(f"[INFO] Image size: {len(image_bytes):,} bytes")

    try:
        response = requests.post(
            f'{PRINT_SERVICE_URL}/api/printers/{PRINTER_ID}/print',
            json={
                'api_key': API_KEY,
                'image_base64': base64.b64encode(image_bytes).decode(),
                'orientation': 'landscape',
                'document_name': f'Business Card Front {DPI}dpi'
            },
            timeout=30
        )

        result = response.json()

        if result.get('success'):
            print(f"[SUCCESS] Print job sent!")
            print(f"  Printer: {result.get('printer')}")
            print(f"  Size: {result.get('size')}")
            print(f"  DPI: {result.get('dpi')}")
        else:
            print(f"[ERROR] Print failed: {result.get('error')}")

        return result

    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Cannot connect to {PRINT_SERVICE_URL}")
        return {'success': False, 'error': 'Connection refused'}
    except Exception as e:
        print(f"[ERROR] {e}")
        return {'success': False, 'error': str(e)}


def save_card(card_image, filename='business_card_front_600dpi.png'):
    """Save card to file."""
    card_image.save(filename, 'PNG', dpi=(DPI, DPI))
    print(f"[OK] Saved to {filename}")


def main():
    print("=" * 60)
    print("  Business Card FRONT - 600 DPI Color")
    print("=" * 60)
    print()

    card = generate_card_front()

    if card is None:
        print("[ERROR] Card generation failed")
        return

    save_card(card)

    if '--no-print' not in sys.argv:
        result = print_card(card)
        if result.get('success'):
            print("\n" + "=" * 60)
            print("  [SUCCESS] Business card FRONT printed!")
            print("=" * 60)
    else:
        print("\n[INFO] Skipped printing (--no-print flag)")


if __name__ == '__main__':
    main()
