# EGS Print Service

## Project Status: ACTIVE — Extracted from fairmont-calcmenu-labels

## What This Is
Standalone multi-brand printer management service. Runs on hotel/site PCs, receives print jobs from CalcMenu, PrepControl, or any EGS product over HTTP.

## Products That Use This
- **CalcMenu ESL** (fairmont-calcmenu-labels) — Evolis badge printing
- **PrepControl** (prepcontrol) — Zebra/Gainsha prep label printing (planned)
- **CalcWaste** (waste-control) — Waste tracking label printing (planned)

## Supported Printers
| Brand | Protocol | Handler | Use Case |
|-------|----------|---------|----------|
| Evolis (Primacy 2, Zenius) | Win32 GDI | `evolis` | Badge/card printing |
| Zebra | ZPL | `zpl` | Prep labels, shelf labels |
| CAB | ZPL emulation | `zpl` | Prep labels |
| SATO | SBPL | `sbpl` | Industrial labels |
| Star | ESC/POS | `escpos` | Thermal receipts |
| Epson | ESC/POS | `escpos` | Thermal receipts |
| Gainsha/Gprinter | TSPL | `tspl` | Prep labels (PrepSafe) |
| TSC | TSPL | `tspl` | General labels |

## Architecture
```
CalcMenu / PrepControl / CalcWaste (cloud)
        |
        | HTTP API (port 5100)
        v
EGS Print Service (hotel PC)
        |
        | USB / Network / Bluetooth
        v
Physical Printer
```

## Running
```bash
# As Python module
python -m egs_print_service

# As standalone script
python main.py

# Custom port
EGS_PRINT_PORT=5200 python main.py
```

## API Endpoints
```
GET  /health                          → Service status
GET  /api/printers                    → List all printers
POST /api/printers                    → Register printer
GET  /api/printers/{id}               → Printer details
PUT  /api/printers/{id}               → Update printer
DEL  /api/printers/{id}               → Remove printer
POST /api/printers/{id}/print         → Submit print job
GET  /api/printers/{id}/status        → Printer status
POST /api/printers/{id}/test          → Test connection
GET  /api/jobs                        → Job history
GET  /api/discover                    → Auto-discover printers
```

### Legacy endpoints (backward compatible with evolis_print_agent)
```
POST /print                           → Print to default Evolis
GET  /printers                        → List Windows printers
GET  /evolis/power/status             → Evolis status
POST /evolis/power/wake               → Wake Evolis
```

## Python Client SDK
```python
from egs_print_service.client import PrintClient

client = PrintClient('http://192.168.1.100:5100', api_key='egs-print-2026')

# List printers
printers = client.list_printers()

# Print image
with open('label.png', 'rb') as f:
    result = client.print_image('PRINTER-ID', f.read())
```

## Configuration
| Env Var | Default | Description |
|---------|---------|-------------|
| `EGS_PRINT_PORT` | 5100 | HTTP port |
| `EGS_PRINT_HOST` | 0.0.0.0 | Bind address |
| `EGS_PRINT_API_KEY` | egs-print-2026 | API authentication key |
| `EGS_PRINT_DATA_DIR` | ~/.egs_print_service | Printer config storage |
| `EGS_PRINT_DEBUG` | false | Debug mode |

## Origin
Extracted from `fairmont-calcmenu-labels/egs_print_service/` on 2026-01-31. The fairmont copy is now deprecated — all development happens here.

## File Structure
```
egs-print-service/
├── main.py                    ← Standalone entry point
├── requirements.txt           ← Dependencies
├── egs_print_service/         ← Python package
│   ├── __init__.py
│   ├── __main__.py            ← python -m entry point
│   ├── app.py                 ← Flask app + all routes
│   ├── config.py              ← Configuration
│   ├── client.py              ← Python SDK for callers
│   ├── handlers/
│   │   ├── base.py            ← Abstract base handler
│   │   ├── evolis.py          ← Evolis (Win32 GDI)
│   │   ├── zpl.py             ← Zebra/CAB (ZPL)
│   │   ├── sbpl.py            ← SATO (SBPL)
│   │   ├── escpos.py          ← Star/Epson (ESC/POS)
│   │   └── tspl.py            ← Gainsha/TSC (TSPL)
│   ├── models/
│   │   ├── printer.py         ← Printer model
│   │   └── job.py             ← Print job model
│   └── web/
│       └── index.html         ← Dashboard UI
└── CLAUDE.md
```

## Key Design Decisions
- **HTTP API, not Python library** — products call this over HTTP, not via pip import. This keeps printer drivers (win32, USB) isolated on the hotel PC.
- **Handler pattern** — each printer protocol is a separate handler class inheriting from BaseHandler. Adding a new printer = one new handler file.
- **Legacy compatibility** — old `/print` endpoint still works so existing evolis_print_agent deployments switch seamlessly.
- **Local file storage** — printer config saved to `~/.egs_print_service/printers.json`. No database required.

## Deployment
On hotel PCs: PyInstaller builds a single `.exe` that runs as a Windows service or tray app. Each EGS product connects to `http://localhost:5100` (or the PC's LAN IP for remote printing).
