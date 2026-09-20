#!/usr/bin/env python3
"""
HyperOS Safe Debloat
Non-destructive debloater, telemetry neutralizer, and audit tool for Xiaomi HyperOS and MIUI.
Designed for both human operators and automated agents over ADB without root.
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

# Exit codes for agentic workflows
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_NO_DEVICE = 2

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
        return "", "ADB binary not found", EXIT_ERROR


def check_device_connected(adb_bin):
    """Verify that an authorized device is online."""
    out, _, code = run_adb(adb_bin, ["get-state"])
    return code == 0 and "device" in out


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
        try:
            urllib.request.urlretrieve(UAD_URL, UAD_LOCAL_FILE)
        except Exception:
            return {}

    try:
        with open(UAD_LOCAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def sync_uad():
    """Force refresh UAD-NG database from GitHub."""
    try:
        urllib.request.urlretrieve(UAD_URL, UAD_LOCAL_FILE)
        size_kb = UAD_LOCAL_FILE.stat().st_size / 1024
        return {"status": "success", "file": str(UAD_LOCAL_FILE), "size_kb": round(size_kb, 1)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


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
        return AUDITED_PRESETS

    installed = get_installed_packages(adb_bin)
    uad_targets = {
        "UAD-NG Recommended (OEM)": [],
        "UAD-NG Recommended (Carrier)": [],
        "UAD-NG Recommended (Misc / Diagnostics)": [],
    }

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


def get_device_status(adb_bin, source="uad"):
    """Programmatic API: Gather status of all tracked packages."""
    info = get_device_info(adb_bin)
    targets = get_target_packages(adb_bin, source=source)

    results = {
        "device": info,
        "source": source,
        "categories": {},
        "summary": {"total": 0, "enabled": 0, "disabled": 0, "appops_restricted": 0, "not_found": 0},
    }

    for category, pkgs in targets.items():
        results["categories"][category] = []
        for pkg, desc in pkgs:
            state = get_package_state(adb_bin, pkg)
            appops_blocked = check_appops_restricted(adb_bin, pkg)

            status = "not_found"
            if state == "DISABLED":
                status = "disabled"
                results["summary"]["disabled"] += 1
            elif appops_blocked:
                status = "appops_restricted"
                results["summary"]["appops_restricted"] += 1
            elif state == "ENABLED":
                status = "enabled"
                results["summary"]["enabled"] += 1
            else:
                results["summary"]["not_found"] += 1

            results["summary"]["total"] += 1
            results["categories"][category].append({
                "package": pkg,
                "status": status,
                "description": desc,
            })

    return results


def apply_debloat(adb_bin, source="uad", dry_run=False):
    """Programmatic API: Apply safe debloat rules with AppOps fallback."""
    info = get_device_info(adb_bin)
    targets = get_target_packages(adb_bin, source=source)

    log = []
    actions_taken = {"disabled": 0, "appops_restricted": 0, "skipped": 0, "already_disabled": 0}

    for category, pkgs in targets.items():
        for pkg, _ in pkgs:
            if pkg in HARDWARE_WHITELIST:
                actions_taken["skipped"] += 1
                log.append({"package": pkg, "action": "skipped_whitelist", "reason": "protected hardware"})
                continue

            state = get_package_state(adb_bin, pkg)
            if state == "DISABLED":
                actions_taken["already_disabled"] += 1
                log.append({"package": pkg, "action": "noop", "reason": "already disabled"})
                continue

            if dry_run:
                log.append({"package": pkg, "action": "dry_run", "reason": "would disable or restrict"})
                continue

            # Step 1: Try AOSP user disable
            out, err, code = run_adb(adb_bin, ["shell", "pm", "disable-user", "--user", "0", pkg])
            if code == 0 and "disabled-user" in out.lower():
                actions_taken["disabled"] += 1
                log.append({"package": pkg, "action": "disabled_user", "method": "pm disable-user"})
            else:
                # Step 2: AppOps Fallback
                run_adb(adb_bin, ["shell", "cmd", "appops", "set", pkg, "RUN_IN_BACKGROUND", "ignore"])
                run_adb(adb_bin, ["shell", "cmd", "appops", "set", pkg, "RUN_ANY_IN_BACKGROUND", "ignore"])
                run_adb(adb_bin, ["shell", "cmd", "appops", "set", pkg, "WAKE_LOCK", "ignore"])
                actions_taken["appops_restricted"] += 1
                log.append({"package": pkg, "action": "appops_restricted", "method": "appops freeze"})

    return {
        "device": info,
        "source": source,
        "dry_run": dry_run,
        "actions": actions_taken,
        "details": log,
    }


def restore_packages(adb_bin, source="all"):
    """Programmatic API: Restore all modified packages to enabled state."""
    targets = get_target_packages(adb_bin, source=source)
    restored = []

    for category, pkgs in targets.items():
        for pkg, _ in pkgs:
            state = get_package_state(adb_bin, pkg)
            if state == "DISABLED":
                run_adb(adb_bin, ["shell", "pm", "enable", pkg])
            run_adb(adb_bin, ["shell", "cmd", "appops", "set", pkg, "RUN_IN_BACKGROUND", "default"])
            run_adb(adb_bin, ["shell", "cmd", "appops", "set", pkg, "RUN_ANY_IN_BACKGROUND", "default"])
            run_adb(adb_bin, ["shell", "cmd", "appops", "set", pkg, "WAKE_LOCK", "default"])
            restored.append(pkg)

    return {"status": "restored", "count": len(restored), "packages": restored}


def run_dexopt(adb_bin):
    """Programmatic API: Trigger AOSP bg-dexopt-job."""
    out, err, code = run_adb(adb_bin, ["shell", "cmd", "package", "bg-dexopt-job"])
    return {"status": "completed" if code == 0 else "failed", "output": out, "error": err}


def scan_spyware(adb_bin):
    """Programmatic API: Run MVT forensic scan."""
    try:
        from mvt.common.indicators import Indicators
    except ImportError:
        return {"status": "error", "message": "mvt package is not installed (pip install mvt)"}

    ind = Indicators()
    ind._load_downloaded_indicators()

    out, _, _ = run_adb(adb_bin, ["shell", "pm", "list", "packages", "-u"])
    packages = [line.replace("package:", "").strip() for line in out.splitlines() if line.startswith("package:")]
    pkg_matches = [pkg for pkg in packages if ind.check_app_id(pkg)]

    out_ps, _, _ = run_adb(adb_bin, ["shell", "ps", "-A"])
    procs = [line.split()[8] for line in out_ps.splitlines() if len(line.split()) >= 9]
    proc_matches = [p for p in procs if ind.check_process(p) and p != "gatekeeperd"]

    return {
        "status": "clean" if (not pkg_matches and not proc_matches) else "threat_detected",
        "total_iocs_loaded": ind.total_ioc_count,
        "packages_scanned": len(packages),
        "package_matches": pkg_matches,
        "processes_scanned": len(procs),
        "process_matches": proc_matches,
    }


def audit_apk(adb_bin, package_name):
    """Programmatic API: Extract and inspect target APK."""
    out, _, _ = run_adb(adb_bin, ["shell", "pm", "path", package_name])
    if not out:
        return {"status": "not_found", "package": package_name}

    apk_remote_path = out.splitlines()[0].replace("package:", "").strip()
    out_dir = Path("audit_apks")
    out_dir.mkdir(exist_ok=True)
    local_apk = out_dir / f"{package_name}.apk"

    run_adb(adb_bin, ["pull", apk_remote_path, str(local_apk)])
    if not local_apk.exists():
        return {"status": "pull_failed", "package": package_name}

    size_mb = local_apk.stat().st_size / (1024 * 1024)
    res_data = {
        "status": "extracted",
        "package": package_name,
        "remote_path": apk_remote_path,
        "local_path": str(local_apk),
        "size_mb": round(size_mb, 2),
    }

    droidasc_bin = shutil.which("droidasc")
    if droidasc_bin:
        res = subprocess.run([droidasc_bin, "getmanifest", str(local_apk)], capture_output=True, text=True)
        if res.returncode == 0:
            res_data["manifest_snippet"] = res.stdout[:1000]

    return res_data


def main():
    parser = argparse.ArgumentParser(
        description="Non-destructive debloater and auditor for Xiaomi HyperOS devices. Supports JSON output for automated agents."
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
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit pure, parseable JSON for automated agents",
    )
    args = parser.parse_args()

    if args.action == "sync-uad":
        res = sync_uad()
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"[*] Sync result: {res}")
        sys.exit(EXIT_SUCCESS if res.get("status") == "success" else EXIT_ERROR)

    adb_bin = find_adb()
    if not check_device_connected(adb_bin):
        err = {"status": "error", "error": "No authorized ADB device connected"}
        if args.json:
            print(json.dumps(err, indent=2))
        else:
            print("[!] Error: No authorized ADB device detected. Connect phone and enable USB Debugging.")
        sys.exit(EXIT_NO_DEVICE)

    if args.action == "status":
        res = get_device_status(adb_bin, source=args.source)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            info = res["device"]
            print("=" * 65)
            print(f" Device: {info['manufacturer']} {info['model']} (Android {info['version']})")
            print(f" Security Patch: {info['patch']}")
            print(f" Source: {res['source'].upper()}")
            print(f" Summary: {res['summary']}")
            print("=" * 65)
            for cat, items in res["categories"].items():
                print(f"\n[ {cat} ] ({len(items)})")
                for it in items:
                    tag = it["status"].upper()
                    print(f"  [{tag:<17}] {it['package']}")
        sys.exit(EXIT_SUCCESS)

    elif args.action == "debloat":
        res = apply_debloat(adb_bin, source=args.source, dry_run=args.dry_run)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"[*] Debloat completed. Actions: {res['actions']}")
            for item in res["details"]:
                print(f"  {item['action'].upper():<17} {item['package']}")
        sys.exit(EXIT_SUCCESS)

    elif args.action == "restore":
        res = restore_packages(adb_bin, source=args.source)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"[*] Restored {res['count']} packages.")
        sys.exit(EXIT_SUCCESS)

    elif args.action == "dexopt":
        res = run_dexopt(adb_bin)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"[*] Dexopt status: {res['status']}")
        sys.exit(EXIT_SUCCESS)

    elif args.action == "scan-spyware":
        res = scan_spyware(adb_bin)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"[*] MVT Scan Result: {res['status']}")
            print(f"    Scanned: {res['packages_scanned']} packages, {res['processes_scanned']} processes")
            print(f"    Threats: packages={res['package_matches']}, processes={res['process_matches']}")
        sys.exit(EXIT_SUCCESS if res.get("status") == "clean" else EXIT_ERROR)

    elif args.action == "audit-apk":
        if not args.package:
            err = {"status": "error", "message": "Missing package argument"}
            if args.json:
                print(json.dumps(err, indent=2))
            else:
                print("[!] Error: Specify package name (e.g. audit-apk com.xiaomi.joyose)")
            sys.exit(EXIT_ERROR)
        res = audit_apk(adb_bin, args.package)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"[*] Extracted: {res}")
        sys.exit(EXIT_SUCCESS)


if __name__ == "__main__":
    main()
