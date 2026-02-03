# EGS Print Service

Standalone multi-brand printer management service for label and badge printing.

## Features

- **Multi-brand support**: Evolis, Zebra, CAB, SATO, Star, Epson, Gainsha/Gprinter, TSC, PrepSafe
- **Protocol handlers**: ZPL, SBPL, ESC/POS, TSPL, Windows drivers
- **Power management**: Sleep timeout, wake, reboot, LED flash (Evolis)
- **Web dashboard**: Built-in management UI
- **REST API**: Full CRUD for printers and jobs
- **Python SDK**: Easy integration for other applications
- **Backward compatible**: Works with existing `evolis_print_agent` endpoints

## Quick Start

### Run the Service

```bash
# From project root
python -m egs_print_service

# Or with custom port
EGS_PRINT_PORT=5200 python -m egs_print_service
```

### Access Dashboard

Open browser to: `http://localhost:5100/`

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EGS_PRINT_PORT` | `5100` | Server port |
| `EGS_PRINT_HOST` | `0.0.0.0` | Bind address |
| `EGS_PRINT_API_KEY` | `egs-print-2026` | API key for authentication |
| `EGS_PRINT_DATA_DIR` | `~/.egs_print_service` | Data storage directory |
| `EGS_PRINT_DEBUG` | `false` | Enable debug mode |

## Supported Printers

| Brand | Protocol | Handler | Connection | Features |
|-------|----------|---------|------------|----------|
| **Evolis** | Win32 | `evolis` | USB | Power management, CR-80 badges |
| **Zebra** | ZPL | `zpl` | Network (9100) | Labels, barcodes, images |
| **CAB** | ZPL | `zpl` | Network (9100) | ZPL emulation mode |
| **SATO** | SBPL | `sbpl` | Network (9100) | Labels, barcodes |
| **Star** | ESC/POS | `escpos` | Network (9100) | Thermal receipts, labels |
| **Epson** | ESC/POS | `escpos` | Network (9100) | Thermal receipts, labels |
| **Gainsha/Gprinter** | TSPL | `tspl` | Network, USB, Bluetooth | Food labels, barcodes |
| **TSC** | TSPL | `tspl` | Network (9100) | Labels, barcodes |
| **PrepSafe** | TSPL | `tspl` | Network, USB, Bluetooth | Food safety labels |

### TSPL Printers (Gainsha, TSC, PrepSafe)

TSPL (TSC Printer Language) is a command language used by many thermal label printers. The following models are supported:

- **Gainsha/Gprinter**: GS-2208, GS-2406T, GS-2408D, GI-2408T, GE-2406T
- **TSC**: All TSPL-compatible models
- **PrepSafe**: Food safety label printers (uses Gainsha hardware)

**Special Features:**

- `print_food_label()` - PrepSafe-style food safety labels with allergens, date, prep info
- `calibrate()` - Auto-detect label size and gap
- QR codes and barcodes (Code128, Code39, EAN13, UPC-A)

## API Reference

### Health & Info

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/` | GET | No | Web dashboard |
| `/health` | GET | No | Health check with system info |
| `/api` | GET | No | API info (JSON) |
| `/api/discover` | GET | No | Auto-discover printers |

### Printer Management

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/printers` | GET | No | List all printers |
| `/api/printers?status=true` | GET | No | List printers with online/offline check |
| `/api/printers/status` | GET | No | Quick status check for ALL printers |
| `/api/printers` | POST | Yes | Add new printer |
| `/api/printers/{id}` | GET | No | Get printer details |
| `/api/printers/{id}` | PUT | Yes | Update printer |
| `/api/printers/{id}` | DELETE | Yes | Delete printer |
| `/api/printers/{id}/test` | POST | No | Test connection (quick TCP check) |
| `/api/printers/{id}/status` | GET | No | Detailed printer status (paper, ribbon, etc.) |

### Check if Printers are Online

**Quick check all printers:**
```bash
curl http://localhost:5100/api/printers/status
```

**Response:**
```json
{
  "success": true,
  "printers": [
    {"id": "...", "name": "Kitchen Zebra", "is_online": true, "status": "online"},
    {"id": "...", "name": "Badge Printer", "is_online": false, "status": "offline"}
  ],
  "summary": {"total": 2, "online": 1, "offline": 1}
}
```

**List printers with status:**
```bash
curl "http://localhost:5100/api/printers?status=true"
```

### Printing

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/printers/{id}/print` | POST | Yes | Submit print job |

**Request body:**
```json
{
    "api_key": "your-api-key",
    "image_base64": "base64-encoded-image",
    "document_name": "Job Name",
    "copies": 1,
    "options": {}
}
```

### Power Management (Evolis Only)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/printers/{id}/power/sleep-timeout` | GET | No | Get sleep timeout |
| `/api/printers/{id}/power/sleep-timeout` | POST | Yes | Set sleep timeout |
| `/api/printers/{id}/power/wake` | POST | Yes | Wake from sleep |
| `/api/printers/{id}/power/reboot` | POST | Yes | Soft reboot |
| `/api/printers/{id}/power/led-flash` | POST | Yes | Flash LED to identify |

### Job History

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/jobs` | GET | No | List recent jobs |
| `/api/jobs?printer_id=X` | GET | No | Filter by printer |
| `/api/jobs?limit=N` | GET | No | Limit results |

### Legacy Endpoints (Backward Compatibility)

These endpoints maintain compatibility with `evolis_print_agent`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/print` | POST | Print to default Evolis |
| `/printers` | GET | List Windows printers |
| `/evolis/power/sleep-timeout` | GET/POST | Sleep timeout |
| `/evolis/power/wake` | POST | Wake printer |
| `/evolis/power/status` | GET | Printer status |
| `/evolis/power/reboot` | POST | Reboot printer |
| `/evolis/power/led-flash` | POST | Flash LED |

## Python SDK

### Installation

```python
# The client is included in the package
from egs_print_service.client import PrintClient
```

### Usage

```python
from egs_print_service.client import PrintClient

# Connect to service
client = PrintClient('http://localhost:5100', api_key='egs-print-2026')

# Check health
if client.is_online():
    print("Service is online")

# List printers
printers = client.list_printers()
for p in printers:
    print(f"{p['name']} - {p['status']}")

# Add a printer
result = client.add_printer(
    name='Kitchen Zebra',
    printer_type='zebra',
    connection_mode='network',
    host='192.168.1.100',
    port=9100,
    location='Main Kitchen'
)

# Print an image
with open('badge.png', 'rb') as f:
    result = client.print_image('PRINTER-ID', f.read())

# Power management (Evolis)
client.set_sleep_timeout('PRINTER-ID', 30)  # 30 minutes
client.wake('PRINTER-ID')
client.flash_led('PRINTER-ID', duration=5)

# Get job history
jobs = client.list_jobs(limit=10)
```

## CalcMenu Integration

The service integrates with CalcMenu for badge printing:

```python
# In CalcMenu routes
from egs_print_service.client import PrintClient

print_client = PrintClient(
    os.environ.get('EGS_PRINT_URL', 'http://localhost:5100'),
    api_key=os.environ.get('EGS_PRINT_API_KEY', 'egs-print-2026')
)

# Print a badge
def print_badge(badge_image_bytes, printer_id=None):
    if printer_id:
        return print_client.print_image(printer_id, badge_image_bytes)
    else:
        # Use default Evolis
        printers = print_client.list_printers()
        evolis = next((p for p in printers if p['printer_type'] == 'evolis'), None)
        if evolis:
            return print_client.print_image(evolis['id'], badge_image_bytes)
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    APPLICATIONS                          │
├─────────────────┬─────────────────┬─────────────────────┤
│  CalcMenu       │  PrepSafe App   │  Other Tools        │
│  (ESL + Badges) │  (Food Safety)  │  (Future)           │
└────────┬────────┴────────┬────────┴──────────┬──────────┘
         │                 │                    │
         └─────────────────┼────────────────────┘
                           │ REST API (HTTP)
                           ▼
┌─────────────────────────────────────────────────────────┐
│          EGS PRINT SERVICE (Port 5100)                  │
├─────────────────────────────────────────────────────────┤
│  Flask App (app.py)                                     │
│  ├── /api/printers     - Printer registry               │
│  ├── /api/jobs         - Job tracking                   │
│  └── Web Dashboard     - Management UI                  │
├─────────────────────────────────────────────────────────┤
│                    PROTOCOL HANDLERS                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │
│  │ Evolis      │ │ ZPL         │ │ ESC/POS     │       │
│  │ (Win32)     │ │ (TCP 9100)  │ │ (TCP 9100)  │       │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘       │
│         │               │               │               │
│  ┌──────┴──────┐ ┌──────┴──────┐ ┌──────┴──────┐       │
│  │ SBPL        │ │             │ │             │       │
│  │ (TCP 9100)  │ │             │ │             │       │
│  └─────────────┘ └─────────────┘ └─────────────┘       │
└─────────────────────────────────────────────────────────┘
          │               │               │
          ▼               ▼               ▼
     ┌─────────┐    ┌─────────┐    ┌─────────┐
     │ USB     │    │ Network │    │ Network │
     │ Evolis  │    │ Zebra   │    │ Star    │
     └─────────┘    └─────────┘    └─────────┘
```

## File Structure

```
egs_print_service/
├── __init__.py           # Package info, version
├── __main__.py           # Entry point
├── app.py                # Flask application
├── config.py             # Configuration
├── client.py             # Python SDK client
├── models/
│   ├── __init__.py
│   ├── printer.py        # Printer data model
│   └── job.py            # PrintJob data model
├── handlers/
│   ├── __init__.py       # Handler registry
│   ├── base.py           # Abstract base class
│   ├── evolis.py         # Evolis (Win32 drivers)
│   ├── zpl.py            # Zebra/CAB (ZPL protocol)
│   ├── escpos.py         # Star/Epson (ESC/POS)
│   └── sbpl.py           # SATO (SBPL protocol)
├── web/
│   └── index.html        # Dashboard UI
└── README.md             # This file
```

## Adding a New Printer Type

1. Create handler in `handlers/`:

```python
# handlers/myprinter.py
from .base import BaseHandler

class MyPrinterHandler(BaseHandler):
    def print_image(self, image_data, **kwargs):
        # Implementation
        pass

    def get_status(self):
        # Implementation
        pass

    def test_connection(self):
        # Implementation
        pass
```

2. Register in `handlers/__init__.py`:

```python
from .myprinter import MyPrinterHandler

HANDLERS = {
    # ...existing handlers...
    'myprinter': MyPrinterHandler,
}
```

3. Add to `config.py`:

```python
PRINTER_TYPES = {
    # ...existing types...
    'myprinter': {
        'name': 'My Printer',
        'handler': 'myprinter',
        'connection': ['network', 'usb'],
        'default_port': 9100,
    },
}
```

## Troubleshooting

### Evolis Not Found

- Ensure Evolis Print Center is installed
- Check printer is connected via USB
- Run service as Administrator for registry access

### Network Printer Timeout

- Verify IP address and port (default: 9100)
- Check firewall allows connection
- Test with: `telnet 192.168.1.100 9100`

### Permission Denied (Sleep Timeout)

- Run service as Administrator
- Or configure via Evolis Print Center directly

## License

Proprietary - EGS Software AG
