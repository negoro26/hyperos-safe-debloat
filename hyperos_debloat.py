#!/usr/bin/env python3
"""
HyperOS Safe Debloat
Non-destructive debloater & telemetry neutralizer for Xiaomi HyperOS / MIUI devices.
Works on Android 14, 15, and 16 without root.
"""

import argparse
import shutil
import subprocess
import sys

# Presets of verified safe bloatware and telemetry packages
TARGET_PACKAGES = {
    "Ad Networks & Commercial Telemetry": [
        ("com.xiaomi.joyose", "OneTrack analytics, cloud profiles, GPU/thermal throttling (AppOps neutralized)"),
        ("com.miui.android.fashiongallery", "Wallpaper Carousel / Glance lockscreen ad network"),
        ("com.amazon.appmanager", "Amazon preload telemetry stub"),
        ("com.mi.global.bbs", "Xiaomi Community app"),
        ("com.miui.audiomonitor", "Background audio recording monitor service"),
    ],
    "Factory, Diagnostic & Hardware Loggers": [
        ("com.bsp.logmanager", "Board Support Package hardware logging daemon"),
        ("com.debug.loggerui", "MediaTek graphical debugging interface"),
        ("com.mi.AutoTest", "Factory assembly testing suite"),
        ("com.wing.wtsarcontrol", "Wingtech SAR control daemon"),
        ("com.wingtech.sartest", "Wingtech SAR RF test tool"),
        ("com.mediatek.engineermode", "MediaTek Engineer Mode testing utility"),
        ("com.mediatek.lbs.em2.ui", "MediaTek GPS diagnostic tool"),
        ("com.mediatek.ygps", "MediaTek YGPS test utility"),
        ("com.xiaomi.mtb", "Modem Test Box (baseband diagnostic tool)"),
    ],
    "Unused Secondary Services": [
        ("com.wdstechnology.android.kryten", "WDS Carrier OTA configuration client"),
        ("com.miui.vsimcore", "Virtual SIM core service"),
        ("com.miui.thirdappassistant", "Third-party app assistant daemon"),
        ("com.xiaomi.barrage", "Bullet screen notifications"),
        ("com.xiaomi.aiasst.vision", "AI assistant vision daemon"),
    ],
}

# Explicitly protected hardware and security packages that must NEVER be touched
HARDWARE_WHITELIST = {
    "com.goodix.fingerprint.setting",
    "com.fingerprints.optical",
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
    import os
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
    """Run an ADB command and return stdout string."""
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


def cmd_status(adb_bin):
    """Print the current status of all tracked packages."""
    info = get_device_info(adb_bin)
    print("=" * 65)
    print(f" Device: {info['manufacturer']} {info['model']} (Android {info['version']})")
    print(f" Security Patch: {info['patch']}")
    print("=" * 65)

    for category, pkgs in TARGET_PACKAGES.items():
        print(f"\n[ {category} ]")
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
            print(f"    └─ {desc}")


def cmd_debloat(adb_bin, dry_run=False):
    """Safely disable or neutralize bloatware packages."""
    info = get_device_info(adb_bin)
    print(f"[*] Target Device: {info['manufacturer']} {info['model']} (Android {info['version']})")
    if dry_run:
        print("[*] Running in DRY-RUN mode. No changes will be made.\n")
    else:
        print("[*] Applying safe Zero-Uninstall debloat...\n")

    for category, pkgs in TARGET_PACKAGES.items():
        print(f"\n--- {category} ---")
        for pkg, _ in pkgs:
            if pkg in HARDWARE_WHITELIST:
                print(f"  [SKIPPED] {pkg} (Protected hardware/biometric component)")
                continue

            state = get_package_state(adb_bin, pkg)
            if state == "DISABLED":
                print(f"  [ALREADY DISABLED] {pkg}")
                continue

            if dry_run:
                print(f"  [WOULD DISABLE/RESTRICT] {pkg}")
                continue

            # Attempt 1: Standard AOSP user disable
            out, err, code = run_adb(adb_bin, ["shell", "pm", "disable-user", "--user", "0", pkg])
            if code == 0 and "disabled-user" in out.lower():
                print(f"  \033[92m[OK DISABLED]\033[0m {pkg}")
            else:
                # Attempt 2: Zero-Uninstall AppOps Fallback for Android 14/15/16 protected packages
                print(f"  \033[93m[APPOPS FALLBACK]\033[0m {pkg} (Protected system package - freezing background)")
                run_adb(adb_bin, ["shell", "cmd", "appops", "set", pkg, "RUN_IN_BACKGROUND", "ignore"])
                run_adb(adb_bin, ["shell", "cmd", "appops", "set", pkg, "RUN_ANY_IN_BACKGROUND", "ignore"])
                run_adb(adb_bin, ["shell", "cmd", "appops", "set", pkg, "WAKE_LOCK", "ignore"])

    print("\n[*] Debloat operation completed safely.")


def cmd_restore(adb_bin):
    """Restore all modified packages to enabled/default state."""
    print("[*] Restoring packages to default state...\n")
    for category, pkgs in TARGET_PACKAGES.items():
        for pkg, _ in pkgs:
            state = get_package_state(adb_bin, pkg)
            if state == "DISABLED":
                run_adb(adb_bin, ["shell", "pm", "enable", pkg])
                print(f"  [RE-ENABLED] {pkg}")
            # Reset AppOps
            run_adb(adb_bin, ["shell", "cmd", "appops", "set", pkg, "RUN_IN_BACKGROUND", "default"])
            run_adb(adb_bin, ["shell", "cmd", "appops", "set", pkg, "RUN_ANY_IN_BACKGROUND", "default"])
            run_adb(adb_bin, ["shell", "cmd", "appops", "set", pkg, "WAKE_LOCK", "default"])
    print("\n[*] All packages and permissions restored.")


def cmd_dexopt(adb_bin):
    """Run the official AOSP profile-guided background dexopt job."""
    print("[*] Triggering official AOSP profile-guided optimization (bg-dexopt-job)...")
    out, err, code = run_adb(adb_bin, ["shell", "cmd", "package", "bg-dexopt-job"])
    print(out if out else "Dexopt triggered.")


def main():
    parser = argparse.ArgumentParser(
        description="Non-destructive, safe debloater for Xiaomi HyperOS / MIUI devices."
    )
    parser.add_argument(
        "action",
        choices=["status", "debloat", "restore", "dexopt"],
        help="Action to perform: status (inspect), debloat (disable), restore (re-enable), dexopt (AOSP profile compile)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without executing",
    )
    args = parser.parse_args()

    adb_bin = find_adb()
    # Verify device connection
    out, _, _ = run_adb(adb_bin, ["get-state"])
    if "device" not in out:
        print("[!] Error: No authorized ADB device detected. Please connect phone and enable USB Debugging.")
        sys.exit(1)

    if args.action == "status":
        cmd_status(adb_bin)
    elif args.action == "debloat":
        cmd_debloat(adb_bin, dry_run=args.dry_run)
    elif args.action == "restore":
        cmd_restore(adb_bin)
    elif args.action == "dexopt":
        cmd_dexopt(adb_bin)


if __name__ == "__main__":
    main()
