@echo off
setlocal
cd /d "%~dp0"

echo ========================================================
echo         HyperOS Safe Debloater (Android 14-16)
echo ========================================================
echo.
echo [1] Check package status
echo [2] Preview changes (Dry-Run)
echo [3] Apply Safe Debloat (Disable + AppOps Fallback)
echo [4] Run MVT Forensic Spyware Scan
echo [5] Audit an installed APK with Droid ASC
echo [6] Trigger AOSP Profile-Guided Dexopt
echo [7] Restore / Re-enable all packages
echo [8] Exit
echo.

set /p choice="Select option (1-8): "

if "%choice%"=="1" python hyperos_debloat.py status
if "%choice%"=="2" python hyperos_debloat.py debloat --dry-run
if "%choice%"=="3" python hyperos_debloat.py debloat
if "%choice%"=="4" python hyperos_debloat.py scan-spyware
if "%choice%"=="5" (
    set /p pkg="Enter package name (e.g. com.xiaomi.joyose): "
    python hyperos_debloat.py audit-apk %pkg%
)
if "%choice%"=="6" python hyperos_debloat.py dexopt
if "%choice%"=="7" python hyperos_debloat.py restore
if "%choice%"=="8" exit /b 0

echo.
pause
