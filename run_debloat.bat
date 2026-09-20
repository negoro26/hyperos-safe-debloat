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
echo [4] Trigger AOSP Profile-Guided Dexopt
echo [5] Restore / Re-enable all packages
echo [6] Exit
echo.

set /p choice="Select option (1-6): "

if "%choice%"=="1" python hyperos_debloat.py status
if "%choice%"=="2" python hyperos_debloat.py debloat --dry-run
if "%choice%"=="3" python hyperos_debloat.py debloat
if "%choice%"=="4" python hyperos_debloat.py dexopt
if "%choice%"=="5" python hyperos_debloat.py restore
if "%choice%"=="6" exit /b 0

echo.
pause
