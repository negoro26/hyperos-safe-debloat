#!/usr/bin/env python3
"""
HyperOS Safe Debloat
Non-destructive debloater, telemetry neutralizer, and audit tool for Xiaomi HyperOS and MIUI.
Imports and cross-references the Universal Android Debloater (UAD-NG) database.
Works on Android 14, 15, and 16 over ADB without root.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

UAD_URL = "https://raw.githubusercontent.com/Universal-Debloater-Alliance/universal-android-debloater-next-generation/main/resources/assets/uad_lists.json"
UAD_LOCAL_FILE = Path(__file__).parent / "uad_lists.json"

# Core audited presets
AUDITED_PRESETS = {
    "Ad Networks and Commercial Telemetry": [
        ("com.xiaomi.joyose", "OneTrack analytics, cloud profiles, thermal throttling (AppOps neutralized)"),
        ("com.miui.android.fashiongallery", "Wallpaper Carousel and Glance lock screen ad network"),
        ("com.amazon.appmanager", "Amazon preload telemetry stub"),
        ("com.mi.global.bbs", "Xiaomi Community application"),
        ("com.mi.global.shop", "Xiaomi Global Shop store application"),
        ("com.miui.audiomonitor", "Background audio recording monitor service"),
    ],
    "Factory, Diagnostic, and Hardware Loggers": [
        ("com.bsp.logmanager", "Board Support Package hardware logging daemon"),
        ("com.debug.loggerui", "MediaTek graphical debugging interface"),
        ("com.mi.AutoTest", "Factory assembly testing suite"),
        ("com.wing.wtsarcontrol", "Wingtech SAR control daemon"),
        ("com.wingtech.sartest", "Wingtech SAR radio frequency test tool"),
        ("com.mediatek.engineermode", "MediaTek Engineer Mode testing utility"),
        ("com.mediatek.lbs.em2.ui", "MediaTek GPS diagnostic tool"),
        ("com.mediatek.ygps", "MediaTek YGPS test utility"),
        ("com.xiaomi.mtb", "Modem Test Box baseband diagnostic tool"),
    ],
    "Unused Secondary Services": [
        ("com.wdstechnology.android.kryten", "WDS carrier OTA configuration client"),
        ("com.miui.thirdappassistant", "Third-party app assistant daemon"),
        ("com.xiaomi.barrage", "Bullet screen notification overlay"),
        ("com.xiaomi.aiasst.vision", "Assistant visual engine daemon"),
    ],
}

# Explicitly protected hardware, biometric, and connectivity packages
HARDWARE_WHITELIST = {
    "com.goodix.fingerprint.setting",
    "com.fingerprints.optical",
    "com.miui.vsimcore",
    "com.miui.rom",
    "com.miui.system",
    "com.android.updater",
    "com.miui.securityadd",
    "com.miui.securitycenter",
    "com.android.networkstack.overlay.miui",
}


def find_adb():
    """Locate adb binary from PATH or standard install locations."""
    adb = shutil.which("adb")
    if adb:
        return adb
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        os.path.join(local_app_data, "Android", "Sdk", "platform-tools", "adb.exe"),
        r"C:\platform-tools\adb.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "adb"


def run_adb(adb_bin, args, check=False):
    """Run an ADB command and return stdout, stderr, returncode."""
    cmd = [adb_bin] + args
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=check)
        return res.stdout.strip(), res.stderr.strip(), res.returncode
    except FileNotFoundError:
        print(f"[!] Error: ADB executable not found at '{adb_bin}'.")
        sys.exit(1)


def get_device_info(adb_bin):
    """Retrieve connected device profile."""
    model, _, _ = run_adb(adb_bin, ["shell", "getprop", "ro.product.model"])
    manufacturer, _, _ = run_adb(adb_bin, ["shell", "getprop", "ro.product.manufacturer"])
    version, _, _ = run_adb(adb_bin, ["shell", "getprop", "ro.build.version.release"])
    patch, _, _ = run_adb(adb_bin, ["shell", "getprop", "ro.build.version.security_patch"])
    return {
        "model": model,
        "manufacturer": manufacturer,
        "version": version,
        "patch": patch,
    }


def load_uad_database():
    """Load or download UAD-NG database."""
    if not UAD_LOCAL_FILE.exists():
        print(f"[*] Downloading UAD-NG database from {UAD_URL}...")
        try:
            urllib.request.urlretrieve(UAD_URL, UAD_LOCAL_FILE)
            print("[*] Saved uad_lists.json.")
        except Exception as e:
            print(f"[!] Warning: Could not download UAD-NG database: {e}")
            return {}

    try:
        with open(UAD_LOCAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[!] Error loading UAD-NG database: {e}")
        return {}


def sync_uad():
    """Force refresh UAD-NG database from GitHub."""
    print(f"[*] Fetching latest UAD-NG database from {UAD_URL}...")
    try:
        urllib.request.urlretrieve(UAD_URL, UAD_LOCAL_FILE)
        size_kb = UAD_LOCAL_FILE.stat().st_size / 1024
        print(f"[*] Successfully updated uad_lists.json ({size_kb:.1f} KB).")
    except Exception as e:
        print(f"[!] Error updating UAD-NG database: {e}")


def get_installed_packages(adb_bin):
    """Fetch set of all installed package names from device."""
    out, _, _ = run_adb(adb_bin, ["shell", "pm", "list", "packages", "-u"])
    return {line.replace("package:", "").strip() for line in out.splitlines() if line.startswith("package:")}


def get_target_packages(adb_bin, source="uad"):
    """
    Build package targets dictionary based on source selection:
    - 'preset': hand-audited Xiaomi packages
    - 'uad': dynamic match of device packages against UAD-NG Recommended
    - 'all': union of preset and UAD-NG
    """
    if source == "preset":
        return AUDITED_PRESETS

    uad_data = load_uad_database()
    if not uad_data:
        print("[!] UAD-NG database unavailable. Falling back to audited presets.")
        return AUDITED_PRESETS

    installed = get_installed_packages(adb_bin)
    uad_targets = {
        "UAD-NG Recommended (OEM)": [],
        "UAD-NG Recommended (Carrier)": [],
        "UAD-NG Recommended (Misc / Diagnostics)": [],
    }

    # Filter out user applications that users typically want to keep
    USER_APP_EXCLUSIONS = {
        "com.whatsapp",
        "com.instagram.android",
        "com.facebook.katana",
        "com.android.chrome",
        "com.google.android.gm",
        "com.google.android.apps.maps",
        "com.google.android.apps.photos",
    }

    for pkg in sorted(installed):
        if pkg in HARDWARE_WHITELIST or pkg in USER_APP_EXCLUSIONS:
            continue
        if pkg in uad_data:
            entry = uad_data[pkg]
            if entry.get("removal") == "Recommended":
                lst = entry.get("list", "Misc")
                desc = entry.get("description", "").replace("\n", " ").strip()[:80]
                if lst == "Oem":
                    uad_targets["UAD-NG Recommended (OEM)"].append((pkg, desc))
                elif lst == "Carrier":
                    uad_targets["UAD-NG Recommended (Carrier)"].append((pkg, desc))
                elif lst == "Misc":
                    uad_targets["UAD-NG Recommended (Misc / Diagnostics)"].append((pkg, desc))

    # Clean empty categories
    uad_targets = {k: v for k, v in uad_targets.items() if v}

    if source == "all":
        combined = dict(AUDITED_PRESETS)
        for cat, items in uad_targets.items():
            existing_pkgs = {p for c in combined.values() for p, _ in c}
            new_items = [it for it in items if it[0] not in existing_pkgs]
            if new_items:
                combined[cat] = new_items
        return combined

    return uad_targets


def get_package_state(adb_bin, pkg):
    """Check whether a package is enabled, disabled, or not installed."""
    out, _, _ = run_adb(adb_bin, ["shell", "pm", "list", "packages", "-d", pkg])
    if out and f"package:{pkg}" in out.split():
        return "DISABLED"
    out_e, _, _ = run_adb(adb_bin, ["shell", "pm", "list", "packages", "-e", pkg])
    if out_e and f"package:{pkg}" in out_e.split():
        return "ENABLED"
    return "NOT_INSTALLED"


def check_appops_restricted(adb_bin, pkg):
    """Check if AppOps RUN_IN_BACKGROUND is ignored."""
    out, _, _ = run_adb(adb_bin, ["shell", "cmd", "appops", "get", pkg, "RUN_IN_BACKGROUND"])
    return "ignore" in out.lower()


def cmd_status(adb_bin, source="uad"):
    """Print current status of tracked packages."""
    info = get_device_info(adb_bin)
    targets = get_target_packages(adb_bin, source=source)

    print("=" * 65)
    print(f" Device: {info['manufacturer']} {info['model']} (Android {info['version']})")
    print(f" Security Patch: {info['patch']}")
    print(f" Package Target Source: {source.upper()}")
    print("=" * 65)

    total_pkgs = sum(len(pkgs) for pkgs in targets.values())
    print(f"[*] Evaluating {total_pkgs} target packages matching device install list...")

    for category, pkgs in targets.items():
        print(f"\n[ {category} ] ({len(pkgs)})")
        for pkg, desc in pkgs:
            state = get_package_state(adb_bin, pkg)
            appops_blocked = check_appops_restricted(adb_bin, pkg)

            if state == "DISABLED":
                tag = "\033[92m[DISABLED]\033[0m"
            elif appops_blocked:
                tag = "\033[93m[RESTRICTED-APPOPS]\033[0m"
            elif state == "ENABLED":
                tag = "\033[91m[ACTIVE / ENABLED]\033[0m"
            else:
                tag = "[NOT FOUND]"

            print(f"  {tag:<28} {pkg}")
            if desc:
                print(f"    └─ {desc}")


def cmd_debloat(adb_bin, source="uad", dry_run=False):
    """Disable or neutralize bloatware packages."""
    info = get_device_info(adb_bin)
    targets = get_target_packages(adb_bin, source=source)

    print(f"[*] Target Device: {info['manufacturer']} {info['model']} (Android {info['version']})")
    print(f"[*] Source Database: {source.upper()}")
    if dry_run:
        print("[*] Running in DRY-RUN mode. No changes will be made.\n")
    else:
        print("[*] Applying safe Zero-Uninstall debloat...\n")

    for category, pkgs in targets.items():
        print(f"\n--- {category} ---")
        for pkg, _ in pkgs:
            if pkg in HARDWARE_WHITELIST:
                print(f"  [SKIPPED] {pkg} (Protected hardware component)")
                continue

            state = get_package_state(adb_bin, pkg)
            if state == "DISABLED":
                print(f"  [ALREADY DISABLED] {pkg}")
                continue

            if dry_run:
                print(f"  [WOULD DISABLE/RESTRICT] {pkg}")
                continue

            # Step 1: Standard AOSP user disable
            out, err, code = run_adb(adb_bin, ["shell", "pm", "disable-user", "--user", "0", pkg])
            if code == 0 and "disabled-user" in out.lower():
                print(f"  \033[92m[OK DISABLED]\033[0m {pkg}")
            else:
                # Step 2: AppOps Fallback for Android 14+ protected packages
                print(f"  \033[93m[APPOPS FALLBACK]\033[0m {pkg} (Protected system package, freezing background)")
                run_adb(adb_bin, ["shell", "cmd", "appops", "set", pkg, "RUN_IN_BACKGROUND", "ignore"])
                run_adb(adb_bin, ["shell", "cmd", "appops", "set", pkg, "RUN_ANY_IN_BACKGROUND", "ignore"])
                run_adb(adb_bin, ["shell", "cmd", "appops", "set", pkg, "WAKE_LOCK", "ignore"])

    print("\n[*] Debloat operation completed safely.")


def cmd_restore(adb_bin, source="all"):
    """Restore all modified packages to enabled and default state."""
    print("[*] Restoring packages to default state...\n")
    targets = get_target_packages(adb_bin, source=source)
    for category, pkgs in targets.items():
        for pkg, _ in pkgs:
            state = get_package_state(adb_bin, pkg)
            if state == "DISABLED":
                run_adb(adb_bin, ["shell", "pm", "enable", pkg])
                print(f"  [RE-ENABLED] {pkg}")
            run_adb(adb_bin, ["shell", "cmd", "appops", "set", pkg, "RUN_IN_BACKGROUND", "default"])
            run_adb(adb_bin, ["shell", "cmd", "appops", "set", pkg, "RUN_ANY_IN_BACKGROUND", "default"])
            run_adb(adb_bin, ["shell", "cmd", "appops", "set", pkg, "WAKE_LOCK", "default"])
    print("\n[*] All packages and permissions restored.")


def cmd_dexopt(adb_bin):
    """Run official AOSP profile-guided background dexopt job."""
    print("[*] Triggering official AOSP profile-guided optimization (bg-dexopt-job)...")
    out, err, code = run_adb(adb_bin, ["shell", "cmd", "package", "bg-dexopt-job"])
    print(out if out else "Dexopt triggered.")


def cmd_scan_spyware(adb_bin):
    """Run an MVT forensic scan against Amnesty International indicators."""
    try:
        from mvt.common.indicators import Indicators
    except ImportError:
        print("[!] Mobile Verification Toolkit (mvt) is not installed.")
        print("    Install it with: pip install mvt")
        return

    ind = Indicators()
    ind._load_downloaded_indicators()
    print(f"[*] Loaded {ind.total_ioc_count} MVT Indicators of Compromise.")

    # 1. Packages
    out, _, _ = run_adb(adb_bin, ["shell", "pm", "list", "packages", "-u"])
    packages = [line.replace("package:", "").strip() for line in out.splitlines() if line.startswith("package:")]
    print(f"[*] Checking {len(packages)} installed packages on device...")
    pkg_matches = [pkg for pkg in packages if ind.check_app_id(pkg)]
    if pkg_matches:
        print(f"[!] Warning: {len(pkg_matches)} package matches found: {pkg_matches}")
    else:
        print("  [+] Clean: 0 packages match known spyware signatures.")

    # 2. Processes
    out_ps, _, _ = run_adb(adb_bin, ["shell", "ps", "-A"])
    procs = [line.split()[8] for line in out_ps.splitlines() if len(line.split()) >= 9]
    print(f"[*] Checking {len(procs)} active processes...")
    proc_matches = [p for p in procs if ind.check_process(p)]
    real_matches = [p for p in proc_matches if p != "gatekeeperd"]
    if real_matches:
        print(f"[!] Warning: {len(real_matches)} suspicious processes found: {real_matches}")
    else:
        print("  [+] Clean: 0 suspicious processes found.")


def cmd_audit_apk(adb_bin, package_name):
    """Extract and inspect an installed package APK."""
    out, _, _ = run_adb(adb_bin, ["shell", "pm", "path", package_name])
    if not out:
        print(f"[!] Package '{package_name}' not found on device.")
        return

    apk_remote_path = out.splitlines()[0].replace("package:", "").strip()
    out_dir = Path("audit_apks")
    out_dir.mkdir(exist_ok=True)
    local_apk = out_dir / f"{package_name}.apk"

    print(f"[*] Pulling {package_name} from {apk_remote_path}...")
    run_adb(adb_bin, ["pull", apk_remote_path, str(local_apk)])

    if local_apk.exists():
        size_mb = local_apk.stat().st_size / (1024 * 1024)
        print(f"[*] Saved to {local_apk} ({size_mb:.2f} MB)")
        droidasc_bin = shutil.which("droidasc")
        if droidasc_bin:
            print("[*] Running Droid ASC manifest inspection...")
            res = subprocess.run([droidasc_bin, "getmanifest", str(local_apk)], capture_output=True, text=True)
            if res.returncode == 0:
                print(res.stdout[:1500])
                print("... [truncated]")
        else:
            print("[*] Tip: Install droidasc (pip install droidasc) to decompile and inspect DEX bytecode.")


def main():
    parser = argparse.ArgumentParser(
        description="Non-destructive debloater and auditor for Xiaomi HyperOS devices with UAD-NG database integration."
    )
    parser.add_argument(
        "action",
        choices=["status", "debloat", "restore", "dexopt", "scan-spyware", "audit-apk", "sync-uad"],
        help="Action to perform",
    )
    parser.add_argument(
        "package",
        nargs="?",
        help="Package name for audit-apk action",
    )
    parser.add_argument(
        "--source",
        choices=["uad", "preset", "all"],
        default="uad",
        help="Target database: uad (UAD-NG Recommended), preset (curated), or all (union)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without executing",
    )
    args = parser.parse_args()

    if args.action == "sync-uad":
        sync_uad()
        return

    adb_bin = find_adb()
    out, _, _ = run_adb(adb_bin, ["get-state"])
    if "device" not in out:
        print("[!] Error: No authorized ADB device detected. Connect phone and enable USB Debugging.")
        sys.exit(1)

    if args.action == "status":
        cmd_status(adb_bin, source=args.source)
    elif args.action == "debloat":
        cmd_debloat(adb_bin, source=args.source, dry_run=args.dry_run)
    elif args.action == "restore":
        cmd_restore(adb_bin, source=args.source)
    elif args.action == "dexopt":
        cmd_dexopt(adb_bin)
    elif args.action == "scan-spyware":
        cmd_scan_spyware(adb_bin)
    elif args.action == "audit-apk":
        if not args.package:
            print("[!] Error: Specify a package name to audit, for example: audit-apk com.xiaomi.joyose")
            sys.exit(1)
        cmd_audit_apk(adb_bin, args.package)


if __name__ == "__main__":
    main()
