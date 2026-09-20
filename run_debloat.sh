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
echo "[4] Trigger AOSP Profile-Guided Dexopt"
echo "[5] Restore / Re-enable all packages"
echo "[6] Exit"
echo ""

read -p "Select option (1-6): " choice

case "$choice" in
  1) python3 hyperos_debloat.py status ;;
  2) python3 hyperos_debloat.py debloat --dry-run ;;
  3) python3 hyperos_debloat.py debloat ;;
  4) python3 hyperos_debloat.py dexopt ;;
  5) python3 hyperos_debloat.py restore ;;
  6) exit 0 ;;
  *) echo "Invalid option" ;;
esac
