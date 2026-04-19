# EGS Print Service

## EGS Context

### Azure Key Vault
**Vault:** `kv-egs-automation` (RG `RG-EGS-AUTOMATION`, sub `Microsoft Partner Network Credit 1`)
- Firewall: **Deny by default**. Allowed: VM subnet, VM public IP `51.136.6.54`, Azure trusted services, Marc's workstation IP
- RBAC: Marc = `Secrets Officer`, VM managed identity (`vm-egs-automation`) = `Secrets User` (read-only)
- Diagnostics → `kv-audit-logs` → Log Analytics `log-egs-audit`
- Full inventory: `docs/secrets-inventory.md` in `egs-automation` repo

### Print-specific secrets
- `EGS-PRINT-SERVICE-KEY` — local print service API key
- `EGS-PRINT-PC-SSH-PASSWORD` — Print PC SSH (192.168.1.39)
- `PRINTNODE-API-KEY` — cloud printing service

### Secret naming
**`UPPERCASE-WITH-HYPHENS`**, pattern `<SERVICE>-<QUALIFIER>`. Tagged with `service`, `server`, `owner`, `access`, `purpose`, `expires`.

Query: `az keyvault secret list --vault-name kv-egs-automation --query "[?tags.service=='egs-print-service']"`

### Cross-project defaults
| Thing | Default |
|---|---|
| Company | EGS Enggist & Grandjean Software SA (Switzerland) |
| Timezone | Europe/Zurich (CET/CEST) |
| Primary domain | `eg-software.com` |
| Languages | DE / FR / EN |
| VPN | Tailscale (`100.64.0.0/10`) |
| SSH | key-only, no root, port 2222 on hardened boxes |
| SMTP alerts | `alerts@calctag.com` via Infomaniak msmtp |
| Git | GitHub private repos, SSH deploy keys per server |

### Inherited rules
- **Check Azure Key Vault first** before asking for any secret
- Never echo/commit secrets; verify vault writes with read-back
- Never claim success without verification evidence
- Swiss German formal tone for customer emails; English OK for internal

---

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

## Office Network Setup
See [docs/OFFICE_NETWORK_SETUP.md](docs/OFFICE_NETWORK_SETUP.md) for:
- Network device inventory (IPs, MACs, hostnames)
- Printer configuration details
- Intel PC setup (DESKTOP-QVS7KUG at 192.168.1.36)
- Troubleshooting guides

## Working with Claude Code

### What Claude Code does in this project

Claude Code is the AI coding assistant used across all EGS projects. In this repo it:

- Reads and edits Python source files, adds new printer handlers, fixes bugs
- Runs HTTP tests against the local service (`curl http://localhost:5100/...`)
- Writes and runs Python scripts to test printer connectivity
- Updates documentation (`CLAUDE.md`, `docs/OFFICE_NETWORK_SETUP.md`)

### Scope of projects Claude Code manages together

All of these are worked on in the same Claude Code session (shared memory):

| Project | Path | Language | Role |
|---------|------|----------|------|
| egs-print-service | `c:/Projects/egs-print-service` | Python | Local printer HTTP agent |
| egs-print-service-go | `c:/Projects/egs-print-service-go` | Go | Go rewrite (Windows + Android) |
| prepfast-server | `c:/Projects/prepfast-server` | Go | Cloud API for label audit |
| prepfast-web | `c:/Projects/prepfast-web` | React/TS | Admin dashboard + mobile quick-print |

### How Claude Code works

1. **Reads before editing** — always reads a file before changing it
2. **Runs scripts to verify** — uses `curl`, Python, `gh`, `ssh` to test things live
3. **Persistent memory** — saves key facts across sessions in `~/.claude/projects/.../memory/`

Memory files:

- `MEMORY.md` — loaded every session: project overview, credentials, IPs
- `prepfast-server.md` — Go API endpoints, schema, gotchas
- `prepfast-web.md` — React frontend routes, API client, RPCs
- `egs-print-service-go.md` — Go agent architecture, CI, TODO list

### Key credentials & access (in memory, not in code)

- **Supabase project:** `kgudcphfmrojnnerehvb` (shared by all EGS projects)
- **Production VPS:** `ssh -i ~/.ssh/calcmenu-deploy-key.pem ubuntu@84.234.29.96`
- **Office printer PC:** Tailscale `100.97.196.7:5100` (DESKTOP-MHKI961, Neuchâtel)
- **API key for egs-print-service:** `egs-print-2026` (header: `Authorization: Bearer egs-print-2026`)
- **PrepFast API:** `https://prepfast.calcmenu.io`

### How to ask Claude Code for help

- **"Run this"** → Claude Code runs curl/Python scripts to test live
- **"Check the printers"** → Claude Code connects to Tailscale IP and queries the service
- **"Deploy"** → Claude Code runs `./scripts/deploy.sh` and checks logs
- **"Document"** → Claude Code updates CLAUDE.md and memory files
- **"Put on GitHub"** → Claude Code initializes git, creates private repo via `gh`, pushes

## Planned Features

### USB Scale Support (TODO)
Adding support for USB scales to read weight data. Will be exposed via API:
```
GET  /api/scales                    → List connected scales
GET  /api/scales/{id}/weight        → Read current weight
POST /api/scales/{id}/tare          → Tare the scale
```

Potential scale protocols to support:
- HID (generic USB scales)
- Serial/RS-232 scales
- Specific brands: CAS, Ohaus, Adam Equipment

## Security Defaults
These rules apply to every code change. Adapt to the project stack.

**Auth:** Every endpoint needs an explicit auth decision. Validate identity owns the resource.
**Input:** Validate type, range, length, allowlist enums. Reject with 400. Add body size limits.
**Database:** Parameterised queries only. Allowlist enum params before use in WHERE clauses.
**Secrets:** Required env vars fail-fast at startup. All vars documented in .env.example. Never log secrets.
**HTTP:** No wildcard CORS on authenticated endpoints. Set X-Content-Type-Options, X-Frame-Options, HSTS.
**Jobs:** Every background job needs an execution timeout.
