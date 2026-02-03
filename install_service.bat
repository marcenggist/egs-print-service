@echo off
REM ============================================================
REM EGS Print Service - Windows Service Installer
REM ============================================================
REM
REM Run this script as Administrator on the target machine
REM (the machine connected to printers)
REM
REM Prerequisites:
REM   1. Python 3.10+ installed
REM   2. NSSM installed (https://nssm.cc/download)
REM   3. Run this script as Administrator
REM
REM ============================================================

setlocal

set SERVICE_NAME=EGSPrintService
set DISPLAY_NAME=EGS Print Service
set DESCRIPTION=Multi-brand printer management service for label and badge printing
set PORT=5100

echo ============================================================
echo   EGS Print Service - Windows Service Installer
echo ============================================================
echo.

REM Check for admin rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Please run this script as Administrator
    echo         Right-click and select "Run as administrator"
    pause
    exit /b 1
)

REM Check for Python
where python >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

REM Check for NSSM
where nssm >nul 2>&1
if %errorLevel% neq 0 (
    echo [WARN] NSSM not found in PATH
    echo.
    echo Please install NSSM:
    echo   1. Download from https://nssm.cc/download
    echo   2. Extract nssm.exe to C:\Windows\System32
    echo   OR
    echo   Run: winget install nssm
    echo.
    pause
    exit /b 1
)

REM Get Python path
for /f "delims=" %%i in ('where python') do set PYTHON_PATH=%%i

REM Check if service already exists
sc query %SERVICE_NAME% >nul 2>&1
if %errorLevel% equ 0 (
    echo [INFO] Service already exists. Stopping and removing...
    nssm stop %SERVICE_NAME%
    nssm remove %SERVICE_NAME% confirm
)

REM Install the service
echo [INFO] Installing service...
echo        Python: %PYTHON_PATH%
echo        Port: %PORT%
echo.

nssm install %SERVICE_NAME% "%PYTHON_PATH%" -m egs_print_service
nssm set %SERVICE_NAME% DisplayName "%DISPLAY_NAME%"
nssm set %SERVICE_NAME% Description "%DESCRIPTION%"
nssm set %SERVICE_NAME% Start SERVICE_AUTO_START
nssm set %SERVICE_NAME% AppDirectory "%~dp0"
nssm set %SERVICE_NAME% AppEnvironmentExtra "EGS_PRINT_PORT=%PORT%"

REM Set up logging
nssm set %SERVICE_NAME% AppStdout "%~dp0logs\service.log"
nssm set %SERVICE_NAME% AppStderr "%~dp0logs\error.log"
nssm set %SERVICE_NAME% AppStdoutCreationDisposition 4
nssm set %SERVICE_NAME% AppStderrCreationDisposition 4
nssm set %SERVICE_NAME% AppRotateFiles 1
nssm set %SERVICE_NAME% AppRotateBytes 1048576

REM Create logs directory
if not exist "%~dp0logs" mkdir "%~dp0logs"

REM Start the service
echo [INFO] Starting service...
nssm start %SERVICE_NAME%

REM Check status
timeout /t 2 >nul
sc query %SERVICE_NAME% | findstr "RUNNING" >nul
if %errorLevel% equ 0 (
    echo.
    echo ============================================================
    echo [OK] Service installed and running!
    echo ============================================================
    echo.
    echo   Service Name: %SERVICE_NAME%
    echo   Port: %PORT%
    echo   Dashboard: http://localhost:%PORT%/
    echo.
    echo   Commands:
    echo     Start:   net start %SERVICE_NAME%
    echo     Stop:    net stop %SERVICE_NAME%
    echo     Status:  sc query %SERVICE_NAME%
    echo     Remove:  nssm remove %SERVICE_NAME%
    echo.
    echo   Logs: %~dp0logs\
    echo.
) else (
    echo.
    echo [ERROR] Service may not have started correctly.
    echo         Check logs at: %~dp0logs\
    echo.
)

pause
