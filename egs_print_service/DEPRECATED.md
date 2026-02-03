# ⚠️ DEPRECATED — Do Not Edit

Development of `egs_print_service` has moved to its own standalone project:

**Location:** `C:\Projects\egs-print-service\`

This copy is frozen as of 2026-01-31. Any changes should be made in the standalone project.

## Why
The print service is shared across multiple EGS products (CalcMenu, PrepControl, CalcWaste). Keeping it inside fairmont-calcmenu-labels meant other products couldn't use it without duplicating code.

## For fairmont-calcmenu-labels
The fairmont app calls the print service over HTTP (port 5100). No code imports needed — it's an API call. The existing `app/services/evolis_agent.py` client already works with the standalone service because the legacy endpoints are backward compatible.
