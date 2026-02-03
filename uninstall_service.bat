@echo off
REM ============================================================
REM EGS Print Service - Windows Service Uninstaller
REM ============================================================

setlocal

set SERVICE_NAME=EGSPrintService

echo ============================================================
echo   EGS Print Service - Uninstaller
echo ============================================================
echo.

REM Check for admin rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Please run this script as Administrator
    pause
    exit /b 1
)

REM Check if service exists
sc query %SERVICE_NAME% >nul 2>&1
if %errorLevel% neq 0 (
    echo [INFO] Service not found. Nothing to uninstall.
    pause
    exit /b 0
)

echo [INFO] Stopping service...
nssm stop %SERVICE_NAME%

echo [INFO] Removing service...
nssm remove %SERVICE_NAME% confirm

echo.
echo [OK] Service removed successfully.
echo.

pause
