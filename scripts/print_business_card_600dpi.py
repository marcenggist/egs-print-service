"""
Print Business Card at 600 DPI for Color Printing
==================================================

CR-80 format at 600 DPI: 2032x1296 pixels
(Double the 300 DPI resolution for high quality color)

Note: 1200 DPI does not work with color ribbon - use 600 DPI max.
"""

from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import qrcode
import os
import sys
import requests
import base64
from io import BytesIO

# Configuration
PRINT_SERVICE_URL = 'http://192.168.1.39:5100'  # Remote print PC via Tailscale
PRINTER_ID = 'A04FCB32'  # Evolis printer ID from print service
API_KEY = os.environ.get('EGS_PRINT_SERVICE_KEY', 'egs-print-2026')

# Card dimensions at 600 DPI (2x of 300 DPI)
DPI = 600
CARD_WIDTH = 2032   # 3.375" x 600 DPI = 2025 (rounded to 2032 for clean scaling)
CARD_HEIGHT = 1296  # 2.125" x 600 DPI = 1275 (rounded to 1296 for clean scaling)

# Contact info
CONTACT = {
    'name': 'Marc Enggist',
    'title': 'CEO & CO-FOUNDER',
    'company': 'EGS Enggist & Grandjean Software SA',
    'location': 'Neuchatel, Switzerland',
    'email': 'marc@calcmenu.com',
    'phone': '+41 76 370 72 94',
    'qr_url': 'https://app.calcmenu.io/contact/marc-enggist'
}

# Colors - BLACK TEXT ONLY (user preference)
BLACK = '#000000'
CHARCOAL = '#2D3436'
CHARCOAL_SOFT = '#4A4F51'
# Accent colors (bars only, not text)
FOREST_GREEN = '#2C5F2D'
SANDY_BROWN = '#F4A460'

# 20 Mottos
MOTTOS = [
    "Your food cost shouldn't depend on who's working today.",
    "Control the prep. Control the cost.",
    "Every gram tracked is margin recovered.",
    "Same recipe. Same result. Every chef. Every shift.",
    "Your standards shouldn't leave when your chef does.",
    "Consistency isn't a person. It's a system.",
    "Allergens don't wait for someone to remember.",
    "14 allergens. 3 languages. Zero guesswork.",
    "Food safety is a system, not a habit.",
    "One recipe. Ten kitchens. One standard.",
    "Scale your food, not your problems.",
    "Hope is not a food safety strategy.",
    "A recipe without a system is just a suggestion.",
    "Your spreadsheet won't catch an allergen.",
    "If your recipe lives in someone's head, it dies when they leave.",
    "Your guest deserves to know. Your label should show.",
    "Transparency starts at the label.",
    "Software that thinks like a chef and reports like a CFO.",
    "Where recipes become operations.",
    "Swiss precision for every kitchen.",
]


def generate_card_600dpi(motto="Your food cost shouldn't depend on who's working today."):
    """Generate business card back at 600 DPI."""

    print(f"[INFO] Generating card at {DPI} DPI ({CARD_WIDTH}x{CARD_HEIGHT} pixels)")

    # Create white card
    card = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), 'white')
    draw = ImageDraw.Draw(card)

    # Font paths (scale factor for 600 DPI)
    scale = 2  # 600 DPI / 300 DPI

    # Font paths: project fonts first (cross-platform), Windows fallback
    def find_font(candidates):
        for path in candidates:
            if os.path.exists(path):
                return path
        return candidates[0]  # Will fail with clear error if none found

    arial_bold = find_font([
        "fonts/sans-serif/Lato-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ])
    arial_regular = find_font([
        "fonts/sans-serif/Lato-Regular.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ])
    arial_italic = find_font([
        "fonts/sans-serif/Lato-Italic.ttf",
        "C:/Windows/Fonts/ariali.ttf",
    ])

    if not os.path.exists(arial_bold):
        print("[ERROR] No suitable bold font found!")
        return None

    # Font sizes at 600 DPI - all Arial family - EVEN BIGGER
    font_name = ImageFont.truetype(arial_bold, 200)       # Name - bold
    font_title = ImageFont.truetype(arial_bold, 85)       # Title - bold
    font_company = ImageFont.truetype(arial_regular, 68)  # Company - regular
    font_motto = ImageFont.truetype(arial_italic, 80)     # Motto - italic (reduced to fit)
    font_contact = ImageFont.truetype(arial_bold, 68)     # Contact - bold
    font_qr_label = ImageFont.truetype(arial_regular, 40) # QR label - regular

    # Load logos
    logos = []
    logo_files = [
        ("business_card_files/calcmenu_clean.png", "CalcMenu"),
        ("business_card_files/velocity_clean.png", "Velocity"),
        ("business_card_files/nooko_clean.png", "Nooko"),
    ]

    for logo_path, logo_name in logo_files:
        if os.path.exists(logo_path):
            try:
                logo = Image.open(logo_path).convert('RGBA')
                # Enhance logo
                if logo.mode == 'RGBA':
                    r, g, b, a = logo.split()
                    rgb_img = Image.merge('RGB', (r, g, b))
                    enhancer = ImageEnhance.Contrast(rgb_img)
                    rgb_img = enhancer.enhance(1.4)
                    enhancer = ImageEnhance.Sharpness(rgb_img)
                    rgb_img = enhancer.enhance(1.5)
                    r, g, b = rgb_img.split()
                    logo = Image.merge('RGBA', (r, g, b, a))
                logos.append((logo, logo_name))
                print(f"  [OK] Loaded {logo_name} logo")
            except Exception as e:
                print(f"  [WARN] Could not load {logo_name}: {e}")

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=2,
    )
    qr.add_data(CONTACT['qr_url'])
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color='#000000', back_color='white')
    qr_size = 320  # Smaller QR to leave more room for logos
    qr_img = qr_img.resize((qr_size, qr_size), Image.LANCZOS)

    # === TOP ACCENT BAR ===
    bar_height = 28
    green_width = int(CARD_WIDTH * 0.6)
    draw.rectangle([(0, 0), (green_width, bar_height)], fill=FOREST_GREEN)
    draw.rectangle([(green_width, 0), (CARD_WIDTH, bar_height)], fill=SANDY_BROWN)

    # === ZONE 1: IDENTITY ===
    y = 80

    # Name centered - BLACK TEXT
    name_bbox = draw.textbbox((0, 0), CONTACT['name'], font=font_name)
    name_height = name_bbox[3] - name_bbox[1]
    name_width = name_bbox[2] - name_bbox[0]
    name_x = (CARD_WIDTH - name_width) // 2
    draw.text((name_x, y), CONTACT['name'], font=font_name, fill=BLACK)
    y += name_height + 40  # Dynamic spacing based on actual text height

    # Title - BLACK TEXT
    title = CONTACT['title']
    title_bbox = draw.textbbox((0, 0), title, font=font_title)
    title_height = title_bbox[3] - title_bbox[1]
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (CARD_WIDTH - title_width) // 2
    draw.text((title_x, y), title, font=font_title, fill=BLACK)
    y += title_height + 30

    # Company + Location - DARK GREY
    company_loc = f"{CONTACT['company']}  \u00b7  {CONTACT['location']}"
    cl_bbox = draw.textbbox((0, 0), company_loc, font=font_company)
    cl_height = cl_bbox[3] - cl_bbox[1]
    cl_width = cl_bbox[2] - cl_bbox[0]
    cl_x = (CARD_WIDTH - cl_width) // 2
    draw.text((cl_x, y), company_loc, font=font_company, fill=BLACK)

    zone1_bottom = y + cl_height + 30

    # === ZONE 3: FOOTER ===
    footer_top = CARD_HEIGHT - 560
    margin = 180

    # Divider
    draw.line([(margin, footer_top), (CARD_WIDTH - margin, footer_top)],
              fill=SANDY_BROWN, width=4)

    # Contact line
    contact_text = f"{CONTACT['phone']}  \u00b7  {CONTACT['email']}"
    ct_bbox = draw.textbbox((0, 0), contact_text, font=font_contact)
    ct_width = ct_bbox[2] - ct_bbox[0]
    ct_x = (CARD_WIDTH - ct_width) // 2
    draw.text((ct_x, footer_top + 40), contact_text, font=font_contact, fill=BLACK)

    # QR code - right side
    qr_x = CARD_WIDTH - margin - qr_size
    qr_y = footer_top + 160
    card.paste(qr_img, (qr_x, qr_y))

    # "SCAN TO CONNECT"
    scan_text = "SCAN TO CONNECT"
    scan_bbox = draw.textbbox((0, 0), scan_text, font=font_qr_label)
    scan_width = scan_bbox[2] - scan_bbox[0]
    scan_x = qr_x + (qr_size - scan_width) // 2
    draw.text((scan_x, qr_y + qr_size + 20), scan_text, font=font_qr_label, fill=BLACK)

    # Logos - left side, smaller to fit without overlap
    if logos:
        logo_height = 140  # Smaller logos to fit in available space
        logo_x = margin
        # Calculate available width (from margin to QR code with gap)
        available_width = qr_x - margin - 60  # 60px gap before QR
        logo_y = qr_y + (qr_size - logo_height) // 2

        # Calculate total width needed for all logos
        total_logo_width = 0
        for logo_img, name in logos:
            ratio = logo_height / logo_img.height
            total_logo_width += int(logo_img.width * ratio) + 40  # 40px spacing

        # If logos would overflow, reduce height further
        if total_logo_width > available_width:
            logo_height = int(logo_height * available_width / total_logo_width)
            logo_y = qr_y + (qr_size - logo_height) // 2

        for logo_img, name in logos:
            ratio = logo_height / logo_img.height
            new_width = int(logo_img.width * ratio)
            resized_logo = logo_img.resize((new_width, logo_height), Image.LANCZOS)

            if resized_logo.mode == 'RGBA':
                card.paste(resized_logo, (logo_x, logo_y), resized_logo)
            else:
                card.paste(resized_logo, (logo_x, logo_y))
            logo_x += new_width + 40  # Reduced spacing

    zone3_top = footer_top

    # === ZONE 2: MOTTO ===
    import textwrap

    motto_zone_top = zone1_bottom + 20
    motto_zone_bottom = zone3_top - 20
    motto_zone_height = motto_zone_bottom - motto_zone_top

    wrapper = textwrap.TextWrapper(width=45)  # Narrower wrap to prevent overflow
    motto_lines = wrapper.wrap(f'"{motto}"')

    # FIXED font size for ALL mottos - consistent appearance
    font_motto_dynamic = font_motto  # Always use 80pt
    line_spacing = 20

    # Calculate line height based on actual font size
    test_bbox = draw.textbbox((0, 0), "Ag", font=font_motto_dynamic)
    line_height = (test_bbox[3] - test_bbox[1]) + line_spacing
    total_motto_height = len(motto_lines) * line_height

    # No dynamic reduction - FIXED 80pt for ALL mottos

    motto_start_y = motto_zone_top + (motto_zone_height - total_motto_height) // 2

    for i, line in enumerate(motto_lines):
        bbox = draw.textbbox((0, 0), line, font=font_motto_dynamic)
        line_width = bbox[2] - bbox[0]
        motto_x = (CARD_WIDTH - line_width) // 2
        draw.text((motto_x, motto_start_y + i * line_height), line, font=font_motto_dynamic, fill=BLACK)  # Pure black

    print(f"[OK] Card generated: {CARD_WIDTH}x{CARD_HEIGHT} @ {DPI} DPI")

    return card


def print_card(card_image):
    """Send card to print service."""

    print(f"\n[INFO] Sending to print service at {PRINT_SERVICE_URL}")

    # Convert to PNG bytes
    buffer = BytesIO()
    card_image.save(buffer, format='PNG', dpi=(DPI, DPI))
    image_bytes = buffer.getvalue()

    print(f"[INFO] Image size: {len(image_bytes):,} bytes")

    # Send to print service
    try:
        response = requests.post(
            f'{PRINT_SERVICE_URL}/api/printers/{PRINTER_ID}/print',
            json={
                'api_key': API_KEY,
                'image_base64': base64.b64encode(image_bytes).decode(),
                'orientation': 'landscape',
                'document_name': f'Business Card {DPI}dpi'
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
        print("  Make sure the print service is running on the print PC")
        return {'success': False, 'error': 'Connection refused'}
    except Exception as e:
        print(f"[ERROR] {e}")
        return {'success': False, 'error': str(e)}


def save_card(card_image, filename='business_card_600dpi.png'):
    """Save card to file."""
    card_image.save(filename, 'PNG', dpi=(DPI, DPI))
    print(f"[OK] Saved to {filename}")


def generate_all_mottos():
    """Generate all 20 business cards with different mottos."""
    output_dir = 'business_cards_preview'
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("  Generating 20 Business Cards at 600 DPI")
    print("=" * 60)
    print()

    for i, motto in enumerate(MOTTOS, 1):
        print(f"\n[{i:02d}/20] {motto[:45]}...")
        card = generate_card_600dpi(motto)
        if card:
            safe_motto = motto[:40].replace(' ', '_').replace("'", '').replace('.', '').replace(',', '')
            filename = f'{output_dir}/card_{i:02d}_{safe_motto}.png'
            card.save(filename, 'PNG', dpi=(DPI, DPI))
            print(f"        -> {filename}")

    print()
    print("=" * 60)
    print(f"  [OK] Generated {len(MOTTOS)} cards to {output_dir}/")
    print("=" * 60)


def main():
    print("=" * 60)
    print("  Business Card Print Test - 600 DPI Color")
    print("=" * 60)
    print()
    print(f"  Resolution: {CARD_WIDTH}x{CARD_HEIGHT} @ {DPI} DPI")
    print(f"  Print Service: {PRINT_SERVICE_URL}")
    print(f"  Printer ID: {PRINTER_ID}")
    print()

    # Generate card
    card = generate_card_600dpi()

    if card is None:
        print("[ERROR] Card generation failed")
        return

    # Save locally for reference
    save_card(card)

    # Print
    if '--no-print' not in sys.argv:
        result = print_card(card)

        if result.get('success'):
            print("\n" + "=" * 60)
            print("  [SUCCESS] Business card printed at 600 DPI!")
            print("=" * 60)
        else:
            print("\n[WARN] Card saved locally but print failed")
            print("  Run with --no-print to skip printing")
    else:
        print("\n[INFO] Skipped printing (--no-print flag)")


if __name__ == '__main__':
    try:
        import qrcode
    except ImportError:
        print("Installing qrcode module...")
        os.system('pip install qrcode[pil]')
        import qrcode

    main()
