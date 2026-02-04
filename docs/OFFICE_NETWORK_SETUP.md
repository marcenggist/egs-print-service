# EGS Print Service - Office Network Setup

**Last Updated:** 2026-02-04
**Network:** 192.168.1.x

## Network Devices

### PCs

| Hostname | IP | Type | Purpose |
|----------|-----|------|---------|
| Laptop7-ME | 192.168.1.35 or .50 | Snapdragon ARM | Dev PC (Claude Code runs here) |
| DESKTOP-QVS7KUG (EGS) | 192.168.1.36 | Intel x64 | Printer PC (USB printers connect here) |
| DESKTOP-MHKI961 | 192.168.1.39 | Unknown | Unknown |

### Printers

| Device | IP | Port | MAC | Protocol | Status |
|--------|-----|------|-----|----------|--------|
| CAB SQUIX Kitchen | 192.168.1.37 | 9100 | 00-02-e7-08-c7-68 | ZPL | Working |
| PrepSafe Food Labels | USB on Intel PC | - | dc:0d:30:20:16:6f | TSPL | Needs setup |
| Canon MF540 | 192.168.1.52 | 9100 | 74-bf-c0-46-17-83 | - | Office printer |

### Other Devices

| Device | IP | MAC | Notes |
|--------|-----|-----|-------|
| Router | 192.168.1.1 | 10-5a-f7-6a-d9-13 | Gateway |
| Netatmo Camera | 192.168.1.33 | 70-ee-50-53-9e-8f | - |
| SOLUM ESL Base | 192.168.1.124 | d0-25-44-21-28-08 | ESL base station |
| Imagotag Service | 192.168.1.36:8000 | - | ESL management |

## EGS Print Service Setup

### Snapdragon PC (Dev - 192.168.1.35)

- Service running on port 5100
- Used for development/testing
- Cannot use USB printers (ARM driver incompatibility)

### Intel PC (DESKTOP-QVS7KUG - 192.168.1.36)

**Status:** Service NOT running - needs to be started

**To Start Service:**
```batch
cd C:\EvolisPrintAgent
python agent.py
```

Or if new EGS Print Service installed:
```batch
python -m egs_print_service
```

**USB Devices to Connect:**
1. PrepSafe/Gprinter label printer (TSPL)
2. USB Scale (to be added)

## Printer Configuration

### CAB SQUIX Kitchen (Network)

- **Type:** ZPL label printer
- **IP:** 192.168.1.37:9100
- **ID in service:** 7BFC181F
- **Status:** Online, working
- **Use case:** Food safety labels

### PrepSafe Food Labels (USB)

- **Type:** TSPL label printer (Gprinter/Gainsha)
- **Connection:** USB to Intel PC
- **MAC:** dc:0d:30:20:16:6f
- **Driver:** Gprinter TSPL (from Seagull/BarTender)
- **Driver URL:** https://www.bartendersoftware.com/resources/printer-drivers/gprinter
- **Status:** Driver installed, needs service running on Intel PC

**Note:** Printer reports IP 192.168.1.100 but network interface not working. Use USB connection instead.

## API Access

### From Dev PC to Intel PC

```bash
# Health check
curl http://192.168.1.36:5100/health

# List printers
curl http://192.168.1.36:5100/api/printers

# Discover USB printers
curl http://192.168.1.36:5100/api/discover

# Register network printer
curl -X POST http://192.168.1.36:5100/api/printers \
  -H "Content-Type: application/json" \
  -d '{"api_key": "egs-print-2026", "name": "CAB SQUIX", "printer_type": "cab", "host": "192.168.1.37", "port": 9100}'

# Print test
curl -X POST http://192.168.1.36:5100/api/printers/{id}/test
```

### API Key

Default: `egs-print-2026`

## TODO

1. [ ] Start EGS Print Service on Intel PC (192.168.1.36)
2. [ ] Register PrepSafe USB printer in service
3. [ ] Test PrepSafe printing
4. [ ] Add USB scale support to service
5. [ ] Set static IP for PrepSafe if network needed later

## Troubleshooting

### PrepSafe Network Not Working

The printer shows IP 192.168.1.100 on its config printout but is not reachable:
- MAC dc:0d:30:20:16:6f not in ARP table
- Likely network interface issue
- **Solution:** Use USB connection instead

### Service Not Starting

1. Check Python is installed: `python --version`
2. Check dependencies: `pip install flask pillow pywin32`
3. Check port 5100 not in use: `netstat -an | findstr 5100`
4. Run with debug: `python -m egs_print_service` (shows errors)

### USB Printer Not Detected

1. Check Windows Settings > Printers
2. Reinstall driver from Seagull/BarTender
3. Try different USB port
4. Check Device Manager for errors
