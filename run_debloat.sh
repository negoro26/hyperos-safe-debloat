#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "========================================================"
echo "        HyperOS Safe Debloater (Android 14-16)"
echo "========================================================"
echo ""
echo "[1] Check package status"
echo "[2] Preview changes (Dry-Run)"
echo "[3] Apply Safe Debloat (Disable + AppOps Fallback)"
echo "[4] Run MVT Forensic Spyware Scan"
echo "[5] Audit an installed APK with Droid ASC"
echo "[6] Trigger AOSP Profile-Guided Dexopt"
echo "[7] Restore / Re-enable all packages"
echo "[8] Exit"
echo ""

read -p "Select option (1-8): " choice

case "$choice" in
  1) python3 hyperos_debloat.py status ;;
  2) python3 hyperos_debloat.py debloat --dry-run ;;
  3) python3 hyperos_debloat.py debloat ;;
  4) python3 hyperos_debloat.py scan-spyware ;;
  5)
     read -p "Enter package name (e.g. com.xiaomi.joyose): " pkg
     python3 hyperos_debloat.py audit-apk "$pkg"
     ;;
  6) python3 hyperos_debloat.py dexopt ;;
  7) python3 hyperos_debloat.py restore ;;
  8) exit 0 ;;
  *) echo "Invalid option" ;;
esac
